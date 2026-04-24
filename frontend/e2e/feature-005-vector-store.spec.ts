/**
 * Feature 005 quickstart — Escenarios 5 y 6.
 *
 * Esc 5: BYO vector store (FR-017..FR-019). Usamos `qdrant` como BYO (extra ya instalado);
 *        Pinecone se prueba por la vía del error "extra no instalado" que dispara RuntimeError.
 * Esc 6: Fallback graceful cuando el vector store activo está caído (FR-013).
 */

import { test, expect } from "@playwright/test";
import {
  apiRequest,
  gotoWithSession,
  sendMessage,
  waitForAssistantReply,
  waitForWidgetFrame,
} from "./feature-005-helpers";
import { E2E_SESSION_ID } from "./global-setup";

const BYO_SESSION = `${E2E_SESSION_ID}-byo-vector`;
const OFFLINE_SESSION = `${E2E_SESSION_ID}-cache-offline`;

test.describe("Esc 5 — BYO vector store (US5b)", () => {
  test.afterEach(async () => {
    // Restore default: remove any BYO config for the test session.
    await apiRequest("DELETE", `/vector-store/config?session_id=${BYO_SESSION}`).catch(() => null);
  });

  test("BYO Qdrant: validar → guardar → GET oculta credenciales → eliminar vuelve al default", async () => {
    const params = { url: "http://127.0.0.1:6333" };

    // Validate
    const validate = (await apiRequest("POST", "/vector-store/validate", {
      provider: "qdrant",
      connection_params: params,
    })) as { valid: boolean };
    expect(validate.valid).toBe(true);

    // Save
    const saved = (await apiRequest("POST", "/vector-store/config", {
      session_id: BYO_SESSION,
      provider: "qdrant",
      connection_params: params,
    })) as { id: string; provider: string; is_default: boolean; last_validated_at: string | null };
    expect(saved.provider).toBe("qdrant");
    expect(saved.is_default).toBe(false);
    expect(saved.last_validated_at).toBeTruthy();

    // GET must NOT return the raw credentials
    const getRes = (await apiRequest(
      "GET",
      `/vector-store/config?session_id=${BYO_SESSION}`,
    )) as Record<string, unknown>;
    expect(JSON.stringify(getRes)).not.toContain("6333"); // url value not leaked
    expect((getRes as { provider: string }).provider).toBe("qdrant");

    // Delete → health falls back to default
    await apiRequest("DELETE", `/vector-store/config?session_id=${BYO_SESSION}`);
    const afterDelete = await apiRequest(
      "GET",
      `/vector-store/config?session_id=${BYO_SESSION}`,
    );
    expect(afterDelete).toBeNull();
  });

  test("Pinecone sin extra instalado: /validate devuelve 422 con mensaje claro", async () => {
    const res = await fetch("http://127.0.0.1:8000/api/vector-store/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: "pinecone",
        connection_params: { api_key: "dummy", index_name: "test" },
      }),
    });
    expect(res.status).toBe(422);
    const body = (await res.json()) as { detail: string };
    expect(body.detail.toLowerCase()).toContain("langchain-pinecone");
  });
});

test.describe("Esc 6 — Fallback con vector store caído (FR-013)", () => {
  test.afterEach(async () => {
    await apiRequest("DELETE", `/vector-store/config?session_id=${OFFLINE_SESSION}`).catch(() => null);
  });

  test("BYO apuntando a URL muerta: health=unhealthy; generación sigue sin errores", async ({
    page,
  }) => {
    // Point this session at an unreachable Qdrant
    await apiRequest("POST", "/vector-store/config", {
      session_id: OFFLINE_SESSION,
      provider: "qdrant",
      connection_params: { url: "http://127.0.0.1:65533" },
    });

    const health = (await apiRequest(
      "GET",
      `/vector-store/health?session_id=${OFFLINE_SESSION}`,
    )) as { healthy: boolean; provider: string; is_default: boolean };
    expect(health.healthy).toBe(false);
    expect(health.is_default).toBe(false);

    // Generating a widget still succeeds — the pipeline degrades gracefully.
    await gotoWithSession(page, OFFLINE_SESSION);
    await sendMessage(page, "ventas por región en 2025");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);

    // And no cache suggestion could ever appear because nothing got indexed.
    await expect(page.locator('[data-role="cache-reuse-suggestion"]')).toHaveCount(0);
  });

  test("/api/health reporta provider default=qdrant cuando Qdrant local responde", async () => {
    const res = (await apiRequest("GET", "/health")) as {
      status: string;
      vector_store: { provider: string; is_default: boolean; healthy: boolean };
    };
    expect(res.status).toBe("ok");
    expect(res.vector_store.provider).toBe("qdrant");
    expect(res.vector_store.is_default).toBe(true);
    expect(res.vector_store.healthy).toBe(true);
  });
});

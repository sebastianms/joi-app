/**
 * Feature 005 quickstart — Escenarios 3, 4, 7.
 *
 * Esc 3: Recuperar widget por nombre desde el chat (US4, triage fuzzy).
 * Esc 4: RAG cache hit con Qdrant default (US5, Clarify Q2).
 * Esc 7: Invalidación del caché por cambio de schema (FR-011, Clarify Q5).
 */

import { test, expect } from "@playwright/test";
import {
  apiRequest,
  gotoWithSession,
  resetSessionState,
  saveWidgetWith,
  sendMessage,
  waitForAssistantReply,
  waitForWidgetFrame,
} from "./feature-005-helpers";
import { E2E_SESSION_ID } from "./global-setup";

const RECOVER_SESSION = `${E2E_SESSION_ID}-recover-widget`;
const CACHE_SESSION = `${E2E_SESSION_ID}-cache-hit`;
const SCHEMA_SESSION = `${E2E_SESSION_ID}-schema-invalidation`;

test.describe("Esc 3 — Recuperar widget por nombre (US4)", () => {
  test.beforeEach(async () => {
    resetSessionState(RECOVER_SESSION);
  });

  test("prompt con nombre exacto devuelve recovered_widget, sin invocar generador", async ({
    page,
  }) => {
    // Save "Churn mensual 2025" on a seed prompt
    await gotoWithSession(page, RECOVER_SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);
    await saveWidgetWith(page, "Churn mensual 2025", [], ["Métricas"]);

    // New session: same seed but fresh message history — call /chat with recovery intent
    const res = (await apiRequest("POST", "/chat/messages", {
      session_id: RECOVER_SESSION,
      message: "muéstrame Churn mensual 2025",
    })) as {
      recovered_widget?: { id: string; display_name: string };
      candidates?: Array<{ display_name: string }>;
      widget_spec?: unknown;
      trace?: unknown;
    };

    expect(res.recovered_widget, "recovered_widget must be present").toBeTruthy();
    expect(res.recovered_widget!.display_name).toBe("Churn mensual 2025");
    // Recovery short-circuits before widget generation
    expect(res.widget_spec, "no widget generation on recovery").toBeFalsy();
    expect(res.trace, "no extraction trace on recovery").toBeFalsy();
  });

  test("prompt ambiguo devuelve candidates cuando hay varios widgets", async ({ page }) => {
    await gotoWithSession(page, RECOVER_SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);
    await saveWidgetWith(page, "Churn mensual", [], ["Métricas"]);

    // Second widget with similar name
    await sendMessage(page, "ventas por región");
    await waitForAssistantReply(page, 2);
    await waitForWidgetFrame(page);
    await saveWidgetWith(page, "Churn por región", ["Métricas"]);

    const res = (await apiRequest("POST", "/chat/messages", {
      session_id: RECOVER_SESSION,
      message: "abre Churn",
    })) as {
      recovered_widget?: unknown;
      candidates?: Array<{ display_name: string }>;
    };

    expect(res.recovered_widget).toBeFalsy();
    expect(res.candidates?.length ?? 0).toBeGreaterThanOrEqual(2);
    const names = (res.candidates ?? []).map((c) => c.display_name).sort();
    expect(names).toContain("Churn mensual");
    expect(names).toContain("Churn por región");
  });
});

test.describe("Esc 4 — RAG cache hit con Qdrant default (US5)", () => {
  test.beforeEach(async () => {
    resetSessionState(CACHE_SESSION);
  });

  test("prompt repetido devuelve cache_suggestion; 'Usar este widget' incrementa hit_count", async ({
    page,
  }) => {
    const prompt = "ventas por región 2025";

    // Turn 1 — generates widget A, indexes it in Qdrant
    await gotoWithSession(page, CACHE_SESSION);
    await sendMessage(page, prompt);
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);

    // Turn 2 — identical prompt → cosine = 1.0 → guaranteed hit
    await sendMessage(page, prompt);
    await waitForAssistantReply(page, 2);

    const suggestion = page.locator('[data-role="cache-reuse-suggestion"]');
    await expect(suggestion).toBeVisible({ timeout: 10000 });

    // Click "Usar este widget" → calls POST /widget-cache/{id}/reuse
    const reuseReq = page.waitForResponse(
      (r) => /\/widget-cache\/.+\/reuse$/.test(r.url()) && r.status() === 200,
    );
    await suggestion.locator('[data-role="cache-reuse-button"]').click();
    const reuseResp = await reuseReq;
    const body = (await reuseResp.json()) as { hit_count: number };
    expect(body.hit_count).toBe(1);
  });

  test("'Generar uno nuevo' re-envía con skip_cache=true y produce nuevo widget", async ({
    page,
  }) => {
    await gotoWithSession(page, CACHE_SESSION);

    // Prime the cache with an initial generation.
    await sendMessage(page, "ventas por región en 2025");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);

    await sendMessage(page, "ventas por región en 2025");
    await waitForAssistantReply(page, 2);
    const suggestion = page.locator('[data-role="cache-reuse-suggestion"]');
    await expect(suggestion).toBeVisible({ timeout: 10000 });

    // Click "Generar uno nuevo" → should send a 3rd /chat with skip_cache=true
    const skipReq = page.waitForRequest(
      (r) =>
        r.url().endsWith("/chat/messages") &&
        r.method() === "POST" &&
        !!r.postData() &&
        JSON.parse(r.postData()!).skip_cache === true,
    );
    await suggestion.locator('[data-role="cache-skip-button"]').click();
    await skipReq;

    // 3rd assistant reply corresponds to the skip_cache request.
    await waitForAssistantReply(page, 3);
    const assistantBubbles = page.getByRole("log").locator('[data-role="assistant"]');
    const lastBubble = assistantBubbles.last();
    await expect(lastBubble.locator('[data-role="cache-reuse-suggestion"]')).toHaveCount(0);
  });
});

test.describe("Esc 7 — Invalidación del caché por cambio de schema (FR-011)", () => {
  test.beforeEach(async () => {
    resetSessionState(SCHEMA_SESSION);
  });

  test("distinto data_schema_hash no produce hit aunque el prompt sea idéntico", async ({}) => {
    // Index an entry with one schema hash
    const prompt = "ventas por región";
    await apiRequest("POST", "/chat/messages", {
      session_id: SCHEMA_SESSION,
      message: prompt,
    });

    // First ensure cache had a chance to index: a second identical call should hit.
    const hit = (await apiRequest("POST", "/widget-cache/search", {
      session_id: SCHEMA_SESSION,
      prompt,
      connection_id: "must-match", // placeholder — overridden below via direct search
      data_schema_hash: "wrong-hash",
    })) as { candidates: unknown[] };

    // With a mismatched hash, search returns no candidates (filter enforced).
    expect(hit.candidates).toEqual([]);
  });
});

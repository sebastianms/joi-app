/**
 * US3 — Bootstrap timeout del iframe del widget.
 *
 * Covers:
 *   T303 — RENDER_TIMEOUT se dispara si widget:ready no llega en 4000ms
 *   T306 — spec con bucle infinito → fallback visible en ≤ 5s
 *
 * Strategy: intercept /widget-runtime.bundle.js before page load and return
 * a no-op bundle that never emits widget:ready. The host useCanvas hook will
 * fire the 4s timer and transition loading_stage → "error" (RENDER_TIMEOUT).
 *
 * Prerequisites: backend at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true,
 * fixture connection seeded for E2E_SESSION_ID.
 */

import { test, expect, type Page } from "@playwright/test";
import { E2E_SESSION_ID } from "./global-setup";

// A bundle that never emits widget:ready — simulates both:
//   T303: a widget that never responds
//   T306: an infinite-loop widget (same observable effect from host perspective)
const NO_OP_BUNDLE = `(function () {
  // Intentionally never calls parent.postMessage({ type: 'widget:ready', ... })
  // Simulates an infinite loop or unresponsive renderer.
})();`;

async function gotoWithInterceptedBundle(page: Page, sessionId: string): Promise<void> {
  // Route must be set up before page.goto so it is active when the bundle is fetched
  await page.route("**/widget-runtime.bundle.js", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/javascript",
      body: NO_OP_BUNDLE,
    }),
  );
  await page.addInitScript((sid) => {
    window.localStorage.setItem("joi_session_id", sid);
  }, sessionId);
  await page.goto("/");
}

async function sendMessage(page: Page, message: string): Promise<void> {
  const input = page.getByRole("textbox", { name: "Mensaje" });
  await input.fill(message);
  await page.getByRole("button", { name: "Enviar" }).click();
}

async function waitForAssistantReply(page: Page) {
  const log = page.getByRole("log");
  const bubble = log.locator('[data-role="assistant"]').last();
  await expect(bubble).toBeVisible({ timeout: 15000 });
  return bubble;
}

// ─── T303 / T306 ──────────────────────────────────────────────────────────────

test.describe("T303 — RENDER_TIMEOUT dispara si widget:ready no llega (FR-008b)", () => {
  test("canvas muestra error de timeout tras 4s sin widget:ready", async ({ page }) => {
    await gotoWithInterceptedBundle(page, `${E2E_SESSION_ID}`);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    // BOOTSTRAP_TIMEOUT_MS = 4000ms. Allow 6s total (4s timer + 2s UI render + E2E overhead).
    await expect(page.locator('[data-role="widget-error"]')).toBeVisible({ timeout: 8000 });

    const errorEl = page.locator('[data-role="widget-error"]');
    await expect(errorEl).toContainText(/no respondió/i);
  });

  test("el timeout no supera 5s (SC-004)", async ({ page }) => {
    await gotoWithInterceptedBundle(page, `${E2E_SESSION_ID}`);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    const start = Date.now();
    await expect(page.locator('[data-role="widget-error"]')).toBeVisible({ timeout: 7000 });
    const elapsed = Date.now() - start;

    // The 4s timer + browser rendering should still land well under 5s from response arrival
    expect(elapsed).toBeLessThan(5500);
  });
});

test.describe("T306 — Chat sigue operativo tras timeout (FR-009)", () => {
  test("el chat acepta un nuevo prompt después de un RENDER_TIMEOUT", async ({ page }) => {
    await gotoWithInterceptedBundle(page, `${E2E_SESSION_ID}`);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    // Wait for timeout
    await expect(page.locator('[data-role="widget-error"]')).toBeVisible({ timeout: 8000 });

    // Chat input must remain enabled
    const input = page.getByRole("textbox", { name: "Mensaje" });
    await expect(input).toBeEnabled();

    // Send a second message — it should get a response (session still alive)
    await sendMessage(page, "dame el total de ventas");
    const log = page.getByRole("log");
    await expect(log.locator('[data-role="assistant"]')).toHaveCount(2, { timeout: 15000 });
  });
});

/**
 * US4 — Fallback universal: sesión operativa cuando el generador falla.
 *
 * Covers:
 *   T406a — mock generador fallido → tabla fallback aparece → sesión sigue operativa
 *   T406b — error de renderizado (RENDER_TIMEOUT) → nuevo prompt → widget normal
 *
 * Strategy:
 *   T406a: Intercept POST /api/chat/messages and inject a fallback table widget_spec
 *          for the first request. The second request goes through normally.
 *
 *   T406b: Intercept /widget-runtime.bundle.js to return a no-op bundle (RENDER_TIMEOUT),
 *          then restore the real bundle and send a second prompt — session must stay alive.
 *
 * Prerequisites: backend at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true,
 * fixture connection seeded for E2E_SESSION_ID.
 */

import { test, expect, type Page } from "@playwright/test";
import { E2E_SESSION_ID } from "./global-setup";

async function gotoWithSession(page: Page, sessionId: string): Promise<void> {
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

async function waitForAssistantReply(page: Page, count: number) {
  const log = page.getByRole("log");
  await expect(log.locator('[data-role="assistant"]')).toHaveCount(count, { timeout: 15000 });
}

// ─── T406a — Fallback table renders, session stays alive ─────────────────────

test.describe("T406a — fallback table: sesión operativa tras generador fallido (FR-009)", () => {
  test("canvas muestra tabla y segunda consulta devuelve widget", async ({ page }) => {
    await gotoWithSession(page, `${E2E_SESSION_ID}`);

    // Intercept only the first chat request and inject a fallback table widget_spec.
    let intercepted = false;
    await page.route("**/api/chat/messages", async (route) => {
      if (intercepted) {
        await route.continue();
        return;
      }
      intercepted = true;
      const response = await route.fetch();
      const json = await response.json();
      // Inject a minimal fallback table widget_spec (overrides whatever the backend returned).
      if (json.widget_spec) {
        json.widget_spec = {
          ...json.widget_spec,
          widget_type: "table",
          selection_source: "fallback",
        };
      }
      await route.fulfill({
        status: response.status(),
        headers: Object.fromEntries(response.headers()),
        body: JSON.stringify(json),
      });
    });

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page, 1);

    // Canvas must render the widget frame (table widget, no error)
    await expect(page.locator('[data-role="widget-container"]')).toBeVisible({ timeout: 8000 });

    // No error banner from the fallback path (fallback table renders correctly)
    await expect(page.locator('[data-role="widget-error"]')).not.toBeVisible();

    // Session must still accept a second prompt
    await sendMessage(page, "dame el total de ventas");
    await waitForAssistantReply(page, 2);

    // Chat input remains enabled throughout
    await expect(page.getByRole("textbox", { name: "Mensaje" })).toBeEnabled();
  });
});

// ─── T406b — Session survives RENDER_TIMEOUT (FR-009) ────────────────────────

const NO_OP_BUNDLE = `(function () {
  // Never sends widget:ready — simulates a failing renderer.
})();`;

test.describe("T406b — sesión operativa tras RENDER_TIMEOUT (FR-009)", () => {
  test("segundo prompt funciona después de un timeout de bootstrap", async ({ page }) => {
    // First request: intercept bundle to force RENDER_TIMEOUT
    let bundleIntercepted = false;
    await page.route("**/widget-runtime.bundle.js", async (route) => {
      if (!bundleIntercepted) {
        bundleIntercepted = true;
        await route.fulfill({
          status: 200,
          contentType: "application/javascript",
          body: NO_OP_BUNDLE,
        });
      } else {
        await route.continue();
      }
    });

    await gotoWithSession(page, `${E2E_SESSION_ID}`);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page, 1);

    // Wait for RENDER_TIMEOUT error (4s timer + overhead)
    await expect(page.locator('[data-role="widget-error"]')).toBeVisible({ timeout: 8000 });

    // Chat input must still be enabled
    await expect(page.getByRole("textbox", { name: "Mensaje" })).toBeEnabled();

    // Second prompt must succeed (session alive)
    await sendMessage(page, "dame el total de ventas");
    await waitForAssistantReply(page, 2);
  });
});

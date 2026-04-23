/**
 * E2E tests for Feature 004 quickstart scenarios 2-5.
 *
 * Scenario 1 is already covered by widget-canvas.spec.ts (Esc 1a-1e).
 * Here we cover:
 *   Esc 2 — KPI widget desde una agregación (row_count=1, 1 numeric)
 *   Esc 3 — Estado vacío: extracción exitosa con row_count=0
 *   Esc 4 — Preferencia explícita: reemplazo del widget sin re-query
 *   Esc 5 — Preferencia incompatible: mensaje explicativo, widget previo persiste
 *
 * Prerequisites (global-setup.ts):
 *   - Backend at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true
 *   - Fixture connection seeded for E2E_SESSION_ID
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

async function waitForAssistantReply(page: Page, count: number = 1) {
  const log = page.getByRole("log");
  const bubbles = log.locator('[data-role="assistant"]');
  await expect(bubbles).toHaveCount(count, { timeout: 15000 });
  return bubbles.last();
}

async function waitForWidgetFrame(page: Page) {
  const frame = page.locator('[data-role="widget-frame"]');
  await expect(frame).toBeVisible({ timeout: 10000 });
  return frame;
}


test.describe("Esc 2 — KPI widget desde una agregación", () => {
  test("prompt con 'total' produce un widget KPI", async ({ page }) => {
    await gotoWithSession(page, `${E2E_SESSION_ID}-kpi`);

    await sendMessage(page, "dame el total de ventas");
    const bubble = await waitForAssistantReply(page);
    await waitForWidgetFrame(page);

    const traceBlock = bubble.locator('[data-role="agent-trace"]');
    await traceBlock.locator("summary").click();
    const wgTrace = traceBlock.locator('[data-role="widget-generation-trace"]');
    await expect(wgTrace).toHaveAttribute("data-widget-type", "kpi");
  });
});


test.describe("Esc 3 — Estado vacío", () => {
  test("prompt sin resultados muestra empty state sin invocar generador", async ({ page }) => {
    await gotoWithSession(page, `${E2E_SESSION_ID}-empty`);

    await sendMessage(page, "muéstrame las ventas en Antártida");
    const bubble = await waitForAssistantReply(page);

    await expect(bubble).toContainText("La consulta no devolvió filas.");

    const canvas = page.locator('[data-role="canvas-panel"]');
    await expect(canvas).toBeVisible();
    // No iframe is mounted for empty extractions
    await expect(page.locator('[data-role="widget-frame"]')).toHaveCount(0);
  });
});


test.describe("Esc 4 — Preferencia explícita del usuario", () => {
  test("segundo prompt con 'como tabla' reemplaza el widget sin re-query", async ({ page }) => {
    await gotoWithSession(page, `${E2E_SESSION_ID}-pref`);

    await sendMessage(page, "muéstrame las ventas por mes");
    const firstBubble = await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);

    // Capture the first extraction_id from the trace data attribute
    const firstTrace = firstBubble.locator('[data-role="agent-trace"]');
    const firstExtractionId = await firstTrace.getAttribute("data-extraction-id");
    expect(firstExtractionId).toBeTruthy();

    // Request preference
    await sendMessage(page, "muéstralo como tabla");
    const secondBubble = await waitForAssistantReply(page, 2);

    // Widget frame still present (updated to table)
    await waitForWidgetFrame(page);

    // The second bubble should reference the same extraction_id (US2, FR-006)
    const secondTrace = secondBubble.locator('[data-role="agent-trace"]');
    const secondExtractionId = await secondTrace.getAttribute("data-extraction-id");
    expect(secondExtractionId).toBe(firstExtractionId);

    // And the widget-generation-trace of the second turn should be a table
    await secondTrace.locator("summary").click();
    const wgTrace = secondTrace.locator('[data-role="widget-generation-trace"]');
    await expect(wgTrace).toHaveAttribute("data-widget-type", "table");
  });
});


test.describe("Esc 5 — Preferencia incompatible con los datos", () => {
  test("heatmap sobre KPI explica la incompatibilidad y no cambia el widget", async ({ page }) => {
    await gotoWithSession(page, `${E2E_SESSION_ID}-incompat`);

    // First turn: KPI from aggregation
    await sendMessage(page, "dame el total de ventas");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);

    // Second turn: request heatmap (incompatible with 1-row 1-numeric KPI)
    await sendMessage(page, "muéstralo como heatmap");
    const bubble = await waitForAssistantReply(page, 2);

    // Response explains the incompatibility and suggests alternatives
    await expect(bubble).toContainText(/heatmap/i);
    await expect(bubble).toContainText(/no es compatible|alternativas/i);

    // The canvas still shows a widget (the KPI is preserved, FR-014)
    await expect(page.locator('[data-role="widget-frame"]')).toHaveCount(1);
  });
});

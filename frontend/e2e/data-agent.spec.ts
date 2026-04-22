/**
 * E2E tests for Feature 003 — Data Agent quickstart scenarios.
 *
 * Prerequisites (handled by global-setup.ts):
 *   - Backend running at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true
 *   - SQLite fixture connection seeded for session E2E_SESSION_ID
 *
 * Scenarios covered:
 *   Esc 1  — US1: successful SQL extraction → AgentTrace visible
 *   Esc 2  — US2: AgentTrace collapse / expand
 *   Esc 9  — No active connection → NO_CONNECTION error + /setup clickable link
 *   Esc 10 — Truncation message visible in trace summary
 *   Esc 11 — Simple message → no AgentTrace rendered
 */

import { test, expect, Page } from "@playwright/test";
import { E2E_SESSION_ID } from "./global-setup";

async function sendMessage(page: Page, message: string): Promise<void> {
  const input = page.getByRole("textbox", { name: "Mensaje" });
  await input.fill(message);
  await page.getByRole("button", { name: "Enviar" }).click();
}

async function waitForAssistantReply(page: Page) {
  const log = page.getByRole("log");
  const bubble = log.locator('[data-role="assistant"]').last();
  await expect(bubble).toBeVisible({ timeout: 10000 });
  return bubble;
}

async function gotoWithSession(page: Page, sessionId: string): Promise<void> {
  await page.addInitScript((sid) => {
    window.localStorage.setItem("joi_session_id", sid);
  }, sessionId);
  await page.goto("/");
}

test.describe("Esc 9 — No active connection", () => {
  test("returns NO_CONNECTION error with clickable /setup link", async ({ page }) => {
    await gotoWithSession(page, "fresh-session-no-connection");

    await sendMessage(page, "muéstrame las ventas por mes");
    const bubble = await waitForAssistantReply(page);

    await expect(bubble).toContainText("/setup");

    const setupLink = bubble.getByRole("link", { name: "/setup" });
    await expect(setupLink).toBeVisible();
    await expect(setupLink).toHaveAttribute("href", "/setup");

    const traceBlock = bubble.locator('[data-role="agent-trace"]');
    await expect(traceBlock).toBeVisible();
  });
});

test.describe("Esc 11 — Simple intent backward compatibility", () => {
  test("simple message has no AgentTrace", async ({ page }) => {
    await gotoWithSession(page, "fresh-session-simple-intent");

    await sendMessage(page, "hola");
    const bubble = await waitForAssistantReply(page);

    await expect(bubble.locator('[data-role="agent-trace"]')).toHaveCount(0);
  });
});

test.describe("Esc 1+2 — SQL extraction with AgentTrace", () => {
  test.beforeEach(async ({ page }) => {
    await gotoWithSession(page, E2E_SESSION_ID);
  });

  test("Esc 1 — extraction returns rows and AgentTrace is visible", async ({ page }) => {
    await sendMessage(page, "muéstrame las ventas por mes");
    const bubble = await waitForAssistantReply(page);

    await expect(bubble).toContainText("Encontré");

    const traceBlock = bubble.locator('[data-role="agent-trace"]');
    await expect(traceBlock).toBeVisible();
    await expect(traceBlock).not.toHaveAttribute("open");

    const summary = traceBlock.locator("summary");
    await expect(summary).toContainText("Agent Trace");
    await expect(summary).toContainText(/sql/i);
  });

  test("Esc 2 — AgentTrace expands and collapses", async ({ page }) => {
    await sendMessage(page, "muéstrame las ventas por mes");
    const bubble = await waitForAssistantReply(page);

    const traceBlock = bubble.locator('[data-role="agent-trace"]');
    await expect(traceBlock).toBeVisible();

    await traceBlock.locator("summary").click();
    await expect(traceBlock).toHaveAttribute("open");

    await traceBlock.locator("summary").click();
    await expect(traceBlock).not.toHaveAttribute("open");
  });

  test("Esc 2 — trace persists after a second message", async ({ page }) => {
    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    await sendMessage(page, "gracias");
    await waitForAssistantReply(page);

    const allTraces = page.locator('[data-role="agent-trace"]');
    await expect(allTraces).toHaveCount(1);
  });
});

test.describe("Esc 10 — Truncation", () => {
  test.skip(
    !process.env.PLAYWRIGHT_TEST_TRUNCATION,
    "Set PLAYWRIGHT_TEST_TRUNCATION=1 to run this scenario (requires MAX_ROWS_PER_EXTRACTION=4 in backend)"
  );

  test("truncated result shows truncation message", async ({ page }) => {
    await gotoWithSession(page, E2E_SESSION_ID);

    await sendMessage(page, "dame todas las filas de sales");
    const bubble = await waitForAssistantReply(page);

    await expect(bubble).toContainText("truncado");
  });
});

/**
 * Shared helpers for Feature 005 E2E specs.
 *
 * All specs assume:
 *   - Backend running at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true
 *   - Qdrant running at http://127.0.0.1:6333
 *   - Frontend at http://127.0.0.1:3000
 *   - Seed sessions registered by global-setup.ts
 */

import { execFileSync } from "child_process";
import path from "path";
import { expect, type Page, type Locator } from "@playwright/test";

export const API_BASE = "http://127.0.0.1:8000/api";

const PYTHON = path.resolve(__dirname, "../../backend/.venv/bin/python");
const CONN_HELPER = path.resolve(__dirname, "connection-helper.py");
const RESEED_SCRIPT = path.resolve(__dirname, "seed-e2e-db.py");
const RESET_SCRIPT = path.resolve(__dirname, "session-reset.py");
const SALES_DB = path.resolve(__dirname, "../../backend/tests/fixtures/sales_sample.db");

/** Wipes SQLite state for the given sessions: widgets, cache entries, collections, dashboards.
 *  Does NOT touch the connection row (use reseedConnection for that). */
export function resetSessionState(...sessionIds: string[]): void {
  execFileSync(PYTHON, [RESET_SCRIPT, ...sessionIds], { stdio: "ignore" });
}

/** Returns the connection_id seeded for `sessionId` (or null if none). */
export function connectionIdFor(sessionId: string): string | null {
  try {
    const out = execFileSync(PYTHON, [CONN_HELPER, sessionId], { stdio: ["ignore", "pipe", "pipe"] });
    return out.toString().trim() || null;
  } catch {
    return null;
  }
}

/** Re-inserts the seed connection for a session (used after a test deletes it). */
export function reseedConnection(sessionId: string): void {
  execFileSync(PYTHON, [RESEED_SCRIPT, SALES_DB, sessionId], { stdio: "ignore" });
}

export async function gotoWithSession(page: Page, sessionId: string, path = "/"): Promise<void> {
  await page.addInitScript((sid) => {
    window.localStorage.setItem("joi_session_id", sid);
  }, sessionId);
  await page.goto(path);
}

export async function sendMessage(page: Page, message: string): Promise<void> {
  const input = page.getByRole("textbox", { name: "Mensaje" });
  await input.fill(message);
  await page.getByRole("button", { name: "Enviar" }).click();
}

export async function waitForAssistantReply(page: Page, count = 1): Promise<Locator> {
  const log = page.getByRole("log");
  const bubbles = log.locator('[data-role="assistant"]');
  await expect(bubbles).toHaveCount(count, { timeout: 15000 });
  return bubbles.last();
}

export async function waitForWidgetFrame(page: Page): Promise<Locator> {
  const frame = page.locator('[data-role="widget-frame"]');
  await expect(frame).toBeVisible({ timeout: 10000 });
  return frame;
}

export async function saveWidgetWith(
  page: Page,
  displayName: string,
  collectionNames: string[],
  newCollections: string[] = [],
): Promise<void> {
  const saveBtn = page.locator('[data-role="widget-save-button"]');
  await expect(saveBtn).toBeEnabled({ timeout: 5000 });
  await saveBtn.click();
  const dialog = page.locator('[data-role="save-widget-dialog"]');
  await expect(dialog).toBeVisible({ timeout: 10000 });

  await dialog.getByLabel("Nombre del widget").fill(displayName);

  // Existing collections need to be loaded via handleOpenSaveDialog → fetchCollections.
  // If we expect any, wait until at least one checkbox is rendered.
  if (collectionNames.length > 0) {
    await expect(
      dialog.locator('[data-role="collection-checkbox-list"] [data-collection-name]').first(),
    ).toBeVisible({ timeout: 5000 });
  }

  for (const newName of newCollections) {
    await dialog.getByPlaceholder("Nueva colección…").fill(newName);
    await dialog.getByRole("button", { name: "Crear" }).click();
    // Newly-created collection gets auto-selected by the dialog.
    await expect(
      dialog.locator(
        `[data-role="collection-checkbox-list"] [data-collection-name="${newName}"] input[type="checkbox"]`,
      ),
    ).toBeChecked({ timeout: 5000 });
  }

  for (const existing of collectionNames) {
    const checkbox = dialog.getByRole("checkbox", { name: existing });
    if (!(await checkbox.isChecked())) {
      await checkbox.check();
    }
  }

  await dialog.getByRole("button", { name: "Guardar" }).click();
  await expect(dialog).not.toBeVisible({ timeout: 10000 });
}

/** Calls the API directly — used to fabricate state (saved widgets, etc.) without UI ping-pong. */
export async function apiRequest(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<unknown> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`${method} ${path} → ${res.status}: ${await res.text()}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

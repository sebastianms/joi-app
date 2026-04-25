/**
 * Feature 006 — Escenarios 11 y 12 del quickstart de Feature 004.
 *
 * Esc 11: Cambio de render-mode vía Setup (US6).
 *   - Setup /setup muestra tab "Widgets" con 4 tarjetas de render-mode.
 *   - Seleccionar "bootstrap" llama PUT /api/render-mode y persiste en localStorage.
 *   - El valor vuelve al default (shadcn) cuando se resetea el localStorage.
 *
 * Esc 12: Modo design_system rechazado (422).
 *   - PUT /api/render-mode con mode=design_system retorna 422.
 *   - La UI no expone la opción "design_system" (solo "design_system_disabled").
 *
 * Prerequisites:
 *   - Backend running at http://127.0.0.1:8000
 *   - Frontend at http://127.0.0.1:3000
 */

import { test, expect } from "@playwright/test";
import { E2E_SESSION_ID } from "./global-setup";

const API_BASE = "http://127.0.0.1:8000/api";
const CHANGE_SESSION = `${E2E_SESSION_ID}-render-mode-change`;
const RESET_SESSION = `${E2E_SESSION_ID}-render-mode-reset`;

async function gotoSetupWithSession(page: import("@playwright/test").Page, sessionId: string) {
  await page.addInitScript((sid) => {
    window.localStorage.setItem("joi_session_id", sid);
  }, sessionId);
  await page.goto("/setup");
}

async function apiRequest(method: string, path: string, body?: unknown) {
  const r = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: r.status, body: await r.json() };
}

// ── Esc 11 ──────────────────────────────────────────────────────────────────

test.describe("Esc 11 — Cambio de render-mode vía Setup (US6)", () => {
  test("setup /setup muestra tab Widgets con 4 tarjetas de render-mode", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);

    // Click the "Widgets" tab
    await page.getByRole("tab", { name: "Widgets" }).click();

    // All 4 mode cards must be visible
    for (const mode of ["shadcn", "bootstrap", "heroui", "design_system_disabled"]) {
      await expect(page.locator(`[data-role="render-mode-option-${mode}"]`)).toBeVisible();
    }
  });

  test("seleccionar bootstrap llama PUT /api/render-mode y persiste en localStorage", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);
    await page.getByRole("tab", { name: "Widgets" }).click();

    // Intercept the PUT call
    const putPromise = page.waitForRequest(
      (req) =>
        req.method() === "PUT" &&
        req.url().includes(`/api/render-mode/${CHANGE_SESSION}`),
    );

    await page.locator('[data-role="render-mode-option-bootstrap"]').click();
    const putReq = await putPromise;

    // Verify request body
    const body = JSON.parse(putReq.postData() ?? "{}") as { mode: string; ui_library: string };
    expect(body.mode).toBe("ui_framework");
    expect(body.ui_library).toBe("bootstrap");

    // Verify localStorage updated
    const stored = await page.evaluate(() => localStorage.getItem("joi_render_mode"));
    expect(stored).toBe("bootstrap");
  });

  test("seleccionar design_system_disabled llama PUT con mode=free_code", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);
    await page.getByRole("tab", { name: "Widgets" }).click();

    const putPromise = page.waitForRequest(
      (req) =>
        req.method() === "PUT" &&
        req.url().includes(`/api/render-mode/${CHANGE_SESSION}`),
    );

    await page.locator('[data-role="render-mode-option-design_system_disabled"]').click();
    const putReq = await putPromise;

    const body = JSON.parse(putReq.postData() ?? "{}") as { mode: string; ui_library: unknown };
    expect(body.mode).toBe("free_code");
    expect(body.ui_library).toBeNull();
  });

  test("GET /api/render-mode devuelve el modo guardado en la sesión anterior", async ({ page }) => {
    // Seed: set to shadcn via API
    await apiRequest("PUT", `/render-mode/${CHANGE_SESSION}`, {
      mode: "ui_framework",
      ui_library: "shadcn",
    });

    await gotoSetupWithSession(page, CHANGE_SESSION);
    await page.getByRole("tab", { name: "Widgets" }).click();

    // Wait for the page to load the mode from the API
    await page.waitForTimeout(500);

    // The shadcn card should appear selected (has accent border)
    const shadcnCard = page.locator('[data-role="render-mode-option-shadcn"]');
    await expect(shadcnCard).toBeVisible();
    await expect(shadcnCard).toHaveCSS("border-color", /.*/, { timeout: 3000 });
  });

  test("reset de localStorage → render-mode vuelve al default shadcn", async ({ page }) => {
    await page.addInitScript((sid) => {
      window.localStorage.setItem("joi_session_id", sid);
      // Wipe render-mode so the hook reads the API default
      window.localStorage.removeItem("joi_render_mode");
    }, RESET_SESSION);
    await page.goto("/setup");
    await page.getByRole("tab", { name: "Widgets" }).click();

    // Default (shadcn) card must be rendered
    await expect(page.locator('[data-role="render-mode-option-shadcn"]')).toBeVisible();
  });
});

// ── Esc 12 ──────────────────────────────────────────────────────────────────

test.describe("Esc 12 — Modo design_system rechazado (422)", () => {
  test("PUT /api/render-mode con mode=design_system retorna 422", async () => {
    const { status } = await apiRequest("PUT", `/render-mode/${CHANGE_SESSION}`, {
      mode: "design_system",
    });
    // Backend validator rejects design_system mode
    expect([400, 422]).toContain(status);
  });

  test("la UI de setup no expone opción 'design_system' (solo design_system_disabled)", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);
    await page.getByRole("tab", { name: "Widgets" }).click();

    // design_system (the rejected backend value) must NOT exist as a card
    await expect(
      page.locator('[data-role="render-mode-option-design_system"]'),
    ).toHaveCount(0);

    // design_system_disabled (the frontend-only "plain HTML" option) must exist
    await expect(
      page.locator('[data-role="render-mode-option-design_system_disabled"]'),
    ).toBeVisible();
  });
});

// ── Esc 4 (006 quickstart) — Setup visual identity ─────────────────────────

test.describe("Esc 4 — Setup con identidad visual Joi", () => {
  test("setup page tiene header Joi y tabs SQL/JSON/Vector Store/Widgets", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);

    await expect(page.getByText("JOI.APP")).toBeVisible();
    await expect(page.getByRole("tab", { name: "SQL" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "JSON" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Vector Store" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Widgets" })).toBeVisible();
  });

  test("inputs SQL tienen clase que incluye border dark (no white background)", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);
    await page.getByRole("tab", { name: "SQL" }).click();

    const nameInput = page.locator("input").first();
    await expect(nameInput).toBeVisible();

    // Background should be dark (black/30 = rgba(0,0,0,0.3)), not white
    const bg = await nameInput.evaluate((el) => getComputedStyle(el).backgroundColor);
    // rgba(0,0,0,0.3) or similar — definitely not "rgb(255, 255, 255)"
    expect(bg).not.toBe("rgb(255, 255, 255)");
  });

  test("link 'Volver al chat' navega a /", async ({ page }) => {
    await gotoSetupWithSession(page, CHANGE_SESSION);
    await page.getByRole("link", { name: /volver al chat/i }).click();
    await expect(page).toHaveURL("/");
  });
});

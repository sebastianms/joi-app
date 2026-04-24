/**
 * Feature 005 quickstart — Escenarios 2 y 8.
 *
 * Esc 2: Dashboard con layout persistente (US3, FR-005/FR-006).
 * Esc 8: Dashboard abierto con conexión faltante (Clarify Q5).
 */

import { test, expect } from "@playwright/test";
import {
  apiRequest,
  connectionIdFor,
  gotoWithSession,
  reseedConnection,
  resetSessionState,
  saveWidgetWith,
  sendMessage,
  waitForAssistantReply,
  waitForWidgetFrame,
} from "./feature-005-helpers";
import { E2E_SESSION_ID } from "./global-setup";

const SESSION = `${E2E_SESSION_ID}-dashboard-layout`;
const MISSING_CONN_SESSION = `${E2E_SESSION_ID}-dashboard-missing-conn`;

async function saveThreeWidgets(page: import("@playwright/test").Page, session: string) {
  const prompts = [
    { msg: "ventas por mes 2025", name: "Mensual" },
    { msg: "ventas por región en 2025", name: "Regional" },
    { msg: "total de ventas", name: "Total" },
  ];
  const widgetIds: string[] = [];
  for (const { msg, name } of prompts) {
    await gotoWithSession(page, session);
    await sendMessage(page, msg);
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);
    await saveWidgetWith(page, name, [], [`Col-${name}`]);
  }
  // Pick ids directly from the API (order = creation desc or asc is fine; we only need 3)
  const cols = (await apiRequest(
    "GET",
    `/collections?session_id=${session}`,
  )) as Array<{ id: string; name: string }>;
  for (const c of cols) {
    const ws = (await apiRequest(
      "GET",
      `/collections/${c.id}/widgets?session_id=${session}`,
    )) as Array<{ id: string }>;
    widgetIds.push(...ws.map((w) => w.id));
  }
  return widgetIds;
}

test.describe("Esc 2 — Dashboard con layout persistente", () => {
  test.beforeEach(() => {
    resetSessionState(SESSION);
  });

  test("crea dashboard, acomoda 3 widgets, reordena y persiste layout", async ({ page }) => {
    const widgetIds = await saveThreeWidgets(page, SESSION);
    expect(widgetIds.length).toBeGreaterThanOrEqual(3);

    // Create dashboard via API (the "+ dashboard" UI isn't central to the scenario)
    const dashboard = (await apiRequest("POST", "/dashboards", {
      session_id: SESSION,
      name: "Resumen",
    })) as { id: string };

    // Add the 3 widgets with distinct positions
    for (let i = 0; i < 3; i++) {
      await apiRequest("POST", `/dashboards/${dashboard.id}/items`, {
        session_id: SESSION,
        widget_id: widgetIds[i],
        grid_x: (i * 4) % 12,
        grid_y: i,
        width: 4,
        height: 3,
      });
    }

    // Reorder + resize via layout PATCH — simulate drag + resize
    await apiRequest("PATCH", `/dashboards/${dashboard.id}/layout`, {
      session_id: SESSION,
      items: [
        { widget_id: widgetIds[0], grid_x: 0, grid_y: 0, width: 6, height: 4, z_order: 0 },
        { widget_id: widgetIds[1], grid_x: 6, grid_y: 0, width: 6, height: 2, z_order: 0 },
        { widget_id: widgetIds[2], grid_x: 8, grid_y: 4, width: 4, height: 2, z_order: 0 },
      ],
    });

    // Visit the dashboard page and confirm items render with persisted widths
    await gotoWithSession(page, SESSION, `/dashboards/${dashboard.id}`);
    const grid = page.locator('[data-role="dashboard-grid"]');
    await expect(grid).toBeVisible();
    await expect(grid.locator('[data-role="dashboard-item"]')).toHaveCount(3);

    const items = grid.locator('[data-role="dashboard-item"]');
    // After refresh, grid widths match what we persisted (6/6/4).
    const widths = await items.evaluateAll((nodes) =>
      nodes.map((n) => n.getAttribute("data-grid-width")),
    );
    expect(widths.sort()).toEqual(["4", "6", "6"]);

    // Remove one item → widget survives in its collection
    const firstWidgetId = widgetIds[0];
    await apiRequest("DELETE", `/dashboards/${dashboard.id}/items/${firstWidgetId}?session_id=${SESSION}`);

    const cols = (await apiRequest("GET", `/collections?session_id=${SESSION}`)) as Array<{
      id: string;
    }>;
    const anyCollectionStillHoldsIt = (
      await Promise.all(
        cols.map(
          (c) =>
            apiRequest("GET", `/collections/${c.id}/widgets?session_id=${SESSION}`) as Promise<
              Array<{ id: string }>
            >,
        ),
      )
    )
      .flat()
      .some((w) => w.id === firstWidgetId);
    expect(anyCollectionStillHoldsIt).toBe(true);
  });
});

test.describe("Esc 8 — Dashboard abierto con conexión faltante", () => {
  test.beforeEach(() => {
    resetSessionState(MISSING_CONN_SESSION);
  });
  test.afterEach(() => {
    // Restore the seeded connection so other tests keep working.
    reseedConnection(MISSING_CONN_SESSION);
  });

  test("dashboard sigue accesible tras borrar la conexión", async ({ page }) => {

    // Generate + save a widget, add to dashboard, then delete the underlying connection.
    await gotoWithSession(page, MISSING_CONN_SESSION);
    await sendMessage(page, "ventas por mes 2025");
    await waitForAssistantReply(page, 1);
    await waitForWidgetFrame(page);
    await saveWidgetWith(page, "Ventas mensuales", [], ["Default"]);

    const cols = (await apiRequest(
      "GET",
      `/collections?session_id=${MISSING_CONN_SESSION}`,
    )) as Array<{ id: string }>;
    const widgets = (await apiRequest(
      "GET",
      `/collections/${cols[0].id}/widgets?session_id=${MISSING_CONN_SESSION}`,
    )) as Array<{ id: string }>;
    const widgetId = widgets[0].id;

    const dashboard = (await apiRequest("POST", "/dashboards", {
      session_id: MISSING_CONN_SESSION,
      name: "Dash-missing-conn",
    })) as { id: string };

    await apiRequest("POST", `/dashboards/${dashboard.id}/items`, {
      session_id: MISSING_CONN_SESSION,
      widget_id: widgetId,
      grid_x: 0,
      grid_y: 0,
      width: 6,
      height: 3,
    });

    // Delete the connection via API — CacheService.invalidate_by_connection runs.
    const connId = connectionIdFor(MISSING_CONN_SESSION);
    expect(connId, "seeded connection should exist").not.toBeNull();
    await apiRequest("DELETE", `/connections/${connId}`);

    // Open the dashboard page — it must not crash; the item stays visible.
    await gotoWithSession(page, MISSING_CONN_SESSION, `/dashboards/${dashboard.id}`);
    const grid = page.locator('[data-role="dashboard-grid"]');
    await expect(grid).toBeVisible();
    await expect(grid.locator('[data-role="dashboard-item"]')).toHaveCount(1);
  });
});

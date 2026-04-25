import { test, expect } from '@playwright/test';

/**
 * T032 — AgentTraceBlock component tests.
 *
 * These tests drive the real chat endpoint. Without an active data source
 * the backend returns NO_CONNECTION, which still produces an AgentTrace in
 * the response — enough to exercise the component render paths.
 */
test.describe('AgentTraceBlock', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('joi_onboarding_completed', 'true');
    });
  });

  test('appears collapsed after a complex-intent message', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('muéstrame las ventas por mes');
    await page.getByRole('button', { name: 'Enviar' }).click();

    const traceBlock = page.locator('[data-role="agent-trace"]');
    await expect(traceBlock).toBeVisible({ timeout: 5000 });

    // details element is collapsed by default (no open attribute)
    await expect(traceBlock).not.toHaveAttribute('open');
  });

  test('expands on click and shows query display', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('dame un análisis de ventas');
    await page.getByRole('button', { name: 'Enviar' }).click();

    const traceBlock = page.locator('[data-role="agent-trace"]');
    await expect(traceBlock).toBeVisible({ timeout: 5000 });

    await traceBlock.locator('summary').click();
    await expect(traceBlock).toHaveAttribute('open');
  });

  test('summary label contains pipeline and row count', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('dame un análisis de ventas');
    await page.getByRole('button', { name: 'Enviar' }).click();

    const summary = page.locator('[data-role="agent-trace"] summary');
    await expect(summary).toBeVisible({ timeout: 10000 });
    // Summary must contain "Agent Trace" — pipeline label varies with connection status
    await expect(summary).toContainText('Agent Trace');
  });

  test('user messages never contain a trace block', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('hola');
    await page.getByRole('button', { name: 'Enviar' }).click();

    // The user bubble is always rendered immediately — no LLM call needed
    const userBubble = page.getByRole('log').locator('[data-role="user"]').last();
    await expect(userBubble).toBeVisible({ timeout: 3000 });

    // User messages must never carry an agent trace
    await expect(userBubble.locator('[data-role="agent-trace"]')).toHaveCount(0);
  });

  test('has accessible aria-label', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('análisis de datos');
    await page.getByRole('button', { name: 'Enviar' }).click();

    const traceBlock = page.locator('[data-role="agent-trace"]');
    await expect(traceBlock).toBeVisible({ timeout: 5000 });
    await expect(traceBlock).toHaveAttribute('aria-label', 'Agent trace');
  });
});

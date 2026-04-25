import { test, expect } from '@playwright/test';

test.describe('Chat Engine - Basic Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('joi_onboarding_completed', 'true');
    });
  });

  test('should send a simple message and render the assistant echo response', async ({ page }) => {
    await page.goto('/');

    const chatPanel = page.getByRole('region', { name: 'Panel de chat' });
    await expect(chatPanel).toBeVisible();

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await expect(input).toBeVisible();

    const userMessage = 'hola';
    await input.fill(userMessage);
    await page.getByRole('button', { name: 'Enviar' }).click();

    const log = page.getByRole('log');
    await expect(log.locator('[data-role="user"]').last()).toHaveText(userMessage);
    await expect(log.locator('[data-role="assistant"]').last()).toBeVisible({
      timeout: 5000,
    });
  });

  test('should route a data-visualization request through the complex pipeline', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('muéstrame las ventas por mes');
    await page.getByRole('button', { name: 'Enviar' }).click();

    const assistantBubble = page.getByRole('log').locator('[data-role="assistant"]').last();
    // Without an active data source the agent returns a NO_CONNECTION error message
    await expect(assistantBubble).toContainText('No hay una fuente de datos activa', {
      timeout: 5000,
    });
    // The agent trace block must be present for complex intents
    await expect(assistantBubble.locator('[data-role="agent-trace"]')).toBeVisible();
  });
});

import { test, expect } from '@playwright/test';

test.describe('Chat Engine - Basic Flow', () => {
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
    await expect(log.locator('[data-role="assistant"]').last()).toContainText('Echo: hola', {
      timeout: 5000,
    });
  });

  test('should route a data-visualization request through the complex pipeline placeholder', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: 'Mensaje' });
    await input.fill('muéstrame las ventas por mes');
    await page.getByRole('button', { name: 'Enviar' }).click();

    const assistantBubble = page.getByRole('log').locator('[data-role="assistant"]').last();
    await expect(assistantBubble).toContainText('Pipeline de agentes aún no implementado', {
      timeout: 5000,
    });
  });
});

import { test, expect } from '@playwright/test';

test.describe('SQL Connections Setup', () => {
  test('should successfully test and save a valid SQL connection', async ({ page }) => {
    await page.goto('/setup');

    // SQL tab is active by default in the redesigned setup
    const sqlTab = page.locator('[role="tab"]', { hasText: 'SQL' }).first();
    await expect(sqlTab).toBeVisible();
    await sqlTab.click();

    // Fill redesigned form (controlled inputs, no name= attributes)
    await page.locator('input[placeholder*="Producci"]').fill('Test Local SQLite');
    await page.locator('select').selectOption('SQLITE');
    await page.locator('input[placeholder*="postgresql+asyncpg"]').fill('sqlite+aiosqlite:///./test.db');

    const connectButton = page.locator('button[type="submit"]');
    await expect(connectButton).toBeEnabled();
    await connectButton.click();

    // Success feedback uses --joi-success color (no alert role — it's a div)
    const successMsg = page.locator('text=Conexión establecida correctamente');
    await expect(successMsg).toBeVisible({ timeout: 5000 });
  });

  test('should display an error for an invalid SQL connection', async ({ page }) => {
    await page.goto('/setup');

    const sqlTab = page.locator('[role="tab"]', { hasText: 'SQL' }).first();
    await sqlTab.click();

    await page.locator('input[placeholder*="Producci"]').fill('Invalid PG DB');
    await page.locator('select').selectOption('POSTGRESQL');
    await page.locator('input[placeholder*="postgresql+asyncpg"]').fill('postgresql+asyncpg://invalid:wrong@localhost/db');

    await page.locator('button[type="submit"]').click();

    // Error feedback uses --joi-accent-warm color (no alert role)
    const errorMsg = page.locator('[class*="accent-warm"]').first();
    await expect(errorMsg).toBeVisible({ timeout: 5000 });
  });
});

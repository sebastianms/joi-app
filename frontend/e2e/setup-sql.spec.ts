import { test, expect } from '@playwright/test';

test.describe('SQL Connections Setup', () => {
  test('should successfully test and save a valid SQL connection', async ({ page }) => {
    // 1. Navigate to the setup page
    await page.goto('/');

    // 2. Ensure we are on the SQL Database tab
    const sqlTab = page.locator('button[role="tab"]', { hasText: 'SQL Database' });
    await expect(sqlTab).toBeVisible();
    await sqlTab.click();

    // 3. Fill the form with valid SQLite credentials
    await page.fill('input[name="name"]', 'Test Local SQLite');
    await page.selectOption('select[name="source_type"]', 'SQLITE');
    await page.fill('input[name="connection_string"]', 'sqlite+aiosqlite:///./test.db');

    // 4. Click Connect
    const connectButton = page.locator('button[type="submit"]', { hasText: 'Connect' });
    await expect(connectButton).toBeEnabled();
    await connectButton.click();

    // 5. Verify success alert
    const successAlert = page.getByRole('alert').filter({ hasText: 'Success' });
    await expect(successAlert).toBeVisible({ timeout: 5000 });
    await expect(successAlert).toContainText('Connection established and saved successfully.');
  });

  test('should display an error for an invalid SQL connection', async ({ page }) => {
    await page.goto('/');

    const sqlTab = page.locator('button[role="tab"]', { hasText: 'SQL Database' });
    await sqlTab.click();

    await page.fill('input[name="name"]', 'Invalid PG DB');
    await page.selectOption('select[name="source_type"]', 'POSTGRESQL');
    await page.fill('input[name="connection_string"]', 'postgresql+asyncpg://invalid:wrong@localhost/db');

    await page.locator('button[type="submit"]', { hasText: 'Connect' }).click();

    // The backend doesn't have asyncpg installed, or the credentials are bad. It should fail.
    const errorAlert = page.getByRole('alert').filter({ hasText: 'Connection Failed' });
    await expect(errorAlert).toBeVisible({ timeout: 5000 });
  });
});

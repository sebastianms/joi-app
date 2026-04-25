import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

test.describe('JSON Uploads Setup', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('joi_onboarding_completed', 'true');
    });
  });
  let validFilePath: string;
  let largeFilePath: string;

  test.beforeAll(() => {
    const tmpDir = os.tmpdir();
    const suffix = process.pid;

    validFilePath = path.join(tmpDir, `valid-test-${suffix}.json`);
    fs.writeFileSync(validFilePath, JSON.stringify([{ id: 1, name: 'test' }]));

    largeFilePath = path.join(tmpDir, `large-test-${suffix}.json`);
    const largeContent = Buffer.alloc(11 * 1024 * 1024, ' ');
    fs.writeFileSync(largeFilePath, largeContent);
  });

  test.afterAll(() => {
    if (fs.existsSync(validFilePath)) fs.unlinkSync(validFilePath);
    if (fs.existsSync(largeFilePath)) fs.unlinkSync(largeFilePath);
  });

  test('should successfully upload a valid JSON file', async ({ page }) => {
    await page.goto('/setup');

    // Click JSON tab (redesigned setup — tab label is "JSON")
    const jsonTab = page.locator('[role="tab"]', { hasText: 'JSON' }).first();
    await expect(jsonTab).toBeVisible();
    await jsonTab.click();

    // Redesigned form uses controlled state (no id= attributes on inputs)
    await page.locator('input[placeholder*="histór"]').fill('My Valid JSON Data');
    await page.locator('input[type="file"]').setInputFiles(validFilePath);

    const uploadButton = page.locator('button[type="submit"]');
    await expect(uploadButton).toBeEnabled();
    await uploadButton.click();

    // Success feedback in Spanish
    const successMsg = page.locator('text=Archivo cargado y validado correctamente');
    await expect(successMsg).toBeVisible({ timeout: 5000 });
  });

  test('should reject a JSON file larger than 10MB on the client side', async ({ page }) => {
    await page.goto('/setup');

    const jsonTab = page.locator('[role="tab"]', { hasText: 'JSON' }).first();
    await jsonTab.click();

    await page.locator('input[placeholder*="histór"]').fill('Too Large JSON');
    await page.locator('input[type="file"]').setInputFiles(largeFilePath);

    // Error message in Spanish
    const errorMsg = page.locator('text=Archivo demasiado grande');
    await expect(errorMsg).toBeVisible({ timeout: 3000 });

    // Submit button is disabled because file was rejected
    const uploadButton = page.locator('button[type="submit"]');
    await expect(uploadButton).toBeDisabled();
  });
});

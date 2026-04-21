import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

test.describe('JSON Uploads Setup', () => {
  let validFilePath: string;
  let largeFilePath: string;

  test.beforeAll(() => {
    // Create temporary JSON files for testing
    const tmpDir = os.tmpdir();
    
    // Valid JSON
    validFilePath = path.join(tmpDir, 'valid-test.json');
    fs.writeFileSync(validFilePath, JSON.stringify([{ id: 1, name: 'test' }]));

    // Large file (> 10MB) - we'll create a 11MB file with spaces
    largeFilePath = path.join(tmpDir, 'large-test.json');
    const largeContent = Buffer.alloc(11 * 1024 * 1024, ' ');
    fs.writeFileSync(largeFilePath, largeContent);
  });

  test.afterAll(() => {
    // Cleanup
    if (fs.existsSync(validFilePath)) fs.unlinkSync(validFilePath);
    if (fs.existsSync(largeFilePath)) fs.unlinkSync(largeFilePath);
  });

  test('should successfully upload a valid JSON file', async ({ page }) => {
    // 1. Navigate to the setup page
    await page.goto('/setup');

    // 2. Go to JSON File tab
    const jsonTab = page.locator('button[role="tab"]', { hasText: 'JSON File' });
    await expect(jsonTab).toBeVisible();
    await jsonTab.click();

    // 3. Fill the form
    await page.fill('input[id="json-name"]', 'My Valid JSON Data');
    
    // 4. Upload file
    await page.setInputFiles('input[id="json-file"]', validFilePath);

    // 5. Submit
    const uploadButton = page.locator('button[type="submit"]', { hasText: 'Upload Data Source' });
    await expect(uploadButton).toBeEnabled();
    await uploadButton.click();

    // 6. Verify success alert
    const successAlert = page.getByRole('alert').filter({ hasText: 'Success' });
    await expect(successAlert).toBeVisible({ timeout: 5000 });
    await expect(successAlert).toContainText('JSON uploaded and validated successfully!');
  });

  test('should reject a JSON file larger than 10MB on the client side', async ({ page }) => {
    await page.goto('/setup');

    const jsonTab = page.locator('button[role="tab"]', { hasText: 'JSON File' });
    await jsonTab.click();

    await page.fill('input[id="json-name"]', 'Too Large JSON');
    
    // Upload large file
    await page.setInputFiles('input[id="json-file"]', largeFilePath);

    // Should immediately show an error without submitting
    const errorAlert = page.getByRole('alert').filter({ hasText: 'Upload Failed' });
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('File is too large. Maximum allowed size is 10 MB.');

    // Submit button should remain disabled because file was rejected and cleared
    const uploadButton = page.locator('button[type="submit"]', { hasText: 'Upload Data Source' });
    await expect(uploadButton).toBeDisabled();
  });
});

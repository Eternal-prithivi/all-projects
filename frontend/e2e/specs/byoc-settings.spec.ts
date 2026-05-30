import { test, expect } from '@playwright/test';

test.describe('BYOC settings validation', () => {
  test('dashboard settings requires authentication', async ({ page }) => {
    await page.goto('/dashboard/settings');
    await expect(page).toHaveURL(/login/);
  });
});

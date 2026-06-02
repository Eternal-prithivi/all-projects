import { test, expect } from '@playwright/test';

test.describe('Mobile shell', () => {
  test.use({
    viewport: { width: 390, height: 844 },
  });

  test('landing shows hamburger and opens drawer', async ({ page }) => {
    await page.goto('/');
    const toggle = page.getByRole('button', { name: /open menu/i });
    await expect(toggle).toBeVisible();
    await toggle.click();
    const drawer = page.getByRole('dialog', { name: /site navigation/i });
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole('link', { name: /features/i })).toBeVisible();
  });

  test('features page shows marketing drawer', async ({ page }) => {
    await page.goto('/features');
    await page.getByRole('button', { name: /open menu/i }).click();
    await expect(page.getByRole('link', { name: /^about$/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /^contact$/i })).toBeVisible();
  });
});

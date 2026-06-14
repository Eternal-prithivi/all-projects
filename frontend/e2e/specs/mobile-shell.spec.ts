import { test, expect } from '@playwright/test';
import { isBackendAvailable, loginViaApi, registerTestUser } from '../helpers';

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
    await expect(drawer.getByRole('link', { name: /^download$/i })).toBeVisible();
  });

  test('features page shows marketing drawer', async ({ page }) => {
    await page.goto('/features');
    await page.getByRole('button', { name: /open menu/i }).click();
    const drawer = page.getByRole('dialog', { name: /site navigation/i });
    await expect(drawer.getByRole('link', { name: /^about$/i })).toBeVisible();
    await expect(drawer.getByRole('link', { name: /^contact$/i })).toBeVisible();
  });

  test('download page shows platform options', async ({ page }) => {
    await page.goto('/download');
    await expect(page.getByRole('heading', { name: /your cloud command center/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /download for your operating system/i })).toBeVisible();
    await expect(page.getByLabel('Choose platform').getByRole('tab', { name: /macOS/i })).toBeVisible();
  });

  test('dashboard shows bottom navigation when logged in', async ({ page, request }) => {
    test.skip(!(await isBackendAvailable(request)), 'Backend not available');

    const user = await registerTestUser(request);
    await loginViaApi(page, request, user);
    await page.goto('/dashboard');

    const bottomNav = page.getByRole('navigation', { name: /main navigation/i });
    await expect(bottomNav).toBeVisible();
    await expect(bottomNav.getByRole('link', { name: /overview/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /more navigation/i })).toBeVisible();
  });
});

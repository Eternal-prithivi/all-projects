import { test, expect } from '@playwright/test';
import { isBackendAvailable, loginViaApi, registerTestUser } from '../helpers';

test.describe('Profile menu', () => {
  test('shows workspace and help links and navigates to billing', async ({ page, request }) => {
    test.setTimeout(60_000);

    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const user = await registerTestUser(request);
    await loginViaApi(page, request, user);

    await page.getByRole('button', { name: /user menu/i }).click();

    await expect(page.getByRole('menu').getByRole('button', { name: /^billing$/i })).toBeVisible();
    await expect(page.getByRole('menu').getByRole('button', { name: /^help center$/i })).toBeVisible();
    await expect(page.getByRole('menu').getByRole('button', { name: /^support$/i })).toBeVisible();
    await expect(page.getByRole('menu').getByRole('button', { name: /keyboard shortcuts/i })).toBeVisible();

    await page.getByRole('menu').getByRole('button', { name: /^billing$/i }).click();
    await page.waitForURL(/\/dashboard\/billing/, { timeout: 15_000 });
    expect(page.url()).toContain('/dashboard/billing');
  });

  test('keyboard shortcuts item opens shortcuts overlay', async ({ page, request }) => {
    test.setTimeout(60_000);

    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const user = await registerTestUser(request);
    await loginViaApi(page, request, user);

    await page.getByRole('button', { name: /user menu/i }).click();
    await page.getByRole('menu').getByRole('button', { name: /keyboard shortcuts/i }).click();

    await expect(page.getByRole('dialog', { name: /keyboard shortcuts/i })).toBeVisible({
      timeout: 10_000,
    });
  });
});

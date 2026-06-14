import { test, expect } from '@playwright/test';
import { adminCredentials, isBackendAvailable, loginOnPage } from '../helpers';

test.describe('Admin smoke', () => {
  test('admin can open system health page', async ({ page, request }) => {
    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const admin = adminCredentials();
    if (!admin) {
      test.skip(true, 'Admin credentials not configured');
    }

    await loginOnPage(page, admin, request);
    await expect
      .poll(async () =>
        page.evaluate(() => JSON.parse(sessionStorage.getItem('cachedUser') || '{}')?.role),
      )
      .toBe('admin');

    await page.goto('/admin/system');
    await expect(page).not.toHaveURL(/access-denied/);

    await expect(page.getByRole('heading', { level: 1, name: /system health/i })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole('heading', { name: /database status/i })).toBeVisible();
  });
});

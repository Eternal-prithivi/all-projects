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
    await page.goto('/admin/system');

    await expect(page.getByRole('heading', { name: /system health/i })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/database status/i)).toBeVisible();
  });
});

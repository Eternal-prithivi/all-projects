import { test, expect } from '@playwright/test';
import { adminCredentials, isBackendAvailable, loginOnPage } from '../helpers';

const SYSTEM_HEALTH_FIXTURE = {
  database: { healthy: true, size_mb: 0.5, collections: 4 },
  collections: { users: 1, vm_assignments: 0, files: 0, payments: 0 },
  platform: {
    celery: {
      broker: { ok: true },
      workers: {},
      beat_schedule: {},
    },
  },
};

test.describe('Admin smoke', () => {
  test('admin can open system health page', async ({ page, request }) => {
    test.setTimeout(60_000);

    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const admin = adminCredentials();
    if (!admin) {
      test.skip(true, 'Admin credentials not configured');
    }

    await page.route('**/admin/system-health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SYSTEM_HEALTH_FIXTURE),
      });
    });

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

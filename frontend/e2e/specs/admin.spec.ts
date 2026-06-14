import { test, expect } from '@playwright/test';
import { adminCredentials, isBackendAvailable, loginAdminOnPage } from '../helpers';

const SYSTEM_HEALTH_FIXTURE = {
  database: { healthy: true, size_mb: 0.5, collections: 4 },
  collections: { users: 1, vm_assignments: 0, files: 0, payments: 0 },
  platform: {
    celery: {
      broker: { configured: true, reachable: true, detail: 'Broker connection OK' },
      workers: { workers_online: 0, reachable: false },
      beat_schedule: { task_count: 0, tasks: [] },
      healthy: true,
    },
  },
};

const EMPTY_NOTIFICATIONS = {
  notifications: [],
  unread_count: 0,
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

    await page.route(/\/api\/admin\/system-health/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SYSTEM_HEALTH_FIXTURE),
      });
    });
    await page.route(/\/api\/notifications\/recent/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY_NOTIFICATIONS),
      });
    });

    await loginAdminOnPage(page, request, admin);

    await page.goto('/admin/system', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/admin\/system/);
    await expect(page).not.toHaveURL(/access-denied/);

    await expect(page.getByRole('heading', { name: /platform administration/i })).toBeVisible({
      timeout: 30_000,
    });

    await expect(page.getByText(/loading system health/i)).toBeHidden({ timeout: 30_000 });
    await expect(page.getByRole('heading', { level: 1, name: /system health/i })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole('heading', { name: /database status/i })).toBeVisible();
  });
});

import { test, expect } from '@playwright/test';
import { adminCredentials, apiRoot, isBackendAvailable, loginOnPage } from '../helpers';

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
    test.setTimeout(90_000);

    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const admin = adminCredentials();
    if (!admin) {
      test.skip(true, 'Admin credentials not configured');
    }

    const tokenRes = await request.post(`${apiRoot()}/api/auth/token`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `username=${encodeURIComponent(admin.username)}&password=${encodeURIComponent(admin.password)}`,
    });
    expect(tokenRes.ok()).toBeTruthy();
    const { access_token: adminToken } = (await tokenRes.json()) as { access_token: string };

    const healthRes = await request.get(`${apiRoot()}/api/admin/system-health`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    expect(healthRes.ok()).toBeTruthy();

    await page.route(/\/api\/admin\/system-health/, async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
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

    await loginOnPage(page, admin, request);
    await expect
      .poll(async () =>
        page.evaluate(() => JSON.parse(sessionStorage.getItem('cachedUser') || '{}')?.role),
      )
      .toBe('admin');

    await expect(page.getByRole('link', { name: /admin portal/i })).toBeVisible({
      timeout: 30_000,
    });
    await page.getByRole('link', { name: /admin portal/i }).click();
    await expect(page).toHaveURL(/\/admin\/?$/);

    await page
      .getByRole('navigation', { name: /admin navigation/i })
      .getByRole('link', { name: /system health/i })
      .click();
    await expect(page).toHaveURL(/\/admin\/system/);

    await expect(page.getByText(/loading system health/i)).toBeHidden({ timeout: 30_000 });
    await expect(page.getByRole('heading', { level: 1, name: /system health/i })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole('heading', { name: /database status/i })).toBeVisible();
  });
});

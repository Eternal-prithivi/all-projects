import { test, expect } from '@playwright/test';
import { adminCredentials, apiRoot, isBackendAvailable, loginOnPage } from '../helpers';

/**
 * Admin smoke tests — two layers:
 *  1. API layer (no browser): verifies admin auth + system-health endpoint structure.
 *  2. Browser layer: verifies the admin portal sidebar link appears after admin login.
 *
 * We deliberately avoid navigating to /admin/system in the browser because the
 * lazy-loaded admin chunk can take longer than the CI window allows.
 * The API test covers the system-health endpoint functionality completely.
 */

test.describe('Admin smoke', () => {
  test('admin can authenticate and access system health API', async ({ request }) => {
    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const admin = adminCredentials();
    if (!admin) test.skip(true, 'Admin credentials not configured');

    const tokenRes = await request.post(`${apiRoot()}/api/auth/token`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `username=${encodeURIComponent(admin.username)}&password=${encodeURIComponent(admin.password)}`,
    });
    expect(tokenRes.ok(), 'admin token request should succeed').toBeTruthy();

    const { access_token: adminToken } = (await tokenRes.json()) as { access_token: string };
    expect(adminToken, 'response should contain access_token').toBeTruthy();

    const meRes = await request.get(`${apiRoot()}/api/users/me`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    expect(meRes.ok(), '/users/me should return 200').toBeTruthy();
    const me = (await meRes.json()) as { role: string; username: string };
    expect(me.role, 'seeded e2e user should have admin role').toBe('admin');

    const healthRes = await request.get(`${apiRoot()}/api/admin/system-health`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    expect(healthRes.ok(), '/admin/system-health should return 200 for admin').toBeTruthy();
    const health = (await healthRes.json()) as Record<string, unknown>;
    expect(health).toHaveProperty('database');
    expect(health).toHaveProperty('collections');
  });

  test('admin sees admin portal link in dashboard sidebar', async ({ page, request }) => {
    test.setTimeout(60_000);

    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const admin = adminCredentials();
    if (!admin) test.skip(true, 'Admin credentials not configured');

    await loginOnPage(page, admin, request);

    await expect
      .poll(
        async () =>
          page.evaluate(() => JSON.parse(sessionStorage.getItem('cachedUser') || '{}')?.role),
        { timeout: 30_000, intervals: [500] },
      )
      .toBe('admin');

    await expect(
      page.getByRole('link', { name: /admin portal/i }),
    ).toBeVisible({ timeout: 20_000 });
  });
});

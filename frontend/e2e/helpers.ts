/** Shared helpers for Playwright specs. */

export const apiRoot = (): string =>
  process.env.PLAYWRIGHT_API_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000';

export async function isBackendAvailable(
  request: import('@playwright/test').APIRequestContext,
): Promise<boolean> {
  try {
    const res = await request.get(`${apiRoot()}/api/platform/status`, { timeout: 5000 });
    return res.ok();
  } catch {
    return false;
  }
}

export async function registerTestUser(
  request: import('@playwright/test').APIRequestContext,
): Promise<{ username: string; password: string; email: string }> {
  const username = `e2e_${Date.now().toString(36)}`;
  const password = 'SecurePass1';
  const email = `${username}@example.com`;
  const res = await request.post(`${apiRoot()}/api/auth/register`, {
    headers: { 'Content-Type': 'application/json' },
    data: JSON.stringify({ username, email, password }),
  });
  if (!res.ok() && res.status() !== 409) {
    throw new Error(`Register failed: ${res.status()} ${await res.text()}`);
  }
  return { username, password, email };
}

/** Obtain JWT via API (avoids UI rate limits and flaky full-page load waits). */
export async function loginViaApi(
  page: import('@playwright/test').Page,
  request: import('@playwright/test').APIRequestContext,
  user: { username: string; password: string },
): Promise<void> {
  const body = new URLSearchParams({
    username: user.username,
    password: user.password,
  });
  const res = await request.post(`${apiRoot()}/api/auth/token`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: body.toString(),
  });
  if (!res.ok()) {
    throw new Error(`Login API failed (${res.status()}): ${await res.text()}`);
  }
  const payload = (await res.json()) as { access_token?: string };
  if (!payload.access_token) {
    throw new Error('Login API response missing access_token');
  }

  await page.goto('/login');
  await page.evaluate((token) => {
    localStorage.setItem('authToken', token);
    sessionStorage.removeItem('cachedUser');
  }, payload.access_token);
  await page.goto('/dashboard');
  await page.waitForURL(/\/dashboard/, { timeout: 30_000, waitUntil: 'commit' });
  await waitForSessionUser(page);
}

export async function loginOnPage(
  page: import('@playwright/test').Page,
  user: { username: string; password: string },
  request?: import('@playwright/test').APIRequestContext,
): Promise<void> {
  if (request) {
    await loginViaApi(page, request, user);
    return;
  }

  await page.goto('/login');
  await page.getByLabel(/username/i).fill(user.username);
  await page.getByLabel(/^password$/i).fill(user.password);
  await page.getByRole('button', { name: /submit login form/i }).click();

  const errorBanner = page.locator('#login-error, .auth-error');
  try {
    await page.waitForURL(/\/dashboard/, { timeout: 30_000, waitUntil: 'commit' });
  } catch {
    const errText = (await errorBanner.first().textContent())?.trim();
    throw new Error(errText ? `Login failed: ${errText}` : 'Login did not reach /dashboard');
  }
}

/** Login as admin with cached session user pre-seeded (stable for /admin/* hard navigations). */
export async function loginAdminOnPage(
  page: import('@playwright/test').Page,
  request: import('@playwright/test').APIRequestContext,
  user: { username: string; password: string },
): Promise<void> {
  const body = new URLSearchParams({
    username: user.username,
    password: user.password,
  });
  const res = await request.post(`${apiRoot()}/api/auth/token`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: body.toString(),
  });
  if (!res.ok()) {
    throw new Error(`Admin login API failed (${res.status()}): ${await res.text()}`);
  }
  const payload = (await res.json()) as { access_token?: string };
  if (!payload.access_token) {
    throw new Error('Admin login API response missing access_token');
  }

  const meRes = await request.get(`${apiRoot()}/api/users/me`, {
    headers: { Authorization: `Bearer ${payload.access_token}` },
  });
  if (!meRes.ok()) {
    throw new Error(`Admin /users/me failed (${meRes.status()}): ${await meRes.text()}`);
  }
  const userData = (await meRes.json()) as { role?: string };
  if (userData.role !== 'admin') {
    throw new Error(`Expected admin role, got '${userData.role ?? 'unknown'}'`);
  }

  await page.goto('/login');
  await page.evaluate(
    ({ token, cached }) => {
      localStorage.setItem('authToken', token);
      sessionStorage.setItem('cachedUser', JSON.stringify(cached));
    },
    { token: payload.access_token, cached: userData },
  );
}

export function adminCredentials(): { username: string; password: string } | null {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME || 'e2e_admin';
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD || 'SecurePass1';
  return { username, password };
}

/** Pro plan payload for BYOC / provision policy E2E. */
export const PRO_ENTITLEMENTS = {
  plan_id: 'pro',
  plan_name: 'Pro',
  features: {
    live_billing: true,
    byoc: true,
    provision_policies: true,
    api_access: true,
    team_seat_billing: true,
    ai_recommendations: true,
  },
  limits: { vm_limit: 10, storage_gb: 100, vms_used: 0, storage_bytes_used: 0 },
  nav: [],
};

export async function mockProEntitlements(page: import('@playwright/test').Page): Promise<void> {
  const handler = async (route: import('@playwright/test').Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(PRO_ENTITLEMENTS),
    });
  };
  await page.route('**/payments/entitlements', handler);
  await page.route('**/api/payments/entitlements', handler);
}

export async function waitForSessionUser(page: import('@playwright/test').Page): Promise<void> {
  await page
    .waitForResponse((r) => r.url().includes('/api/users/me') && r.ok(), { timeout: 30_000 })
    .catch(() => undefined);
}

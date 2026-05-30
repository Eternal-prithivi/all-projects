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

export async function loginOnPage(
  page: import('@playwright/test').Page,
  user: { username: string; password: string },
): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/username/i).fill(user.username);
  await page.getByLabel(/^password$/i).fill(user.password);
  await page.getByRole('button', { name: /submit login form/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
}

export function adminCredentials(): { username: string; password: string } | null {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME || 'e2e_admin';
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD || 'SecurePass1';
  return { username, password };
}

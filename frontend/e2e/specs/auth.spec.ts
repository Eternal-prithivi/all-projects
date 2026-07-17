import { test, expect } from '@playwright/test';
import { isBackendAvailable, loginOnPage, registerTestUser } from '../helpers';

test.describe('Auth smoke', () => {
  test('login page shows sign-in form', async ({ page }) => {
    await page.goto('/login');
    // Wait for the page to fully render before asserting
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/^password$/i)).toBeVisible();
    // Verify the submit button exists with the correct aria-label
    await expect(
      page.getByRole('button', { name: /submit login form/i }),
    ).toBeVisible();
  });

  test('login navigates to dashboard', async ({ page, request }) => {
    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running — start API on :8000 with Mongo for this test');
    }

    const user = await registerTestUser(request);
    // Pass `request` so loginOnPage uses the API path — this bypasses the
    // Turnstile CAPTCHA widget that blocks UI-based login on CI runners.
    await loginOnPage(page, user, request);

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(user.username);
    await expect(page.getByText(/operational overview/i)).toBeVisible();
  });
});

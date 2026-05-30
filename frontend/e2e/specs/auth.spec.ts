import { test, expect } from '@playwright/test';
import { isBackendAvailable, loginOnPage, registerTestUser } from '../helpers';

test.describe('Auth smoke', () => {
  test('login page shows sign-in form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test('login navigates to dashboard', async ({ page, request }) => {
    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running — start API on :8000 with Mongo for this test');
    }

    const user = await registerTestUser(request);
    await loginOnPage(page, user);

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole('heading', { level: 2 })).toContainText(user.username);
    await expect(page.getByText(/cloud overview/i)).toBeVisible();
  });
});

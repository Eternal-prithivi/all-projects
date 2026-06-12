import { test, expect } from '@playwright/test';
import { isBackendAvailable, loginOnPage, registerTestUser } from '../helpers';

test.describe('BYOC form validation', () => {
  test('shows GCP validation errors when required fields empty', async ({ page, request }) => {
    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    const user = await registerTestUser(request);

    await page.route('**/api/byoc/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          eligible: true,
          current_plan: 'pro',
          connections: {
            aws: { connected: false },
            gcp: { connected: false },
            azure: { connected: false },
          },
          capabilities: {
            aws: { connected: false, features: {}, unlocked_features: [], gaps: [] },
            gcp: { connected: false, features: {}, unlocked_features: [], gaps: [] },
            azure: { connected: false, features: {}, unlocked_features: [], gaps: [] },
          },
        }),
      });
    });
    await page.route('**/api/byoc/policy-templates', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await loginOnPage(page, user, request);
    await page.goto('/dashboard/settings');

    const connectButtons = page.getByRole('button', { name: /^connect$/i });
    await connectButtons.nth(1).click();

    await expect(page.getByText(/step 1 — verify credentials/i)).toBeVisible();
    await expect(page.getByText(/service account json is required/i)).toBeVisible();
    await expect(page.getByText(/bucket name is required/i)).toBeVisible();
  });
});

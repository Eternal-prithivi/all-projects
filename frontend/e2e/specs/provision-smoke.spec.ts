import { test, expect } from '@playwright/test';
import { isBackendAvailable, loginViaApi, mockProEntitlements, registerTestUser } from '../helpers';

test.describe('Provision page smoke', () => {
  test('tabs load without application error', async ({ page, request }) => {
    if (!(await isBackendAvailable(request))) {
      test.skip(true, 'Backend not running');
    }

    await mockProEntitlements(page);
    const user = await registerTestUser(request);
    await loginViaApi(page, request, user);

    await page.goto('/dashboard/provision');
    await expect(page.getByRole('heading', { name: /infrastructure/i })).toBeVisible({
      timeout: 30_000,
    });

    const tabGroup = page.getByRole('group', { name: /infrastructure sections/i });
    const tabCount = await tabGroup.count();
    if (tabCount === 0) {
      // No cloud configured — empty state is acceptable for smoke
      return;
    }

    for (const tab of ['Deployments', 'Activity', 'Policies', 'Build']) {
      await tabGroup.getByRole('button', { name: tab }).click();
      await expect(page.getByText(/unexpected application error/i)).toHaveCount(0);
    }

    await expect(page.getByText(/objects are not valid as a react child/i)).toHaveCount(0);
  });
});

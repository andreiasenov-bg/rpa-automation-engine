import { test, expect } from '@playwright/test';
import { setupDashboardMocks } from './helpers';

test.describe('Dashboard Widget Customization', () => {
  test.beforeEach(async ({ page }) => {
    await setupDashboardMocks(page);
    // Clear localStorage to start fresh
    await page.addInitScript(() => {
      localStorage.removeItem('rpa_dashboard_widgets');
    });
    await page.goto('/');
  });

  test('shows customize button in dashboard header', async ({ page }) => {
    await expect(page.locator('button[title="Customize dashboard"]')).toBeVisible();
  });

  test('opens customizer panel on click', async ({ page }) => {
    await page.locator('button[title="Customize dashboard"]').click();
    await expect(page.getByText('Customize Dashboard')).toBeVisible();
  });

  test('shows all 7 widgets listed in the customizer', async ({ page }) => {
    await page.locator('button[title="Customize dashboard"]').click();
    const widgetLabels = [
      'Statistics Cards',
      'Quick Actions',
      'Success Rate',
      'System Health',
      'Recent Executions',
      'Analytics Charts',
      'Activity Timeline',
    ];
    for (const label of widgetLabels) {
      await expect(page.getByText(label, { exact: true })).toBeVisible();
    }
  });

  test('shows visible count as 7/7 by default', async ({ page }) => {
    await page.locator('button[title="Customize dashboard"]').click();
    await expect(page.getByText('7/7 visible')).toBeVisible();
  });

  test('hides a widget when toggled off', async ({ page }) => {
    // Verify Quick Actions is visible initially
    await expect(page.getByText('Quick Actions').first()).toBeVisible();

    // Open customizer and toggle off Quick Actions
    await page.locator('button[title="Customize dashboard"]').click();
    // Click the Quick Actions row in the customizer
    const qaRow = page.locator('button', { hasText: 'Quick Actions' }).last();
    await qaRow.click();

    // Count should now be 6/7
    await expect(page.getByText('6/7 visible')).toBeVisible();
  });

  test('reset button restores default widgets', async ({ page }) => {
    // Open customizer and toggle off a widget
    await page.locator('button[title="Customize dashboard"]').click();
    const qaRow = page.locator('button', { hasText: 'Quick Actions' }).last();
    await qaRow.click();
    await expect(page.getByText('6/7 visible')).toBeVisible();

    // Click reset
    await page.getByText('Reset').click();
    await expect(page.getByText('7/7 visible')).toBeVisible();
  });

  test('closes customizer on close button click', async ({ page }) => {
    await page.locator('button[title="Customize dashboard"]').click();
    await expect(page.getByText('Customize Dashboard')).toBeVisible();

    // Click the X button inside customizer
    const closeBtn = page.locator('[data-customizer] button').filter({ has: page.locator('svg.lucide-x') });
    await closeBtn.click();

    await expect(page.getByText('Customize Dashboard')).not.toBeVisible();
  });
});

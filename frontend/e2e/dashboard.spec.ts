import { test, expect } from '@playwright/test';
import { setupDashboardMocks } from './helpers';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupDashboardMocks(page);
  });

  test('should display dashboard page', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' }).first()).toBeVisible();
  });

  test('should show stat cards with correct values', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('24').first()).toBeVisible(); // total workflows
    await expect(page.getByText('1847').first()).toBeVisible(); // total executions
    await expect(page.getByText('1692').first()).toBeVisible(); // completed
    await expect(page.getByText('112').first()).toBeVisible(); // failed
  });

  test('should show Quick Actions widget', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Quick Actions')).toBeVisible();
    await expect(page.getByText('New Workflow')).toBeVisible();
    await expect(page.getByText('Credentials').first()).toBeVisible();
  });

  test('should show Success Rate ring', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Success Rate').first()).toBeVisible();
    await expect(page.getByText('94%').first()).toBeVisible();
  });

  test('should show System Health widget', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('System Health')).toBeVisible();
    await expect(page.getByText(/WebSocket/)).toBeVisible();
  });

  test('should show recent executions', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Invoice Processing').first()).toBeVisible();
  });

  test('should show Analytics section', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Analytics')).toBeVisible();
    await expect(page.getByText('Execution Timeline')).toBeVisible();
  });

  test('should show sidebar navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('RPA Engine')).toBeVisible();
    await expect(page.locator('nav').getByRole('link', { name: 'Workflows' })).toBeVisible();
    await expect(page.locator('nav').getByRole('link', { name: 'Executions' })).toBeVisible();
    await expect(page.locator('nav').getByRole('link', { name: 'Agents' })).toBeVisible();
    await expect(page.locator('nav').getByRole('link', { name: 'Settings' })).toBeVisible();
  });

  test('should navigate to workflows from sidebar', async ({ page }) => {
    await page.goto('/');
    await page.locator('nav').getByRole('link', { name: 'Workflows' }).click();
    await expect(page).toHaveURL(/\/workflows/);
  });

  test('should navigate to executions from sidebar', async ({ page }) => {
    await page.goto('/');
    await page.locator('nav').getByRole('link', { name: 'Executions' }).click();
    await expect(page).toHaveURL(/\/executions/);
  });
});

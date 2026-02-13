import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute } from './helpers';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);

    // Mock dashboard data
    await mockApiRoute(page, '**/api/v1/workflows*', {
      items: [
        { id: 'wf-1', name: 'Web Scraper', status: 'active', created_at: '2025-01-01T00:00:00Z' },
        { id: 'wf-2', name: 'Email Bot', status: 'draft', created_at: '2025-01-02T00:00:00Z' },
      ],
      total: 2,
      page: 1,
      per_page: 20,
    });

    await mockApiRoute(page, '**/api/v1/executions*', {
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    });

    await mockApiRoute(page, '**/api/v1/agents/stats*', {
      total: 3,
      online: 2,
      by_status: { active: 2, inactive: 1 },
    });

    await mockApiRoute(page, '**/api/v1/schedules*', {
      items: [],
      total: 0,
    });
  });

  test('should display dashboard page', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('should show sidebar navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('RPA Engine')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Workflows' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Executions' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Agents' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
  });

  test('should navigate to workflows page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Workflows' }).click();
    await expect(page).toHaveURL(/\/workflows/);
  });

  test('should navigate to executions page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Executions' }).click();
    await expect(page).toHaveURL(/\/executions/);
  });

  test('should navigate to agents page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Agents' }).click();
    await expect(page).toHaveURL(/\/agents/);
  });
});

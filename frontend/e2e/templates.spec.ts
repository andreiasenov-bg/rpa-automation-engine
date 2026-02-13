import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute } from './helpers';

const MOCK_TEMPLATES = {
  total: 3,
  templates: [
    { id: 't1', name: 'Invoice Processor', description: 'Extract invoice data from PDFs', category: 'Data Processing', icon: 'FileText', tags: ['pdf', 'extraction'], difficulty: 'intermediate', estimated_duration: '5 min', step_count: 8 },
    { id: 't2', name: 'Slack Notifier', description: 'Send automated notifications', category: 'Notifications', icon: 'MessageSquare', tags: ['slack'], difficulty: 'beginner', estimated_duration: '2 min', step_count: 3 },
    { id: 't3', name: 'Database Sync', description: 'Sync between PostgreSQL and APIs', category: 'Integrations', icon: 'Database', tags: ['database', 'sync'], difficulty: 'advanced', estimated_duration: '15 min', step_count: 12 },
  ],
};

test.describe('Templates', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, '**/api/v1/templates/categories*', { categories: ['Data Processing', 'Notifications', 'Integrations'] });
    await mockApiRoute(page, '**/api/v1/templates*', MOCK_TEMPLATES);
  });

  test('should display templates page', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('Workflow Templates')).toBeVisible();
  });

  test('should show template cards', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('Invoice Processor')).toBeVisible();
    await expect(page.getByText('Slack Notifier')).toBeVisible();
    await expect(page.getByText('Database Sync')).toBeVisible();
  });

  test('should show difficulty badges', async ({ page }) => {
    await page.goto('/templates');
    // Difficulty badges use capitalize CSS — check via the badge span elements
    await expect(page.locator('span.capitalize', { hasText: 'intermediate' })).toBeVisible();
    await expect(page.locator('span.capitalize', { hasText: 'beginner' })).toBeVisible();
    await expect(page.locator('span.capitalize', { hasText: 'advanced' })).toBeVisible();
  });

  test('should show search and filter controls', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByPlaceholder(/search/i)).toBeVisible();
    await expect(page.locator('select').first()).toBeVisible();
  });

  test('should show step count and duration', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('8 steps')).toBeVisible();
    await expect(page.getByText('5 min').first()).toBeVisible();
  });

  test('should show tags', async ({ page }) => {
    await page.goto('/templates');
    await expect(page.getByText('pdf', { exact: true })).toBeVisible();
    await expect(page.getByText('extraction', { exact: true })).toBeVisible();
  });
});

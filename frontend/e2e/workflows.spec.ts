import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute } from './helpers';

const MOCK_WORKFLOWS = {
  items: [
    {
      id: 'wf-1',
      name: 'Daily Web Scraper',
      description: 'Scrapes product prices daily',
      status: 'active',
      trigger_type: 'schedule',
      created_at: '2025-01-10T12:00:00Z',
      updated_at: '2025-06-01T08:30:00Z',
      total_executions: 150,
      success_rate: 98.5,
    },
    {
      id: 'wf-2',
      name: 'Email Notification Bot',
      description: 'Sends email digests',
      status: 'draft',
      trigger_type: 'manual',
      created_at: '2025-02-15T10:00:00Z',
      updated_at: '2025-05-20T16:00:00Z',
      total_executions: 0,
      success_rate: 0,
    },
    {
      id: 'wf-3',
      name: 'API Health Monitor',
      description: 'Monitors API endpoints every 5 minutes',
      status: 'active',
      trigger_type: 'schedule',
      created_at: '2025-03-01T09:00:00Z',
      updated_at: '2025-06-01T12:00:00Z',
      total_executions: 5000,
      success_rate: 99.2,
    },
  ],
  total: 3,
  page: 1,
  per_page: 20,
};

test.describe('Workflows', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, '**/api/v1/workflows*', MOCK_WORKFLOWS);
  });

  test('should display workflow list', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page.getByText('Daily Web Scraper')).toBeVisible();
    await expect(page.getByText('Email Notification Bot')).toBeVisible();
    await expect(page.getByText('API Health Monitor')).toBeVisible();
  });

  test('should show workflow count', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page.getByText('3').first()).toBeVisible();
  });

  test('should have create workflow button', async ({ page }) => {
    await page.goto('/workflows');
    const createBtn = page.getByRole('button', { name: /new|create/i });
    await expect(createBtn).toBeVisible();
  });

  test('should navigate to workflow editor on click', async ({ page }) => {
    await mockApiRoute(page, '**/api/v1/workflows/wf-1*', {
      id: 'wf-1',
      name: 'Daily Web Scraper',
      description: 'Scrapes product prices daily',
      status: 'active',
      definition: { nodes: [], edges: [] },
    });
    await page.goto('/workflows');
    await page.getByText('Daily Web Scraper').click();
    // Should navigate to editor
    await page.waitForURL(/\/workflows\/wf-1\/edit/, { timeout: 5_000 });
  });
});

test.describe('Workflow Editor', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, '**/api/v1/workflows/wf-1*', {
      id: 'wf-1',
      name: 'Test Workflow',
      description: 'A test workflow',
      status: 'draft',
      definition: {
        nodes: [
          { id: 'start-1', type: 'start', position: { x: 250, y: 50 }, data: { label: 'Start' } },
        ],
        edges: [],
      },
    });
    await mockApiRoute(page, '**/api/v1/task-types*', {
      task_types: [
        { name: 'web_scrape', label: 'Web Scrape', category: 'browser' },
        { name: 'api_request', label: 'API Request', category: 'integration' },
        { name: 'send_email', label: 'Send Email', category: 'communication' },
      ],
    });
  });

  test('should load workflow editor', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.getByText('Test Workflow')).toBeVisible({ timeout: 10_000 });
  });

  test('should show React Flow canvas', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    // React Flow renders a div with class "react-flow"
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10_000 });
  });
});

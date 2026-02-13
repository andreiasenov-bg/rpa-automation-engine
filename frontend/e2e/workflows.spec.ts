import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute, MOCK_WORKFLOWS } from './helpers';

test.describe('Workflows List', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, /\/api\/v1\/workflows\/\?/, MOCK_WORKFLOWS);
  });

  test('should display workflow list', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page.getByText('Invoice Processing')).toBeVisible();
    await expect(page.getByText('Customer Onboarding')).toBeVisible();
    await expect(page.getByText('Daily Report Gen')).toBeVisible();
  });

  test('should show workflow count', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page.getByText('3').first()).toBeVisible();
  });

  test('should have create workflow button', async ({ page }) => {
    await page.goto('/workflows');
    const createBtn = page.getByRole('button', { name: /new workflow|create/i });
    await expect(createBtn).toBeVisible();
  });

  test('should show workflow statuses', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page.getByText('active').first()).toBeVisible();
    await expect(page.getByText('draft').first()).toBeVisible();
  });

  test('should navigate to workflow editor on click', async ({ page }) => {
    await mockApiRoute(page, '**/api/v1/workflows/wf-1', {
      id: 'wf-1',
      name: 'Invoice Processing',
      description: 'Auto-extract invoice data',
      status: 'active',
      version: 3,
      definition: { steps: [], variables: {} },
    });
    await page.goto('/workflows');
    await page.getByText('Invoice Processing').click();
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
      version: 1,
      definition: {
        steps: [
          { id: 'step-1', type: 'api_request', name: 'Fetch Data', config: {}, position: { x: 250, y: 50 } },
          { id: 'step-2', type: 'database', name: 'Save Results', config: {}, next: [], position: { x: 250, y: 200 } },
        ],
        variables: {},
      },
    });
  });

  test('should load workflow editor', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.locator('input[value="Test Workflow"]')).toBeVisible({ timeout: 10_000 });
  });

  test('should show React Flow canvas', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10_000 });
  });

  test('should show step nodes', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.getByText('Fetch Data')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Save Results')).toBeVisible();
  });

  test('should show Add Step button', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.getByRole('button', { name: /add step/i })).toBeVisible({ timeout: 10_000 });
  });

  test('should open step palette on click', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await page.getByRole('button', { name: /add step/i }).click();
    await expect(page.getByText('Drag to canvas or click')).toBeVisible();
    await expect(page.getByText('Web Scraping')).toBeVisible();
    await expect(page.getByText('API Request').first()).toBeVisible();
    await expect(page.getByText('Database').first()).toBeVisible();
  });

  test('should add a new step via palette click', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await page.getByRole('button', { name: /add step/i }).click();
    await page.getByText('Email').click();
    await expect(page.getByText(/Email \d/).first()).toBeVisible();
    await expect(page.getByText('3 steps')).toBeVisible();
  });

  test('should show Save button', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible({ timeout: 10_000 });
  });

  test('should show Variables button', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.getByRole('button', { name: /variables/i })).toBeVisible({ timeout: 10_000 });
  });

  test('should show step count', async ({ page }) => {
    await page.goto('/workflows/wf-1/edit');
    await expect(page.getByText('2 steps')).toBeVisible({ timeout: 10_000 });
  });
});

import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute } from './helpers';

const MOCK_WORKFLOW = {
  id: 'wf-editor-test',
  name: 'Test Workflow',
  description: 'Test workflow for editor',
  status: 'draft',
  version: 1,
  definition: {
    steps: [
      { id: 'step_1', type: 'web_scraping', name: 'Scrape Data', config: {}, position: { x: 250, y: 50 }, next: ['step_2'] },
      { id: 'step_2', type: 'api_request', name: 'Send API', config: {}, position: { x: 250, y: 200 } },
    ],
    variables: {},
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-02-14T09:00:00Z',
};

test.describe('Workflow Editor Enhanced Features', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, '**/api/v1/workflows/wf-editor-test', MOCK_WORKFLOW);
    await mockApiRoute(page, '**/api/v1/workflow-variables/wf-editor-test/variables', { variables: {}, mappings: {} });
    await page.goto('/workflows/wf-editor-test/edit');
    await page.waitForLoadState('networkidle');
  });

  test('displays undo and redo buttons in toolbar', async ({ page }) => {
    await expect(page.locator('button[title*="Undo"]')).toBeVisible();
    await expect(page.locator('button[title*="Redo"]')).toBeVisible();
  });

  test('undo button is initially disabled', async ({ page }) => {
    await expect(page.locator('button[title*="Undo"]')).toBeDisabled();
  });

  test('redo button is initially disabled', async ({ page }) => {
    await expect(page.locator('button[title*="Redo"]')).toBeDisabled();
  });

  test('shows keyboard shortcuts button', async ({ page }) => {
    await expect(page.locator('button[title*="Keyboard shortcuts"]')).toBeVisible();
  });

  test('opens keyboard shortcuts modal', async ({ page }) => {
    await page.locator('button[title*="Keyboard shortcuts"]').click();
    await expect(page.getByText('Keyboard Shortcuts')).toBeVisible();
    await expect(page.getByText('Ctrl+S')).toBeVisible();
    await expect(page.getByText('Ctrl+Z')).toBeVisible();
    await expect(page.getByText('Save workflow')).toBeVisible();
  });

  test('closes shortcuts modal with Escape', async ({ page }) => {
    await page.locator('button[title*="Keyboard shortcuts"]').click();
    await expect(page.getByText('Keyboard Shortcuts')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByText('Keyboard Shortcuts')).not.toBeVisible();
  });

  test('shows step and edge count in top-right panel', async ({ page }) => {
    // The workflow has 2 steps and 1 edge
    await expect(page.getByText('2 steps')).toBeVisible();
    await expect(page.getByText('1 edge')).toBeVisible();
  });

  test('palette still works — shows task types when opened', async ({ page }) => {
    await page.getByText('Add Step').click();
    await expect(page.getByText('Drag to canvas or click')).toBeVisible();
    await expect(page.getByText('Web Scraping').first()).toBeVisible();
    await expect(page.getByText('API Request').first()).toBeVisible();
  });

  test('adding a step from palette increases step count', async ({ page }) => {
    await expect(page.getByText('2 steps')).toBeVisible();
    await page.getByText('Add Step').click();
    // Click Delay to add a simple step
    await page.locator('[role="button"]', { hasText: 'Delay' }).click();
    await expect(page.getByText('3 steps')).toBeVisible();
  });

  test('undo becomes enabled after adding a step', async ({ page }) => {
    await expect(page.locator('button[title*="Undo"]')).toBeDisabled();
    await page.getByText('Add Step').click();
    await page.locator('[role="button"]', { hasText: 'Delay' }).click();
    await expect(page.locator('button[title*="Undo"]')).toBeEnabled();
  });
});

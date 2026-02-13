import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute, MOCK_EXECUTIONS } from './helpers';

test.describe('Executions List', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, /\/api\/v1\/executions\/\?/, MOCK_EXECUTIONS);
  });

  test('should display execution list page', async ({ page }) => {
    await page.goto('/executions');
    await expect(page.getByRole('heading', { name: /Executions/i }).first()).toBeVisible();
  });

  test('should show all execution statuses', async ({ page }) => {
    await page.goto('/executions');
    await expect(page.getByText('completed').first()).toBeVisible();
    await expect(page.getByText('running').first()).toBeVisible();
    await expect(page.getByText('failed').first()).toBeVisible();
  });

  test('should show execution IDs', async ({ page }) => {
    await page.goto('/executions');
    // Page displays truncated execution IDs
    await expect(page.getByText('exec-001').first()).toBeVisible();
    await expect(page.getByText('exec-002').first()).toBeVisible();
  });

  test('should have view detail links', async ({ page }) => {
    await page.goto('/executions');
    const detailLinks = page.locator('a[href*="/executions/exec-"]');
    await expect(detailLinks.first()).toBeVisible();
  });

  test('should show retry count badges', async ({ page }) => {
    await page.goto('/executions');
    await expect(page.getByText('retry #2')).toBeVisible();
  });
});

test.describe('Execution Detail', () => {
  const MOCK_EXECUTION_DETAIL = {
    id: 'exec-001',
    workflow_id: 'wf-1',
    workflow_name: 'Invoice Processing',
    status: 'completed',
    trigger_type: 'schedule',
    started_at: '2026-02-14T09:15:00Z',
    completed_at: '2026-02-14T09:15:34Z',
    duration_ms: 34200,
    retry_count: 0,
    agent_id: 'agent-1',
    agent_name: 'worker-01',
    steps: [
      { id: 's1', name: 'Fetch PDF', type: 'api_request', status: 'completed', started_at: '2026-02-14T09:15:00Z', completed_at: '2026-02-14T09:15:10Z', duration_ms: 10000 },
      { id: 's2', name: 'Extract Data', type: 'custom_script', status: 'completed', started_at: '2026-02-14T09:15:10Z', completed_at: '2026-02-14T09:15:25Z', duration_ms: 15000 },
      { id: 's3', name: 'Save to DB', type: 'database', status: 'completed', started_at: '2026-02-14T09:15:25Z', completed_at: '2026-02-14T09:15:34Z', duration_ms: 9200 },
    ],
    logs: [],
  };

  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, '**/api/v1/executions/exec-001', MOCK_EXECUTION_DETAIL);
    await mockApiRoute(page, '**/api/v1/executions/exec-001/logs', []);
  });

  test('should display execution detail page', async ({ page }) => {
    await page.goto('/executions/exec-001');
    await expect(page.getByText('exec-001').first()).toBeVisible({ timeout: 10_000 });
  });

  test('should show execution status badge', async ({ page }) => {
    await page.goto('/executions/exec-001');
    await expect(page.getByText('completed').first()).toBeVisible({ timeout: 10_000 });
  });

  test('should show step timeline', async ({ page }) => {
    await page.goto('/executions/exec-001');
    await expect(page.getByText('Fetch PDF').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Extract Data').first()).toBeVisible();
    await expect(page.getByText('Save to DB').first()).toBeVisible();
  });

  test('should show execution metadata', async ({ page }) => {
    await page.goto('/executions/exec-001');
    await expect(page.getByText('exec-001').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/schedule/i).first()).toBeVisible();
  });
});

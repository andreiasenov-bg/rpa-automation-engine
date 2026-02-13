import { type Page, expect } from '@playwright/test';

/* ─── Auth helpers ─── */

export async function login(page: Page, email = 'admin@example.com', password = 'admin123') {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
  await page.waitForURL('/', { timeout: 10_000 });
}

export async function logout(page: Page) {
  await page.getByRole('button', { name: /log\s*out/i }).click();
  await page.waitForURL('/login', { timeout: 5_000 });
}

/* ─── Navigation helpers ─── */

export async function navigateTo(page: Page, label: string) {
  await page.getByRole('link', { name: label }).click();
  await page.waitForLoadState('networkidle');
}

/* ─── Assertion helpers ─── */

export async function expectPageTitle(page: Page, title: string) {
  await expect(page.getByRole('heading', { name: title }).first()).toBeVisible({ timeout: 5_000 });
}

export async function expectToast(page: Page, text: string) {
  await expect(page.getByText(text).first()).toBeVisible({ timeout: 5_000 });
}

/* ─── Mock API helpers ─── */

export async function mockApiRoute(
  page: Page,
  urlPattern: string | RegExp,
  body: unknown,
  status = 200,
) {
  await page.route(urlPattern, (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    }),
  );
}

export async function mockAuthToken(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'mock-jwt-token-for-testing');
    localStorage.setItem('refresh_token', 'mock-refresh-token-for-testing');
  });
}

export async function mockUser(page: Page) {
  await page.route('**/api/v1/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-user-id',
        email: 'admin@example.com',
        first_name: 'Test',
        last_name: 'Admin',
        org_id: 'test-org-id',
        is_active: true,
        roles: ['admin'],
        created_at: '2026-01-01T00:00:00Z',
      }),
    }),
  );
}

/* ─── Common mock data shapes ─── */

export const MOCK_DASHBOARD_STATS = {
  total_workflows: 24,
  active_workflows: 18,
  total_executions: 1847,
  running_executions: 3,
  completed_executions: 1692,
  failed_executions: 112,
  pending_executions: 5,
  avg_duration_ms: 34200,
  agents_online: 4,
  agents_total: 6,
  schedules_active: 12,
};

export const MOCK_WORKFLOWS = {
  total: 3,
  workflows: [
    { id: 'wf-1', name: 'Invoice Processing', description: 'Auto-extract invoice data', status: 'active', steps_count: 8, created_at: '2026-01-15T10:00:00Z', updated_at: '2026-02-14T08:30:00Z', last_run_at: '2026-02-14T09:15:00Z', last_run_status: 'completed' },
    { id: 'wf-2', name: 'Customer Onboarding', description: 'Multi-step registration', status: 'active', steps_count: 12, created_at: '2026-01-20T14:00:00Z', updated_at: '2026-02-13T16:45:00Z', last_run_at: '2026-02-14T07:00:00Z', last_run_status: 'running' },
    { id: 'wf-3', name: 'Daily Report Gen', description: 'Daily analytics reports', status: 'draft', steps_count: 6, created_at: '2026-02-01T09:00:00Z', updated_at: '2026-02-12T11:20:00Z' },
  ],
};

export const MOCK_EXECUTIONS = {
  total: 5,
  executions: [
    { id: 'exec-001', workflow_name: 'Invoice Processing', workflow_id: 'wf-1', status: 'completed', trigger_type: 'schedule', started_at: '2026-02-14T09:15:00Z', completed_at: '2026-02-14T09:15:34Z', duration_ms: 34200, retry_count: 0 },
    { id: 'exec-002', workflow_name: 'Customer Onboarding', workflow_id: 'wf-2', status: 'running', trigger_type: 'api', started_at: '2026-02-14T09:20:00Z', duration_ms: null, retry_count: 0 },
    { id: 'exec-003', workflow_name: 'Invoice Processing', workflow_id: 'wf-1', status: 'failed', trigger_type: 'schedule', started_at: '2026-02-13T23:00:00Z', completed_at: '2026-02-13T23:02:15Z', duration_ms: 135000, retry_count: 2, error_message: 'Timeout on step 3' },
    { id: 'exec-004', workflow_name: 'Daily Report Gen', workflow_id: 'wf-3', status: 'completed', trigger_type: 'manual', started_at: '2026-02-14T06:00:00Z', completed_at: '2026-02-14T06:00:22Z', duration_ms: 22100, retry_count: 0 },
    { id: 'exec-005', workflow_name: 'Invoice Processing', workflow_id: 'wf-1', status: 'cancelled', trigger_type: 'api', started_at: '2026-02-11T09:30:00Z', completed_at: '2026-02-11T09:31:00Z', duration_ms: 60000, retry_count: 0 },
  ],
};

export const MOCK_ANALYTICS_OVERVIEW = {
  total_executions: 1847,
  successful_executions: 1692,
  failed_executions: 112,
  average_duration_ms: 34200,
  success_rate: 93.8,
  period_days: 7,
};

export const MOCK_ANALYTICS_TIMELINE = {
  interval: 'day',
  period_days: 7,
  timeline: [
    { timestamp: '2026-02-08', count: 245 },
    { timestamp: '2026-02-09', count: 198 },
    { timestamp: '2026-02-10', count: 267 },
    { timestamp: '2026-02-11', count: 289 },
    { timestamp: '2026-02-12', count: 312 },
    { timestamp: '2026-02-13', count: 278 },
    { timestamp: '2026-02-14', count: 158 },
  ],
};

export const MOCK_ANALYTICS_WORKFLOWS = {
  period_days: 7,
  limit: 10,
  workflows: [
    { workflow_id: 'wf-1', workflow_name: 'Invoice Processing', execution_count: 420, success_count: 408, failure_count: 12, average_duration_ms: 34200, success_rate: 97.1, last_execution: '2026-02-14T09:15:34Z' },
  ],
};

export const MOCK_ACTIVITY = {
  activities: [
    { id: '1', action: 'execution.completed', resource_type: 'execution', resource_id: 'exec-001', actor_id: '1', actor_name: 'Admin User', description: 'Invoice Processing completed', icon: 'CheckCircle2', color: 'emerald', timestamp: '2026-02-14T09:15:34Z', metadata: null },
  ],
  grouped: { '2026-02-14': [{ id: '1', action: 'execution.completed', resource_type: 'execution', resource_id: 'exec-001', actor_id: '1', actor_name: 'Admin User', description: 'Invoice Processing completed', icon: 'CheckCircle2', color: 'emerald', timestamp: '2026-02-14T09:15:34Z', metadata: null }] },
  total: 1,
  period_days: 7,
};

/** Set up all common dashboard API mocks */
export async function setupDashboardMocks(page: Page) {
  await mockAuthToken(page);
  await mockUser(page);
  await mockApiRoute(page, '**/api/v1/dashboard/stats*', MOCK_DASHBOARD_STATS);
  await mockApiRoute(page, '**/api/v1/analytics/overview*', MOCK_ANALYTICS_OVERVIEW);
  await mockApiRoute(page, '**/api/v1/analytics/executions/timeline*', MOCK_ANALYTICS_TIMELINE);
  await mockApiRoute(page, '**/api/v1/analytics/workflows/performance*', MOCK_ANALYTICS_WORKFLOWS);
  await mockApiRoute(page, '**/api/v1/activity*', MOCK_ACTIVITY);
  await mockApiRoute(page, '**/api/v1/executions*', MOCK_EXECUTIONS);
}

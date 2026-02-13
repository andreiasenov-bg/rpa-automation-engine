import { test, expect } from '@playwright/test';
import { mockAuthToken, mockUser, mockApiRoute } from './helpers';

const MOCK_OVERVIEW = {
  organization: {
    id: 'org-1',
    name: 'Test Corp',
    plan: 'enterprise',
    created_at: '2025-01-01T00:00:00Z',
  },
  counts: {
    users: 12,
    workflows: 45,
    agents: 5,
    credentials: 8,
    executions_total: 15234,
    executions_running: 3,
    executions_failed: 42,
  },
};

const MOCK_ROLES = {
  roles: [
    { id: 'r-1', name: 'Admin', slug: 'admin', permissions: [{ id: 'p-1', code: 'admin.*' }] },
    { id: 'r-2', name: 'Operator', slug: 'operator', permissions: [{ id: 'p-2', code: 'workflows.read' }, { id: 'p-3', code: 'workflows.execute' }] },
    { id: 'r-3', name: 'Viewer', slug: 'viewer', permissions: [{ id: 'p-4', code: 'workflows.read' }] },
  ],
};

const MOCK_PERMISSIONS = {
  permissions: [
    { id: 'p-1', name: 'Full Admin', code: 'admin.*' },
    { id: 'p-2', name: 'Read Workflows', code: 'workflows.read' },
    { id: 'p-3', name: 'Execute Workflows', code: 'workflows.execute' },
    { id: 'p-4', name: 'Manage Users', code: 'users.manage' },
  ],
};

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthToken(page);
    await mockUser(page);
    await mockApiRoute(page, '**/api/v1/admin/overview*', MOCK_OVERVIEW);
    await mockApiRoute(page, '**/api/v1/admin/roles*', MOCK_ROLES);
    await mockApiRoute(page, '**/api/v1/admin/permissions*', MOCK_PERMISSIONS);
  });

  test('should display admin panel with overview', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
    await expect(page.getByText('Test Corp').first()).toBeVisible();
  });

  test('should show stat cards in overview', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.getByText('12').first()).toBeVisible();
    await expect(page.getByText('45').first()).toBeVisible();
  });

  test('should switch to roles tab', async ({ page }) => {
    await page.goto('/admin');
    await page.getByRole('button', { name: /roles/i }).click();
    await expect(page.getByText('Operator').first()).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Viewer').first()).toBeVisible({ timeout: 5_000 });
  });

  test('should show create role button', async ({ page }) => {
    await page.goto('/admin');
    await page.getByRole('button', { name: /roles/i }).click();
    await expect(page.getByRole('button', { name: /new role/i })).toBeVisible();
  });

  test('should switch to permissions tab', async ({ page }) => {
    await page.goto('/admin');
    await page.getByRole('button', { name: /permissions/i }).click();
    await expect(page.getByText('admin.*').first()).toBeVisible({ timeout: 5_000 });
  });

  test('should protect admin role from deletion', async ({ page }) => {
    await page.goto('/admin');
    await page.getByRole('button', { name: /roles/i }).click();
    await expect(page.getByText('admin').first()).toBeVisible();
  });
});

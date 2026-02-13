import { test, expect } from '@playwright/test';
import { mockApiRoute } from './helpers';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Mock auth endpoints
    await mockApiRoute(page, '**/api/v1/auth/login', {
      access_token: 'mock-jwt-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
    });
    await mockApiRoute(page, '**/api/v1/auth/me', {
      id: 'user-1',
      email: 'admin@example.com',
      first_name: 'Test',
      last_name: 'Admin',
      org_id: 'org-1',
      is_active: true,
      roles: ['admin'],
      created_at: '2026-01-01T00:00:00Z',
    });
  });

  test('should show login form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /log\s*in|sign\s*in/i })).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
    // HTML5 validation should prevent submission
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toHaveAttribute('required', '');
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should show register page', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
  });

  test('should login successfully and redirect to dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@example.com');
    await page.locator('input[type="password"]').fill('password123');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
    await page.waitForURL('/', { timeout: 5_000 });
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 5_000 });
  });

  test('should handle login failure', async ({ page }) => {
    await mockApiRoute(page, '**/api/v1/auth/login', { detail: 'Invalid credentials' }, 401);
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('wrong@example.com');
    await page.locator('input[type="password"]').fill('wrong');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
    await expect(page.getByText(/invalid|error|failed/i).first()).toBeVisible({ timeout: 5_000 });
  });
});

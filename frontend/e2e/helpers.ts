import { type Page, expect } from '@playwright/test';

/* ─── Auth helpers ─── */

export async function login(page: Page, email = 'admin@example.com', password = 'admin123') {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
  // Wait for redirect to dashboard
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
        full_name: 'Test Admin',
        role: 'admin',
        organization_id: 'test-org-id',
        is_active: true,
      }),
    }),
  );
}

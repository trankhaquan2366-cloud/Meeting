import { test, expect } from '@playwright/test';
import type { Route } from '@playwright/test';

async function mockDashboardApi(
  route: Route,
  onBookingRequest?: () => void,
): Promise<void> {
  const { pathname } = new URL(route.request().url());
  const method = route.request().method();

  if (method === 'OPTIONS') {
    await route.fulfill({
      status: 204,
      headers: {
        'access-control-allow-origin': route.request().headers().origin ?? '*',
        'access-control-allow-credentials': 'true',
        'access-control-allow-headers': 'authorization, content-type',
        'access-control-allow-methods': 'GET, POST, PATCH, OPTIONS',
      },
    });
    return;
  }

  let body: unknown = [];
  if (pathname.endsWith('/users/me')) {
    body = {
      id: 1,
      full_name: 'Playwright Tester',
      email: 'playwright@example.test',
    };
  } else if (pathname.endsWith('/meetings/validate')) {
    body = { is_valid: true, blocking_errors: [], warnings: [] };
  } else if (pathname.endsWith('/meetings/book') && method === 'POST') {
    onBookingRequest?.();
    body = { meeting: { id: 1 } };
  }

  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

async function openMeetingForm(
  page: import('@playwright/test').Page,
  onBookingRequest?: () => void,
): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'playwright-test-token');
    localStorage.setItem('user_name', 'Playwright Tester');
    localStorage.setItem('user_email', 'playwright@example.test');
    localStorage.setItem('user_id', '1');
  });
  await page.route('**/api/**', route => mockDashboardApi(route, onBookingRequest));
  await page.goto('/dashboard?preview=meeting');
  await expect(page.getByRole('dialog', { name: 'Tạo cuộc họp' })).toBeVisible();
}

test('shows required-field errors when title and date are empty', async ({ page }) => {
  let bookingRequested = false;
  await openMeetingForm(page, () => {
    bookingRequested = true;
  });

  await page.locator('#cmTitle').fill('');
  await page.locator('#cmDate').fill('');
  await page.locator('#cmModeOnline').click();
  await page.locator('#cmMeetingLink').fill('https://meet.example.test/validation');
  await page.locator('#cmSubmit').click();

  await expect(page.locator('#cmTitleError')).toHaveClass(/is-visible/);
  await expect(page.locator('#cmDateError')).toHaveClass(/is-visible/);
  await expect(page.locator('#cmTitle')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#cmDate')).toHaveAttribute('aria-invalid', 'true');
  expect(bookingRequested).toBe(false);
});

test('rejects a meeting whose end time is not after its start time', async ({ page }) => {
  let bookingRequested = false;
  await openMeetingForm(page, () => {
    bookingRequested = true;
  });

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const date = [
    tomorrow.getFullYear(),
    String(tomorrow.getMonth() + 1).padStart(2, '0'),
    String(tomorrow.getDate()).padStart(2, '0'),
  ].join('-');

  await page.locator('#cmTitle').fill('Invalid time meeting');
  await page.locator('#cmDate').fill(date);
  await page.locator('#start_time').fill('11:00');
  await page.locator('#end_time').fill('10:00');
  await page.locator('#cmModeOnline').click();
  await page.locator('#cmMeetingLink').fill('https://meet.example.test/validation');
  await page.locator('#cmSubmit').click();

  await expect(page.locator('#cmEndError')).toHaveClass(/is-visible/);
  await expect(page.locator('#end_time')).toHaveAttribute('aria-invalid', 'true');
  expect(bookingRequested).toBe(false);
});

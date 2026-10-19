import { test, expect } from '@playwright/test';
import type { Route } from '@playwright/test';

const meetingTitle = 'Playwright cancellation test';

function upcomingMeeting() {
  const start = new Date();
  start.setDate(start.getDate() + 1);
  start.setHours(10, 0, 0, 0);
  const end = new Date(start);
  end.setMinutes(30);

  return {
    id: 41,
    title: meetingTitle,
    meeting_type: 'online',
    meeting_link: 'https://meet.example.test/cancel-test',
    start_time: start.toISOString(),
    end_time: end.toISOString(),
    organizer_id: 1,
    organizer_name: 'Playwright Tester',
    is_organizer: true,
    participants: [],
    status: 'SCHEDULED',
  };
}

async function installDashboardMocks(
  page: import('@playwright/test').Page,
  isCancelled: () => boolean = () => false,
): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'playwright-test-token');
    localStorage.setItem('user_name', 'Playwright Tester');
    localStorage.setItem('user_email', 'playwright@example.test');
    localStorage.setItem('user_id', '1');
    localStorage.setItem('role', 'user');
  });

  await page.route('**/api/**', async (route: Route) => {
    const { pathname } = new URL(route.request().url());
    const method = route.request().method();
    let body: unknown = [];

    if (pathname.endsWith('/users/me')) {
      body = {
        id: 1,
        full_name: 'Playwright Tester',
        email: 'playwright@example.test',
      };
    } else if (pathname.endsWith('/rooms/')) {
      body = [
        {
          id: 1,
          name: 'Cedar Meeting Room',
          location: 'North Wing',
          capacity: 8,
          status: 'AVAILABLE',
          is_available: true,
          amenities: [],
        },
        {
          id: 2,
          name: 'Maple Meeting Room',
          location: 'South Wing',
          capacity: 6,
          status: 'AVAILABLE',
          is_available: true,
          amenities: [],
        },
      ];
    } else if (pathname.endsWith('/meetings/mine')) {
      body = isCancelled() ? [] : [upcomingMeeting()];
    } else if (pathname.endsWith('/meetings/')) {
      body = isCancelled() ? [] : [upcomingMeeting()];
    } else if (pathname.endsWith('/cancel') && method === 'PATCH') {
      body = { message: 'Meeting cancelled' };
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

async function openDashboard(page: import('@playwright/test').Page): Promise<void> {
  await installDashboardMocks(page);
  await page.goto('/dashboard');
}

test('searches available meeting rooms by name', async ({ page }) => {
  await openDashboard(page);

  const roomCards = page.locator('#roomGridOverview .room-card');
  await expect(roomCards).toHaveCount(2);

  await page.locator('#searchInput').fill('Cedar');

  await expect(roomCards).toHaveCount(1);
  await expect(roomCards.getByRole('heading', { name: 'Cedar Meeting Room' })).toBeVisible();
  await expect(roomCards.getByRole('heading', { name: 'Maple Meeting Room' })).toHaveCount(0);
});

test('cancels a meeting from the organizer booking list', async ({ page }) => {
  let cancelled = false;
  await installDashboardMocks(page, () => cancelled);
  await page.route('**/api/meetings/41/cancel', async (route: Route) => {
    if (route.request().method() === 'PATCH') cancelled = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Meeting cancelled' }),
    });
  });
  page.on('dialog', dialog => dialog.accept());

  await page.goto('/dashboard');
  await page.locator('#navMyBookings').click();
  await page.locator('#bookingTabMine').click();

  const meetingCard = page.locator('#myBookingsTableBody .booking-list-card')
    .filter({ hasText: meetingTitle });
  await expect(meetingCard).toBeVisible();
  await meetingCard.getByRole('button', { name: 'Hủy lịch' }).click();
  await expect(page.locator('#cancelMeetingModal')).toBeVisible();
  await page.getByRole('button', { name: 'Xác nhận hủy' }).click();

  await expect(page.locator('#cancelMeetingModal')).toBeHidden();
  await expect(page.locator('#myBookingsTableBody')).toContainText(
    'Bạn chưa chủ trì cuộc họp nào.',
  );
  expect(cancelled).toBe(true);
});

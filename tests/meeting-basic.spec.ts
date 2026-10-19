import { test, expect } from '@playwright/test';

interface MeetingPayload {
  title: string;
  meeting_type: string;
  meeting_link: string;
  start_time: string;
  end_time: string;
}

test('creates an online meeting from the meeting form', async ({ page }) => {
  const meetingTitle = 'Playwright meeting';
  let createdMeeting: {
    id: number;
    title: string;
    meeting_type: string;
    meeting_link: string;
    start_time: string;
    end_time: string;
    is_organizer: boolean;
    participants: [];
  } | null = null;

  await page.addInitScript(() => {
    localStorage.setItem('token', 'playwright-test-token');
    localStorage.setItem('user_name', 'Playwright Tester');
    localStorage.setItem('user_email', 'playwright@example.test');
    localStorage.setItem('user_id', '1');
  });

  await page.route('**/api/**', async route => {
    const { pathname } = new URL(route.request().url());
    const requestHeaders = route.request().headers();
    const method = route.request().method();
    const headers = {
      'access-control-allow-origin': requestHeaders.origin ?? '*',
      'access-control-allow-credentials': 'true',
      'access-control-allow-headers': 'authorization, content-type',
      'access-control-allow-methods': 'GET, POST, OPTIONS',
    };

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers });
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
      const payload = route.request().postDataJSON() as MeetingPayload;
      createdMeeting = {
        id: 1,
        title: payload.title,
        meeting_type: payload.meeting_type,
        meeting_link: payload.meeting_link,
        start_time: payload.start_time,
        end_time: payload.end_time,
        is_organizer: true,
        participants: [],
      };
      body = { meeting: { id: 1 } };
    } else if (pathname.endsWith('/meetings/mine')) {
      body = createdMeeting ? [createdMeeting] : [];
    }

    await route.fulfill({
      status: 200,
      headers,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });

  await page.goto('http://localhost:8000/dashboard?preview=meeting');

  const meetingDialog = page.getByRole('dialog', { name: 'Tạo cuộc họp' });
  await expect(meetingDialog).toBeVisible();
  await expect(page.locator('#cmOrganizerName')).toHaveText('Playwright Tester');

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const date = [
    tomorrow.getFullYear(),
    String(tomorrow.getMonth() + 1).padStart(2, '0'),
    String(tomorrow.getDate()).padStart(2, '0'),
  ].join('-');

  await page.locator('#cmTitle').fill(meetingTitle);
  await page.locator('#cmDate').fill(date);
  await page.locator('#start_time').fill('10:00');
  await page.locator('#end_time').fill('10:30');
  await page.locator('#cmModeOnline').click();
  await expect(page.locator('#cmModeOnline')).toHaveAttribute('aria-pressed', 'true');
  await page.locator('#cmMeetingLink').fill('https://meet.example.test/roomsync-e2e');

  await page.locator('#cmSubmit').click();

  await expect(page.getByRole('heading', { name: 'Đã tạo cuộc họp' })).toBeVisible();
  expect(createdMeeting?.title).toBe(meetingTitle);

  await page.locator('#cmSuccessView').getByRole('button', { name: 'Đóng' }).click();
  await page.locator('#navMyBookings').click();
  await page.locator('#bookingTabMine').click();
  await expect(
    page.locator('#myBookingsTableBody').getByText(meetingTitle, { exact: true }),
  ).toBeVisible({ timeout: 10_000 });
});

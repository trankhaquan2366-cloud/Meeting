import { test, expect } from '@playwright/test';
import type { BrowserContext, Route } from '@playwright/test';

interface MeetingRecord {
  id: number;
  title: string;
  meeting_type: string;
  meeting_link: string;
  start_time: string;
  end_time: string;
  organizer_name: string;
  is_organizer: boolean;
  participants: [];
}

interface MeetingPayload {
  title: string;
  meeting_type: string;
  meeting_link: string;
  start_time: string;
  end_time: string;
}

async function mockMeetingApi(
  context: BrowserContext,
  role: 'host' | 'participant',
  getMeeting: () => MeetingRecord | null,
  setMeeting: (meeting: MeetingRecord) => void,
): Promise<void> {
  await context.route('**/api/**', async (route: Route) => {
    const { pathname } = new URL(route.request().url());
    const method = route.request().method();

    if (method === 'OPTIONS') {
      await route.fulfill({
        status: 204,
        headers: {
          'access-control-allow-origin': route.request().headers().origin ?? '*',
          'access-control-allow-credentials': 'true',
          'access-control-allow-headers': 'authorization, content-type',
          'access-control-allow-methods': 'GET, POST, OPTIONS',
        },
      });
      return;
    }

    let body: unknown = [];

    if (pathname.endsWith('/users/me')) {
      body = {
        id: role === 'host' ? 1 : 2,
        full_name: role === 'host' ? 'Host' : 'Participant',
        email: `${role}@example.test`,
      };
    } else if (pathname.endsWith('/meetings/validate')) {
      body = { is_valid: true, blocking_errors: [], warnings: [] };
    } else if (pathname.endsWith('/meetings/book') && method === 'POST') {
      const payload = route.request().postDataJSON() as MeetingPayload;
      setMeeting({
        id: 1,
        title: payload.title,
        meeting_type: payload.meeting_type,
        meeting_link: payload.meeting_link,
        start_time: payload.start_time,
        end_time: payload.end_time,
        organizer_name: 'Host',
        is_organizer: true,
        participants: [],
      });
      body = { meeting: { id: 1 } };
    } else if (pathname.endsWith('/meetings/mine')) {
      const meeting = getMeeting();
      body = meeting
        ? [{ ...meeting, is_organizer: role === 'host' }]
        : [];
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test('host creates a meeting that appears in the participant dashboard', async ({ browser }) => {
  let createdMeeting: MeetingRecord | null = null;
  const meetingTitle = 'Họp Đánh Giá Đồ An';
  const hostContext = await browser.newContext();
  const participantContext = await browser.newContext();

  try {
    await Promise.all([
      hostContext.addInitScript(() => {
        localStorage.setItem('token', 'host-test-token');
        localStorage.setItem('user_name', 'Host');
        localStorage.setItem('user_email', 'host@example.test');
        localStorage.setItem('user_id', '1');
      }),
      participantContext.addInitScript(() => {
        localStorage.setItem('token', 'participant-test-token');
        localStorage.setItem('user_name', 'Participant');
        localStorage.setItem('user_email', 'participant@example.test');
        localStorage.setItem('user_id', '2');
      }),
      mockMeetingApi(hostContext, 'host', () => createdMeeting, meeting => {
        createdMeeting = meeting;
      }),
      mockMeetingApi(participantContext, 'participant', () => createdMeeting, meeting => {
        createdMeeting = meeting;
      }),
    ]);

    const hostPage = await hostContext.newPage();
    await hostPage.goto('/dashboard?preview=meeting');
    await expect(hostPage.getByRole('dialog', { name: 'Tạo cuộc họp' })).toBeVisible();
    const participantPage = await participantContext.newPage();
    await participantPage.goto('/dashboard?preview=meeting');
    await expect(participantPage.getByRole('dialog', { name: 'Tạo cuộc họp' })).toBeVisible();
    await participantPage.locator('#createMeetingModal button[aria-label="Đóng"]').click();

    await hostPage.locator('#cmTitle').fill(meetingTitle);
    await hostPage.locator('#cmModeOnline').click();
    await hostPage.locator('#cmMeetingLink').fill('https://meet.example.test/evaluation');
    await hostPage.locator('#cmSubmit').click();
    await expect(hostPage.getByRole('heading', { name: 'Đã tạo cuộc họp' })).toBeVisible();
    expect(createdMeeting?.title).toBe(meetingTitle);

    await participantPage.reload();
    await expect(participantPage.getByRole('dialog', { name: 'Tạo cuộc họp' })).toBeVisible();
    await participantPage.locator('#createMeetingModal button[aria-label="Đóng"]').click();
    await participantPage.locator('#navMyBookings').click();
    await expect(participantPage.locator('#viewMyBookings')).toBeVisible();
    await participantPage.locator('#bookingTabInvited').click();
    await participantPage.waitForLoadState('networkidle');
    await expect(
      participantPage.locator('#invitedBookingsList').getByText(meetingTitle, { exact: true }),
    ).toBeVisible({ timeout: 15_000 });
  } finally {
    await Promise.all([
      hostContext.close(),
      participantContext.close(),
    ]);
  }
});

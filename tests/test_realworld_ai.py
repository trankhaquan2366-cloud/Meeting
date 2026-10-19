from __future__ import annotations

import asyncio
import logging
import os
import re
import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from playwright.async_api import (
    Browser,
    BrowserContext,
    Dialog,
    Error as PlaywrightError,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = ROOT_DIR / "test-results"
GEMINI_MODEL ="gemini-1.5-flash"

load_dotenv(ROOT_DIR / ".env")
BASE_URL = os.getenv("ROOMSYNC_BASE_URL", "http://localhost:8000").rstrip("/")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USERNAME = os.getenv("ROOMSYNC_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ROOMSYNC_ADMIN_PASSWORD", "123456")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("roomsync-ai-qa")


@dataclass(frozen=True)
class RuntimeIssue:
    category: str
    detail: str


def on_console_message(message: Any, issues: list[RuntimeIssue]) -> None:
    if message.type == "error":
        issues.append(RuntimeIssue("Console Error", message.text))


def on_response(response: Response, issues: list[RuntimeIssue]) -> None:
    if response.status >= 400:
        issues.append(
            RuntimeIssue(
                "HTTP Error",
                f"{response.status} {response.request.method} {response.url}",
            )
        )


def on_request_failed(request: Any, issues: list[RuntimeIssue]) -> None:
    failure = request.failure or "Unknown network failure"
    issues.append(
        RuntimeIssue(
            "Network Error",
            f"{request.method} {request.url} ({failure})",
        )
    )


async def accept_browser_dialog(dialog: Dialog) -> None:
    await dialog.accept()


async def analyze_screenshot_with_ai(
    client: genai.Client | None,
    image_path: Path,
    context_prompt: str,
) -> None:
    if client is None:
        logger.info("Bỏ qua Gemini cho %s: chưa cấu hình GEMINI_API_KEY.", image_path.name)
        return

    prompt = f"""
Bạn là Principal QA Engineer đánh giá RoomSync/Meeting System.
Ngữ cảnh ảnh: {context_prompt}

Đưa ra nhận xét ngắn gọn bằng tiếng Việt theo đúng 4 tiêu chí:
1. Bố cục & Visual: có vỡ layout, tràn chữ, lệch căn chỉnh hoặc lỗi hiển thị không?
2. Trải nghiệm người dùng (UX Ergonomics): thông báo lỗi/thành công có rõ ràng,
   dễ hiểu với người dùng phổ thông không?
3. Điểm sẵn sàng thương mại từ 1 đến 10, kèm một câu giải thích.
4. Một đề xuất cải tiến quan trọng nhất để nâng chất lượng sản phẩm/báo cáo đồ án.
Chỉ đánh giá những gì nhìn thấy trong ảnh; không suy đoán dữ liệu phía sau.
"""
    try:
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_path.read_bytes(),
                    mime_type="image/png",
                ),
            ],
        )
    except (genai_errors.APIError, httpx.HTTPError, OSError) as exc:
        error_detail = (
            f"HTTP {exc.code}"
            if isinstance(exc, genai_errors.APIError)
            else type(exc).__name__
        )
        logger.error(
            "Gemini không phân tích được %s (%s).",
            image_path.name,
            error_detail,
        )
        return

    logger.info("=== Gemini đánh giá: %s ===", image_path.name)
    logger.info("%s", response.text or "(Gemini không trả về nội dung văn bản.)")


async def capture_and_analyze(
    page: Page,
    filename: str,
    context_prompt: str,
    client: genai.Client | None,
) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = SCREENSHOT_DIR / filename

    # Redact user identity, room details, booking data, and credential fields
    # before screenshots are saved or sent to the external vision service.
    private_content = page.locator(
        ".sidebar-user, .room-card, #myBookingsTableBody, "
        "#invitedBookingsList, #bookingCalendarGrid, "
        ".booking-guest-list, #notificationPopup, #cmOrganizerName, "
        "#cmAttendeeSuggest, #cmAttendeeChips, "
        "input[type='password'], #cmMeetingLink"
    )
    await page.screenshot(
        path=str(image_path),
        full_page=True,
        mask=[private_content],
    )
    logger.info("Đã lưu ảnh đã che dữ liệu riêng tư: %s", image_path)
    await analyze_screenshot_with_ai(client, image_path, context_prompt)


async def capture_created_meeting_id(
    response: Response,
    state: dict[str, int | None],
) -> None:
    if (
        response.request.method != "POST"
        or not response.url.rstrip("/").endswith("/meetings/book")
        or response.status >= 400
    ):
        return

    payload = await response.json()
    if not isinstance(payload, dict):
        return

    meeting = payload.get("meeting")
    meeting_id = payload.get("id") or payload.get("meeting_id")
    if meeting_id is None and isinstance(meeting, dict):
        meeting_id = meeting.get("id")
    if isinstance(meeting_id, int):
        state["meeting_id"] = meeting_id


async def cleanup_created_meeting(
    page: Page | None,
    context: BrowserContext | None,
    meeting_id: int | None,
    cancelled: bool,
    issues: list[RuntimeIssue],
) -> bool:
    if meeting_id is None or cancelled or page is None or context is None:
        return cancelled

    token = await page.evaluate("() => window.localStorage.getItem('token')")
    if not isinstance(token, str) or not token:
        issues.append(
            RuntimeIssue(
                "Cleanup Error",
                f"Không thể lấy phiên đăng nhập để hủy cuộc họp {meeting_id}.",
            )
        )
        return False

    try:
        response = await context.request.patch(
            f"{BASE_URL}/api/meetings/{meeting_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
            data={"cancellation_reason": "Automated QA cleanup"},
        )
    except PlaywrightError as exc:
        issues.append(
            RuntimeIssue(
                "Cleanup Error",
                f"PATCH /api/meetings/{meeting_id}/cancel failed ({type(exc).__name__}).",
            )
        )
        return False

    if response.status >= 400:
        issues.append(
            RuntimeIssue(
                "Cleanup Error",
                f"{response.status} PATCH {BASE_URL}/api/meetings/{meeting_id}/cancel",
            )
        )
        return False

    logger.info("Cuộc họp thử nghiệm %s đã được hủy trong cleanup.", meeting_id)
    return True


def print_runtime_report(issues: list[RuntimeIssue], scenario_completed: bool) -> None:
    print("\n=== BÁO CÁO LỖI CONSOLE / NETWORK ===")
    if issues:
        for index, issue in enumerate(issues, start=1):
            print(f"{index}. [{issue.category}] {issue.detail}")
    elif scenario_completed:
        print("✅ HỆ THỐNG ĐẠT CHUẨN TỐT NGHIỆP / COMMERCIAL READY (0 LỖI RUNTIME)")
    else:
        print("Không ghi nhận lỗi runtime; kịch bản chưa hoàn thành nên chưa kết luận sẵn sàng.")


async def run_realworld_qa() -> None:
    issues: list[RuntimeIssue] = []
    meeting_state: dict[str, int | None] = {"meeting_id": None}
    browser: Browser | None = None
    context: BrowserContext | None = None
    page: Page | None = None
    gemini_client: genai.Client | None = None
    meeting_cancelled = False
    scenario_completed = False

    if GEMINI_API_KEY:
        try:
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except (TypeError, ValueError) as exc:
            issues.append(
                RuntimeIssue("Gemini Error", f"Client initialization failed ({type(exc).__name__}).")
            )
    else:
        logger.info("Chưa cấu hình GEMINI_API_KEY; kịch bản UI vẫn chạy, phần AI sẽ được bỏ qua.")

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False, slow_mo=500)
            context = await browser.new_context()
            page = await context.new_page()
            page.on("console", lambda message: on_console_message(message, issues))
            page.on("response", lambda response: on_response(response, issues))
            page.on("requestfailed", lambda request: on_request_failed(request, issues))
            page.on(
            "response", 
            lambda res: print(f"⚠️ [Network {res.status}]: {res.request.method} {res.url}") 
            if res.status >= 400 else None
        )

            print("1. Mở dashboard và xác thực nếu được yêu cầu.")
            await page.goto(f"{BASE_URL}/static/dashboard.html", wait_until="domcontentloaded")

            login_form = page.locator("#loginForm")
            has_token = await page.evaluate(
                "() => Boolean(localStorage.getItem('token') || localStorage.getItem('access_token'))"
            )
            if not has_token and not await login_form.is_visible():
                await page.goto(f"{BASE_URL}/static/index.html", wait_until="domcontentloaded")
            if await login_form.is_visible():
                await page.locator("#username").fill(ADMIN_USERNAME)
                await page.locator("#password").fill(ADMIN_PASSWORD)
                await login_form.locator("button[type='submit']").click()
                await page.wait_for_function(
                    "() => location.pathname.endsWith('/dashboard.html') "
                    "|| location.pathname === '/dashboard'",
                    timeout=20_000,
                )

            for selector in ("#statTotal", "#statInUse", "#statAvailable", "#statBookings"):
                await page.locator(selector).wait_for(state="visible", timeout=20_000)

            print("2. Kiểm tra dashboard, thống kê và tìm kiếm phòng.")
            room_heading = page.locator("#roomGridOverview .room-card h3").first
            await room_heading.wait_for(state="visible", timeout=20_000)
            room_name = (await room_heading.inner_text()).strip()
            search = page.locator("#searchInput")
            await search.fill(room_name)
            if await page.locator("#roomGridOverview .room-card").count() == 0:
                raise AssertionError("Tìm kiếm không trả về phòng khớp với tên phòng đang hiển thị.")
            await search.fill("")
            await capture_and_analyze(
                page,
                "01_dashboard_overview.png",
                "Dashboard tổng quan sau đăng nhập, gồm các thẻ thống kê và khu vực tìm kiếm.",
                gemini_client,
            )

            print("3. Kiểm tra validation trường trống và giờ kết thúc không hợp lệ.")
            await page.locator(".cm-top-create").click()
            title_input = page.locator("#cmTitle")
            date_input = page.locator("#cmDate")
            await title_input.fill("")
            await date_input.fill("")
            await page.locator("#cmModeOnline").click()
            await page.locator("#cmMeetingLink").fill("https://example.com/roomsync-qa")
            await page.locator("#cmSubmit").click()
            await page.locator("#cmTitleError").wait_for(state="visible", timeout=5_000)
            await page.locator("#cmDateError").wait_for(state="visible", timeout=5_000)

            test_date = (date.today() + timedelta(days=1)).isoformat()
            await title_input.fill("Họp Đánh Giá Chất Lượng AI")
            await date_input.fill(test_date)
            await page.locator("#start_time").fill("15:00")
            await page.locator("#end_time").fill("13:00")
            await page.locator("#cmSubmit").click()
            await page.locator("#cmEndError").wait_for(state="visible", timeout=5_000)
            await capture_and_analyze(
                page,
                "02_validation_errors.png",
                "Form tạo cuộc họp đang hiển thị các thông báo validation khi bỏ trống trường "
                "bắt buộc và chọn giờ kết thúc trước giờ bắt đầu.",
                gemini_client,
            )

            print("4. Tạo cuộc họp online, xác minh danh sách và hủy lịch thử nghiệm.")
            meeting_title = "Họp Đánh Giá Chất Lượng AI"
            await page.locator("#start_time").fill("15:00")
            await page.locator("#end_time").fill("15:30")
            await page.locator("#cmSubmit").click()

            warning_dialog = page.locator("#cmWarningDialog")
            await page.wait_for_function(
                "() => { const success = document.querySelector('#cmSuccessView'); "
                "const warning = document.querySelector('#cmWarningDialog'); "
                "return Boolean(success && !success.classList.contains('hidden')) "
                "|| Boolean(warning && warning.open); }",
                timeout=20_000,
            )
            if await warning_dialog.is_visible():
                await warning_dialog.get_by_role(
                    "button",
                    name=re.compile("Xác nhận vẫn đặt phòng", re.IGNORECASE),
                ).click()

            await page.locator("#cmSuccessView").wait_for(state="visible", timeout=20_000)
            await page.locator("#cmSuccessView").get_by_role(
                "button",
                name="Đóng",
            ).click()
            await page.locator("#navMyBookings").click()
            await page.locator("#bookingTabMine").click()

            booking_card = page.locator("#myBookingsTableBody .booking-list-card").filter(
                has_text=meeting_title
            ).first
            await booking_card.wait_for(state="visible", timeout=20_000)
            cancel_button = booking_card.locator(".booking-cancel-button")
            onclick = await cancel_button.get_attribute("onclick")
            if meeting_state["meeting_id"] is None and onclick:
                match = re.search(r"cancelBooking\((\d+)\)", onclick)
                if match:
                    meeting_state["meeting_id"] = int(match.group(1))

            await capture_and_analyze(
                page,
                "03_meeting_created_success.png",
                "Cuộc họp online vừa tạo thành công và đang xuất hiện trong danh sách lịch do người "
                "dùng chủ trì. Nội dung động đã được che để bảo vệ dữ liệu.",
                gemini_client,
            )

            await cancel_button.click()
            cancel_modal = page.locator("#cancelMeetingModal")
            await cancel_modal.wait_for(state="visible", timeout=5_000)
            page.once("dialog", accept_browser_dialog)
            async with page.expect_response(
                lambda response: response.request.method == "PATCH"
                and "/meetings/" in response.url
                and response.url.endswith("/cancel")
                and response.status < 400,
                timeout=20_000,
            ):
                await page.locator(".cancellation-confirm-button").click()
            meeting_cancelled = True
            await cancel_modal.wait_for(state="hidden", timeout=10_000)
            await capture_and_analyze(
                page,
                "04_after_cancellation.png",
                "Danh sách cuộc họp sau khi hủy lịch thử nghiệm; thông tin lịch và danh tính đã được che.",
                gemini_client,
            )
            scenario_completed = True
    finally:
        try:
            if not meeting_cancelled:
                meeting_cancelled = await cleanup_created_meeting(
                    page,
                    context,
                    meeting_state["meeting_id"],
                    meeting_cancelled,
                    issues,
                )
        finally:
            try:
                if browser is not None:
                    await browser.close()
            finally:
                try:
                    if gemini_client is not None:
                        await gemini_client.aio.aclose()
                finally:
                    print_runtime_report(issues, scenario_completed)


if __name__ == "__main__":
    asyncio.run(run_realworld_qa())

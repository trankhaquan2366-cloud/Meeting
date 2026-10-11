import logging
import smtplib
import ssl
from contextlib import contextmanager
from email.message import EmailMessage
from html import escape
from typing import Iterator, Optional

from app.core.config import SMTPSettings, get_smtp_settings

logger = logging.getLogger(__name__)


@contextmanager
def smtp_connection(
    settings: SMTPSettings,
    timeout: int = 15,
) -> Iterator[smtplib.SMTP]:
    if settings.port == 465:
        with smtplib.SMTP_SSL(
            settings.host,
            settings.port,
            timeout=timeout,
            context=ssl.create_default_context(),
        ) as smtp:
            yield smtp
        return

    with smtplib.SMTP(settings.host, settings.port, timeout=timeout) as smtp:
        smtp.ehlo()
        if settings.starttls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        yield smtp


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """Gửi email qua giao thức SMTP. Nếu chưa cấu hình SMTP, ghi log warning và bỏ qua."""
    if not to_email or "@" not in to_email:
        logger.warning("Bỏ qua gửi email: Địa chỉ người nhận không hợp lệ (%s)", to_email)
        return False

    settings = get_smtp_settings()

    if (
        settings is None
        or not settings.host
        or not settings.username
        or not settings.password
        or not settings.from_email
    ):
        logger.info(
            "Cấu hình SMTP chưa đầy đủ (SMTP_HOST/SMTP_USER/SMTP_PASSWORD/EMAILS_FROM_EMAIL). "
            "Email '%s' tới %s được ghi log nội bộ.",
            subject,
            to_email,
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.from_email
    message["To"] = to_email
    message.set_content(body_text)

    if body_html:
        message.add_alternative(body_html, subtype="html")

    try:
        with smtp_connection(settings) as smtp:
            smtp.login(settings.username, settings.password)
            smtp.send_message(message)
        logger.info("Đã gửi email thành công tới %s (Subject: %s)", to_email, subject)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Gửi email tới %s thất bại: %s", to_email, exc)
        return False


def send_meeting_invitation_email(
    to_email: str,
    user_name: str,
    meeting_title: str,
    start_time_str: str,
    location_str: str,
    meeting_link: Optional[str] = None,
) -> bool:
    """Send a meeting invitation email without propagating SMTP failures."""
    safe_name = escape(user_name)
    safe_title = escape(meeting_title)
    safe_start = escape(start_time_str)
    safe_location = escape(location_str)
    safe_link = escape(meeting_link, quote=True) if meeting_link else None
    link_text = f"\n• Link tham gia: {meeting_link}" if meeting_link else ""
    link_html = (
        f'<p style="margin:6px 0"><strong>Link tham gia:</strong> '
        f'<a href="{safe_link}">{safe_link}</a></p>'
        if safe_link
        else ""
    )
    body_text = (
        f"Xin chào {user_name},\n\n"
        f"Bạn được mời tham dự cuộc họp '{meeting_title}'.\n\n"
        f"• Thời gian: {start_time_str}\n"
        f"• Địa điểm: {location_str}{link_text}\n\n"
        "Vui lòng đăng nhập RoomSync để xem chi tiết và phản hồi lời mời."
    )
    body_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;line-height:1.6;color:#1e293b;background:#f8fafc;padding:20px">
  <div style="max-width:580px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px">
    <h2 style="margin-top:0;color:#1d4ed8">Bạn được mời họp trên RoomSync</h2>
    <p>Xin chào <strong>{safe_name}</strong>,</p>
    <p>Bạn được mời tham dự cuộc họp:</p>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px">
      <h3 style="margin:0 0 12px;color:#0f172a">{safe_title}</h3>
      <p style="margin:6px 0"><strong>Thời gian:</strong> {safe_start}</p>
      <p style="margin:6px 0"><strong>Địa điểm:</strong> {safe_location}</p>
      {link_html}
    </div>
    <p>Đăng nhập RoomSync để xem chi tiết và phản hồi lời mời.</p>
  </div>
</body></html>"""
    return send_email(
        to_email,
        f"[RoomSync] Lời mời tham dự cuộc họp: {meeting_title}",
        body_text,
        body_html,
    )


def send_meeting_cancellation_email(
    to_email: str,
    user_name: str,
    meeting_title: str,
    start_time_str: str,
    location_str: str,
    cancellation_reason: Optional[str] = None,
) -> bool:
    """Notify an attendee that a meeting was canceled."""
    safe_name = escape(user_name)
    safe_title = escape(meeting_title)
    safe_start = escape(start_time_str)
    safe_location = escape(location_str)
    safe_reason = escape(cancellation_reason) if cancellation_reason else None
    reason_text = f"\n• Lý do: {cancellation_reason}" if cancellation_reason else ""
    reason_html = (
        f'<p style="margin:6px 0"><strong>Lý do:</strong> {safe_reason}</p>'
        if safe_reason
        else ""
    )
    body_text = (
        f"Xin chào {user_name},\n\n"
        f"Cuộc họp '{meeting_title}' đã bị hủy.\n"
        f"• Thời gian dự kiến: {start_time_str}\n"
        f"• Địa điểm: {location_str}{reason_text}\n\n"
        "Thông tin trên RoomSync đã được cập nhật."
    )
    body_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;line-height:1.6;color:#1e293b;background:#f8fafc;padding:20px">
  <div style="max-width:580px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px">
    <h2 style="margin-top:0;color:#b91c1c">Cuộc họp đã bị hủy</h2>
    <p>Xin chào <strong>{safe_name}</strong>,</p>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px">
      <h3 style="margin:0 0 12px;color:#0f172a">{safe_title}</h3>
      <p style="margin:6px 0"><strong>Thời gian dự kiến:</strong> {safe_start}</p>
      <p style="margin:6px 0"><strong>Địa điểm:</strong> {safe_location}</p>
      {reason_html}
    </div>
    <p>Thông tin trên RoomSync đã được cập nhật.</p>
  </div>
</body></html>"""
    return send_email(
        to_email,
        f"[RoomSync] Cuộc họp đã bị hủy: {meeting_title}",
        body_text,
        body_html,
    )


def send_rsvp_notification_email(
    organizer_email: str,
    organizer_name: str,
    participant_name: str,
    participant_email: str,
    meeting_title: str,
    start_time_str: str,
    status: str,
) -> bool:
    """Gửi email thông báo cho người tổ chức khi người tham dự phản hồi (Đồng ý/Từ chối)."""
    is_accepted = status.lower() == "accepted"
    status_text_vi = "ĐỒNG Ý tham gia" if is_accepted else "TỪ CHỐI tham gia"
    subject = f"[RoomSync] {participant_name} đã {status_text_vi} cuộc họp: {meeting_title}"

    body_text = (
        f"Kính gửi {organizer_name},\n\n"
        f"Thành viên {participant_name} ({participant_email}) vừa phản hồi lời mời tham gia cuộc họp của bạn:\n\n"
        f"• Cuộc họp: {meeting_title}\n"
        f"• Thời gian: {start_time_str}\n"
        f"• Trạng thái phản hồi: {status_text_vi}\n\n"
        "Vui lòng truy cập hệ thống RoomSync để xem danh sách chi tiết người tham dự.\n\n"
        "Trân trọng,\nHệ thống Quản lý Phòng họp RoomSync"
    )

    badge_color = "#16a34a" if is_accepted else "#dc2626"
    badge_bg = "#dcfce7" if is_accepted else "#fee2e2"

    body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;">
    <h2 style="color: #0f172a; margin-top: 0; font-size: 20px;">Thông báo Phản hồi Lời mời Họp</h2>
    <p>Xin chào <strong>{organizer_name}</strong>,</p>
    <p>Người tham dự <strong>{participant_name}</strong> vừa gửi phản hồi về cuộc họp của bạn:</p>
    
    <div style="background-color: #f1f5f9; border-radius: 6px; padding: 16px; margin: 20px 0;">
      <p style="margin: 6px 0;"><strong>Cuộc họp:</strong> {meeting_title}</p>
      <p style="margin: 6px 0;"><strong>Thời gian:</strong> {start_time_str}</p>
      <p style="margin: 6px 0;"><strong>Người phản hồi:</strong> {participant_name} ({participant_email})</p>
      <p style="margin: 6px 0;">
        <strong>Phản hồi:</strong> 
        <span style="display: inline-block; padding: 4px 10px; border-radius: 12px; font-weight: bold; background-color: {badge_bg}; color: {badge_color};">
          {status_text_vi}
        </span>
      </p>
    </div>

    <p style="font-size: 13px; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
      Email được gửi tự động từ hệ thống RoomSync Meeting Management.
    </p>
  </div>
</body>
</html>"""

    return send_email(organizer_email, subject, body_text, body_html)


def send_meeting_reminder_email(
    user_email: str,
    user_name: str,
    meeting_title: str,
    start_time_str: str,
    location_str: str,
    reminder_label: str,  # ví dụ: "sau 30 phút nữa" hoặc "sau 15 phút nữa"
    online_link: Optional[str] = None,
) -> bool:
    """Gửi email nhắc nhở trước cuộc họp ở mốc 30 hoặc 15 phút."""
    subject = f"[RoomSync Nhắc nhở] Cuộc họp '{meeting_title}' diễn ra {reminder_label}"

    link_info_text = f"\n• Đường dẫn họp trực tuyến: {online_link}" if online_link else ""
    link_info_html = f'<p style="margin: 6px 0;"><strong>Link trực tuyến:</strong> <a href="{online_link}" target="_blank">{online_link}</a></p>' if online_link else ""

    body_text = (
        f"Kính gửi {user_name},\n\n"
        f"Hệ thống RoomSync xin nhắc nhở bạn về cuộc họp sắp diễn ra {reminder_label}:\n\n"
        f"• Cuộc họp: {meeting_title}\n"
        f"• Thời gian bắt đầu: {start_time_str}\n"
        f"• Địa điểm / Phòng họp: {location_str}"
        f"{link_info_text}\n\n"
        "Vui lòng sắp xếp thời gian tham gia đúng giờ.\n\n"
        "Trân trọng,\nHệ thống Quản lý Phòng họp RoomSync"
    )

    body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;">
    <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
      <strong style="color: #1d4ed8; font-size: 16px;">⏰ Nhắc nhở lịch họp ({reminder_label})</strong>
    </div>
    <p>Xin chào <strong>{user_name}</strong>,</p>
    <p>Bạn có một cuộc họp sắp diễn ra:</p>
    
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin: 16px 0;">
      <h3 style="margin-top: 0; color: #0f172a;">{meeting_title}</h3>
      <p style="margin: 6px 0;"><strong>Thời gian:</strong> {start_time_str}</p>
      <p style="margin: 6px 0;"><strong>Địa điểm:</strong> {location_str}</p>
      {link_info_html}
    </div>

    <p style="font-size: 13px; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
      Email được gửi tự động từ hệ thống RoomSync Meeting Management.
    </p>
  </div>
</body>
</html>"""

    return send_email(user_email, subject, body_text, body_html)

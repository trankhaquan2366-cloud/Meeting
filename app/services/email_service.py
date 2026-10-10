import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


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

    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username
    port = int(os.getenv("SMTP_PORT", "587"))
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().lower() in {"1", "true", "yes"}

    if not all((host, username, password, from_email)):
        logger.info(
            "Cấu hình SMTP chưa đầy đủ (SMTP_HOST/USERNAME/PASSWORD/FROM_EMAIL). "
            "Email '%s' tới %s được ghi log nội bộ.",
            subject,
            to_email,
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body_text)

    if body_html:
        message.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            if use_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)
        logger.info("Đã gửi email thành công tới %s (Subject: %s)", to_email, subject)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Gửi email tới %s thất bại: %s", to_email, exc)
        return False


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

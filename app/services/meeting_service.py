from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status

from app.models.room import Room
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.meeting import MeetingCreateRequest

logger = logging.getLogger(__name__)

class MeetingService:

    @staticmethod
    def cancel_meeting(db: Session, meeting_id: int, current_user: User):
        """Cancel a meeting without deleting it or its participants."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kh?ng t?m th?y cu?c h?p.",
            )

        is_admin = str(current_user.role or "").strip().casefold() == "admin"
        if meeting.organizer_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="B?n kh?ng c? quy?n h?y cu?c h?p n?y.",
            )

        # Idempotent: repeating the operation is a successful no-op.
        if meeting.status != "CANCELLED":
            meeting.status = "CANCELLED"
            try:
                db.commit()
                db.refresh(meeting)
            except SQLAlchemyError as exc:
                db.rollback()
                logger.exception(
                    "Failed to cancel meeting_id=%s for user_id=%s",
                    meeting_id,
                    current_user.id,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Không thể hủy cuộc họp do lỗi cơ sở dữ liệu. "
                    "Vui lòng kiểm tra migration schema và thử lại.",
                ) from exc

        return meeting

    @staticmethod
    def get_all_active_rooms(db: Session):
        """VIỆC 1: Lấy danh sách tất cả phòng họp đang hoạt động"""
        return db.query(Room).filter(Room.is_active == True).all()

    @staticmethod
    def create_meeting(db: Session, payload: MeetingCreateRequest, organizer_id: int | None = None):
        """VIỆC 2 & 3: Đặt phòng đơn hoặc định kỳ + Chặn quá khứ + Kiểm tra chống trùng lịch toàn diện"""

        # 0. Kiểm tra thời gian bắt đầu không được ở trong quá khứ
        now = datetime.now()
        if payload.start_time < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể đặt lịch họp với thời gian bắt đầu nằm trong quá khứ!"
            )

        # 0b. Kiểm tra end_time phải sau start_time
        if payload.end_time <= payload.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thời gian kết thúc phải sau thời gian bắt đầu!"
            )

        # 1. Xác định meeting_type và kiểm tra phòng (chỉ khi offline)
        meeting_type = getattr(payload, 'meeting_type', 'offline') or 'offline'
        meeting_link = (
            getattr(payload, 'meeting_link', None)
            or getattr(payload, 'online_link', None)
            or ''
        ).strip() or None
        room_id = payload.room_id

        if meeting_type == 'offline':
            if room_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Offline meetings require a room_id",
                )
            room = db.query(Room).filter(
                Room.id == room_id,
                Room.is_active == True
            ).first()
            if not room:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phòng họp không tồn tại hoặc đã ngưng hoạt động!"
                )
        elif meeting_type == 'online':
            if not meeting_link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Online meetings require a meeting_link",
                )
            room_id = None
            room = None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="meeting_type must be 'offline' or 'online'",
            )

        # 2. Xử lý danh sách các mốc thời gian (Hỗ trợ cả lịch đơn và lịch định kỳ tuần/tháng)
        meeting_dates = []
        start_date = payload.start_time
        end_date = payload.end_time
        
        # Lấy thông tin lặp lịch từ payload
        recurrence_type = getattr(payload, "recurrence_type", "none")
        recurrence_end_date = getattr(payload, "recurrence_end_date", None)

        if recurrence_type == "until_changed" and not recurrence_end_date:
            recurrence_end_date = start_date + timedelta(days=365)

        if not recurrence_type or recurrence_type == "none" or not recurrence_end_date:
            meeting_dates.append((start_date, end_date))
        else:
            # Vòng lặp sinh ra các khoảng thời gian lặp định kỳ
            current_start = start_date
            current_end = end_date
            while current_start <= recurrence_end_date:
                meeting_dates.append((current_start, current_end))
                if recurrence_type == "weekly":
                    current_start += timedelta(weeks=1)
                    current_end += timedelta(weeks=1)
                elif recurrence_type == "monthly":
                    current_start += timedelta(days=30)
                    current_end += timedelta(days=30)
                elif recurrence_type == "until_changed":
                    current_start += timedelta(days=30)
                    current_end += timedelta(days=30)
                else:
                    break

        # 3. Vòng lặp kiểm tra trùng phòng & quản lý Transaction (Rollback nếu dính bất kỳ ngày nào)
        try:
            created_meetings = []
            requested_equipments = getattr(payload, "equipments", []) or []

            # Kiểm tra tồn kho thiết bị cho từng khung giờ
            if requested_equipments:
                from app.services.equipment_service import check_equipment_availability
                for s_time, e_time in meeting_dates:
                    check_equipment_availability(db, s_time, e_time, requested_equipments)
            
            for s_time, e_time in meeting_dates:
                # Kiểm tra conflict phòng — chỉ áp dụng cho OFFLINE meeting
                if meeting_type == 'offline':
                    overlapping_meeting = db.query(Meeting).filter(
                        Meeting.room_id == room_id,
                        Meeting.status.notin_(["CANCELLED", "canceled"]),
                        and_(
                            Meeting.start_time < e_time,
                            Meeting.end_time > s_time
                        )
                    ).first()

                    if overlapping_meeting:
                        db.rollback()
                        date_str = s_time.strftime("%d/%m/%Y lúc %H:%M")
                        if not recurrence_type or recurrence_type == "none":
                            detail_msg = f"Phòng họp '{room.name}' đã có cuộc họp trong khung giờ này."
                        else:
                            detail_msg = f"Phòng họp '{room.name}' đã bị trùng lịch vào ngày {date_str}."
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=detail_msg
                        )

                # Tạo bản ghi cuộc họp
                new_meeting = Meeting(
                    title=payload.title,
                    description=payload.description,
                    meeting_type=meeting_type,
                    meeting_link=meeting_link,
                    room_id=room_id,
                    organizer_id=organizer_id,
                    start_time=s_time,
                    end_time=e_time,
                    is_recurring=recurrence_type not in (None, "none"),
                    recurring_type=recurrence_type if recurrence_type != "none" else None,
                    status="scheduled"
                )
                db.add(new_meeting)
                db.flush()

                # Lưu các thiết bị mượn kèm
                if requested_equipments:
                    from app.models.equipment import MeetingEquipment
                    for item in requested_equipments:
                        me = MeetingEquipment(
                            meeting_id=new_meeting.id,
                            equipment_id=item.equipment_id,
                            quantity=item.quantity,
                            note=getattr(item, 'note', None)
                        )
                        db.add(me)

                # Lưu participants — D2: skip organizer, atomic flush
                participant_ids_list = getattr(payload, 'participant_ids', []) or []
                for pid in participant_ids_list:
                    if pid == organizer_id:  # D2: organizer đã track qua organizer_id, skip
                        continue
                    mp = MeetingParticipant(meeting_id=new_meeting.id, user_id=pid)
                    db.add(mp)

                if participant_ids_list:
                    try:
                        db.flush()  # một flush duy nhất, atomic với transaction
                    except IntegrityError:
                        db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="participant_ids chứa user không tồn tại hoặc bị trùng lặp."
                        )

                created_meetings.append(new_meeting)

            # Tiến hành commit lưu tất cả vào database
            db.commit()
            for m in created_meetings:
                db.refresh(m)
                
            return created_meetings

        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def calculate_suggested_times(db: Session, participant_ids: list[int], date_str: str, duration_minutes: int):
        """VIỆC CỦA LIÊM: Thuật toán truy vấn, so sánh lịch rảnh/bận để tìm khung giờ trống chung"""
        
        # KIỂM TRA: Đảm bảo tất cả user trong participant_ids phải tồn tại trong database
        existing_users = db.query(User).filter(User.id.in_(participant_ids)).all()
        existing_user_ids = {user.id for user in existing_users}
        missing_ids = [uid for uid in participant_ids if uid not in existing_user_ids]
        
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy người tham gia với ID: {missing_ids}"
            )

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Khung giờ làm việc mặc định trong ngày: 08:00 - 12:00 và 13:00 - 17:00
        work_start1 = datetime.combine(target_date, datetime.strptime("08:00", "%H:%M").time())
        work_end1 = datetime.combine(target_date, datetime.strptime("12:00", "%H:%M").time())
        work_start2 = datetime.combine(target_date, datetime.strptime("13:00", "%H:%M").time())
        work_end2 = datetime.combine(target_date, datetime.strptime("17:00", "%H:%M").time())
        
        working_intervals = [(work_start1, work_end1), (work_start2, work_end2)]

        # Lấy toàn bộ cuộc họp trong ngày, loại trừ trạng thái 'canceled'
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        
        meetings = db.query(Meeting).filter(
            Meeting.status.notin_(["CANCELLED", "canceled"]),
            Meeting.start_time <= day_end,
            Meeting.end_time >= day_start,
            Meeting.organizer_id.in_(participant_ids)
        ).all()

        # Thu thập các khoảng thời gian bận
        busy_intervals = [(m.start_time, m.end_time) for m in meetings]

        # Sắp xếp và gộp các khoảng bận bị chồng chéo
        busy_intervals.sort(key=lambda x: x[0])
        merged_busy = []
        for interval in busy_intervals:
            if not merged_busy or merged_busy[-1][1] <= interval[0]:
                merged_busy.append(interval)
            else:
                merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], interval[1]))

        # Tính toán khoảng thời gian rảnh bằng cách trừ khoảng bận khỏi giờ làm việc
        free_slots = []
        for w_start, w_end in working_intervals:
            current_start = w_start
            for b_start, b_end in merged_busy:
                if b_end <= current_start:
                    continue
                if b_start >= w_end:
                    break
                if b_start > current_start:
                    free_slots.append((current_start, b_start))
                current_start = max(current_start, b_end)
            if current_start < w_end:
                free_slots.append((current_start, w_end))

        # Lọc ra các khoảng rảnh có độ dài >= duration_minutes
        suggested_slots = []
        duration_delta = timedelta(minutes=duration_minutes)
        for f_start, f_end in free_slots:
            slot_start = f_start
            while slot_start + duration_delta <= f_end:
                slot_end = slot_start + duration_delta
                suggested_slots.append({
                    "start_time": slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end_time": slot_end.strftime("%Y-%m-%dT%H:%M:%S")
                })
                slot_start += timedelta(minutes=30)  # Bước nhảy gợi ý mỗi 30 phút

        return {"suggested_slots": suggested_slots}

    @staticmethod
    def suggest_time(db: Session, payload):
        """Alias cho calculate_suggested_times — dùng bởi router /suggest-time."""
        return MeetingService.calculate_suggested_times(
            db=db,
            participant_ids=payload.participant_ids,
            date_str=payload.date,
            duration_minutes=payload.duration_minutes
        )

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment
from app.models.user import User  # Thêm import model User nếu chưa có
from app.schemas.meeting import MeetingCreateRequest

class MeetingService:


    @staticmethod
    def book_equipments(db: Session, meeting_id: int, equipment_ids: list[int], current_user: User):
        """Atomically attach available equipment to a meeting."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cuộc họp.",
            )

        if meeting.organizer_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền đặt thiết bị cho cuộc họp này.",
            )

        # De-duplicate while preserving the request order.
        unique_ids = list(dict.fromkeys(equipment_ids))
        if not unique_ids:
            return {"meeting_id": meeting.id, "equipment_ids": []}

        try:
            equipments = (
                db.query(Equipment)
                .filter(Equipment.id.in_(unique_ids))
                .with_for_update()
                .all()
            )
            equipment_by_id = {equipment.id: equipment for equipment in equipments}
            missing_ids = [equipment_id for equipment_id in unique_ids if equipment_id not in equipment_by_id]
            if missing_ids:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy thiết bị với ID: {missing_ids}",
                )

            invalid = [
                equipment for equipment in equipments
                if not equipment.is_active
                or (equipment.status or "").strip().lower() in {
                    "maintenance", "under_maintenance", "under maintenance",
                }
            ]
            if invalid:
                db.rollback()
                invalid_ids = [equipment.id for equipment in invalid]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Thiết bị không hoạt động hoặc đang bảo trì: {invalid_ids}",
                )

            existing_links = db.query(MeetingEquipment).filter(
                MeetingEquipment.meeting_id == meeting.id,
                MeetingEquipment.equipment_id.in_(unique_ids),
            ).all()
            existing_ids = {link.equipment_id for link in existing_links}

            # Check each new equipment against all non-cancelled meetings whose
            # intervals overlap. The target meeting itself is explicitly ignored.
            for equipment_id in unique_ids:
                if equipment_id in existing_ids:
                    continue
                conflict = (
                    db.query(MeetingEquipment)
                    .join(Meeting, Meeting.id == MeetingEquipment.meeting_id)
                    .filter(
                        MeetingEquipment.equipment_id == equipment_id,
                        MeetingEquipment.meeting_id != meeting.id,
                        Meeting.status.notin_(["CANCELLED", "canceled"]),
                        Meeting.start_time < meeting.end_time,
                        Meeting.end_time > meeting.start_time,
                    )
                    .first()
                )
                if conflict:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Thiết bị {equipment_id} đã được đặt trong khung giờ trùng với cuộc họp.",
                    )

            for equipment_id in unique_ids:
                if equipment_id not in existing_ids:
                    db.add(MeetingEquipment(meeting_id=meeting.id, equipment_id=equipment_id))

            db.commit()
            assigned_ids = [
                link.equipment_id
                for link in db.query(MeetingEquipment)
                .filter(MeetingEquipment.meeting_id == meeting.id)
                .order_by(MeetingEquipment.id)
                .all()
            ]
            return {"meeting_id": meeting.id, "equipment_ids": assigned_ids}
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def cancel_meeting(db: Session, meeting_id: int, current_user: User):
        """Cancel a meeting without deleting it or its participants."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kh?ng t?m th?y cu?c h?p.",
            )

        is_admin = current_user.role == "admin"
        if meeting.organizer_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="B?n kh?ng c? quy?n h?y cu?c h?p n?y.",
            )

        # Idempotent: repeating the operation is a successful no-op.
        if meeting.status != "CANCELLED":
            meeting.status = "CANCELLED"
            db.commit()
            db.refresh(meeting)

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

        # 1. Kiểm tra phòng họp có tồn tại và active không
        room = db.query(Room).filter(Room.id == payload.room_id, Room.is_active == True).first()

        if not room:
         raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Phòng họp không tồn tại hoặc đã bị ngưng hoạt động!"
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
            
            for s_time, e_time in meeting_dates:
                # Kiểm tra chồng lặp thời gian cho từng ngày trong chu kỳ đối với đúng phòng đó
                overlapping_meeting = db.query(Meeting).filter(
                    Meeting.room_id == payload.room_id,
                    Meeting.status.notin_(["CANCELLED", "canceled"]),
                    and_(
                        Meeting.start_time < e_time,
                        Meeting.end_time > s_time
                    )
                ).first()

                # Nếu tìm thấy lịch trùng -> Rollback yêu cầu hiện tại
                if overlapping_meeting:
                    db.rollback()
                    date_str = s_time.strftime("%d/%m/%Y lúc %H:%M")
                    
                    if not recurrence_type or recurrence_type == "none":
                        detail_msg = f"Phòng họp '{room.name}' đã bị trùng khung giờ vào ngày {date_str}! Vui lòng chọn thời gian khác."
                    else:
                        detail_msg = f"Phòng họp '{room.name}' đã bị trùng lịch vào ngày {date_str}. Yêu cầu đặt chuỗi định kỳ đã bị từ chối để tránh xung đột."

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=detail_msg
                    )

                # Tạo bản ghi đặt phòng cho ngày hiện tại
                new_meeting = Meeting(
                    title=payload.title,
                    description=payload.description,
                    room_id=payload.room_id,
                    organizer_id=organizer_id,
                    start_time=s_time,
                    end_time=e_time,
                    is_recurring=recurrence_type not in (None, "none"),
                    recurring_type=recurrence_type if recurrence_type != "none" else None,
                    status="scheduled"
                )
                db.add(new_meeting)
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
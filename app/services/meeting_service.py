 feature/meeting-api
from datetime import datetime, timedelta

from datetime import datetime
 main
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.room import Room
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreateRequest

class MeetingService:

    @staticmethod
    def get_all_active_rooms(db: Session):
        """VIỆC 1: Lấy danh sách tất cả phòng họp đang hoạt động"""
        return db.query(Room).filter(Room.is_active == True).all()

    @staticmethod
    def create_meeting(db: Session, payload: MeetingCreateRequest, organizer_id: int | None = None):
 feature/meeting-api
        """VIỆC 2 & 3: Đặt phòng đơn hoặc định kỳ + Chặn quá khứ + Kiểm tra chống trùng lịch toàn diện"""

        # 0. Kiểm tra thời gian bắt đầu không được ở trong quá khứ
        now = datetime.now()
        if payload.start_time < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể đặt lịch họp với thời gian bắt đầu nằm trong quá khứ!"
            )

        """VIỆC 2 & 3: Đặt phòng + Kiểm tra chống trùng lịch"""
 main

        # 1. Kiểm tra phòng họp có tồn tại và active không
        room = db.query(Room).filter(Room.id == payload.room_id, Room.is_active == True).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng họp không tồn tại hoặc đã bị khóa!"
            )

 feature/meeting-api
        # 2. Xử lý danh sách các mốc thời gian (Hỗ trợ cả lịch đơn và lịch định kỳ tuần/tháng)
        meeting_dates = []
        start_date = payload.start_time
        end_date = payload.end_time
        
        # Lấy thông tin lặp lịch từ payload
        recurrence_type = getattr(payload, "recurrence_type", "none")
        recurrence_end_date = getattr(payload, "recurrence_end_date", None)

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
                else:
                    break

        # 3. Vòng lặp kiểm tra trùng phòng & quản lý Transaction (Rollback yêu cầu mới nếu dính bất kỳ ngày nào)
        try:
            created_meetings = []
            
            for s_time, e_time in meeting_dates:
                # Kiểm tra chồng lặp thời gian cho từng ngày trong chu kỳ đối với đúng phòng đó
                overlapping_meeting = db.query(Meeting).filter(
                    Meeting.room_id == payload.room_id,
                    Meeting.status != "canceled",
                    and_(
                        Meeting.start_time < e_time,
                        Meeting.end_time > s_time
                    )
                ).first()

                # Nếu tìm thấy lịch trùng -> Rollback yêu cầu hiện tại, giữ nguyên các lịch cũ đã tồn tại trước đó
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
                    status="scheduled"
                )
                db.add(new_meeting)
                created_meetings.append(new_meeting)

            # Nếu mọi thứ đều mượt mà, tiến hành commit lưu tất cả vào database
            db.commit()
            for m in created_meetings:
                db.refresh(m)
                
            return created_meetings

        except Exception as e:
            db.rollback()
            raise e

        # 2. VIỆC 3: LOGIC CHỐNG TRÙNG LỊCH HỌP (OVERLAPPING CHECK)
        # Tìm cuộc họp nào thuộc phòng này, chưa bị hủy (status != 'canceled')
        # và có khoảng thời gian đè đan xen với khoảng thời gian mới đăng ký.
        overlapping_meeting = db.query(Meeting).filter(
            Meeting.room_id == payload.room_id,
            Meeting.status != "canceled",
            and_(
                Meeting.start_time < payload.end_time,
                Meeting.end_time > payload.start_time
            )
        ).first()

        # Nếu tìm thấy dù chỉ 1 cuộc họp bị trùng -> Chặn lại ngay!
        if overlapping_meeting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phòng họp '{room.name}' đã bị trùng lịch! "
                       f"Đã có cuộc họp '{overlapping_meeting.title}' "
                       f"từ {overlapping_meeting.start_time.strftime('%H:%M')} "
                       f"đến {overlapping_meeting.end_time.strftime('%H:%M')}."
            )

        # 3. Tạo bản ghi đặt phòng mới nếu thỏa mãn điều kiện
        new_meeting = Meeting(
            title=payload.title,
            description=payload.description,
            room_id=payload.room_id,
            organizer_id=organizer_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status="scheduled"
        )

        db.add(new_meeting)
        db.commit()
        db.refresh(new_meeting)
        return new_meeting
 main

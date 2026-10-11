from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from app.models.room import Room
from app.models.meeting import Meeting


class ReportRoomService:
    @staticmethod
    async def get_room_usage_report(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        room_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # 1. Thiết lập giá trị thời gian mặc định nếu không được cung cấp
        now = datetime.now()
        if not end_date:
            end_date = now
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # 2. Tính toán tham số days: days = max((end_date - start_date).total_seconds()/86400, 1/24)
        total_seconds = (end_date - start_date).total_seconds()
        days = max(total_seconds / 86400.0, 1.0 / 24.0)

        # 3. Điều kiện lọc cuộc họp (chỉ CONFIRMED hoặc COMPLETED và thuộc khoảng thời gian)
        meeting_filter = and_(
            Meeting.status.in_(["CONFIRMED", "COMPLETED"]),
            Meeting.start_time >= start_date,
            Meeting.end_time <= end_date
        )

        # Tính thời lượng cuộc họp bằng giây qua TIMESTAMPDIFF (tối ưu cho MySQL)
        meeting_duration_hours = func.timestampdiff(func.SECOND, Meeting.start_time, Meeting.end_time) / 3600.0

        # 4. Truy vấn cơ sở dữ liệu tối ưu với LEFT JOIN và GROUP BY
        query = (
            select(
                Room.id.label("room_id"),
                Room.name.label("room_name"),
                func.count(case((meeting_filter, Meeting.id), else_=None)).label("total_meetings"),
                func.coalesce(
                    func.sum(case((meeting_filter, meeting_duration_hours), else_=0.0)),
                    0.0
                ).label("total_hours")
            )
            .select_from(Room)
            .outerjoin(Meeting, Room.id == Meeting.room_id)
            .group_by(Room.id, Room.name)
        )

        if room_id is not None:
            query = query.where(Room.id == room_id)

        result = await db.execute(query)
        rows = result.all()

        # 5. Duyệt và tính toán các chỉ số cho từng phòng
        room_details: List[Dict[str, Any]] = []
        sum_occupancy_rate = 0.0
        total_system_meetings = 0
        total_system_hours = 0.0

        for row in rows:
            r_id = row.room_id
            r_name = row.room_name
            t_meetings = int(row.total_meetings)
            t_hours = round(float(row.total_hours), 1)

            # Công thức: occupancy_rate = (total_hours / (days * 8)) * 100
            raw_occupancy = (t_hours / (days * 8.0)) * 100.0
            occ_rate = round(raw_occupancy, 1)

            room_details.append({
                "room_id": r_id,
                "room_name": r_name,
                "total_meetings": t_meetings,
                "total_hours": t_hours,
                "occupancy_rate": occ_rate
            })

            total_system_meetings += t_meetings
            total_system_hours += t_hours
            sum_occupancy_rate += occ_rate

        # 6. Tổng hợp dữ liệu summary toàn hệ thống
        total_rooms = len(room_details)
        avg_occupancy_rate = round(sum_occupancy_rate / total_rooms, 1) if total_rooms > 0 else 0.0
        total_system_hours = round(total_system_hours, 1)

        return {
            "summary": {
                "total_rooms": total_rooms,
                "total_meetings": total_system_meetings,
                "total_hours": total_system_hours,
                "average_occupancy_rate": avg_occupancy_rate
            },
            "room_details": room_details
        }
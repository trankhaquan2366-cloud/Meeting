from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RoomReportDetail(BaseModel):
    room_id: int = Field(..., description="ID của phòng họp")
    room_name: str = Field(..., description="Tên phòng họp")
    total_meetings: int = Field(..., description="Tổng số cuộc họp hợp lệ")
    total_hours: float = Field(..., description="Tổng số giờ họp (đã làm tròn 1 chữ số thập phân)")
    occupancy_rate: float = Field(..., description="Tỷ lệ lấp đầy (%) (đã làm tròn 1 chữ số thập phân)")

    model_config = ConfigDict(from_attributes=True)


class RoomReportSummary(BaseModel):
    total_rooms: int = Field(..., description="Tổng số phòng họp trong báo cáo")
    total_meetings: int = Field(..., description="Tổng số cuộc họp toàn hệ thống")
    total_hours: float = Field(..., description="Tổng số giờ họp toàn hệ thống")
    average_occupancy_rate: float = Field(..., description="Trung bình occupancy_rate các phòng")


class RoomUsageReportResponse(BaseModel):
    summary: RoomReportSummary
    room_details: List[RoomReportDetail]
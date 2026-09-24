from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional

app = FastAPI(title="RoomSync API", version="1.0.0")

# Cấu hình CORS để Front-end kết nối không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSDL Giả lập (In-Memory)
users_db = [{"full_name": "System Admin", "email": "admin@congty.com", "password": "123456"}]

rooms_db = [
    {"id": 1, "name": "Phòng Họp Hội Đồng", "floor": "Tầng 5", "capacity": "16-20 người", "is_available": True, "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=500"},
    {"id": 2, "name": "Phòng Họp Sáng Tạo", "floor": "Tầng 3", "capacity": "6-8 người", "is_available": False, "image_url": "https://images.unsplash.com/photo-1517502884422-41eaead166d4?w=500"},
    {"id": 3, "name": "Phòng Hội Nghị A", "floor": "Tầng 2", "capacity": "10-12 người", "is_available": True, "image_url": "https://images.unsplash.com/photo-1431540015161-0bf868a2d407?w=500"}
]

bookings_db = [
    {"id": 1, "title": "Họp Hội Đồng - Quý 3", "room_id": 1, "start_time": "2026-09-24T09:00:00", "end_time": "2026-09-24T10:30:00"}
]

# Struct dữ liệu đầu vào (Schemas)
class RegisterModel(BaseModel):
    fullName: str
    email: EmailStr
    password: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str

class RoomModel(BaseModel):
    name: str
    floor: str
    capacity: str

class BookingModel(BaseModel):
    title: str
    room_id: int
    date: str
    start_time: str
    end_time: str

# API Endpoints
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterModel):
    for u in users_db:
        if u["email"] == data.email:
            raise HTTPException(status_code=400, detail="Email đã tồn tại!")
    users_db.append({"full_name": data.fullName, "email": data.email, "password": data.password})
    return {"message": "Đăng ký thành công!"}

@app.post("/api/auth/login")
def login(data: LoginModel):
    for u in users_db:
        if u["email"] == data.email and u["password"] == data.password:
            return {"status": "success", "token": f"token-admin-{data.email}" if "admin" in data.email else f"token-user-{data.email}"}
    raise HTTPException(status_code=400, detail="Sai tài khoản hoặc mật khẩu!")

@app.get("/api/rooms")
def get_rooms():
    return rooms_db

@app.post("/api/rooms", status_code=status.HTTP_201_CREATED)
def create_room(room: RoomModel):
    new_room = {"id": len(rooms_db) + 1, "name": room.name, "floor": room.floor, "capacity": room.capacity, "is_available": True, "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=500"}
    rooms_db.append(new_room)
    return new_room

@app.delete("/api/rooms/{room_id}")
def delete_room(room_id: int):
    global rooms_db
    rooms_db = [r for r in rooms_db if r["id"] != room_id]
    return {"message": "Đã xóa phòng thành công!"}

@app.get("/api/bookings")
def get_bookings():
    return bookings_db

@app.post("/api/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(b: BookingModel):
    new_booking = {"id": len(bookings_db) + 1, "title": b.title, "room_id": b.room_id, "start_time": f"{b.date}T{b.start_time}:00", "end_time": f"{b.date}T{b.end_time}:00"}
    bookings_db.append(new_booking)
    return new_booking

# Phục vụ Static Files Front-end
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

@app.get("/dashboard.html")
def read_dashboard():
    return FileResponse("static/dashboard.html")
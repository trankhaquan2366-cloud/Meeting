from fastapi import FastAPI

app = FastAPI(title="Meeting Management API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Chào mừng đến với API Quản lý phòng họp của Tam Thái Tử!"}
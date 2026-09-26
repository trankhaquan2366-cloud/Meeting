from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.responses import Response
from app.routers import auth, room

app = FastAPI(title="RoomSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# BẮT BUỘC Phải include router auth ở đây
app.include_router(auth.router)
app.include_router(room.router)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

@app.get("/")
def read_root():
    return {"message": "Server RoomSync đang chạy!"}
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)
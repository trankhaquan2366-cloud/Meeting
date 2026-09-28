from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.routers import auth, rooms, meetings
from app.core.database import Base, engine, get_db
from app.core.security import authenticate_user
from app.routers.auth import issue_token
from app.schemas.auth import LoginRequest
import app.models  # Register all SQLAlchemy models before create_all.
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Meeting Management System API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(meetings.router, prefix="/api", tags=["meetings"])
@app.post("/api/login", tags=["auth"])
def legacy_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Compatibility endpoint; it uses the exact same database auth as /api/auth/login."""
    user = authenticate_user(db, payload.username, payload.password)
    token_response = issue_token(user)
    return {
        **token_response.model_dump(),
        "user_name": token_response.full_name,
    }
@app.get("/", tags=["Root"])
def read_root():
    return {"status": "success", "message": "Meeting Management System API is running"}
@app.get("/dashboard", tags=["Web UI"])
def render_dashboard_page():
    path = FRONTEND_DIR / "dashboard.html"
    return FileResponse(path) if path.exists() else {"error": "Dashboard page not found"}
@app.get("/app", tags=["Web UI"])
def render_index_page():
    path = FRONTEND_DIR / "index.html"
    return FileResponse(path) if path.exists() else {"error": "Application page not found"}

import os
import re
import secrets
from datetime import datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.google_calendar_service import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    encrypt_refresh_token,
    revoke_google_refresh_token,
    sync_user_meetings_to_google,
    verify_calendar_consent_signature,
)

router = APIRouter(prefix="/auth")

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_STATE_COOKIE = "google_oauth_state"


def _google_oauth_config() -> tuple[str, str, str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )
    frontend_login_url = os.getenv(
        "FRONTEND_LOGIN_URL",
        "http://localhost:8000/static/login.html",
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )
    return client_id, client_secret, redirect_uri, frontend_login_url


def _frontend_redirect(frontend_login_url: str, values: dict[str, str], *, fragment: bool) -> str:
    parts = urlsplit(frontend_login_url)
    encoded_values = urlencode(values)
    if fragment:
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, encoded_values))
    query = f"{parts.query}&{encoded_values}" if parts.query else encoded_values
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _unique_google_username(db: Session, email: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_.-]", "_", email.split("@", 1)[0]).strip("._-")[:40]
    base = base or "google_user"
    username = base
    suffix = 1
    while db.query(User.id).filter(User.username == username).first():
        suffix_text = f"_{suffix}"
        username = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return username


def _google_authorization_redirect(
    flow: str,
    user_id: int | None = None,
    *,
    return_authorization_url: bool = False,
):
    client_id, _, redirect_uri, _ = _google_oauth_config()
    state = secrets.token_urlsafe(32)
    cookie_value = f"{state}|{flow}|{user_id or ''}"
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    if flow.startswith("calendar"):
        query["scope"] += f" {GOOGLE_CALENDAR_EVENTS_SCOPE}"
        query["access_type"] = "offline"
        query["prompt"] = "consent"
    authorization_url = f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(query)}"
    response = (
        JSONResponse({"authorization_url": authorization_url})
        if return_authorization_url
        else RedirectResponse(authorization_url)
    )
    response.set_cookie(
        GOOGLE_STATE_COOKIE,
        cookie_value,
        max_age=600,
        path="/api/auth/google",
        secure=redirect_uri.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return response


def _frontend_dashboard_url(frontend_login_url: str) -> str:
    configured_url = os.getenv("FRONTEND_DASHBOARD_URL")
    if configured_url:
        return configured_url
    parts = urlsplit(frontend_login_url)
    if parts.path.endswith("/login.html"):
        path = f"{parts.path[:-len('login.html')]}dashboard.html"
    else:
        path = "/static/dashboard.html"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def issue_token(user: User) -> TokenResponse:
    token = create_access_token(data={"sub": user.username, "user_id": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        full_name=user.full_name or user.username,
    )


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return issue_token(authenticate_user(db, payload.username, payload.password))


@router.get("/google/login", summary="Đăng nhập bằng Google")
def google_login():
    return _google_authorization_redirect("login")


@router.get("/google/calendar/connect", summary="Cấp quyền Google Calendar")
def google_calendar_connect(
    user_id: int,
    expires: int,
    signature: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user or not verify_calendar_consent_signature(user, expires, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Calendar consent link is invalid or expired")
    return _google_authorization_redirect("calendar", user.id)


@router.get("/google/calendar/authorize", summary="Kết nối Google Calendar cá nhân")
def google_calendar_authorize(current_user: User = Depends(get_current_user)):
    return _google_authorization_redirect(
        "calendar_settings",
        current_user.id,
        return_authorization_url=True,
    )


@router.get("/google/callback", summary="Hoàn tất đăng nhập Google")
def google_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    _, client_secret, redirect_uri, frontend_login_url = _google_oauth_config()
    cookie_parts = request.cookies.get(GOOGLE_STATE_COOKIE, "").split("|", 2)
    if len(cookie_parts) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    expected_state, flow, flow_user_text = cookie_parts
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    if flow not in {"login", "calendar", "calendar_settings"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth flow")
    if error:
        error_code = (
            "calendar_permission_denied"
            if flow in {"calendar", "calendar_settings"} and error == "access_denied"
            else "access_denied" if error == "access_denied" else "oauth_failed"
        )
        redirect_url = (
            _frontend_dashboard_url(frontend_login_url)
            if flow == "calendar_settings"
            else frontend_login_url
        )
        return RedirectResponse(
            _frontend_redirect(redirect_url, {"google_error": error_code}, fragment=False),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth code")

    try:
        token_response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        google_access_token = token_data.get("access_token")
        if not google_access_token:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google did not return an access token")

        profile_response = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
            timeout=10,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not complete Google sign-in",
        ) from exc

    email = str(profile.get("email") or "").strip().lower()
    if not email or profile.get("email_verified") is not True:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account email is not verified")

    if flow in {"calendar", "calendar_settings"}:
        try:
            calendar_user_id = int(flow_user_text)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid calendar account") from exc
        user = db.query(User).filter(User.id == calendar_user_id, User.is_active.is_(True)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Calendar account is not available",
            )
        if flow == "calendar" and (
            not user.email or user.email.strip().lower() != email
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Google email must match the invited RoomSync account",
            )
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google did not return calendar authorization; retry consent",
            )
        try:
            user.google_refresh_token = encrypt_refresh_token(refresh_token)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        user.google_calendar_connected_at = datetime.now()
        db.commit()
        background_tasks.add_task(sync_user_meetings_to_google, user.id)
        _, _, redirect_uri, frontend_login_url = _google_oauth_config()
        redirect = RedirectResponse(
            _frontend_redirect(
                _frontend_dashboard_url(frontend_login_url),
                {"calendar_connected": "1"},
                fragment=False,
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
        redirect.delete_cookie(
            GOOGLE_STATE_COOKIE,
            path="/api/auth/google",
            secure=redirect_uri.startswith("https://"),
            httponly=True,
            samesite="lax",
        )
        return redirect

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        user = User(
            username=_unique_google_username(db, email),
            email=email,
            full_name=str(profile.get("name") or email.split("@", 1)[0])[:150],
            hashed_password=hash_password(secrets.token_urlsafe(48)),
            role="employee",
            is_active=True,
        )
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            user = db.query(User).filter(func.lower(User.email) == email).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create Google account") from exc
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")

    token = issue_token(user)
    redirect_values = {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email or "",
        "user_id": str(user.id),
        "picture": str(profile.get("picture") or ""),
    }
    redirect = RedirectResponse(
        _frontend_redirect(frontend_login_url, redirect_values, fragment=True),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    redirect.delete_cookie(
        GOOGLE_STATE_COOKIE,
        path="/api/auth/google",
        secure=redirect_uri.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.get("/me", response_model=UserResponse, summary="Lấy thông tin cá nhân")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/google/calendar/status", summary="Trạng thái kết nối Google Calendar")
def google_calendar_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": bool(current_user.google_refresh_token),
        "connected_at": current_user.google_calendar_connected_at,
    }


@router.delete("/google/calendar/disconnect", summary="Ngắt kết nối Google Calendar")
def google_calendar_disconnect(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    encrypted_refresh_token = current_user.google_refresh_token
    current_user.google_refresh_token = None
    current_user.google_calendar_connected_at = None
    db.commit()
    if encrypted_refresh_token:
        background_tasks.add_task(revoke_google_refresh_token, encrypted_refresh_token)
    return {"connected": False}


@router.get("/admin-only", summary="Kiểm tra quyền Admin")
def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {"status": "success", "message": f"Xin chào Admin {current_user.full_name}! Bạn có toàn quyền quản trị."}

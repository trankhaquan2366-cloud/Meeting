import logging
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
    verify_password,
)
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserResponse
from app.services.google_calendar_service import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    encrypt_refresh_token,
    revoke_google_refresh_token,
    sync_user_meetings_to_google,
    verify_calendar_consent_signature,
)

logger = logging.getLogger("uvicorn.error")

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
        "https://roomsync-app.onrender.com/api/auth/google/callback"
        if (os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_URL"))
        else "http://localhost:8000/api/auth/google/callback",
    )
    if "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    frontend_login_url = os.getenv(
        "FRONTEND_LOGIN_URL",
        "http://localhost:8000/static/login.html",
    )
    if "localhost" not in frontend_login_url and "127.0.0.1" not in frontend_login_url:
        frontend_login_url = frontend_login_url.replace("http://", "https://")
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
        user_id=user.id,
    )


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return issue_token(authenticate_user(db, payload.username, payload.password))


@router.post("/change-password", summary="Đổi mật khẩu và kích hoạt tài khoản")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(func.lower(User.email) == payload.email)
        .first()
    )
    if user is None or not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email hoặc mật khẩu hiện tại không chính xác.",
        )

    user.hashed_password = hash_password(payload.new_password)
    if (user.status or "").upper() == "PENDING":
        user.status = "ACTIVE"
        user.is_active = True
    db.commit()
    return {"message": "Đổi mật khẩu thành công. Bạn có thể đăng nhập ngay bây giờ."}


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
    try:
        code = code or request.query_params.get("code")
        state = state or request.query_params.get("state")
        error = error or request.query_params.get("error")

        try:
            client_id, client_secret, redirect_uri, frontend_login_url = _google_oauth_config()
        except HTTPException as conf_exc:
            logger.error(f"Google OAuth configuration error: {conf_exc.detail}")
            return JSONResponse(status_code=conf_exc.status_code, content={"detail": conf_exc.detail})

        # Ensure HTTPS for non-localhost redirect URIs (e.g. Render)
        if "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri:
            redirect_uri = redirect_uri.replace("http://", "https://")

        cookie_parts = request.cookies.get(GOOGLE_STATE_COOKIE, "").split("|", 2)
        if len(cookie_parts) != 3:
            logger.warning("OAuth callback: Missing or invalid OAuth state cookie")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid OAuth state"})

        expected_state, flow, flow_user_text = cookie_parts
        if not state or not expected_state or not secrets.compare_digest(state, expected_state):
            logger.warning("OAuth callback: State mismatch or missing")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid OAuth state"})

        if flow not in {"login", "calendar", "calendar_settings"}:
            logger.warning(f"OAuth callback: Invalid flow '{flow}'")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid OAuth flow"})

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
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Missing authorization code"},
            )

        # 1. Đổi code lấy token từ Google (bọc try-except an toàn)
        try:
            token_response = httpx.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10.0,
            )
        except Exception as net_exc:
            logger.error(f"Google Token Request Network/Timeout Error: {net_exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": f"Could not connect to Google OAuth service: {str(net_exc)}"},
            )

        token_status = getattr(token_response, "status_code", 200)
        if token_status != 200:
            token_err_text = getattr(token_response, "text", str(token_response))
            logger.error(f"Google Token Exchange Failed ({token_status}): {token_err_text}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Token exchange failed: {token_err_text}"},
            )

        try:
            token_data = token_response.json()
        except Exception as json_exc:
            logger.error(f"Failed to parse token response JSON: {json_exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "Invalid JSON response from Google Token endpoint"},
            )

        google_access_token = token_data.get("access_token")
        if not google_access_token:
            logger.error(f"Google did not return an access token: {token_data}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Google did not return an access token"},
            )

        # 2. Lấy thông tin user từ Google (bọc try-except an toàn)
        try:
            profile_response = httpx.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10.0,
            )
        except Exception as net_exc:
            logger.error(f"Google Userinfo Request Network/Timeout Error: {net_exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": f"Could not connect to Google Userinfo service: {str(net_exc)}"},
            )

        profile_status = getattr(profile_response, "status_code", 200)
        if profile_status != 200:
            profile_err_text = getattr(profile_response, "text", str(profile_response))
            logger.error(f"Google Profile Fetch Failed ({profile_status}): {profile_err_text}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Profile fetch failed: {profile_err_text}"},
            )

        try:
            profile = profile_response.json()
        except Exception as json_exc:
            logger.error(f"Failed to parse profile response JSON: {json_exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "Invalid JSON response from Google Userinfo endpoint"},
            )

        email = str(profile.get("email") or "").strip().lower()
        if not email or profile.get("email_verified") is not True:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Google account email is not verified"},
            )

        # Xử lý luồng kết nối Calendar
        if flow in {"calendar", "calendar_settings"}:
            try:
                calendar_user_id = int(flow_user_text)
            except (ValueError, TypeError) as exc:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid calendar account"},
                )

            try:
                user = db.query(User).filter(User.id == calendar_user_id, User.is_active.is_(True)).first()
            except Exception as db_exc:
                logger.error(f"Database error querying user for calendar: {db_exc}", exc_info=True)
                db.rollback()
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": f"Database error querying calendar account: {str(db_exc)}"},
                )

            if not user:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Calendar account is not available"},
                )
            if flow == "calendar" and (
                not user.email or user.email.strip().lower() != email
            ):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Google email must match the invited RoomSync account"},
                )

            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Google did not return calendar authorization; retry consent"},
                )

            try:
                user.google_refresh_token = encrypt_refresh_token(refresh_token)
            except RuntimeError as exc:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": str(exc)},
                )

            try:
                user.google_calendar_connected_at = datetime.now()
                db.commit()
            except Exception as db_exc:
                logger.error(f"Database error saving calendar authorization: {db_exc}", exc_info=True)
                db.rollback()
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": f"Database error saving calendar authorization: {str(db_exc)}"},
                )

            try:
                background_tasks.add_task(sync_user_meetings_to_google, user.id)
            except Exception as bg_exc:
                logger.warning(f"Could not enqueue calendar sync task: {bg_exc}")

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

        # 3. Tìm hoặc tạo User trong DB (Flow: Đăng nhập người dùng)
        try:
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
                except IntegrityError:
                    db.rollback()
                    user = db.query(User).filter(func.lower(User.email) == email).first()
                    if user is None:
                        return JSONResponse(
                            status_code=status.HTTP_409_CONFLICT,
                            content={"detail": "Could not create Google account"},
                        )
        except Exception as db_exc:
            logger.error(f"Database error during user sign-in: {db_exc}", exc_info=True)
            db.rollback()
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Database error during sign-in: {str(db_exc)}"},
            )

        if not user.is_active:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Tài khoản đã bị khóa"},
            )

        # 4. Sinh JWT token và chuyển hướng về trang web thành công
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

    except HTTPException as exc:
        logger.warning(f"OAuth Callback HTTPException ({exc.status_code}): {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    except Exception as exc:
        logger.error(f"CRITICAL OAUTH CALLBACK ERROR: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Google Sign-In Server Error: {str(exc)}"},
        )


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

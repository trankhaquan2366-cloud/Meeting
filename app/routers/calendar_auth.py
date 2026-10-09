import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import SECRET_KEY, get_current_user
from app.models.calendar import UserCalendarToken
from app.models.user import User
from app.services.calendar_sync_service import (
    CalendarSyncError,
    store_authorized_tokens,
)


router = APIRouter()

_OAUTH_CONFIG = {
    "google": {
        "client_id": "GOOGLE_CLIENT_ID",
        "client_secret": "GOOGLE_CLIENT_SECRET",
        "redirect_uri": "GOOGLE_REDIRECT_URI",
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "openid email https://www.googleapis.com/auth/calendar.events",
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
    },
    "outlook": {
        "client_id": "MICROSOFT_CLIENT_ID",
        "client_secret": "MICROSOFT_CLIENT_SECRET",
        "redirect_uri": "MICROSOFT_REDIRECT_URI",
        "authorization_url": (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        ),
        "token_url": (
            "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        ),
        "scope": "offline_access User.Read Calendars.ReadWrite",
        "extra_auth_params": {"response_mode": "query"},
    },
}
_OAUTH_ENV_ALIASES = {
    "MICROSOFT_CLIENT_ID": "OUTLOOK_CLIENT_ID",
    "MICROSOFT_CLIENT_SECRET": "OUTLOOK_CLIENT_SECRET",
    "MICROSOFT_REDIRECT_URI": "OUTLOOK_REDIRECT_URI",
}


def _get_oauth_env(name: str) -> str | None:
    return os.getenv(name) or os.getenv(_OAUTH_ENV_ALIASES.get(name, ""))


def _encode_state(user_id: int, provider: str) -> str:
    payload = json.dumps(
        {
            "user_id": user_id,
            "provider": provider,
            "expires_at": int(time.time()) + 600,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        encoded_payload,
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded_payload.decode('ascii')}.{encoded_signature.decode('ascii')}"


def _decode_state(state: str) -> dict[str, Any]:
    try:
        encoded_payload, encoded_signature = state.split(".", 1)
        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        if not hmac.compare_digest(expected_signature, signature):
            raise ValueError("Invalid OAuth state signature")

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes)
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("user_id"), int)
            or payload.get("provider") not in _OAUTH_CONFIG
            or not isinstance(payload.get("expires_at"), int)
            or payload["expires_at"] < int(time.time())
        ):
            raise ValueError("Invalid or expired OAuth state")
        return payload
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state không hợp lệ hoặc đã hết hạn",
        ) from exc


def _get_provider_config(provider: str) -> dict[str, Any]:
    config = _OAUTH_CONFIG.get(provider)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="provider phải là 'google' hoặc 'outlook'",
        )

    values = {
        key: _get_oauth_env(config[env_key])
        for key, env_key in (
            ("client_id", "client_id"),
            ("client_secret", "client_secret"),
            ("redirect_uri", "redirect_uri"),
        )
    }
    missing = []
    for key, value in values.items():
        if value:
            continue
        name = config[key]
        alias = _OAUTH_ENV_ALIASES.get(name)
        missing.append(f"{name} (or {alias})" if alias else name)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Thiếu cấu hình OAuth: {', '.join(missing)}",
        )
    return {**config, **values}


@router.get("/auth-url")
def get_calendar_auth_url(
    provider: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    config = _get_provider_config(provider)
    parameters = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scope"],
        "state": _encode_state(current_user.id, provider),
        **config["extra_auth_params"],
    }
    return {"authorization_url": f"{config['authorization_url']}?{urlencode(parameters)}"}


@router.get("/callback")
def calendar_oauth_callback(
    code: str | None = Query(None),
    state: str = Query(...),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nhà cung cấp lịch từ chối kết nối",
        )
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu authorization code từ nhà cung cấp lịch",
        )

    state_payload = _decode_state(state)
    provider = state_payload["provider"]
    user = (
        db.query(User)
        .filter(User.id == state_payload["user_id"], User.is_active.is_(True))
        .one_or_none()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản RoomSync không còn hoạt động",
        )

    config = _get_provider_config(provider)
    form_data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"],
        "grant_type": "authorization_code",
        "code": code,
    }
    if provider == "outlook":
        form_data["scope"] = config["scope"]

    try:
        response = httpx.post(config["token_url"], data=form_data, timeout=20.0)
        response.raise_for_status()
        token_data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không thể hoàn tất OAuth với {provider}",
        ) from exc

    try:
        store_authorized_tokens(db, user.id, provider, token_data)
    except CalendarSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000/dashboard",
    ).rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}?calendar_connected={provider}#settings",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/status")
def get_calendar_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_providers = {
        provider
        for (provider,) in (
            db.query(UserCalendarToken.provider)
            .filter(
                UserCalendarToken.user_id == current_user.id,
                UserCalendarToken.is_active.is_(True),
            )
            .all()
        )
    }
    return {
        provider: {"connected": provider in active_providers}
        for provider in _OAUTH_CONFIG
    }


@router.post("/disconnect")
def disconnect_calendar(
    provider: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if provider not in _OAUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="provider phải là 'google' hoặc 'outlook'",
        )

    token = (
        db.query(UserCalendarToken)
        .filter_by(user_id=current_user.id, provider=provider)
        .one_or_none()
    )
    if token is None or not token.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lịch này chưa được kết nối",
        )

    token.is_active = False
    db.commit()
    return {"connected": False, "provider": provider}

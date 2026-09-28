from datetime import datetime, timedelta
from typing import Any, Dict
import hashlib
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not configured")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
DEFAULT_ITERATIONS = 100_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(plain_password: str, salt: str | None = None, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return a PBKDF2-HMAC-SHA256 password hash."""
    salt = salt or secrets.token_hex(12)
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = hashed_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), int(iterations_text)
        )
        return secrets.compare_digest(digest.hex(), expected)
    except (TypeError, ValueError):
        return False


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Authenticate exclusively against the MySQL users table."""
    user = db.query(User).filter(User.username == username).first()
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sai tên đăng nhập hoặc mật khẩu",
    )
    if user is None or not verify_password(password, user.hashed_password):
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")
    return user


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền hạn không đủ! Yêu cầu vai trò {required_role.upper()}.",
            )
        return current_user

    return role_checker

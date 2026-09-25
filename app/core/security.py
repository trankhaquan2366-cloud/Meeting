import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

# Cấu hình Token & PBKDF2
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_FOR_MEETING_MANAGEMENT_SYSTEM"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token có hiệu lực trong 24 giờ
DEFAULT_ITERATIONS = 100_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --- LOGIC BĂM MẬT KHẨU BẰNG HASHLIB ---
def hash_password(plain_password: str, salt: str | None = None, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Băm mật khẩu bằng PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_hex(12)
    dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu với hash PBKDF2 tương thích với seed.py và schema.sql."""
    try:
        algo, iter_s, salt, digest_hex = hashed_password.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_s)
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return secrets.compare_digest(dk.hex(), digest_hex)
    except Exception:
        return False


# --- LOGIC QUẢN LÝ JWT TOKEN ---
def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Tạo chuỗi JWT Token chứa thông tin username và role."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Xác thực Token và lấy thông tin User đang đăng nhập."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn!",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(required_role: str):
    """Middleware phân quyền: Kiểm tra vai trò Admin hoặc Employee."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền hạn không đủ! Yêu cầu vai trò {required_role.upper()}."
            )
        return current_user
    return role_checker
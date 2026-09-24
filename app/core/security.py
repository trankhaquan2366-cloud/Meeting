import hashlib
import secrets

# Dinh dang hash: pbkdf2_sha256$<iterations>$<salt>$<hex_digest>
# Khong dung bcrypt/passlib de tranh phu thuoc bien dich.

DEFAULT_ITERATIONS = 100_000


def _get_iteration_count(hashed: str) -> int:
    try:
        return int(hashed.split("$")[1])
    except Exception:
        return DEFAULT_ITERATIONS


def hash_password(plain_password: str, salt: str | None = None, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Bam mat khau bang PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_hex(12)
    dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiem tra mat khau voi hash PBKDF2. Tuong thich voi dinh dang hash_password."""
    try:
        algo, iter_s, salt, digest_hex = hashed_password.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_s)
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return secrets.compare_digest(dk.hex(), digest_hex)
    except Exception:
        return False
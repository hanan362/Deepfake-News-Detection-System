"""Password hashing and JWT helpers."""
from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72  # bcrypt ignores everything after 72 bytes, so we reject longer passwords instead

_PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def validate_password_strength(password: str) -> str | None:
    """Return an error message, or None when the password is acceptable."""
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "Password must be at most 72 bytes long."
    if not _PASSWORD_RULE.match(password):
        return "Password must be at least 8 characters and contain a letter and a digit."
    return None


def hash_password(password: str) -> str:
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:MAX_PASSWORD_BYTES], hashed.encode("utf-8"))
    except ValueError:
        return False


def password_version(changed_at: datetime | None) -> int:
    """Millisecond timestamp of the last password change (0 if never changed)."""
    if changed_at is None:
        return 0
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    return int(changed_at.timestamp() * 1000)


def create_access_token(user_id: int, pwd_version: int = 0) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at). `pwd_version` ties the token to the current password."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=s.access_token_expire_minutes)
    jti = uuid.uuid4().hex
    claims = {"sub": str(user_id), "jti": jti, "pv": pwd_version, "iat": now, "exp": exp}
    token = jwt.encode(claims, s.secret_key, algorithm=ALGORITHM)
    return token, jti, exp


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError for invalid or expired tokens."""
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "jti"]})


def new_reset_token() -> tuple[str, str]:
    """Return (token, sha256_hex). Only the hash is stored."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

"""Shared FastAPI dependencies: database session, authentication and authorisation."""
from __future__ import annotations

from datetime import datetime, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import decode_access_token, password_version
from app.db.session import get_db
from app.models import RevokedToken, User

bearer = HTTPBearer(auto_error=False)


def get_token_payload(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> dict:
    if creds is None or creds.scheme.lower() != "bearer":
        raise APIError(401, "UNAUTHENTICATED", "Authentication required.")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise APIError(401, "INVALID_TOKEN", "Invalid or expired token.")
    if db.get(RevokedToken, payload["jti"]) is not None:
        raise APIError(401, "INVALID_TOKEN", "This session has ended. Please log in again.")
    return payload


def get_current_user(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> User:
    try:
        user = db.get(User, int(payload["sub"]))
    except (TypeError, ValueError):
        user = None
    if user is None or not user.is_active:
        raise APIError(401, "INVALID_TOKEN", "Account not found or disabled.")
    if payload.get("pv", 0) != password_version(user.password_changed_at):
        raise APIError(401, "INVALID_TOKEN", "Your password was changed. Please log in again.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise APIError(403, "FORBIDDEN", "Administrator access is required.")
    return user


def purge_expired_tokens(db: Session) -> None:
    db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete()
    db.commit()

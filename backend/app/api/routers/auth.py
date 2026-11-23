"""Registration, login, logout and password reset."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token_payload, purge_expired_tokens
from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import (create_access_token, hash_password, hash_token, new_reset_token, password_version,
                               verify_password)
from app.db.session import get_db
from app.models import PasswordResetToken, RevokedToken, User, as_utc
from app.schemas.user import (ForgotPasswordRequest, LoginRequest, MessageResponse, RegisterRequest, ResetPasswordRequest,
                              TokenResponse, UserOut)
from app.services import accounts
from app.utils.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_RESET_MESSAGE = "If an account with that e-mail exists, password reset instructions have been created."


@router.post("/register", response_model=UserOut, status_code=201, summary="Create an account")
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if accounts.email_taken(db, body.email):
        raise APIError(409, "EMAIL_TAKEN", "An account with this e-mail already exists.")
    if accounts.username_taken(db, body.username):
        raise APIError(409, "USERNAME_TAKEN", "This username is already taken.")
    user = User(email=body.email, username=body.username, full_name=body.full_name, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    audit(db, request, user, "user.register", "user", user.id)
    return accounts.user_out(user)


@router.post("/login", response_model=TokenResponse, summary="Log in with e-mail or username")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = accounts.find_by_identifier(db, body.identifier)
    ok = verify_password(body.password, user.hashed_password if user else accounts.dummy_hash())
    if user is None or not ok:
        audit(db, request, user, "auth.login_failed", "user", user.id if user else None)
        raise APIError(401, "INVALID_CREDENTIALS", "Incorrect e-mail/username or password.")
    if not user.is_active:
        raise APIError(403, "ACCOUNT_DISABLED", "This account has been disabled. Contact an administrator.")
    token, _, exp = create_access_token(user.id, password_version(user.password_changed_at))
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    audit(db, request, user, "auth.login", "user", user.id)
    return TokenResponse(access_token=token, expires_at=exp, user=accounts.user_out(user))


@router.post("/logout", response_model=MessageResponse, summary="End the current session")
def logout(request: Request, payload: dict = Depends(get_token_payload), user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    db.merge(RevokedToken(jti=payload["jti"], expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)))
    db.commit()
    purge_expired_tokens(db)
    audit(db, request, user, "auth.logout", "user", user.id)
    return MessageResponse(message="Logged out.")


@router.post("/forgot-password", response_model=MessageResponse, summary="Start a password reset")
def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    s = get_settings()
    user = accounts.find_by_identifier(db, body.email)
    token_out: str | None = None
    if user is not None and user.is_active:
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).delete()
        token, token_hash = new_reset_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash,
                                  expires_at=datetime.now(timezone.utc) + timedelta(minutes=s.password_reset_expire_minutes)))
        db.commit()
        audit(db, request, user, "auth.password_reset_requested", "user", user.id)
        # There is no e-mail service in the base install. The token is only ever returned in development.
        token_out = token if s.expose_reset_token else None
    return MessageResponse(message=GENERIC_RESET_MESSAGE, reset_token=token_out)


@router.post("/reset-password", response_model=MessageResponse, summary="Finish a password reset")
def reset_password(body: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == hash_token(body.token)).one_or_none()
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or as_utc(row.expires_at) < now:
        raise APIError(400, "INVALID_RESET_TOKEN", "This reset link is invalid or has expired.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise APIError(400, "INVALID_RESET_TOKEN", "This reset link is invalid or has expired.")
    user.hashed_password = hash_password(body.new_password)
    user.password_changed_at = now  # ends every session that was opened with the old password
    row.used_at = now
    db.commit()
    audit(db, request, user, "auth.password_reset", "user", user.id)
    return MessageResponse(message="Password updated. Please log in with your new password.")

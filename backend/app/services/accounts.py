"""Account helpers shared by routers and start-up code."""
from __future__ import annotations

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, validate_password_strength
from app.models import ROLES, Role, User
from app.schemas.user import UserOut

logger = logging.getLogger("ddn.accounts")

_dummy_hash: str | None = None


def dummy_hash() -> str:
    """A genuine bcrypt hash used when the account does not exist, so unknown and known accounts take similar time."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("placeholder-Password-1")
    return _dummy_hash


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, username=user.username, full_name=user.full_name, role=user.role,
                   is_active=user.is_active, has_avatar=bool(user.avatar_path), created_at=user.created_at,
                   last_login_at=user.last_login_at)


def find_by_identifier(db: Session, identifier: str) -> User | None:
    ident = identifier.strip().lower()
    return (db.query(User)
            .filter((func.lower(User.email) == ident) | (func.lower(User.username) == ident)).first())


def email_taken(db: Session, email: str, exclude_id: int | None = None) -> bool:
    q = db.query(User.id).filter(func.lower(User.email) == email.lower())
    return (q.filter(User.id != exclude_id) if exclude_id else q).first() is not None


def username_taken(db: Session, username: str, exclude_id: int | None = None) -> bool:
    q = db.query(User.id).filter(func.lower(User.username) == username.lower())
    return (q.filter(User.id != exclude_id) if exclude_id else q).first() is not None


def ensure_roles(db: Session) -> None:
    """Make sure every role the code uses exists. Safe to call at every start."""
    existing = {name for (name,) in db.query(Role.name).all()}
    for name, description in ROLES.items():
        if name not in existing:
            db.add(Role(name=name, description=description))
    db.commit()


def ensure_initial_admin(db: Session) -> None:
    """Create the first administrator from ADMIN_EMAIL / ADMIN_PASSWORD, if both are configured."""
    s = get_settings()
    if not (s.admin_email and s.admin_password):
        return
    problem = validate_password_strength(s.admin_password)
    if problem:
        logger.error("ADMIN_PASSWORD rejected: %s", problem)
        return
    if email_taken(db, s.admin_email):
        return
    username = s.admin_email.split("@")[0][:40] or "admin"
    while username_taken(db, username):
        username = f"{username[:40]}_"
    db.add(User(email=s.admin_email.lower(), username=username, full_name="Administrator",
                hashed_password=hash_password(s.admin_password), role="admin"))
    db.commit()
    logger.info("Created initial administrator %s", s.admin_email)

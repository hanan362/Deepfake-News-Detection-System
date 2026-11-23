"""Request and response models for accounts and authentication."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_strength

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,50}$"


def _check_password(value: str) -> str:
    problem = validate_password_strength(value)
    if problem:
        raise ValueError(problem)
    return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: str | None = None
    role: str
    is_active: bool
    has_avatar: bool = False
    created_at: datetime
    last_login_at: datetime | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str
    full_name: str | None = Field(default=None, max_length=120)

    _pw = field_validator("password")(_check_password)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255, description="E-mail address or username")
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
    # Only present when EXPOSE_RESET_TOKEN=true (development). There is no e-mail service in the base install.
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str

    _pw = field_validator("new_password")(_check_password)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str

    _pw = field_validator("new_password")(_check_password)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, pattern=USERNAME_PATTERN)

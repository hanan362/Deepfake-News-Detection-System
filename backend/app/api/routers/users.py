"""The signed-in user's own profile, password and avatar."""
from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import ImageOps
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import APIError
from app.core.security import create_access_token, hash_password, password_version, verify_password
from app.db.session import get_db
from app.ml.image_detection import ela
from app.models import User
from app.schemas.user import ChangePasswordRequest, ProfileUpdate, TokenResponse, UserOut
from app.services import accounts, files
from app.utils.audit import audit

router = APIRouter(prefix="/users/me", tags=["profile"])
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_SIZE = 256


@router.get("", response_model=UserOut, summary="Current user")
def read_me(user: User = Depends(get_current_user)):
    return accounts.user_out(user)


@router.patch("", response_model=UserOut, summary="Update profile")
def update_me(body: ProfileUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    changes: dict = {}
    if body.username is not None and body.username != user.username:
        if accounts.username_taken(db, body.username, exclude_id=user.id):
            raise APIError(409, "USERNAME_TAKEN", "This username is already taken.")
        user.username = body.username
        changes["username"] = True
    if "full_name" in body.model_fields_set:
        user.full_name = (body.full_name or "").strip() or None
        changes["full_name"] = True
    db.commit()
    audit(db, request, user, "user.update_profile", "user", user.id, changes or None)
    return accounts.user_out(user)


@router.post("/password", response_model=TokenResponse, summary="Change password")
def change_password(body: ChangePasswordRequest, request: Request, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise APIError(400, "WRONG_PASSWORD", "The current password is incorrect.")
    user.hashed_password = hash_password(body.new_password)
    user.password_changed_at = datetime.now(timezone.utc)  # every older session stops working
    db.commit()
    audit(db, request, user, "user.change_password", "user", user.id)
    token, _, exp = create_access_token(user.id, password_version(user.password_changed_at))
    return TokenResponse(access_token=token, expires_at=exp, user=accounts.user_out(user))


@router.post("/avatar", response_model=UserOut, summary="Upload a profile picture")
async def upload_avatar(request: Request, file: UploadFile = File(...), user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    data = await files.read_limited(file, AVATAR_MAX_BYTES)
    try:
        img = ela.open_validated(data, 25_000_000)
    except ela.ImageRejected as exc:
        raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", str(exc))
    # Re-encode to a small PNG: strips metadata and any hidden payload, and bounds storage use.
    img = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (AVATAR_SIZE, AVATAR_SIZE))
    out = io.BytesIO()
    img.save(out, format="PNG")
    old = user.avatar_path
    user.avatar_path = files.save_bytes("avatars", out.getvalue(), "png")
    db.commit()
    files.remove_media("avatars", old)
    audit(db, request, user, "user.upload_avatar", "user", user.id)
    return accounts.user_out(user)


@router.get("/avatar", summary="Download your profile picture")
def read_avatar(user: User = Depends(get_current_user)):
    if not user.avatar_path:
        raise APIError(404, "NOT_FOUND", "No profile picture set.")
    return FileResponse(files.resolve_media("avatars", user.avatar_path), media_type="image/png",
                        headers={"Cache-Control": "private, no-store"})


@router.delete("/avatar", response_model=UserOut, summary="Remove your profile picture")
def delete_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    files.remove_media("avatars", user.avatar_path)
    user.avatar_path = None
    db.commit()
    return accounts.user_out(user)

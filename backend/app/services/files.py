"""Safe handling of uploaded files and private media storage."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import APIError

_CHUNK = 1 << 20
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def media_dir(kind: str) -> Path:
    path = get_settings().storage_dir / "uploads" / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


async def read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload, refusing anything larger than `max_bytes` without loading it all into memory first."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise APIError(413, "PAYLOAD_TOO_LARGE", f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
        chunks.append(chunk)
    if total == 0:
        raise APIError(400, "EMPTY_FILE", "The uploaded file is empty.")
    return b"".join(chunks)


def safe_display_name(filename: str | None) -> str | None:
    """A sanitised name for showing to the user. It is never used to build a path."""
    if not filename:
        return None
    name = Path(filename.replace("\\", "/")).name
    name = _CONTROL.sub("", name).strip()
    return name[:120] or None


def save_bytes(kind: str, data: bytes, extension: str) -> str:
    """Store bytes under a random name and return that name."""
    name = f"{uuid.uuid4().hex}.{extension}"
    (media_dir(kind) / name).write_bytes(data)
    return name


def resolve_media(kind: str, name: str) -> Path:
    """Map a stored name back to a path, refusing anything that escapes the media folder."""
    base = media_dir(kind).resolve()
    path = (base / name).resolve()
    if base not in path.parents or not path.is_file():
        raise APIError(404, "NOT_FOUND", "File not found.")
    return path


def remove_media(kind: str, name: str | None) -> None:
    if not name:
        return
    try:
        resolve_media(kind, name).unlink(missing_ok=True)
    except APIError:
        pass

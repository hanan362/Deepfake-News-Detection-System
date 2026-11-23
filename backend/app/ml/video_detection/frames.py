"""Opening a video safely and sampling frames from it.

An upload is judged by its content, never by its file name or declared type: the first bytes must be a known video
container, OpenCV must be able to read it, and its size, length and resolution must be inside the configured limits.
Frames are taken at evenly spaced positions across the whole video, so a long video is covered from start to end
instead of only its opening seconds.

Decoding untrusted media is done by OpenCV's bundled FFmpeg in this process, with hard limits on size, length, pixels
and time. A subprocess sandbox would be safer and is listed as a limitation."""
from __future__ import annotations

import importlib.util
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

# container signature -> file extension stored on disk
_SIGNATURES = (
    (lambda h: h[4:8] == b"ftyp", None),            # MP4 / MOV / M4V: the brand decides the extension below
    (lambda h: h[:4] == b"\x1a\x45\xdf\xa3", "webm"),  # Matroska / WebM
    (lambda h: h[:4] == b"RIFF" and h[8:12] == b"AVI ", "avi"),
)
MAX_SIDE = 4096
MAX_DECODE_SECONDS = 90.0  # wall-clock budget for reading frames


class VideoRejected(ValueError):
    """The upload is not an acceptable video. The message is safe to show to the user."""

    def __init__(self, message: str, too_large: bool = False):
        super().__init__(message)
        self.too_large = too_large  # a limit was exceeded (413) rather than the file being the wrong kind (415)


def cv2_installed() -> bool:
    return importlib.util.find_spec("cv2") is not None


@dataclass
class VideoInfo:
    extension: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


@dataclass
class SampledFrame:
    index: int
    timestamp: float
    image: np.ndarray  # BGR, as OpenCV returns it


def sniff_extension(head: bytes) -> str:
    for test, ext in _SIGNATURES:
        if len(head) >= 12 and test(head):
            if ext:
                return ext
            return "mov" if head[8:12] == b"qt  " else "mp4"
    raise VideoRejected("The file is not a supported video. Use MP4, MOV, WebM or AVI.")


class _TempVideo:
    """OpenCV reads from a path, so the bytes are written to a private temp file that is removed afterwards."""

    def __init__(self, data: bytes, extension: str):
        fd, name = tempfile.mkstemp(suffix="." + extension, prefix="ddn_video_")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        self.path = Path(name)

    def __enter__(self) -> Path:
        return self.path

    def __exit__(self, *exc) -> None:
        self.path.unlink(missing_ok=True)


def temp_video(data: bytes, extension: str) -> _TempVideo:
    return _TempVideo(data, extension)


def probe(path: Path, extension: str, max_seconds: float, max_side: int = MAX_SIDE) -> VideoInfo:
    import cv2

    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise VideoRejected("The video could not be opened. It may be damaged or use an unsupported codec.")
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()
    if width <= 0 or height <= 0 or fps <= 0 or count <= 0:
        raise VideoRejected("The video has no readable length or picture size.")
    if max(width, height) > max_side:
        raise VideoRejected(f"The video is larger than {max_side} pixels on a side.", too_large=True)
    duration = count / fps
    if duration > max_seconds:
        raise VideoRejected(f"The video is longer than {int(max_seconds)} seconds.", too_large=True)
    return VideoInfo(extension, width, height, round(fps, 3), count, round(duration, 3))


def sample_indices(frame_count: int, n: int) -> list[int]:
    """n evenly spaced frame numbers, centred in n equal slices of the video."""
    n = max(1, min(n, frame_count))
    return sorted({min(frame_count - 1, int((i + 0.5) * frame_count / n)) for i in range(n)})


def read_frames(path: Path, info: VideoInfo, n: int) -> Iterator[SampledFrame]:
    """Yield the sampled frames in order. Frames are decoded sequentially (seeking is unreliable for many codecs) and
    stopped when the time budget runs out."""
    import cv2

    wanted = sample_indices(info.frame_count, n)
    want = iter(wanted)
    target = next(want, None)
    cap = cv2.VideoCapture(str(path))
    started = time.monotonic()
    index = 0
    try:
        while target is not None:
            if time.monotonic() - started > MAX_DECODE_SECONDS:
                raise VideoRejected("Reading the video took too long.")
            if not cap.grab():
                break
            if index == target:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    yield SampledFrame(index, round(index / info.fps, 3), frame)
                target = next(want, None)
            index += 1
    finally:
        cap.release()

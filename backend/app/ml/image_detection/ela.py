"""Forensic indicators for still images: Error Level Analysis (ELA) and metadata.

This is NOT a classifier of AI-generated or manipulated images and it is never presented as one.
ELA re-compresses the image once as JPEG and measures how much each pixel changes. Regions that were edited or pasted
from another source *can* show a different error level, but so can many ordinary images (sharp text, graphics,
different compression history). The numbers and the map are real measurements; their interpretation is left to the
person, with the caveats attached to every result.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import ExifTags, Image, ImageChops, ImageOps

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ELA_QUALITY = 90
ELA_AMPLIFY_TARGET = 255.0
GRID = 16  # the ELA map is summarised on a GRID x GRID block grid
# Uncalibrated rule of thumb, used only to word one observation. It has not been validated on a labelled dataset.
UNEVEN_ERROR_CV = 1.0
EDITING_SOFTWARE = ("photoshop", "gimp", "lightroom", "affinity", "pixelmator", "canva", "paint.net", "snapseed")


class ImageRejected(ValueError):
    """The upload is not an acceptable image. The message is safe to show to the user."""


@dataclass
class ElaResult:
    width: int
    height: int
    image_format: str
    ela_mean: float
    ela_max: float
    ela_block_cv: float
    heatmap_png: bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)


def open_validated(data: bytes, max_pixels: int) -> Image.Image:
    """Open an upload by content (never by file name or declared type) and enforce format and size limits."""
    Image.MAX_IMAGE_PIXELS = max_pixels  # Pillow raises DecompressionBombError above 2x this value
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        width, height = probe.size
        probe.verify()  # structural check; the file must be reopened afterwards
    except Image.DecompressionBombError:
        raise ImageRejected("The image has too many pixels.")
    except Exception:
        raise ImageRejected("The file is not a valid image.")
    if fmt not in ALLOWED_FORMATS:
        raise ImageRejected("Only JPEG, PNG and WEBP images are supported.")
    if width * height > max_pixels:
        raise ImageRejected(f"The image is larger than {max_pixels:,} pixels.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise ImageRejected("The image file is damaged.")
    return img


def _metadata(img: Image.Image) -> dict[str, Any]:
    meta: dict[str, Any] = {"has_exif": False}
    try:
        exif = img.getexif()
    except Exception:
        exif = None
    if exif:
        meta["has_exif"] = True
        names = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
        for key in ("Make", "Model", "Software", "DateTime"):
            if key in names:
                meta[key.lower()] = str(names[key])[:120]
    if "icc_profile" in img.info:
        meta["has_icc_profile"] = True
    return meta


def analyse(data: bytes, max_pixels: int) -> ElaResult:
    img = open_validated(data, max_pixels)
    fmt = img.format or "UNKNOWN"
    meta = _metadata(img)
    rgb = ImageOps.exif_transpose(img).convert("RGB")
    width, height = rgb.size

    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=ELA_QUALITY)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")
    diff = ImageChops.difference(rgb, resaved)
    arr = np.asarray(diff, dtype=np.float32).max(axis=2)  # per-pixel error level (0-255)

    ela_mean = float(arr.mean())
    ela_max = float(arr.max())
    # How uneven is the error level across the picture? Coefficient of variation of the block means.
    h_edges = np.linspace(0, height, GRID + 1, dtype=int)
    w_edges = np.linspace(0, width, GRID + 1, dtype=int)
    blocks = np.array([[arr[h_edges[i]:h_edges[i + 1], w_edges[j]:w_edges[j + 1]].mean()
                        if h_edges[i + 1] > h_edges[i] and w_edges[j + 1] > w_edges[j] else 0.0
                        for j in range(GRID)] for i in range(GRID)])
    block_mean = float(blocks.mean())
    block_cv = float(blocks.std() / block_mean) if block_mean > 1e-6 else 0.0

    scale = ELA_AMPLIFY_TARGET / max(ela_max, 1.0)
    heat = Image.fromarray(np.clip(arr * scale, 0, 255).astype(np.uint8), mode="L")
    heat.thumbnail((1024, 1024))
    out = io.BytesIO()
    heat.save(out, format="PNG")

    obs: list[str] = []
    if fmt == "PNG":
        obs.append("The file is a lossless PNG. ELA compares JPEG recompression, so it is less informative here.")
    if not meta["has_exif"]:
        obs.append("No camera metadata (EXIF) found. This is normal for images shared through messaging apps and "
                   "social media, which strip it, so it says little by itself.")
    software = meta.get("software", "").lower()
    if any(name in software for name in EDITING_SOFTWARE):
        obs.append(f"The metadata names editing software ('{meta['software']}'). The image passed through an editor; "
                   "that is not proof of deceptive manipulation.")
    if block_cv > UNEVEN_ERROR_CV:
        obs.append("The error level is very uneven across the image. Edited areas can look like this, but so can "
                   "sharp text, logos or images that were saved several times. Look at the map before drawing conclusions.")
    if not obs:
        obs.append("No notable indicator was found by these two checks. That does not show the image is authentic or "
                   "human-made: AI-generated and carefully edited images often pass checks like these.")

    return ElaResult(width, height, fmt, round(ela_mean, 4), round(ela_max, 4), round(block_cv, 4),
                     out.getvalue(), meta, obs)


def extension_for(fmt: str) -> str:
    return ALLOWED_FORMATS[fmt]

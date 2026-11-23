"""Does a caption describe an image? Cosine similarity of CLIP embeddings (openai/clip-vit-base-patch32, pretrained).

The raw similarity is not meaningful on its own, so it is turned into three labels with two thresholds measured on a
labelled sample (ai_models/training/evaluate_clip_consistency.py writes them into the registry file):
consistent (clearly high), inconsistent (clearly low) and unclear (in between, the usual case for loose captions).
Without those measured thresholds the similarity is shown but not interpreted.

Limits that matter: CLIP reads at most 77 tokens of text, so a long article is represented by its headline or opening
sentences; it recognises objects and scenes, not whether a photo is from the event the text names."""
from __future__ import annotations

import importlib.util
import io
import json
import logging
import threading
import time
from typing import Any

from app.core.config import PROJECT_ROOT, get_settings
from app.ml.loading import may_retry

logger = logging.getLogger("ddn.clip")
REGISTRY_FILE = PROJECT_ROOT / "ai_models" / "model_registry" / "multimodal_clip.json"
DEFAULT_MODEL = "openai/clip-vit-base-patch32"


def deps_installed() -> bool:
    return all(importlib.util.find_spec(m) for m in ("torch", "transformers"))


def load_calibration() -> dict[str, Any] | None:
    if not REGISTRY_FILE.exists():
        return None
    cal = (json.loads(REGISTRY_FILE.read_text(encoding="utf-8")).get("calibration") or {})
    return cal if {"consistent_min", "inconsistent_max"} <= set(cal) else None


class ClipConsistency:
    def __init__(self, model_id: str = DEFAULT_MODEL):
        self.model_id = model_id
        self._bundle: Any = None
        self._error: str | None = None
        self._failed_at: float | None = None
        self._lock = threading.Lock()

    def problem(self) -> str | None:
        if not deps_installed():
            return "The packages torch and transformers are not installed (pip install -r backend/requirements-ml.txt)."
        return self._error

    def _load(self):
        with self._lock:
            if self._bundle is None and self._error is not None and may_retry(self._failed_at):
                self._error = None  # a failed download is tried again after a pause
            if self._bundle is None and self._error is None and deps_installed():
                try:
                    import torch
                    from transformers import CLIPModel, CLIPProcessor

                    self._bundle = (torch, CLIPProcessor.from_pretrained(self.model_id), CLIPModel.from_pretrained(self.model_id).eval())
                    logger.info("Loaded CLIP model %s", self.model_id)
                except Exception as exc:
                    self._error = f"The CLIP model {self.model_id} could not be loaded ({type(exc).__name__}: {str(exc)[:160]})."
                    self._failed_at = time.monotonic()
                    logger.warning(self._error)
        return self._bundle

    @property
    def available(self) -> bool:
        return deps_installed() and self._load() is not None

    def embed_images(self, images: list) -> Any:
        torch, proc, model = self._load()
        with torch.no_grad():
            f = model.get_image_features(**proc(images=images, return_tensors="pt"))
        f = f if hasattr(f, "norm") else f.pooler_output
        return f / f.norm(dim=-1, keepdim=True)

    def embed_texts(self, texts: list[str]) -> Any:
        torch, proc, model = self._load()
        with torch.no_grad():
            f = model.get_text_features(**proc(text=texts, return_tensors="pt", padding=True, truncation=True, max_length=77))
        f = f if hasattr(f, "norm") else f.pooler_output
        return f / f.norm(dim=-1, keepdim=True)

    def similarity(self, image_bytes: bytes, caption: str) -> float:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return float((self.embed_images([img]) @ self.embed_texts([caption]).T)[0, 0])


_clip: ClipConsistency | None = None


def get_clip() -> ClipConsistency:
    global _clip
    if _clip is None:
        _clip = ClipConsistency(get_settings().clip_model_id)
    return _clip


def label_for(similarity: float, calibration: dict[str, Any] | None) -> str:
    if not calibration:
        return "not_calibrated"
    if similarity >= calibration["consistent_min"]:
        return "consistent"
    if similarity <= calibration["inconsistent_max"]:
        return "inconsistent"
    return "unclear"


def caption_for(headline: str | None, text: str | None) -> tuple[str | None, str | None]:
    """The text CLIP reads: the headline, else the first sentences of the text (CLIP truncates at 77 tokens)."""
    if headline and headline.strip():
        return headline.strip()[:300], "headline"
    if text and text.strip():
        t = " ".join(text.split())
        return t[:300], "opening of the text"
    return None, None


def assess(image_bytes: bytes | None, headline: str | None, text: str | None, clip: ClipConsistency | None = None) -> dict[str, Any]:
    caption, source = caption_for(headline, text)
    cal = load_calibration()
    base: dict[str, Any] = {"status": "not_possible", "label": None, "similarity": None, "caption_used": caption,
                            "caption_source": source, "thresholds": cal, "model": get_settings().clip_model_id, "note": ""}
    if image_bytes is None or caption is None:
        return {**base, "note": "Consistency needs both an image and some text."}
    clip = clip or get_clip()
    if not clip.available:
        return {**base, "status": "not_assessed", "note": clip.problem() or "The CLIP model is not available."}
    sim = round(clip.similarity(image_bytes, caption), 4)
    label = label_for(sim, cal)
    note = ("Thresholds were measured on Flickr30k test captions, not on news. Treat 'unclear' as the normal outcome for loose captions."
            if cal else "No measured thresholds are installed, so the similarity is shown without interpretation.")
    return {**base, "status": "assessed", "similarity": sim, "label": label, "note": note}

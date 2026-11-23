"""Per-frame real/fake classifier for face crops: a pretrained image model (Swin-Tiny) from the Hugging Face Hub.

It looks at one face crop at a time. It has no notion of motion or of what came before or after, so on its own it is a
FRAME-BASED classifier. What the application adds on top is temporal aggregation of the per-frame scores (temporal.py),
which is a summary of the sequence, not a model that learns temporal inconsistencies."""
from __future__ import annotations

import importlib.util
import logging
import threading
import time
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.ml.loading import may_retry

logger = logging.getLogger("ddn.video")
DEFAULT_MODEL = "hchcsuim/FFPP-Raw_1FPS_faces-expand-40-aligned_val-ds-celeb-df"
# Pinned so the evaluated model and the deployed model are the same files (a Swin-Tiny fine-tuned on FaceForensics++ faces).
DEFAULT_REVISION = "41921375ab59212cf5757c1a5820bbf34868e019"
BATCH = 16


def deps_installed() -> bool:
    return all(importlib.util.find_spec(m) for m in ("torch", "transformers", "cv2"))


class FrameClassifier:
    def __init__(self, model_id: str | None = None, revision: str | None = None):
        self.model_id = model_id or get_settings().video_model_id
        self.revision = revision if revision is not None else (DEFAULT_REVISION if self.model_id == DEFAULT_MODEL else None)
        self._bundle: Any = None
        self._error: str | None = None
        self._failed_at: float | None = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._bundle is None and self._error is not None and may_retry(self._failed_at):
                self._error = None  # a failed download is tried again after a pause
            if self._bundle is None and self._error is None and deps_installed():
                try:
                    import torch
                    from transformers import AutoImageProcessor, AutoModelForImageClassification

                    proc = AutoImageProcessor.from_pretrained(self.model_id, revision=self.revision)
                    model = AutoModelForImageClassification.from_pretrained(self.model_id, revision=self.revision).eval()
                    labels = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
                    fake_ids = [k for k, v in labels.items() if "fake" in v or "deepfake" in v or "ai" == v]
                    if len(fake_ids) != 1:
                        raise ValueError(f"cannot tell which label means fake: {labels}")
                    self._bundle = (torch, proc, model, fake_ids[0])
                    logger.info("Loaded frame classifier %s", self.model_id)
                except Exception as exc:
                    self._error = f"The frame model {self.model_id} could not be loaded ({type(exc).__name__}: {str(exc)[:160]})."
                    self._failed_at = time.monotonic()
                    logger.warning(self._error)
        return self._bundle

    def problem(self) -> str | None:
        if not deps_installed():
            return "The packages torch, transformers and opencv are not installed (pip install -r backend/requirements-ml.txt)."
        self._load()
        return self._error

    @property
    def available(self) -> bool:
        return self.problem() is None

    def p_fake(self, crops: list[np.ndarray]) -> list[float]:
        """Probability that each RGB face crop is fake, as the model estimates it."""
        torch, proc, model, fake_id = self._load()
        out: list[float] = []
        for i in range(0, len(crops), BATCH):
            with torch.no_grad():
                logits = model(**proc(images=[c for c in crops[i:i + BATCH]], return_tensors="pt")).logits
            out.extend(torch.softmax(logits, dim=-1)[:, fake_id].tolist())
        return [round(float(p), 4) for p in out]


_classifier: FrameClassifier | None = None


def get_classifier() -> FrameClassifier:
    global _classifier
    if _classifier is None or _classifier.model_id != get_settings().video_model_id:
        _classifier = FrameClassifier()
    return _classifier

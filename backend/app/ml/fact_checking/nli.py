"""Natural-language inference: does a piece of evidence support, contradict or say nothing about a claim?

A pretrained English NLI model (default cross-encoder/nli-deberta-v3-small, Apache-2.0, about 570 MB). It needs the optional
packages in requirements-ml.txt. Without them the evidence module still retrieves evidence but cannot judge its stance,
and says so. MNLI models compare two short texts; they do not know whether the evidence itself is right."""
from __future__ import annotations

import importlib.util
import logging
import threading
import time
from typing import Any

from app.ml.loading import may_retry

logger = logging.getLogger("ddn.nli")
DEFAULT_MODEL = "cross-encoder/nli-deberta-v3-small"
DEFAULT_REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"  # the commit that was evaluated; a moved model is not picked up silently


def deps_installed() -> bool:
    return all(importlib.util.find_spec(m) for m in ("torch", "transformers"))


class NliModel:
    def __init__(self, model_id: str = DEFAULT_MODEL, revision: str | None = None):
        self.model_id = model_id
        self.revision = revision if revision is not None else (DEFAULT_REVISION if model_id == DEFAULT_MODEL else None)
        self._bundle: Any = None
        self._error: str | None = None
        self._failed_at: float | None = None
        self._lock = threading.Lock()

    @property
    def installed(self) -> bool:
        return deps_installed()

    def problem(self) -> str | None:
        if not self.installed:
            return "The packages torch and transformers are not installed (pip install -r backend/requirements-ml.txt)."
        return self._error

    def _load(self):
        with self._lock:
            if self._bundle is None and self._error is not None and may_retry(self._failed_at):
                self._error = None  # a failed download is tried again after a pause
            if self._bundle is None and self._error is None:
                try:
                    import torch
                    from transformers import AutoModelForSequenceClassification, AutoTokenizer

                    tok = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
                    model = AutoModelForSequenceClassification.from_pretrained(self.model_id, revision=self.revision).eval()
                    labels = {int(i): str(n).lower() for i, n in model.config.id2label.items()}
                    wanted = {"entailment", "neutral", "contradiction"}
                    if set(labels.values()) != wanted:
                        raise ValueError(f"unexpected label set {sorted(labels.values())}")
                    self._bundle = (torch, tok, model, labels)
                    logger.info("Loaded NLI model %s", self.model_id)
                except Exception as exc:  # download or load failure: reported, not hidden
                    self._error = f"The NLI model {self.model_id} could not be loaded ({type(exc).__name__}: {str(exc)[:160]})."
                    self._failed_at = time.monotonic()
                    logger.warning(self._error)
        return self._bundle

    @property
    def available(self) -> bool:
        return self.installed and self._load() is not None

    def predict(self, pairs: list[tuple[str, str]], batch_size: int = 16) -> list[dict[str, float]]:
        """For each (evidence, claim) pair, the probability of entailment, neutral and contradiction."""
        bundle = self._load()
        if bundle is None:
            raise RuntimeError(self.problem() or "NLI model not available")
        torch, tok, model, labels = bundle
        out: list[dict[str, float]] = []
        for i in range(0, len(pairs), batch_size):
            chunk = pairs[i:i + batch_size]
            enc = tok([p for p, _h in chunk], [h for _p, h in chunk], truncation=True, max_length=256, padding=True, return_tensors="pt")
            with torch.no_grad():
                probs = torch.softmax(model(**enc).logits, dim=-1).tolist()
            out += [{labels[j]: round(p, 4) for j, p in enumerate(row)} for row in probs]
        return out


_nli: NliModel | None = None


def get_nli() -> NliModel:
    global _nli
    if _nli is None:
        from app.core.config import get_settings

        _nli = NliModel(get_settings().nli_model_id)
    return _nli

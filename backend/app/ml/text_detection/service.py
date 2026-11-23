"""Inference for the English TF-IDF + Logistic Regression baseline.

What this module does and does not claim
----------------------------------------
* The score is a statistical similarity to the writing patterns of the training articles. It is not a fact check.
* The per-term "explanation" is exact for this linear model: each term's contribution is its TF-IDF value times the
  learned coefficient. It shows what moved the score, not whether a claim is true.
* The model never outputs "Misleading"; it is a binary classifier.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn

from app.core.config import get_settings
from app.ml.text_detection.preprocess import clean_text, clean_urdu, looks_urdu, script_hint, token_count

logger = logging.getLogger("ddn.text")

LABEL_FAKE = "Likely Fake"
LABEL_REAL = "Likely Real"
LABEL_UNVERIFIED = "Unverified"


class TextModelUnavailable(RuntimeError):
    """Raised when no trained checkpoint exists."""


class TextDetector:
    """One detector per language. `language` is "en" or "ur"; the two share the decision rule and the explanation."""

    def __init__(self, checkpoint: Path, language: str = "en"):
        self.checkpoint = checkpoint
        self.language = language
        self._bundle: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def meta_path(self) -> Path:
        return self.checkpoint.with_name("model_meta.json")

    def problem(self) -> str | None:
        """Why the model cannot be used, or None. A pickled scikit-learn model is only trustworthy with the same
        scikit-learn version that trained it, so a mismatch is reported instead of silently scoring."""
        if not self.checkpoint.exists():
            return (f"No trained text model found at {self.checkpoint}. "
                    f"Run: python ai_models/training/{self._trainer}")
        try:
            trained_with = json.loads(self.meta_path.read_text(encoding="utf-8")).get("sklearn_version")
        except (OSError, ValueError):
            trained_with = None
        if trained_with != sklearn.__version__:
            return (f"The text model was trained with scikit-learn {trained_with or 'an unknown version'} but "
                    f"{sklearn.__version__} is installed. Retrain it: "
                    f"python ai_models/training/{self._trainer}")
        return None

    @property
    def _trainer(self) -> str:
        return "train_text_urdu.py" if self.language == "ur" else "train_text_baseline.py"

    @property
    def available(self) -> bool:
        return self.problem() is None

    def _load(self) -> dict[str, Any]:
        with self._lock:
            if self._bundle is None:
                problem = self.problem()
                if problem:
                    raise TextModelUnavailable(problem)
                self._bundle = joblib.load(self.checkpoint)
                logger.info("Loaded text model from %s", self.checkpoint)
            return self._bundle

    def reload(self) -> None:
        with self._lock:
            self._bundle = None

    def analyse(self, headline: str | None, text: str, top_k: int = 8) -> dict[str, Any]:
        """Return a decision dictionary. Never raises for bad input; returns an 'Unverified' result with a reason."""
        s = get_settings()
        combined = f"{headline.strip()}. {text.strip()}" if headline and headline.strip() else text.strip()
        n_tokens = token_count(combined)
        base: dict[str, Any] = {"token_count": n_tokens, "script_hint": script_hint(combined)}

        base["language"] = self.language
        # 1) Input the model cannot be trusted with. We say so instead of producing a number.
        if self.language == "en" and base["script_hint"] == "arabic_script":
            return {**base, "verdict": LABEL_UNVERIFIED, "confidence": None, "reason": "unsupported_language",
                    "message": "This text looks like Arabic-script text, and no model for its language is installed. "
                               "The English model was trained on English articles only, so it cannot assess it."}
        if self.language == "ur" and not looks_urdu(combined):
            return {**base, "verdict": LABEL_UNVERIFIED, "confidence": None, "reason": "unsupported_language",
                    "message": "This does not look like Urdu text. The Urdu model was trained on Urdu news only."}
        if n_tokens < s.min_text_tokens:
            return {**base, "verdict": LABEL_UNVERIFIED, "confidence": None, "reason": "too_short",
                    "message": f"The text has {n_tokens} words. The model was trained on full articles and needs at "
                               f"least {s.min_text_tokens} words; shorter claims are outside what it has seen."}

        bundle = self._load()
        vec, clf = bundle["vectorizer"], bundle["classifier"]
        cleaned = clean_urdu(combined) if self.language == "ur" else clean_text(combined)
        x = vec.transform([cleaned])
        p_fake = float(clf.predict_proba(x)[0, 1])
        p_real = 1.0 - p_fake

        # 2) Decision rule: only lean to a side when the model is clearly on one side.
        threshold = s.text_confidence_threshold
        if p_fake >= threshold:
            verdict, reason = LABEL_FAKE, "model_leans_fake"
        elif p_real >= threshold:
            verdict, reason = LABEL_REAL, "model_leans_real"
        else:
            verdict, reason = LABEL_UNVERIFIED, "low_confidence"

        return {
            **base,
            "verdict": verdict,
            "confidence": round(max(p_fake, p_real), 4),
            "reason": reason,
            "probabilities": {"fake": round(p_fake, 4), "real": round(p_real, 4)},
            "decision_rule": {"threshold": threshold, "min_tokens": s.min_text_tokens},
            "explanation": self._explain(vec, clf, x, top_k, self.language),
        }

    @staticmethod
    def _explain(vec, clf, x, top_k: int, language: str = "en") -> dict[str, Any]:
        coef = clf.coef_[0]
        row = x.tocoo()
        contrib = row.data * coef[row.col]  # exact additive contribution of each present term to the log-odds
        terms = np.array(vec.get_feature_names_out())[row.col]
        order = np.argsort(contrib)
        toward_real = [{"term": str(terms[i]), "weight": round(float(contrib[i]), 4)} for i in order[:top_k] if contrib[i] < 0]
        toward_fake = [{"term": str(terms[i]), "weight": round(float(contrib[i]), 4)} for i in order[::-1][:top_k] if contrib[i] > 0]
        return {
            "method": "TF-IDF value x logistic-regression coefficient (exact for this linear model)"
                      + (". The terms are character sequences, not whole words" if language == "ur" else ""),
            "toward_fake": toward_fake,
            "toward_real": toward_real,
            "intercept": round(float(clf.intercept_[0]), 4),
            "caution": "These terms show what moved the score in the training data's statistics. They are not evidence "
                       "that any claim in the text is true or false.",
        }


_detector: TextDetector | None = None
_urdu_detector: TextDetector | None = None


def get_detector() -> TextDetector:
    global _detector
    if _detector is None:
        _detector = TextDetector(get_settings().models_dir / "text_baseline_en" / "model.joblib", "en")
    return _detector


def get_urdu_detector() -> TextDetector:
    global _urdu_detector
    if _urdu_detector is None:
        _urdu_detector = TextDetector(get_settings().models_dir / "text_baseline_ur" / "model.joblib", "ur")
    return _urdu_detector


def choose_detector(headline: str | None, text: str) -> TextDetector:
    """Urdu text goes to the Urdu model when it is installed. Everything else goes to the English one, which declines
    scripts it does not know."""
    combined = f"{headline.strip()}. {text.strip()}" if headline and headline.strip() else text.strip()
    if looks_urdu(combined) and get_urdu_detector().available:
        return get_urdu_detector()
    return get_detector()

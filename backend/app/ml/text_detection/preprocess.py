"""Text cleaning and language-script detection, shared by training and inference.

Using the same function in both places is essential: the model must see text prepared the same way it was trained.
"""
from __future__ import annotations

import html
import re
import unicodedata

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
# Source tags such as "WASHINGTON (Reuters) -" are strong shortcuts in some public datasets: a model can learn
# "the article names a wire agency" instead of anything about the content. We remove the most common ones.
_DATELINE = re.compile(r"^\s*[A-Z][A-Za-z .,'/&-]{1,45}\((?:Reuters|AP|AFP)\)\s*[-–—]\s*")
_SOURCE_WORDS = re.compile(r"\b(?:reuters|21st century wire|featured image|getty images?|image via)\b", re.I)
_WS = re.compile(r"\s+")
_ARABIC_SCRIPT = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = _URL.sub(" ", text)
    text = _DATELINE.sub("", text)
    text = _SOURCE_WORDS.sub(" ", text)
    return _WS.sub(" ", text).strip()


def script_hint(text: str) -> str:
    """'arabic_script' (Urdu, Arabic, Persian...) or 'latin_or_other'. Roman Urdu cannot be detected this way."""
    letters = _LETTER.findall(text)
    if not letters:
        return "latin_or_other"
    arabic = len(_ARABIC_SCRIPT.findall(text))
    return "arabic_script" if arabic / len(letters) > 0.3 else "latin_or_other"


def token_count(text: str) -> int:
    return len(text.split())


# Letters that Urdu uses and Arabic does not (and Persian mostly does not): ٹ ڈ ڑ ں ے ہ ھ. Used to tell Urdu apart from
# other Arabic-script text, which the Urdu model has never seen.
_URDU_ONLY = re.compile(r"[ٹڈڑںےہھ]")


def clean_urdu(text: str) -> str:
    """Unicode NFC, links removed, white space collapsed. ai_models/training/train_text_urdu.py has an identical copy
    (a test keeps the two the same), because the model must see text prepared exactly as it was trained."""
    text = unicodedata.normalize("NFC", text or "")
    return _WS.sub(" ", _URL.sub(" ", text)).strip()


def looks_urdu(text: str) -> bool:
    """True when Arabic-script text contains enough Urdu-only letters to be Urdu. Roman Urdu cannot be detected."""
    letters = _LETTER.findall(text)
    if not letters or script_hint(text) != "arabic_script":
        return False
    return len(_URDU_ONLY.findall(text)) / len(letters) >= 0.02

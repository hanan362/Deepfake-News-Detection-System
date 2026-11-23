"""The Urdu text baseline: language routing, honest declines, and a real model result. Needs the trained Urdu model
(python ai_models/training/train_text_urdu.py) for the tests marked needs_urdu."""
import ast
import math
import re
import unicodedata
from pathlib import Path

import pytest

from app.ml.text_detection import service as text_service
from app.ml.text_detection.preprocess import clean_urdu, looks_urdu
from app.ml.text_detection.service import choose_detector, get_detector, get_urdu_detector
from tests.conftest import API, ARTICLE

needs_urdu = pytest.mark.skipif(not get_urdu_detector().available, reason="Urdu model not trained (run ai_models/training/train_text_urdu.py)")

# Urdu written for these tests (a made-up local news item), long enough to pass the 60-word minimum.
URDU = (
    "شہر کی انتظامیہ نے منگل کی شام اجلاس میں آئندہ دو سال کے لیے نیا بجٹ منظور کر لیا جس میں پبلک ٹرانسپورٹ، سڑکوں کی مرمت "
    "اور لائبریریوں کے لیے رقم بڑھائی گئی ہے۔ اجلاس میں شریک ارکان نے کہا کہ یہ منصوبہ کئی ماہ کی مشاورت اور آزاد آڈیٹروں کی "
    "جائزہ رپورٹوں کے بعد تیار کیا گیا ہے۔ میئر نے صحافیوں کو بتایا کہ اس کے اخراجات پارکنگ فیس میں معمولی اضافے اور غیر ضروری "
    "انتظامی منصوبوں کی تاخیر سے ہونے والی بچت سے پورے کیے جائیں گے۔ اپوزیشن ارکان نے کہا کہ وقت کا جدول بہت مشکل ہے اور "
    "ہر تین ماہ بعد پیش رفت کی رپورٹ پیش کرنے کا مطالبہ کیا۔ شہریوں نے بھی اس اقدام پر ملا جلا ردعمل ظاہر کیا۔"
)
ARABIC = "هذا نص عربي طويل عن الأخبار والسياسة في العالم العربي والاقتصاد " * 12
PERSIAN = "این یک متن فارسی درباره اخبار و سیاست و اقتصاد در کشور است که نوشته شده " * 12


def test_urdu_text_is_told_apart_from_arabic_persian_and_english():
    assert looks_urdu(URDU)
    assert not looks_urdu(ARABIC)
    assert not looks_urdu(PERSIAN)
    assert not looks_urdu(ARTICLE)
    assert not looks_urdu("")


def test_urdu_cleaning_is_identical_in_training_and_serving():
    """The trainer keeps its own copy of clean_urdu. If the two ever differ, the model would see different text than it
    was trained on."""
    src = Path(__file__).resolve().parents[2] / "ai_models" / "training" / "train_text_urdu.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    wanted = {"_URL", "_WS", "clean_urdu"}
    parts = [ast.get_source_segment(src.read_text(encoding="utf-8"), n) for n in tree.body
             if (isinstance(n, ast.FunctionDef) and n.name in wanted)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in wanted for t in n.targets))]
    ns = {"re": re, "unicodedata": unicodedata}
    exec("\n".join(parts), ns)  # noqa: S102  (our own training script, read from the repository)
    for sample in (URDU, "  http://example.com/x  خبر\n\n آج  ", "é ٹھیک ہے", ""):
        assert ns["clean_urdu"](sample) == clean_urdu(sample)


@needs_urdu
def test_urdu_text_goes_to_the_urdu_model_and_returns_a_valid_result():
    assert choose_detector(None, URDU).language == "ur"
    a = get_urdu_detector().analyse("بجٹ", URDU)
    assert a["language"] == "ur" and a["verdict"] in {"Likely Fake", "Likely Real", "Unverified"}
    p = a["probabilities"]
    assert math.isclose(p["fake"] + p["real"], 1.0, abs_tol=1e-3)
    assert a == get_urdu_detector().analyse("بجٹ", URDU)  # deterministic
    assert "character sequences" in a["explanation"]["method"]
    assert a["explanation"]["toward_fake"] or a["explanation"]["toward_real"]


@needs_urdu
def test_the_urdu_explanation_adds_up_exactly():
    """Each term's contribution plus the intercept equals the model's log-odds, as for the English model."""
    import numpy as np

    det = get_urdu_detector()
    bundle = det._load()
    vec, clf = bundle["vectorizer"], bundle["classifier"]
    x = vec.transform([clean_urdu("بجٹ. " + URDU)])
    row = x.tocoo()
    total = float((row.data * clf.coef_[0][row.col]).sum() + clf.intercept_[0])
    assert math.isclose(total, float(clf.decision_function(x)[0]), abs_tol=1e-6)
    assert isinstance(np.asarray(clf.coef_), np.ndarray)


@needs_urdu
def test_urdu_endpoint_stores_the_language_and_the_urdu_model_version(client, alice):
    r = client.post(f"{API}/analysis/text", json={"headline": "بجٹ", "text": URDU}, headers=alice.headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["details"]["language"] == "ur"
    assert body["model"]["name"] == "text_baseline_ur" and body["model"]["status"] == "experimental"
    assert "experimental Urdu" in body["limitations"] and "No other Urdu data" in body["limitations"]
    assert client.get(f"{API}/analysis/{body['id']}", headers=alice.headers).json()["details"]["language"] == "ur"


@needs_urdu
def test_short_urdu_and_other_arabic_script_text_are_declined(client, alice):
    short = client.post(f"{API}/analysis/text", json={"text": "یہ ایک مختصر خبر ہے"}, headers=alice.headers).json()
    assert short["verdict"] == "Unverified" and short["details"]["reason"] == "too_short"
    for text in (ARABIC, PERSIAN):
        r = client.post(f"{API}/analysis/text", json={"text": text}, headers=alice.headers).json()
        assert r["verdict"] == "Unverified" and r["details"]["reason"] == "unsupported_language"
        assert "probabilities" not in r["details"]


def test_without_the_urdu_model_urdu_text_is_declined_not_guessed(monkeypatch):
    monkeypatch.setattr(text_service.TextDetector, "available", property(lambda self: self.language != "ur" and True))
    det = choose_detector(None, URDU)
    assert det.language == "en"
    if get_detector().available:
        r = det.analyse(None, URDU)
        assert r["verdict"] == "Unverified" and r["reason"] == "unsupported_language" and "probabilities" not in r


@needs_urdu
def test_registry_reports_the_urdu_model_as_experimental_with_its_measured_numbers(client, admin):
    models = {m["module"]: m for m in client.get(f"{API}/models", headers=admin.headers).json()["models"]}
    ur = models["text_ur"]
    assert ur["status"] == "experimental" and ur["metrics"]["test"]["roc_auc"] > 0.5
    assert client.get(f"{API}/models", headers=admin.headers).json()["limits"]["text_languages"] == ["en", "ur"]
    assert client.get(f"{API}/modules").json()["limits"]["text_languages"] == ["en", "ur"]
    ev = client.get(f"{API}/models/text-ur/evaluation", headers=admin.headers).json()
    assert ev["evaluation"]["test"]["n"] == ur["metrics"]["test"]["n"]
    assert ev["dataset"]["pairing"]["nearest_neighbour_has_opposite_label"] > 0.5  # the data-quality finding is kept

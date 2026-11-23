import math

import numpy as np
import pytest

from app.core.config import get_settings
from app.ml.text_detection.preprocess import clean_text, script_hint, token_count
from app.ml.text_detection.service import get_detector

from .conftest import API, ARTICLE

needs_model = pytest.mark.skipif(not get_detector().available, reason="text model not trained (run ai_models/training/train_text_baseline.py)")


def test_clean_text_removes_source_shortcuts_but_keeps_content():
    out = clean_text("WASHINGTON (Reuters) - The senate passed the bill. Read more at https://example.com/x &amp; here")
    assert "Reuters" not in out and "http" not in out and "&amp;" not in out
    assert "senate passed the bill" in out


def test_script_hint_and_token_count():
    assert script_hint("This is plain English text.") == "latin_or_other"
    assert script_hint("یہ ایک اردو جملہ ہے جو خبر کے بارے میں ہے") == "arabic_script"
    assert script_hint("") == "latin_or_other"
    assert token_count("one two  three") == 3


@needs_model
def test_short_text_is_declined_not_scored():
    r = get_detector().analyse(None, "Breaking: shocking news you will not believe!")
    assert r["verdict"] == "Unverified" and r["reason"] == "too_short" and r["confidence"] is None
    assert "probabilities" not in r


@needs_model
def test_non_english_script_is_declined():
    urdu = "یہ ایک بہت لمبی اردو خبر ہے " * 30
    r = get_detector().analyse(None, urdu)
    assert r["verdict"] == "Unverified" and r["reason"] == "unsupported_language"


@needs_model
def test_probabilities_are_valid_deterministic_and_never_misleading():
    a = get_detector().analyse("Budget", ARTICLE)
    b = get_detector().analyse("Budget", ARTICLE)
    assert a == b
    p = a["probabilities"]
    assert math.isclose(p["fake"] + p["real"], 1.0, abs_tol=1e-3)
    assert a["verdict"] in {"Likely Fake", "Likely Real", "Unverified"}  # the binary model never outputs "Misleading"
    assert a["confidence"] == pytest.approx(max(p.values()), abs=1e-4)


@needs_model
def test_decision_rule_respects_threshold():
    s = get_settings()
    a = get_detector().analyse(None, ARTICLE)
    if a["confidence"] < s.text_confidence_threshold:
        assert a["verdict"] == "Unverified" and a["reason"] == "low_confidence"
    else:
        assert a["verdict"] != "Unverified"


@needs_model
def test_explanation_is_exact_for_the_linear_model():
    """The listed term contributions must be the real ones: TF-IDF value x coefficient, and together with the intercept
    they must reproduce the model's log-odds."""
    detector = get_detector()
    bundle = detector._load()
    vec, clf = bundle["vectorizer"], bundle["classifier"]
    result = detector.analyse("Budget", ARTICLE)
    x = vec.transform([clean_text("Budget. " + ARTICLE)])
    logit = float((x @ clf.coef_[0])[0] + clf.intercept_[0])
    assert result["probabilities"]["fake"] == pytest.approx(1 / (1 + math.exp(-logit)), abs=1e-3)
    names = list(vec.get_feature_names_out())
    for item in result["explanation"]["toward_fake"] + result["explanation"]["toward_real"]:
        idx = names.index(item["term"])
        assert item["weight"] == pytest.approx(float(x[0, idx] * clf.coef_[0][idx]), abs=1e-3)
    assert all(i["weight"] > 0 for i in result["explanation"]["toward_fake"])
    assert all(i["weight"] < 0 for i in result["explanation"]["toward_real"])
    import re
    words = set(re.findall(r"\b\w\w+\b", ("Budget. " + ARTICLE).lower()))
    for item in result["explanation"]["toward_fake"] + result["explanation"]["toward_real"]:
        assert set(item["term"].split()) <= words  # every listed term really occurs in the submitted text


@needs_model
def test_text_endpoint_stores_a_complete_result(client, alice):
    r = client.post(f"{API}/analysis/text", json={"headline": "City budget", "text": ARTICLE}, headers=alice.headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["analysis_type"] == "text" and body["model"]["status"] == "trained_baseline"
    assert "not a fact checker" in body["limitations"] and body["is_demo"] is False
    assert body["details"]["decision_rule"]["min_tokens"] == get_settings().min_text_tokens
    assert body["submitted_text"] == ARTICLE  # the detail view returns the text so the page can mark the explained words
    listing = client.get(f"{API}/analysis", headers=alice.headers).json()["items"][0]
    assert listing["submitted_text"] is None  # the list view stays light
    again = client.get(f"{API}/analysis/{body['id']}", headers=alice.headers).json()
    assert again["verdict"] == body["verdict"] and again["details"] == body["details"]


@needs_model
def test_short_text_endpoint_is_honest(client, alice):
    r = client.post(f"{API}/analysis/text", json={"text": "Too short to judge."}, headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["verdict"] == "Unverified" and r.json()["confidence"] is None
    assert r.json()["details"]["reason"] == "too_short"


def test_text_endpoint_validation(client, alice):
    assert client.post(f"{API}/analysis/text", json={"text": ""}, headers=alice.headers).status_code == 422
    assert client.post(f"{API}/analysis/text", json={}, headers=alice.headers).status_code == 422
    assert client.post(f"{API}/analysis/text", json={"text": "x " * 40}).status_code == 401
    too_long = "word " * (get_settings().max_text_chars // 4)
    assert client.post(f"{API}/analysis/text", json={"text": too_long}, headers=alice.headers).status_code == 413


def test_missing_model_gives_a_clear_503(client, alice, monkeypatch, tmp_path):
    from app.ml.text_detection import service
    monkeypatch.setattr(service, "_detector", service.TextDetector(tmp_path / "missing.joblib"))
    r = client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=alice.headers)
    assert r.status_code == 503 and r.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert "train_text_baseline" in r.json()["error"]["message"]


@needs_model
def test_registry_metrics_match_the_evaluation_file():
    """The numbers the app reports must be the numbers the training run measured, not typed in by hand."""
    import json
    from app.core.config import PROJECT_ROOT
    res = json.loads((PROJECT_ROOT / "ai_models/evaluation/results/text_baseline_en_metrics.json").read_text())
    reg = json.loads((PROJECT_ROOT / "ai_models/model_registry/text_baseline_en.json").read_text())
    lr = res["comparison"]["logistic_regression"]
    assert reg["metrics"]["test"] == lr["test"] and reg["metrics"]["external_liar2"] == lr["external_liar2"]
    assert np.isclose(reg["metrics"]["test"]["roc_auc"], lr["test"]["roc_auc"])


@needs_model
def test_version_mismatch_is_refused_not_silently_scored(client, alice, admin, tmp_path, monkeypatch):
    """A model pickled by another scikit-learn version must not be used; the user gets a clear retrain message."""
    import json
    import shutil

    from app.ml.text_detection import service
    ckpt = tmp_path / "model.joblib"
    shutil.copy(get_detector().checkpoint, ckpt)
    (tmp_path / "model_meta.json").write_text(json.dumps({"sklearn_version": "0.0.1"}))
    monkeypatch.setattr(service, "_detector", service.TextDetector(ckpt))
    r = client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=alice.headers)
    assert r.status_code == 503 and "Retrain" in r.json()["error"]["message"] and "0.0.1" in r.json()["error"]["message"]
    text_entry = next(m for m in client.get(f"{API}/modules").json()["models"] if m["module"] == "text")
    assert text_entry["status"] == "unavailable" and "not available" in text_entry["description"]
    assert "Retrain" not in text_entry["description"]  # the instructions for the owner are for administrators only
    detail = next(m for m in client.get(f"{API}/models", headers=admin.headers).json()["models"] if m["module"] == "text")
    assert "Retrain" in detail["description"]

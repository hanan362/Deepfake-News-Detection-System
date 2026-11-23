"""Image + text analysed together: the fusion rule, the consistency check and the API. CLIP is replaced by a stub for the
logic tests (so they are exact and fast); one test runs the real CLIP model when it is installed."""
import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.db.session import SessionLocal
from app.ml.multimodal import clip_consistency as cc
from app.ml.multimodal.fusion import fuse
from app.ml.text_detection.service import get_detector
from app.models import AuditLog
from tests.conftest import API, ARTICLE, make_image_bytes

needs_model = pytest.mark.skipif(not get_detector().available, reason="text model not trained")
needs_clip = pytest.mark.skipif(not cc.get_clip().available, reason="CLIP not available (pip install -r backend/requirements-ml.txt)")
CAL = {"consistent_min": 0.33, "inconsistent_max": 0.27}


class StubClip:
    available = True

    def __init__(self, sim):
        self.sim = sim

    def problem(self):
        return None

    def similarity(self, image_bytes, caption):
        return self.sim


class DownClip(StubClip):
    available = False

    def problem(self):
        return "The packages torch and transformers are not installed."


@pytest.fixture
def stub(monkeypatch):
    def use(sim=0.30, calibrated=True, clip=None):
        monkeypatch.setattr(cc, "get_clip", lambda: clip or StubClip(sim))
        monkeypatch.setattr(cc, "load_calibration", lambda: CAL if calibrated else None)
    return use


# ------------------------------------------------------------------ the fusion rule (pure)

@pytest.mark.parametrize("text,image,cons,verdict", [
    ("Likely Real", True, "consistent", "Likely Real"), ("Likely Real", True, "unclear", "Likely Real"),
    ("Likely Real", True, "inconsistent", "Mismatch Flagged"), ("Unverified", True, "inconsistent", "Mismatch Flagged"),
    ("Likely Fake", True, "inconsistent", "Likely Fake"), ("Likely Fake", False, None, "Likely Fake"),
    (None, True, None, "Indicators Only"), (None, True, "not_possible", "Indicators Only"),
    ("Unverified", True, "consistent", "Unverified"), ("Unverified", False, None, "Unverified"),
])
def test_fusion_rule(text, image, cons, verdict):
    assert fuse(text, image, cons)["verdict"] == verdict


def test_fusion_never_lets_image_forensics_or_a_missing_clip_change_the_verdict():
    assert fuse("Likely Real", True, "not_assessed")["verdict"] == "Likely Real"
    assert fuse("Likely Real", True, "not_calibrated")["verdict"] == "Likely Real"
    assert "rule" in fuse(None, False, None) and "Image forensics never changes" in fuse(None, False, None)["rule"]


# ------------------------------------------------------------------ consistency (stubbed model)

def test_caption_comes_from_the_headline_then_the_text():
    assert cc.caption_for("  A headline ", "text") == ("A headline", "headline")
    assert cc.caption_for(None, "Some   text\nhere") == ("Some text here", "opening of the text")
    assert cc.caption_for(None, "  ") == (None, None)


@pytest.mark.parametrize("sim,label", [(0.40, "consistent"), (0.33, "consistent"), (0.30, "unclear"), (0.27, "inconsistent"), (0.10, "inconsistent")])
def test_similarity_becomes_a_label_through_measured_thresholds(sim, label):
    assert cc.label_for(sim, CAL) == label
    assert cc.label_for(sim, None) == "not_calibrated"


def test_consistency_states(stub):
    img = make_image_bytes()
    stub(0.40)
    assert cc.assess(None, "headline", None)["status"] == "not_possible"
    assert cc.assess(img, None, None)["status"] == "not_possible"
    a = cc.assess(img, "A headline", "text")
    assert a["status"] == "assessed" and a["label"] == "consistent" and a["similarity"] == 0.4 and a["thresholds"] == CAL
    stub(clip=DownClip(0))
    d = cc.assess(img, "A headline", None)
    assert d["status"] == "not_assessed" and "not installed" in d["note"] and d["similarity"] is None
    stub(0.40, calibrated=False)
    assert cc.assess(img, "h", None)["label"] == "not_calibrated"


def test_the_installed_thresholds_are_ordered_and_measured():
    cal = cc.load_calibration()
    if cal is None:
        pytest.skip("evaluate_clip_consistency.py has not been run")
    assert cal["inconsistent_max"] < cal["consistent_min"] and 0 < cal["inconsistent_max"] < 1


@needs_clip
def test_the_real_model_scores_matching_text_above_mismatching_text():
    img = Image.new("RGB", (336, 336), "white")
    ImageDraw.Draw(img).text((40, 120), "DOG", fill="black", font=ImageFont.load_default(size=140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    clip = cc.get_clip()
    assert clip.similarity(buf.getvalue(), 'a photo of the word "DOG"') > clip.similarity(buf.getvalue(), 'a photo of the word "BANANA"')


# ------------------------------------------------------------------ the API

def _post(client, user, *, image=None, text=None, headline=None, name="photo.jpg"):
    files = {"file": (name, image, "image/jpeg")} if image is not None else None
    data = {k: v for k, v in (("text", text), ("headline", headline)) if v is not None}
    return client.post(f"{API}/analysis/multimodal", files=files, data=data, headers=user.headers)


@needs_model
def test_image_and_article_get_three_separate_results_and_a_fused_verdict(client, alice, stub):
    stub(0.30)
    r = _post(client, alice, image=make_image_bytes(), text=ARTICLE, headline="City council approves budget")
    assert r.status_code == 201, r.text
    a = r.json()
    d = a["details"]
    assert a["analysis_type"] == "multimodal" and a["has_heatmap"] and a["source_filename"] == "photo.jpg"
    assert d["modalities"] == {"text": "analysed", "image": "analysed", "consistency": "assessed"}
    assert "probabilities" in d["text_result"] and d["image_result"]["ela"]["mean"] >= 0 and d["consistency"]["label"] == "unclear"
    assert d["fusion"]["verdict"] == a["verdict"] == d["text_result"]["verdict"] and d["fusion"]["rule"]
    assert a["model"]["name"] == "text_image_consistency"
    # the image and the error-level map are served to the owner only
    assert client.get(f"{API}/analysis/{a['id']}/image", headers=alice.headers).status_code == 200
    assert client.get(f"{API}/analysis/{a['id']}/heatmap", headers=alice.headers).headers["content-type"] == "image/png"
    pdf = client.get(f"{API}/analysis/{a['id']}/report.pdf", headers=alice.headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get(f"{API}/analysis?analysis_type=multimodal", headers=alice.headers).json()["total"] == 1
    assert client.delete(f"{API}/analysis/{a['id']}", headers=alice.headers).status_code == 204
    assert client.get(f"{API}/analysis/{a['id']}/image", headers=alice.headers).status_code == 404


def test_a_clear_mismatch_with_a_short_caption_is_flagged_not_called_fake(client, alice, stub):
    stub(0.10)
    a = _post(client, alice, image=make_image_bytes(), text="Flood waters rise in the capital after heavy rain.").json()
    d = a["details"]
    assert d["modalities"]["text"] == "too_short"  # a caption is far below the text model's 60-word minimum
    assert d["consistency"]["label"] == "inconsistent" and a["verdict"] == "Mismatch Flagged" and a["confidence"] is None
    assert d["fusion"]["base_verdict"] == "Unverified"
    assert "Flickr" in a["limitations"]


def test_a_matching_short_caption_stays_unverified(client, alice, stub):
    stub(0.40)
    a = _post(client, alice, image=make_image_bytes(), text="A man in an orange hat.").json()
    assert a["verdict"] == "Unverified" and a["details"]["consistency"]["label"] == "consistent"
    assert any("could not be judged" in n for n in a["details"]["fusion"]["notes"])


def test_each_modality_can_be_missing_and_the_result_says_so(client, alice, stub):
    stub(0.30)
    img = _post(client, alice, image=make_image_bytes()).json()
    assert img["verdict"] == "Indicators Only" and img["details"]["modalities"] == {"text": "not_provided", "image": "analysed", "consistency": "not_possible"}
    assert img["details"]["text_result"] is None and img["details"]["image_result"]
    txt = _post(client, alice, text=ARTICLE).json()
    assert txt["details"]["modalities"]["image"] == "not_provided" and txt["details"]["consistency"]["status"] == "not_possible" and not txt["has_heatmap"]
    assert txt["details"]["image_result"] is None


def test_without_clip_the_other_results_still_work_and_say_consistency_was_not_assessed(client, alice, stub):
    stub(clip=DownClip(0))
    a = _post(client, alice, image=make_image_bytes(), text="A man in an orange hat.").json()
    assert a["details"]["modalities"]["consistency"] == "not_assessed" and a["details"]["image_result"] and a["verdict"] == "Unverified"


def test_bad_input_is_refused_cleanly(client, alice, stub):
    stub()
    assert _post(client, alice).status_code == 422
    r = _post(client, alice, image=b"not an image", text="hello there")
    assert r.status_code == 415 and r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert _post(client, alice, text="x" * 50_001).status_code == 413
    assert client.post(f"{API}/analysis/multimodal", data={"text": "hello"}).status_code == 401
    assert client.get(f"{API}/analysis", headers=alice.headers).json()["total"] == 0


def test_privacy_and_audit(client, alice, bob, stub):
    stub()
    a = _post(client, alice, image=make_image_bytes(), text="A short caption for the photo.").json()
    assert client.get(f"{API}/analysis/{a['id']}", headers=bob.headers).status_code == 404
    assert client.get(f"{API}/analysis/{a['id']}/image", headers=bob.headers).status_code == 404
    with SessionLocal() as db:
        assert db.query(AuditLog).filter(AuditLog.action == "analysis.multimodal").count() == 1


def test_the_registry_entry_states_how_the_verdict_is_made(client, admin):
    m = {x["module"]: x for x in client.get(f"{API}/models", headers=admin.headers).json()["models"]}["multimodal"]
    assert m["status"] in {"pretrained", "heuristic"} and "fixed rule" in m["description"]
    assert any("not a learned model" in x for x in m["limitations"]) and any("Flickr30k" in x for x in m["limitations"])

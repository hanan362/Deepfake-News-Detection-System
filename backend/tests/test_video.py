"""Video analysis: validation, frame sampling, the decision rule, storage and the API.

Real video files are made with OpenCV. The face detector and the frame classifier are replaced by stubs in the logic
tests, so those tests check the pipeline's rules (never one frame, no face means no score, the thresholds) exactly and fast;
they do not measure detection quality. Detection and classification quality are measured separately on real datasets
(ai_models/training/evaluate_video.py); one test here runs the real face detector on a face-free video."""
import os
import struct
from pathlib import Path

import numpy as np
import pytest

from app.core.config import get_settings
from app.ml.video_detection import faces, frames as vf, pipeline, temporal
from app.ml.video_detection.faces import Face
from tests.conftest import API

cv2 = pytest.importorskip("cv2", reason="opencv not installed (pip install -r backend/requirements-ml.txt)")
needs_detector = pytest.mark.skipif(faces.problem() is not None, reason="face detector file missing")
CAL = {"fake_min": 0.70, "real_max": 0.30, "target_precision": 0.8, "aggregator": "mean"}


def make_video(tmp_path: Path, frames: int = 40, fps: int = 20, size=(160, 120), name="clip.mp4", fourcc="mp4v") -> bytes:
    path = tmp_path / name
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*fourcc), fps, size)
    assert w.isOpened(), "this OpenCV build cannot write test videos"
    rng = np.random.default_rng(1)
    for i in range(frames):
        img = np.full((size[1], size[0], 3), (i * 5) % 255, dtype=np.uint8)
        img[rng.integers(0, size[1] // 2), :, :] = 255
        w.write(img)
    w.release()
    return path.read_bytes()


class StubClassifier:
    model_id = "stub/frame-model"

    def __init__(self, score=0.9, problem=None):
        self.score, self._problem = score, problem

    def problem(self):
        return self._problem

    def p_fake(self, crops):
        return [self.score] * len(crops)


@pytest.fixture
def video_bytes(tmp_path):
    return make_video(tmp_path)


@pytest.fixture
def use(monkeypatch):
    """Pretend every frame has a face (the whole frame), with a stub classifier and thresholds."""
    def _use(score=0.9, calibration=CAL, face_every=1, problem=None):
        counter = {"n": 0}

        def fake_face(frame):
            counter["n"] += 1
            if counter["n"] % face_every:
                return None
            h, w = frame.shape[:2]
            return Face((10, 10, w // 2, h // 2), cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), 0.5, 0.99)

        monkeypatch.setattr(faces, "largest_face", fake_face)
        monkeypatch.setattr(pipeline, "get_classifier", lambda: StubClassifier(score, problem))
        monkeypatch.setattr(pipeline, "calibration", lambda: calibration)
    return _use


def post_video(client, user, data, name="clip.mp4", mime="video/mp4"):
    return client.post(f"{API}/analysis/video", headers=user.headers, files={"file": (name, data, mime)})


# ------------------------------------------------------------------ pure parts

def test_container_is_recognised_by_content_not_name():
    assert vf.sniff_extension(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8) == "mp4"
    assert vf.sniff_extension(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 8) == "mov"
    assert vf.sniff_extension(b"\x1a\x45\xdf\xa3" + b"\x00" * 12) == "webm"
    assert vf.sniff_extension(b"RIFF" + struct.pack("<I", 100) + b"AVI LIST") == "avi"
    for junk in (b"MZ" + b"\x00" * 20, b"GIF89a" + b"\x00" * 20, b"<html>" + b"\x00" * 20, b"short"):
        with pytest.raises(vf.VideoRejected):
            vf.sniff_extension(junk)


def test_samples_are_spread_over_the_whole_video():
    idx = vf.sample_indices(1000, 10)
    assert len(idx) == 10 and idx == sorted(idx) and idx[0] < 100 and idx[-1] > 900
    assert all(b - a > 50 for a, b in zip(idx, idx[1:]))
    assert vf.sample_indices(5, 24) == [0, 1, 2, 3, 4]  # a short video yields every frame once, never duplicates


def test_aggregation_and_summary():
    scores = [0.1, 0.2, 0.9, 0.95, 0.9, 0.1, 0.2, 0.1]
    agg = temporal.aggregate(scores)
    assert agg["flagged_share"] == pytest.approx(3 / 8) and agg["top_quartile_mean"] == pytest.approx((0.95 + 0.9) / 2)
    summary = temporal.summarise(list(range(8)), scores)
    assert summary["longest_flagged_run"] == 3 and summary["frames_scored"] == 8 and summary["max"] == 0.95
    moments = temporal.suspicious_moments([float(i) for i in range(8)], scores, top=3)
    assert [m["t"] for m in moments] == [2.0, 3.0, 4.0]  # in time order
    assert temporal.suspicious_moments([0.0, 1.0], [0.1, 0.2]) == []  # nothing is called suspicious below the flag level


def test_thresholds_need_real_separation():
    rng = np.random.default_rng(0)
    y = np.array([0] * 30 + [1] * 30)
    good = np.concatenate([rng.uniform(0.0, 0.4, 30), rng.uniform(0.6, 1.0, 30)])
    cal = temporal.calibrate(y, good)
    assert cal["fake_min"] is not None and cal["real_max"] is not None and cal["real_max"] < cal["fake_min"]
    assert temporal.decide(0.95, cal) == "fake" and temporal.decide(0.05, cal) == "real" and temporal.decide(0.5, cal) == "undecided"
    # ties and overlap: the thresholds never cross, however the scores are distributed
    for seed in range(5):
        noise = temporal.calibrate(y, np.random.default_rng(seed).uniform(0, 1, 60))
        assert noise["fake_min"] is None or noise["real_max"] is None or noise["real_max"] < noise["fake_min"]
    flat = temporal.calibrate(y, np.full(60, 0.5))  # a score that never changes cannot separate anything
    assert flat["fake_min"] is None and flat["real_max"] is None
    assert temporal.calibrate(np.array([0, 1] * 3), np.array([0.1, 0.9] * 3))["fake_min"] is None  # too few videos to trust a rule


# ------------------------------------------------------------------ the API

def test_requires_login_and_a_file(client, alice):
    assert client.post(f"{API}/analysis/video", files={"file": ("a.mp4", b"x", "video/mp4")}).status_code == 401
    assert client.post(f"{API}/analysis/video", headers=alice.headers).status_code == 422


@pytest.mark.parametrize("name,mime,data", [
    ("virus.mp4", "video/mp4", b"MZ" + b"\x00" * 200), ("notes.txt", "text/plain", b"hello world, not a video"),
    ("fake.mp4", "video/mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100)])
def test_non_videos_are_refused_by_content(client, alice, name, mime, data):
    r = post_video(client, alice, data, name, mime)
    assert r.status_code == 415 and r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert client.get(f"{API}/analysis", headers=alice.headers).json()["total"] == 0


def test_empty_and_oversized_uploads(client, alice, video_bytes, monkeypatch):
    assert post_video(client, alice, b"").status_code == 400
    monkeypatch.setattr(get_settings(), "max_video_mb", 0)
    assert post_video(client, alice, video_bytes).status_code == 413


def test_video_over_the_length_limit(client, alice, tmp_path, monkeypatch, use):
    use()
    monkeypatch.setattr(get_settings(), "max_video_seconds", 1)
    r = post_video(client, alice, make_video(tmp_path, frames=60, fps=20))
    assert r.status_code == 413 and "longer than 1 seconds" in r.json()["error"]["message"]


def test_a_video_without_a_face_is_not_scored_with_the_real_detector(client, alice, video_bytes):
    if faces.problem():
        pytest.skip("face detector file missing")
    r = post_video(client, alice, video_bytes)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["analysis_type"] == "video" and a["verdict"] == "Unverified" and a["confidence"] is None
    d = a["details"]
    assert d["decision"]["status"] == "not_enough_faces" and d["temporal"] is None
    assert d["sampling"]["with_face"] == 0 and d["sampling"]["sampled"] >= 8
    assert all(f["face_found"] is False and f["p_fake"] is None for f in d["frames"])
    assert "single frame" in " ".join(d["observations"])


def test_every_call_needs_at_least_eight_face_frames(client, alice, video_bytes, use):
    use(score=0.99, face_every=6)  # 40 frames sampled -> ~6 with a face, all scored as very fake
    a = post_video(client, alice, video_bytes).json()
    assert 0 < a["details"]["sampling"]["with_face"] < temporal.MIN_FACE_FRAMES
    assert a["verdict"] == "Unverified" and a["details"]["decision"]["status"] == "not_enough_faces"


@pytest.mark.parametrize("score,verdict,status", [
    (0.95, "Likely Fake", "decided"), (0.05, "Likely Real", "decided"), (0.5, "Unverified", "undecided")])
def test_verdict_follows_the_measured_thresholds(client, alice, video_bytes, use, score, verdict, status):
    use(score=score)
    a = post_video(client, alice, video_bytes).json()
    assert a["verdict"] == verdict and a["details"]["decision"]["status"] == status
    t = a["details"]["temporal"]
    assert t["video_score"] == pytest.approx(score) and t["frames_scored"] >= temporal.MIN_FACE_FRAMES
    assert a["details"]["decision"]["thresholds"]["fake_min"] == 0.70
    assert a["details"]["model"]["temporal_model"] is False  # never claimed
    assert "not a model that learns motion" in a["details"]["model"]["note"]
    assert a["confidence"] is None  # a classifier score is not a probability that the video is fake


def test_without_measured_thresholds_scores_are_shown_but_not_interpreted(client, alice, video_bytes, use):
    use(score=0.99, calibration=None)
    a = post_video(client, alice, video_bytes).json()
    assert a["verdict"] == "Indicators Only" and a["details"]["decision"]["status"] == "not_calibrated"
    assert a["details"]["temporal"]["video_score"] == pytest.approx(0.99)


def test_without_the_classifier_only_measurements_are_given(client, alice, video_bytes, use):
    use(problem="The packages torch and transformers are not installed.")
    a = post_video(client, alice, video_bytes).json()
    assert a["verdict"] == "Indicators Only" and a["details"]["decision"]["status"] == "classifier_unavailable"
    assert a["details"]["temporal"] is None and a["details"]["model"]["problem"]
    scored = [f for f in a["details"]["frames"] if f["face_found"]]
    assert scored and all(f["p_fake"] is None and f["sharpness"] is not None for f in scored)


def test_one_sided_calibration_makes_no_call_on_the_missing_side(client, alice, video_bytes, use):
    use(score=0.95, calibration={**CAL, "fake_min": None})
    a = post_video(client, alice, video_bytes).json()
    assert a["verdict"] == "Unverified" and "never reached" in " ".join(a["details"]["observations"])


def test_missing_opencv_is_reported_as_unavailable(client, alice, video_bytes, monkeypatch):
    monkeypatch.setattr(vf, "cv2_installed", lambda: False)
    r = post_video(client, alice, video_bytes)
    assert r.status_code == 503 and r.json()["error"]["code"] == "MODEL_UNAVAILABLE" and "opencv" in r.json()["error"]["message"]


def test_busy_server_says_so(client, alice, video_bytes, use):
    use()
    taken = [pipeline._slots.acquire(blocking=False) for _ in range(2)]
    try:
        r = post_video(client, alice, video_bytes)
        assert r.status_code == 503 and r.json()["error"]["code"] == "BUSY"
    finally:
        for ok in taken:
            if ok:
                pipeline._slots.release()
    assert post_video(client, alice, video_bytes).status_code == 201


def test_frames_video_history_report_privacy_and_delete(client, alice, bob, video_bytes, use):
    use(score=0.9)
    a = post_video(client, alice, video_bytes, "my clip.mp4").json()
    aid, d = a["id"], a["details"]
    assert a["source_filename"] == "my clip.mp4" and a["has_heatmap"] is False
    assert all("file" not in f and f["has_image"] for f in d["frames"]), "stored file names must stay on the server"
    # a frame thumbnail and the video itself can be fetched by their owner only
    fr = client.get(f"{API}/analysis/{aid}/frames/0", headers=alice.headers)
    assert fr.status_code == 200 and fr.headers["content-type"] == "image/jpeg" and fr.content[:2] == b"\xff\xd8"
    assert client.get(f"{API}/analysis/{aid}/frames/999", headers=alice.headers).status_code == 404
    vid = client.get(f"{API}/analysis/{aid}/video", headers=alice.headers)
    assert vid.status_code == 200 and vid.headers["content-type"] == "video/mp4" and vid.content == video_bytes
    part = client.get(f"{API}/analysis/{aid}/video", headers={**alice.headers, "Range": "bytes=0-99"})
    assert part.status_code == 206 and len(part.content) == 100  # seeking works
    for path in (f"frames/0", "video"):
        assert client.get(f"{API}/analysis/{aid}/{path}", headers=bob.headers).status_code == 404
        assert client.get(f"{API}/analysis/{aid}/{path}").status_code == 401
    # history and the PDF report
    hist = client.get(f"{API}/analysis?analysis_type=video", headers=alice.headers).json()
    assert hist["total"] == 1 and hist["items"][0]["details"] is None
    pdf = client.get(f"{API}/analysis/{aid}/report.pdf", headers=alice.headers)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # deleting removes the video and every frame file
    storage = Path(os.environ["STORAGE_DIR"]) / "uploads"
    assert len(list((storage / "videos").iterdir())) == 1 and len(list((storage / "video_frames").iterdir())) == len(d["frames"])
    assert client.delete(f"{API}/analysis/{aid}", headers=bob.headers).status_code == 404
    assert client.delete(f"{API}/analysis/{aid}", headers=alice.headers).status_code == 204
    assert not list((storage / "videos").iterdir()) and not list((storage / "video_frames").iterdir())
    assert client.get(f"{API}/analysis/{aid}", headers=alice.headers).status_code == 404


def test_only_a_video_has_frames_and_a_video_file(client, alice):
    img = client.post(f"{API}/analysis/image", headers=alice.headers, files={"file": ("a.jpg", __import__("tests.conftest", fromlist=["x"]).make_image_bytes(), "image/jpeg")}).json()
    assert client.get(f"{API}/analysis/{img['id']}/frames/0", headers=alice.headers).status_code == 404
    assert client.get(f"{API}/analysis/{img['id']}/video", headers=alice.headers).status_code == 404


def test_registry_describes_the_video_module_honestly(client, admin):
    m = next(x for x in client.get(f"{API}/models", headers=admin.headers).json()["models"] if x["module"] == "video")
    assert m["status"] in {"experimental", "heuristic", "unavailable"}
    text = (m["description"] + " ".join(m["limitations"])).lower()
    assert "frame-based" in text and "not a model that learns motion" in text and "audio" in text


def test_audit_log_records_the_analysis(client, alice, video_bytes, use):
    from app.db.session import SessionLocal
    from app.models import AuditLog

    use()
    a = post_video(client, alice, video_bytes).json()
    with SessionLocal() as db:
        row = db.query(AuditLog).filter_by(action="analysis.video", entity_id=str(a["id"])).one()
        assert row.user_id == alice.id

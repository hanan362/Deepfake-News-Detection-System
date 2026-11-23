"""A model that failed to download is tried again later, not written off until the server restarts."""
import importlib.util
from types import SimpleNamespace

import pytest

from app.ml import loading
from app.ml.fact_checking.nli import NliModel
from app.ml.multimodal.clip_consistency import ClipConsistency
from app.ml.video_detection.classifier import FrameClassifier

needs_ml = pytest.mark.skipif(
    not all(importlib.util.find_spec(m) for m in ("torch", "transformers", "cv2")),
    reason="machine-learning packages not installed (pip install -r backend/requirements-ml.txt)",
)


class _Clock:
    now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = _Clock()
    monkeypatch.setattr(loading.time, "monotonic", c)
    return c


class _Net:
    """Stands in for the download: fails while `up` is False."""

    def __init__(self, result):
        self.up, self.calls, self.result = False, 0, result

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if not self.up:
            raise OSError("connection reset by peer")
        return self.result


def _model_with(labels):
    m = SimpleNamespace(config=SimpleNamespace(id2label=labels))
    m.eval = lambda: m
    return m


def test_the_retry_rule():
    assert loading.may_retry(None) is False


@needs_ml
@pytest.mark.parametrize("kind", ["clip", "nli", "video"])
def test_a_failed_download_is_retried_after_a_pause_and_then_works(monkeypatch, clock, kind):
    import transformers

    if kind == "clip":
        net_a, net_b = _Net(object()), _Net(_model_with({}))
        monkeypatch.setattr(transformers.CLIPProcessor, "from_pretrained", net_a)
        monkeypatch.setattr(transformers.CLIPModel, "from_pretrained", net_b)
        obj = ClipConsistency("x/y")
    elif kind == "nli":
        net_a, net_b = _Net(object()), _Net(_model_with({0: "entailment", 1: "neutral", 2: "contradiction"}))
        monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", net_a)
        monkeypatch.setattr(transformers.AutoModelForSequenceClassification, "from_pretrained", net_b)
        obj = NliModel("x/y")
    else:
        net_a, net_b = _Net(object()), _Net(_model_with({0: "real", 1: "fake"}))
        monkeypatch.setattr(transformers.AutoImageProcessor, "from_pretrained", net_a)
        monkeypatch.setattr(transformers.AutoModelForImageClassification, "from_pretrained", net_b)
        obj = FrameClassifier("x/y", None)

    assert obj._load() is None and obj.problem() and "could not be loaded" in obj.problem()
    first_attempts = net_a.calls

    clock.now += loading.RETRY_AFTER_SECONDS - 1  # too soon: no new attempt, the stored reason is still shown
    assert obj._load() is None
    assert net_a.calls == first_attempts
    assert "could not be loaded" in (obj.problem() or "")

    net_a.up = net_b.up = True  # the connection is back
    clock.now += 2
    assert obj._load() is not None, "the model should have loaded on the retry"
    assert net_a.calls == first_attempts + 1
    assert obj.problem() is None
    assert obj._load() is not None and net_a.calls == first_attempts + 1, "a loaded model is not loaded again"

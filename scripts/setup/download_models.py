"""Download the three pretrained models once, so the first analysis does not have to.

    CLIP (image and text check)        about 600 MB
    NLI model (evidence stance)        about 570 MB
    Frame classifier (video)           about 110 MB   (about 1.3 GB in all)

Without this step each model is downloaded the first time its page is used, which took up to 15 minutes on a slow
connection, and the server answers slowly until it has finished. Run from the project root:
    python scripts/setup/download_models.py            # all three
    python scripts/setup/download_models.py clip nli   # only some
Exit code 0 when every requested model loaded, 1 otherwise (the application still works; each model is then fetched on use)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _clip():
    from app.ml.multimodal.clip_consistency import get_clip
    c = get_clip()
    return c.model_id, (c.available, c.problem())


def _nli():
    from app.ml.fact_checking.nli import get_nli
    n = get_nli()
    return n.model_id, (n.available, n.problem())


def _video():
    from app.ml.video_detection.classifier import get_classifier
    v = get_classifier()
    return v.model_id, (v.available, v.problem())


MODELS = {"clip": ("CLIP image-text model", _clip), "nli": ("Evidence stance model", _nli), "video": ("Video frame classifier", _video)}


def main(argv: list[str]) -> int:
    wanted = argv or list(MODELS)
    unknown = [w for w in wanted if w not in MODELS]
    if unknown:
        print(f"Unknown model name(s): {', '.join(unknown)}. Choose from: {', '.join(MODELS)}.")
        return 2
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        print("torch and transformers are not installed. Run scripts/setup/install_ml first.")
        return 1
    failed = 0
    for key in wanted:
        label, loader = MODELS[key]
        print(f"- {label}: downloading and loading (this can take several minutes the first time)...", flush=True)
        t0 = time.time()
        model_id, (ok, problem) = loader()
        secs = time.time() - t0
        if ok:
            print(f"  OK  {model_id} ({secs:.0f} s)", flush=True)
        else:
            failed += 1
            print(f"  FAILED  {model_id}: {problem}", flush=True)
    if failed:
        print(f"\n{failed} of {len(wanted)} models could not be loaded. Check the internet connection and run this again. "
              "The application still starts; a missing model is downloaded when its page is first used.")
        return 1
    print("\nAll requested models are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

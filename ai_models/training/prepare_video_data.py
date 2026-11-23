"""Downloads the three small video samples that evaluate_video.py uses, with the same seeded selection every time.

  calibration  60 real + 60 fake Celeb-DF v2 videos that are NOT on the dataset's official test list  -> datasets/raw/celebdf_v2_train
  test         24 real + 24 fake videos from the official Celeb-DF v2 test list                         -> datasets/raw/celebdf_v2_test
  fresh        20 real + 20 fake videos of Google's DeepFakeDetection set (angads24/deepfake-video)     -> datasets/raw/dfd_sample

Sources are public Hugging Face mirrors (gonnerthetooner/deepfake_video_data for Celeb-DF v2, angads24/deepfake-video for
DeepFakeDetection). Both datasets keep their own terms (Celeb-DF: research use; check them before any other use). Nothing
is redistributed by this repository. About 350 MB in total.

Usage: python ai_models/training/prepare_video_data.py [--dry-run]   (--dry-run only writes the selection lists)"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "datasets" / "raw"
HF = "https://huggingface.co"
CELEB = "gonnerthetooner/deepfake_video_data"
DFD = "angads24/deepfake-video"


def get(url: str, binary: bool = False):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ddn-research"}), timeout=120) as r:
        return r.read() if binary else r.read().decode()


def siblings(repo: str) -> list[str]:
    return [s["rfilename"] for s in json.loads(get(f"{HF}/api/datasets/{repo}"))["siblings"]]


def write_selection(folder: Path, picks: list[tuple[str, str]]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "selected.txt").write_text("\n".join(f"{label}\t{path}" for path, label in picks))


def download(repo: str, prefix: str, folder: Path, picks: list[tuple[str, str]]) -> None:
    def one(item):
        path, _ = item
        out = folder / path.replace("/", "__")
        if out.exists() and out.stat().st_size > 10_000:
            return True
        try:
            out.write_bytes(get(f"{HF}/datasets/{repo}/resolve/main/{prefix}{path}", binary=True))
            return True
        except Exception as exc:  # a missing file is reported, the evaluation skips it
            print("failed:", path, exc)
            return False

    with cf.ThreadPoolExecutor(5) as ex:
        ok = list(ex.map(one, picks))
    print(f"{folder.name}: {sum(ok)} of {len(ok)} videos ready")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    test_dir, train_dir, dfd_dir = RAW / "celebdf_v2_test", RAW / "celebdf_v2_train", RAW / "dfd_sample"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "List_of_testing_videos.txt").write_text(get(f"{HF}/datasets/{CELEB}/resolve/main/celebdf_v2/List_of_testing_videos.txt"))
    rows = [l.split() for l in (test_dir / "List_of_testing_videos.txt").read_text().splitlines() if l.strip()]
    test_real, test_fake = [p for l, p in rows if l == "1"], [p for l, p in rows if l == "0"]  # 1 = real, 0 = fake in Celeb-DF's list
    rnd = random.Random(42)
    test_picks = [(p, "real") for p in rnd.sample(test_real, 24)] + [(p, "fake") for p in rnd.sample(test_fake, 24)]

    on_test_list = {p for _, p in rows}
    celeb = [s[len("celebdf_v2/"):] for s in siblings(CELEB) if s.startswith("celebdf_v2/") and s.endswith(".mp4")]
    train = [p for p in celeb if p not in on_test_list]
    t_real, t_fake = [p for p in train if not p.startswith("Celeb-synthesis")], [p for p in train if p.startswith("Celeb-synthesis")]
    rnd = random.Random(7)
    train_picks = [(p, "real") for p in rnd.sample(t_real, 60)] + [(p, "fake") for p in rnd.sample(t_fake, 60)]

    dfd = [s for s in siblings(DFD) if s.endswith(".mp4")]
    d_real, d_fake = [p for p in dfd if "/real/" in p], [p for p in dfd if "/fake/" in p]
    rnd = random.Random(11)
    dfd_picks = [(p, "real") for p in rnd.sample(d_real, 20)] + [(p, "fake") for p in rnd.sample(d_fake, 20)]

    write_selection(test_dir, test_picks)
    write_selection(train_dir, train_picks)
    write_selection(dfd_dir, dfd_picks)
    print("selection lists written")
    if args.dry_run:
        return
    download(CELEB, "celebdf_v2/", test_dir, test_picks)
    download(CELEB, "celebdf_v2/", train_dir, train_picks)
    download(DFD, "", dfd_dir, dfd_picks)


if __name__ == "__main__":
    main()

"""Turning many per-frame scores into one result for the video.

This is temporal AGGREGATION: the frame classifier scores each frame independently, and this module summarises the
sequence of scores (typical level, share of flagged frames, longest run, how much the score jumps). Nothing here learns
motion or frame-to-frame inconsistency; do not describe it as a temporal model.

A video is never judged from a single frame: at least MIN_FACE_FRAMES frames with a detected face are required."""
from __future__ import annotations

from typing import Any

import numpy as np

MIN_FACE_FRAMES = 8
FRAME_FLAG = 0.5       # a frame counts as "flagged" when its fake probability is at least this
AGGREGATORS = ("mean", "median", "top_quartile_mean", "flagged_share")
TARGET_PRECISION = 0.90  # was 0.80; at 0.80 the undecided band was ~0.01 wide, so almost every video got a call


def aggregate(scores: list[float]) -> dict[str, float]:
    s = np.asarray(scores, dtype=float)
    k = max(1, int(np.ceil(len(s) / 4)))
    return {"mean": float(s.mean()), "median": float(np.median(s)),
            "top_quartile_mean": float(np.sort(s)[-k:].mean()), "flagged_share": float((s >= FRAME_FLAG).mean())}


def summarise(times: list[float], scores: list[float]) -> dict[str, Any]:
    """Descriptive statistics of the score sequence, shown to the user next to the verdict."""
    s = np.asarray(scores, dtype=float)
    flagged = s >= FRAME_FLAG
    longest = run = 0
    for f in flagged:
        run = run + 1 if f else 0
        longest = max(longest, run)
    return {"frames_scored": len(s), "mean": round(float(s.mean()), 4), "median": round(float(np.median(s)), 4),
            "min": round(float(s.min()), 4), "max": round(float(s.max()), 4), "std": round(float(s.std()), 4),
            "flagged_share": round(float(flagged.mean()), 4), "longest_flagged_run": int(longest),
            "jumpiness": round(float(np.abs(np.diff(s)).mean()), 4) if len(s) > 1 else 0.0}


def suspicious_moments(times: list[float], scores: list[float], top: int = 5) -> list[dict[str, float]]:
    """The frames the model scored highest, in time order. Where the model looked most suspicious, not proof."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:top]
    return [{"t": times[i], "p_fake": scores[i]} for i in sorted(order) if scores[i] >= FRAME_FLAG]


def calibrate(y: np.ndarray, s: np.ndarray) -> dict[str, Any]:
    """Two thresholds on the video score, chosen on the calibration videos: videos scoring at or above `fake_min` are called
    fake, at or below `real_max` real, the rest are left undecided. Of all pairs where each side is at least
    TARGET_PRECISION correct (and rests on enough videos) and the two do not overlap, the pair deciding the most videos
    is used (the widest undecided band among equals). A side that cannot reach the target is dropped (None): the application then makes no call on that side."""
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    n = len(s)
    support = max(5, int(np.ceil(0.1 * n)))
    values = np.unique(s)
    fake_opts: list[float | None] = [None] + [float(t) for t in values if (s >= t).sum() >= support and y[s >= t].mean() >= TARGET_PRECISION]
    real_opts: list[float | None] = [None] + [float(t) for t in values if (s <= t).sum() >= support and (1 - y[s <= t].mean()) >= TARGET_PRECISION]
    best: tuple[int, float, float | None, float | None] = (-1, 0.0, None, None)
    for f in fake_opts:
        for r in real_opts:
            if f is not None and r is not None and r >= f:
                continue
            decided = (int((s >= f).sum()) if f is not None else 0) + (int((s <= r).sum()) if r is not None else 0)
            gap = (f - r) if f is not None and r is not None else 0.0  # equal coverage: prefer the wider undecided band
            if (decided, gap) > (best[0], best[1]):
                best = (decided, gap, f, r)
    _, _, f, r = best
    return {"fake_min": None if f is None else round(f, 4), "real_max": None if r is None else round(r, 4),
            "target_precision": TARGET_PRECISION, "chosen_on_videos": int(n)}


def decide(score: float, cal: dict[str, Any]) -> str:
    if cal.get("fake_min") is not None and score >= cal["fake_min"]:
        return "fake"
    if cal.get("real_max") is not None and score <= cal["real_max"]:
        return "real"
    return "undecided"


def report_on(y: np.ndarray, s: np.ndarray, cal: dict[str, Any]) -> dict[str, Any]:
    calls = [decide(float(v), cal) for v in s]
    decided = [(c, int(t)) for c, t in zip(calls, y) if c != "undecided"]
    correct = sum((c == "fake") == bool(t) for c, t in decided)
    fake_calls = [(c, t) for c, t in decided if c == "fake"]
    real_calls = [(c, t) for c, t in decided if c == "real"]
    return {"n": int(len(y)), "decided": len(decided), "decided_share": round(len(decided) / max(1, len(y)), 4),
            "accuracy_on_decided": round(correct / len(decided), 4) if decided else None,
            "fake_calls": len(fake_calls), "fake_calls_correct": sum(t == 1 for _, t in fake_calls),
            "real_calls": len(real_calls), "real_calls_correct": sum(t == 0 for _, t in real_calls)}

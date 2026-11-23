"""How the separate results are combined into one verdict. A fixed rule, written out here and shown in every result,
not a learned model: there is no labelled multimodal news data in this project to learn one from.

    base verdict  = the text model's verdict when the text was long enough to be judged;
                    "Indicators Only" when only an image was given; otherwise "Unverified".
    final verdict = "Mismatch Flagged" when the consistency check says the image and text clearly do not match and the
                    base verdict is not already "Likely Fake"; otherwise the base verdict.

The image forensics never changes the verdict: error-level analysis gives indicators, not a decision. A mismatch is
flagged rather than reported as fake, because a mismatched photo is not proof that the text is false."""
from __future__ import annotations

from typing import Any

RULE = ('Base verdict = the text model\'s verdict (or "Indicators Only" for an image alone, otherwise "Unverified"). '
        'If image and text clearly do not match and the base verdict is not "Likely Fake", the verdict is "Mismatch Flagged". '
        "Image forensics never changes the verdict.")


def fuse(text_verdict: str | None, image_present: bool, consistency_label: str | None) -> dict[str, Any]:
    if text_verdict in ("Likely Fake", "Likely Real", "Unverified"):
        base = text_verdict
    elif image_present and text_verdict is None:
        base = "Indicators Only"
    else:
        base = "Unverified"
    flagged = consistency_label == "inconsistent" and base != "Likely Fake"
    notes = []
    if text_verdict is None and image_present:
        notes.append("No text was given, so only image indicators are available.")
    if text_verdict == "Unverified" and consistency_label in (None, "consistent", "unclear", "not_calibrated"):
        notes.append("The text could not be judged by the text model, so the combined verdict stays Unverified.")
    if consistency_label == "inconsistent" and base == "Likely Fake":
        notes.append("The image and text also look mismatched, which is shown but does not change a Likely Fake verdict.")
    return {"verdict": "Mismatch Flagged" if flagged else base, "base_verdict": base, "rule": RULE,
            "inputs": {"text_verdict": text_verdict, "consistency": consistency_label, "image_present": image_present}, "notes": notes}

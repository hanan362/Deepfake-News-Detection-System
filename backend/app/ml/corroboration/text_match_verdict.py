"""What the text-against-headline result does to a verdict.

The comparison itself (consistency.py) has five results. Measured on real articles (docs/technical_documentation/ai_model_documentation.md,
section 6b) they are not equally reliable:
  Unrelated          the text is about another story. Real articles were wrongly given this result in 1 of 242 cases, and a text taken
                     from another story was given it in 93% to 97% of cases. It stops a "Likely Real".
  Contradicts and    the text is about the same subject, but the model reads it as saying the opposite, or a number or name of the
  Different details  headline is not in it. These also appeared on about one real article in seven (an updated story under its first
                     headline, a rounded figure, a typing slip, a model misreading). They are shown as a warning and do not change
                     the verdict, unless the server is set to be strict (TEXT_MATCH_STRICT=true), when they stop a "Likely Real" too.
Nothing here ever produces "Likely Fake".
"""
from __future__ import annotations

from typing import Any

from app.ml.corroboration import consistency

WITHHOLDS = frozenset({"unrelated"})
WARNING = ("Shown as a warning, not as a verdict, so the result above is unchanged: in tests a difference like this also appeared in "
           "about one real article in seven, for example when a story was updated under its first headline or a figure was rounded.")


def apply(result: dict[str, Any], match: dict[str, Any], *, strict: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """The result after the text was compared with its headline, and the comparison with the note on what it did (or did not) change."""
    status = match.get("status")
    if strict or status in WITHHOLDS:
        return consistency.combine_text_match(result, match), match
    if status in consistency.MISMATCH:
        return result, {**match, "effect_note": WARNING}
    return result, match

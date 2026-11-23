"""Shared rule for models that are downloaded on first use.

A download can fail for a passing reason (the connection dropped, Hugging Face was slow). Remembering that failure for the
life of the server would leave the check "unavailable" until someone restarted it, so a failed load is tried again once
RETRY_AFTER_SECONDS have passed. Until then the stored reason is shown, so a request is never held up by repeated attempts."""
from __future__ import annotations

import time

RETRY_AFTER_SECONDS = 30.0


def may_retry(failed_at: float | None) -> bool:
    return failed_at is not None and time.monotonic() - failed_at >= RETRY_AFTER_SECONDS

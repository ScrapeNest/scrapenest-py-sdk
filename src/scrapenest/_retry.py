"""Pure retry-policy helpers shared by the sync and async transports."""

from __future__ import annotations

import random
from typing import Any

# Status codes that are safe to retry. POST /jobs is made safe by an
# auto-attached idempotency_token, so 429/5xx replays do not double-submit.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

_MAX_BACKOFF_SECONDS = 30.0


def is_retryable_status(status_code: int) -> bool:
    return status_code in RETRY_STATUSES


def parse_retry_after(value: Any) -> float | None:
    """Parse a Retry-After header value expressed in seconds."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds >= 0 else None


def compute_delay(
    *,
    attempt: int,
    backoff_factor: float,
    retry_after: float | None = None,
) -> float:
    """Delay before the next attempt (0-indexed).

    Honors a server `Retry-After` when present; otherwise uses exponential
    backoff with full jitter, capped at 30s.
    """
    if retry_after is not None:
        return min(retry_after, _MAX_BACKOFF_SECONDS)
    base = backoff_factor * (2**attempt)
    jittered = random.uniform(0, base)
    return min(jittered, _MAX_BACKOFF_SECONDS)

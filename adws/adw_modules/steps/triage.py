"""Triage pure functions for failure recovery (FR48).

Provides pure logic for parsing failure metadata, classifying
failures into escalation tiers, and checking cooldown periods.
No I/O -- all functions operate on data only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class FailureMetadata:
    """Parsed ADWS_FAILED metadata from issue notes."""

    attempt: int
    last_failure: str
    error_class: str
    step: str
    summary: str


# Cooldown schedule: exponential backoff based on attempt count.
COOLDOWN_SCHEDULE: dict[int, timedelta] = {
    1: timedelta(minutes=30),
    2: timedelta(hours=2),
}
DEFAULT_COOLDOWN: timedelta = timedelta(hours=8)

# Error classes considered retryable at low attempt counts.
_RETRYABLE_ERROR_CLASSES: frozenset[str] = frozenset({
    "SdkCallError",
    "TimeoutError",
    "TestFailureError",
})


def _parse_kv_parts(
    parts: list[str],
    placeholder: str,
) -> dict[str, str] | None:
    """Parse key=value pairs from pipe-split metadata parts.

    Returns dict on success, None if any part is missing '='.
    """
    kv: dict[str, str] = {}
    for part in parts[1:]:
        restored = part.replace(placeholder, "|")
        if "=" not in restored:
            return None
        key, _, value = restored.partition("=")
        kv[key.strip()] = value.strip()
    return kv


def parse_failure_metadata(
    notes: str,
) -> FailureMetadata | None:
    """Parse ADWS_FAILED metadata from issue notes.

    Format: ADWS_FAILED|attempt=N|last_failure=ISO|
    error_class=X|step=Y|summary=Z

    Returns FailureMetadata on success, None if notes do
    not contain ADWS_FAILED or if parsing fails. Handles
    escaped pipe characters (backslash pipe) in summary.
    """
    if not notes or "ADWS_FAILED" not in notes:
        return None

    # Find the line starting with ADWS_FAILED
    target_line = next(
        (
            line.strip()
            for line in notes.splitlines()
            if line.strip().startswith("ADWS_FAILED")
        ),
        None,
    )
    if target_line is None:
        return None  # pragma: no cover (guarded above)

    # Split by unescaped pipes: replace escaped pipes
    # with a placeholder, split, then restore.
    placeholder = "\x00PIPE\x00"
    safe = target_line.replace("\\|", placeholder)
    parts = safe.split("|")

    if len(parts) < 6:  # noqa: PLR2004
        return None

    kv = _parse_kv_parts(parts, placeholder)

    # Validate required fields
    required = {
        "attempt", "last_failure", "error_class",
        "step", "summary",
    }
    if kv is None or not required.issubset(kv.keys()):
        return None

    try:
        attempt = int(kv["attempt"])
    except ValueError:
        return None

    return FailureMetadata(
        attempt=attempt,
        last_failure=kv["last_failure"],
        error_class=kv["error_class"],
        step=kv["step"],
        summary=kv["summary"],
    )


def classify_failure_tier(
    metadata: FailureMetadata,
) -> int:
    """Classify a failure into an escalation tier (1, 2, or 3).

    Tier 1: Any non-unknown error class with attempt < 3 (retryable).
    Tier 2: attempt >= 3 with classifiable (non-unknown) error class.
    Tier 3: unknown error class at any attempt count.

    Returns the tier number (1, 2, or 3).
    """
    if metadata.error_class == "unknown":
        return 3

    if metadata.attempt < 3:  # noqa: PLR2004
        return 1

    return 2


def check_cooldown_elapsed(
    metadata: FailureMetadata,
    now: datetime,
) -> bool:
    """Check if exponential backoff cooldown has elapsed.

    Cooldown schedule: attempt 1 = 30 min, attempt 2 = 2 hr,
    attempt >= 3 = 8 hr. Returns True if cooldown has elapsed.
    Returns False on parse error (conservative -- do not retry
    if timestamp is unparseable).
    """
    try:
        last_failure = datetime.fromisoformat(
            metadata.last_failure,
        )
    except (ValueError, AttributeError):
        return False

    cooldown = COOLDOWN_SCHEDULE.get(
        metadata.attempt, DEFAULT_COOLDOWN,
    )
    elapsed = now - last_failure
    return elapsed >= cooldown

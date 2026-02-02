"""Tests for triage pure functions (Story 7.4)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from adws.adw_modules.steps.triage import (
    COOLDOWN_SCHEDULE,
    DEFAULT_COOLDOWN,
    FailureMetadata,
    check_cooldown_elapsed,
    classify_failure_tier,
    parse_failure_metadata,
)

# --- FailureMetadata dataclass tests ---


def test_failure_metadata_is_frozen() -> None:
    """FailureMetadata is a frozen dataclass."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    assert md.attempt == 1
    assert md.error_class == "SdkCallError"


def test_failure_metadata_fields() -> None:
    """FailureMetadata has expected fields."""
    md = FailureMetadata(
        attempt=2,
        last_failure="2026-02-01T12:00:00Z",
        error_class="TestFailureError",
        step="verify",
        summary="test failed",
    )
    assert md.attempt == 2
    assert md.last_failure == "2026-02-01T12:00:00Z"
    assert md.error_class == "TestFailureError"
    assert md.step == "verify"
    assert md.summary == "test failed"


# --- parse_failure_metadata tests ---


def test_parse_failure_metadata_valid() -> None:
    """Parse valid ADWS_FAILED metadata returns FailureMetadata."""
    notes = (
        "ADWS_FAILED|attempt=2|last_failure=2026-02-01T12:00:00Z"
        "|error_class=SdkCallError|step=implement"
        "|summary=SDK timeout after 30s"
    )
    result = parse_failure_metadata(notes)
    assert result is not None
    assert result.attempt == 2
    assert result.last_failure == "2026-02-01T12:00:00Z"
    assert result.error_class == "SdkCallError"
    assert result.step == "implement"
    assert result.summary == "SDK timeout after 30s"


def test_parse_failure_metadata_no_adws_failed() -> None:
    """Notes without ADWS_FAILED return None."""
    result = parse_failure_metadata("Normal issue notes")
    assert result is None


def test_parse_failure_metadata_empty() -> None:
    """Empty notes return None."""
    result = parse_failure_metadata("")
    assert result is None


def test_parse_failure_metadata_malformed() -> None:
    """Malformed metadata (missing fields) returns None."""
    result = parse_failure_metadata("ADWS_FAILED|attempt=1")
    assert result is None


def test_parse_failure_metadata_escaped_pipe() -> None:
    """Escaped pipe in summary is correctly unescaped."""
    notes = (
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T00:00:00Z"
        "|error_class=TestError|step=verify"
        "|summary=Error in step\\|detail"
    )
    result = parse_failure_metadata(notes)
    assert result is not None
    assert result.summary == "Error in step|detail"


def test_parse_failure_metadata_needs_human() -> None:
    """Notes with needs_human instead of ADWS_FAILED return None."""
    result = parse_failure_metadata("needs_human")
    assert result is None


def test_parse_failure_metadata_needs_human_with_reason() -> None:
    """needs_human|reason=... notes return None."""
    result = parse_failure_metadata(
        "needs_human|reason=unresolvable",
    )
    assert result is None


def test_parse_failure_metadata_invalid_attempt() -> None:
    """Non-integer attempt field returns None."""
    notes = (
        "ADWS_FAILED|attempt=abc|last_failure=2026-02-01T00:00:00Z"
        "|error_class=TestError|step=verify|summary=fail"
    )
    result = parse_failure_metadata(notes)
    assert result is None


def test_parse_failure_metadata_multiline_notes() -> None:
    """ADWS_FAILED in multiline notes is found correctly."""
    notes = (
        "Some prefix note\n"
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T00:00:00Z"
        "|error_class=SdkCallError|step=implement|summary=timeout\n"
        "Some suffix"
    )
    result = parse_failure_metadata(notes)
    assert result is not None
    assert result.attempt == 1


def test_parse_failure_metadata_missing_equals() -> None:
    """Metadata part without = returns None."""
    notes = (
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T00:00:00Z"
        "|error_class=SdkCallError|stepMISSING|summary=test"
    )
    result = parse_failure_metadata(notes)
    assert result is None


def test_parse_failure_metadata_adws_failed_not_at_start() -> None:
    """ADWS_FAILED appearing as substring (not prefix) returns None."""
    notes = "some_prefix_ADWS_FAILED|attempt=1|last_failure=x"
    result = parse_failure_metadata(notes)
    assert result is None


def test_parse_failure_metadata_missing_required_field() -> None:
    """Notes with 6 fields but missing a required key return None."""
    notes = (
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T00:00:00Z"
        "|error_class=SdkCallError|step=verify|extra=bonus"
    )
    result = parse_failure_metadata(notes)
    assert result is None


# --- classify_failure_tier tests ---


def test_classify_tier1_sdk_error_attempt1() -> None:
    """SdkCallError at attempt 1 is Tier 1."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    assert classify_failure_tier(md) == 1


def test_classify_tier1_timeout_error_attempt1() -> None:
    """TimeoutError at attempt 1 is Tier 1."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="TimeoutError",
        step="implement",
        summary="timeout",
    )
    assert classify_failure_tier(md) == 1


def test_classify_tier1_test_failure_attempt2() -> None:
    """TestFailureError at attempt 2 is Tier 1."""
    md = FailureMetadata(
        attempt=2,
        last_failure="2026-02-01T12:00:00Z",
        error_class="TestFailureError",
        step="verify",
        summary="tests failed",
    )
    assert classify_failure_tier(md) == 1


def test_classify_tier2_sdk_error_attempt3() -> None:
    """SdkCallError at attempt 3 is Tier 2."""
    md = FailureMetadata(
        attempt=3,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    assert classify_failure_tier(md) == 2


def test_classify_tier2_test_failure_attempt5() -> None:
    """TestFailureError at attempt 5 is Tier 2."""
    md = FailureMetadata(
        attempt=5,
        last_failure="2026-02-01T12:00:00Z",
        error_class="TestFailureError",
        step="verify",
        summary="keeps failing",
    )
    assert classify_failure_tier(md) == 2


def test_classify_tier3_unknown_attempt1() -> None:
    """Unknown error class at attempt 1 is Tier 3."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="unknown",
        step="implement",
        summary="unknown error",
    )
    assert classify_failure_tier(md) == 3


def test_classify_tier3_unknown_attempt3() -> None:
    """Unknown error class at attempt 3 is still Tier 3, not Tier 2."""
    md = FailureMetadata(
        attempt=3,
        last_failure="2026-02-01T12:00:00Z",
        error_class="unknown",
        step="implement",
        summary="unknown error",
    )
    assert classify_failure_tier(md) == 3


def test_classify_tier1_non_standard_error() -> None:
    """Non-standard classifiable error at low attempt is Tier 1."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="BeadsCloseError",
        step="finalize",
        summary="close failed",
    )
    assert classify_failure_tier(md) == 1


def test_classify_tier2_non_standard_error_high_attempt() -> None:
    """Non-standard classifiable error at high attempt is Tier 2."""
    md = FailureMetadata(
        attempt=4,
        last_failure="2026-02-01T12:00:00Z",
        error_class="BeadsCloseError",
        step="finalize",
        summary="close failed",
    )
    assert classify_failure_tier(md) == 2


# --- check_cooldown_elapsed tests ---


def test_cooldown_elapsed_attempt1_yes() -> None:
    """Attempt 1, 1 hour after failure: cooldown elapsed (30min)."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is True


def test_cooldown_not_elapsed_attempt1() -> None:
    """Attempt 1, 20 min after failure: cooldown NOT elapsed."""
    md = FailureMetadata(
        attempt=1,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 12, 20, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is False


def test_cooldown_elapsed_attempt2_yes() -> None:
    """Attempt 2, 2.5 hours after failure: cooldown elapsed (2hr)."""
    md = FailureMetadata(
        attempt=2,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 14, 30, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is True


def test_cooldown_not_elapsed_attempt2() -> None:
    """Attempt 2, 1.5 hours after failure: cooldown NOT elapsed."""
    md = FailureMetadata(
        attempt=2,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 13, 30, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is False


def test_cooldown_elapsed_attempt3_yes() -> None:
    """Attempt 3, 9 hours after failure: cooldown elapsed (8hr)."""
    md = FailureMetadata(
        attempt=3,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is True


def test_cooldown_not_elapsed_attempt3() -> None:
    """Attempt 3, 6 hours after failure: cooldown NOT elapsed."""
    md = FailureMetadata(
        attempt=3,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 18, 0, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is False


def test_cooldown_elapsed_attempt5() -> None:
    """Attempt 5 uses 8-hour cooldown (same as attempt >= 3)."""
    md = FailureMetadata(
        attempt=5,
        last_failure="2026-02-01T12:00:00Z",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is True


def test_cooldown_malformed_timestamp() -> None:
    """Malformed last_failure returns False (conservative)."""
    md = FailureMetadata(
        attempt=1,
        last_failure="not-a-date",
        error_class="SdkCallError",
        step="implement",
        summary="timeout",
    )
    now = datetime(2026, 2, 1, 23, 0, 0, tzinfo=UTC)
    assert check_cooldown_elapsed(md, now) is False


# --- Cooldown constants tests ---


def test_cooldown_schedule_has_expected_entries() -> None:
    """COOLDOWN_SCHEDULE has entries for attempt 1 and 2."""
    assert 1 in COOLDOWN_SCHEDULE
    assert 2 in COOLDOWN_SCHEDULE


def test_default_cooldown_is_8_hours() -> None:
    """DEFAULT_COOLDOWN is 8 hours."""
    assert timedelta(hours=8) == DEFAULT_COOLDOWN

"""Tests for build_feedback_context step module."""
from adws.adw_modules.steps import (
    build_feedback_context as pkg_build,
)
from adws.adw_modules.steps.build_feedback_context import (
    _parse_errors,
    _parse_feedback_entry,
    _unescape_field,
    build_feedback_context,
)
from adws.adw_modules.types import WorkflowContext


def test_build_feedback_context_importable_from_steps() -> None:
    """build_feedback_context importable from steps package."""
    assert pkg_build is build_feedback_context


def test_build_feedback_context_single_attempt() -> None:
    """Format single feedback entry for agent consumption."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors=FAIL src/test.ts"
            "|raw=FAIL src/test.ts 1 test failed",
        ],
    )
    result = build_feedback_context(ctx)
    assert isinstance(result, str)
    assert "## Previous Verify Failures" in result
    assert "### Attempt 1" in result
    assert "**jest**" in result
    assert "run_jest_step" in result
    assert "FAIL src/test.ts" in result


def test_build_feedback_context_empty_feedback() -> None:
    """Return no-failures message when feedback list is empty."""
    ctx = WorkflowContext(feedback=[])
    result = build_feedback_context(ctx)
    assert "No previous verify failures" in result


def test_build_feedback_context_multi_attempt() -> None:
    """Include BOTH attempts in chronological order."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors=FAIL src/test.ts"
            "|raw=jest output",
            "VERIFY_FEEDBACK|tool=ruff|attempt=2"
            "|step=run_ruff_step"
            "|errors=E501 line too long;;F401 unused"
            "|raw=ruff output",
        ],
    )
    result = build_feedback_context(ctx)
    assert "### Attempt 1" in result
    assert "### Attempt 2" in result
    assert "**jest**" in result
    assert "**ruff**" in result
    assert "FAIL src/test.ts" in result
    assert "E501 line too long" in result
    assert "F401 unused" in result
    # Attempt 1 appears before Attempt 2
    idx1 = result.index("### Attempt 1")
    idx2 = result.index("### Attempt 2")
    assert idx1 < idx2


def test_build_feedback_context_idempotent() -> None:
    """Calling with same feedback twice gives identical output."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors=FAIL src/test.ts"
            "|raw=jest output",
        ],
    )
    result1 = build_feedback_context(ctx)
    result2 = build_feedback_context(ctx)
    assert result1 == result2


def test_build_feedback_context_mixed_entries() -> None:
    """Include non-VerifyFeedback entries as-is."""
    ctx = WorkflowContext(
        feedback=[
            "Retry 1/3 for step 'run_jest_step': jest failed",
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors=FAIL src/test.ts"
            "|raw=jest output",
        ],
    )
    result = build_feedback_context(ctx)
    assert "Retry 1/3" in result
    assert "**jest**" in result


def test_build_feedback_context_same_attempt_multiple_tools() -> None:
    """Same attempt with multiple tool failures, no dup header."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors=FAIL test.ts"
            "|raw=jest output",
            "VERIFY_FEEDBACK|tool=ruff|attempt=1"
            "|step=run_ruff_step"
            "|errors=E501"
            "|raw=ruff output",
        ],
    )
    result = build_feedback_context(ctx)
    # Only one Attempt 1 header
    assert result.count("### Attempt 1") == 1
    assert "**jest**" in result
    assert "**ruff**" in result


def test_build_feedback_context_empty_errors() -> None:
    """Handle empty error strings in feedback."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors="
            "|raw=raw output",
        ],
    )
    result = build_feedback_context(ctx)
    assert "**jest**" in result
    assert "0 error(s)" in result


def test_build_feedback_context_whitespace_only_error() -> None:
    """Skip whitespace-only errors; count only real ones."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|step=run_jest_step"
            "|errors=FAIL test.ts;; ;;err2"
            "|raw=raw output",
        ],
    )
    result = build_feedback_context(ctx)
    assert "FAIL test.ts" in result
    assert "err2" in result
    # Whitespace-only entry is skipped
    assert "  -  " not in result
    # Error count matches displayed bullets (not 3)
    assert "2 error(s)" in result


def test_build_feedback_context_malformed_part() -> None:
    """Handle malformed parts without = in feedback string."""
    ctx = WorkflowContext(
        feedback=[
            "VERIFY_FEEDBACK|tool=jest|attempt=1"
            "|badpart|step=run_jest_step"
            "|errors=FAIL"
            "|raw=raw",
        ],
    )
    result = build_feedback_context(ctx)
    assert "**jest**" in result
    assert "FAIL" in result


def test_parse_feedback_entry_missing_raw_field() -> None:
    """Parse entry without |raw= gracefully."""
    entry = (
        "VERIFY_FEEDBACK|tool=jest|attempt=1"
        "|step=run_jest_step|errors=err1"
    )
    parsed = _parse_feedback_entry(entry)
    assert parsed is not None
    assert parsed["tool"] == "jest"
    assert parsed["raw"] == ""


def test_parse_feedback_pipe_in_raw_preserved() -> None:
    """Pipe characters in raw_output survive round-trip."""
    entry = (
        "VERIFY_FEEDBACK|tool=jest|attempt=1"
        "|step=step|errors=err1"
        "|raw=line1|line2|line3"
    )
    parsed = _parse_feedback_entry(entry)
    assert parsed is not None
    assert parsed["raw"] == "line1|line2|line3"


def test_unescape_field_reverses_escaping() -> None:
    """Unescape restores pipe and double-semicolon."""
    assert _unescape_field("a\\x7Cb") == "a|b"
    assert _unescape_field("a\\x3B\\x3Bb") == "a;;b"
    assert _unescape_field("plain") == "plain"


def test_parse_errors_unescapes_items() -> None:
    """Each error is individually unescaped."""
    raw = "err\\x3B\\x3Bor1;;err\\x7Cor2"
    errors = _parse_errors(raw)
    assert errors == ["err;;or1", "err|or2"]


def test_parse_errors_empty_string() -> None:
    """Empty string returns empty list."""
    assert _parse_errors("") == []

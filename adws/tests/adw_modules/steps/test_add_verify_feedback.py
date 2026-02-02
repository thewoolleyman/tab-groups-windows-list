"""Tests for add_verify_feedback_to_context step module."""
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    add_verify_feedback_to_context as pkg_add,
)
from adws.adw_modules.steps.add_verify_feedback import (
    _escape_field,
    add_verify_feedback_to_context,
)
from adws.adw_modules.steps.build_feedback_context import (
    _parse_feedback_entry,
)
from adws.adw_modules.types import WorkflowContext


def test_add_verify_feedback_importable_from_steps() -> None:
    """add_verify_feedback_to_context from steps package."""
    assert pkg_add is add_verify_feedback_to_context


def test_add_verify_feedback_to_empty_context() -> None:
    """Append VerifyFeedback to empty feedback list."""
    ctx = WorkflowContext()
    error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 1 error(s)",
        context={
            "tool_name": "jest",
            "errors": ["FAIL src/test.ts"],
            "raw_output": "FAIL output",
        },
    )
    updated = add_verify_feedback_to_context(
        ctx, error, attempt=1,
    )
    assert isinstance(updated, WorkflowContext)
    assert updated is not ctx
    assert len(updated.feedback) == 1
    entry = updated.feedback[0]
    assert entry.startswith("VERIFY_FEEDBACK|")
    assert "tool=jest" in entry
    assert "attempt=1" in entry
    assert "step=run_jest_step" in entry
    assert "FAIL src/test.ts" in entry


def test_add_verify_feedback_appends_to_existing() -> None:
    """New feedback appended, preserving existing entries."""
    ctx = WorkflowContext(
        feedback=["existing feedback entry"],
    )
    error = PipelineError(
        step_name="run_ruff_step",
        error_type="VerifyFailed",
        message="ruff check failed: 2 error(s)",
        context={
            "tool_name": "ruff",
            "errors": ["E501 line too long"],
            "raw_output": "ruff output",
        },
    )
    updated = add_verify_feedback_to_context(
        ctx, error, attempt=1,
    )
    assert len(updated.feedback) == 2
    assert updated.feedback[0] == "existing feedback entry"
    assert updated.feedback[1].startswith(
        "VERIFY_FEEDBACK|",
    )
    assert "tool=ruff" in updated.feedback[1]


def test_add_verify_feedback_sequential_calls() -> None:
    """Multi-attempt: all entries preserved in order."""
    ctx = WorkflowContext()
    error1 = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed",
        context={
            "tool_name": "jest",
            "errors": ["FAIL src/test.ts"],
            "raw_output": "jest output",
        },
    )
    error2 = PipelineError(
        step_name="run_ruff_step",
        error_type="VerifyFailed",
        message="ruff check failed",
        context={
            "tool_name": "ruff",
            "errors": ["E501 line too long"],
            "raw_output": "ruff output",
        },
    )
    ctx1 = add_verify_feedback_to_context(
        ctx, error1, attempt=1,
    )
    ctx2 = add_verify_feedback_to_context(
        ctx1, error2, attempt=2,
    )
    assert len(ctx2.feedback) == 2
    assert "tool=jest" in ctx2.feedback[0]
    assert "attempt=1" in ctx2.feedback[0]
    assert "tool=ruff" in ctx2.feedback[1]
    assert "attempt=2" in ctx2.feedback[1]


def test_escape_field_escapes_pipe_and_semicolons() -> None:
    """Pipe and ;; are escaped to prevent format corruption."""
    assert _escape_field("a|b") == "a\\x7Cb"
    assert _escape_field("a;;b") == "a\\x3B\\x3Bb"
    assert _escape_field("plain") == "plain"


def test_serialize_round_trip_with_pipes_in_raw() -> None:
    """Pipe chars in raw_output survive serialize -> parse."""
    ctx = WorkflowContext()
    error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest failed",
        context={
            "tool_name": "jest",
            "errors": ["FAIL test.ts"],
            "raw_output": "line1|line2|line3",
        },
    )
    updated = add_verify_feedback_to_context(
        ctx, error, attempt=1,
    )
    parsed = _parse_feedback_entry(
        updated.feedback[0],
    )
    assert parsed is not None
    assert parsed["raw"] == "line1|line2|line3"

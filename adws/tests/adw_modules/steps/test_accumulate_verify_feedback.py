"""Tests for accumulate_verify_feedback step module."""
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    accumulate_verify_feedback as pkg_accumulate,
)
from adws.adw_modules.steps.accumulate_verify_feedback import (
    accumulate_verify_feedback,
)
from adws.adw_modules.types import VerifyFeedback


def test_accumulate_verify_feedback_importable_from_steps() -> None:
    """accumulate_verify_feedback importable from steps pkg."""
    assert pkg_accumulate is accumulate_verify_feedback


def test_accumulate_verify_feedback_from_verify_failed_error() -> None:
    """Extract VerifyFeedback from a VerifyFailed PipelineError."""
    error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 1 error(s)",
        context={
            "tool_name": "jest",
            "errors": ["FAIL src/test.ts"],
            "raw_output": "FAIL src/test.ts\n1 test failed",
        },
    )
    feedback = accumulate_verify_feedback(error, attempt=1)
    assert isinstance(feedback, VerifyFeedback)
    assert feedback.tool_name == "jest"
    assert feedback.errors == ["FAIL src/test.ts"]
    assert feedback.raw_output == (
        "FAIL src/test.ts\n1 test failed"
    )
    assert feedback.attempt == 1
    assert feedback.step_name == "run_jest_step"


def test_accumulate_verify_feedback_missing_context_keys() -> None:
    """Fallback to defaults when context keys are missing."""
    error = PipelineError(
        step_name="run_mypy_step",
        error_type="VerifyFailed",
        message="mypy check failed",
        context={},
    )
    feedback = accumulate_verify_feedback(error, attempt=2)
    assert isinstance(feedback, VerifyFeedback)
    assert feedback.tool_name == "unknown"
    assert feedback.errors == []
    assert feedback.raw_output == ""
    assert feedback.attempt == 2
    assert feedback.step_name == "run_mypy_step"


def test_accumulate_verify_feedback_non_verify_error() -> None:
    """Handle non-VerifyFailed error types gracefully."""
    error = PipelineError(
        step_name="execute_shell_step",
        error_type="TimeoutError",
        message="Command timed out after 30s",
        context={
            "tool_name": "shell",
            "raw_output": "timeout reached",
        },
    )
    feedback = accumulate_verify_feedback(error, attempt=3)
    assert isinstance(feedback, VerifyFeedback)
    assert feedback.tool_name == "shell"
    assert feedback.errors == []
    assert feedback.raw_output == "timeout reached"
    assert feedback.attempt == 3
    assert feedback.step_name == "execute_shell_step"

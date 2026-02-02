"""Tests for PipelineError and error types."""
import dataclasses

from adws.adw_modules.errors import PipelineError


def test_pipeline_error_construction() -> None:
    """Test PipelineError stores all fields correctly."""
    error = PipelineError(
        step_name="test_step",
        error_type="TestError",
        message="test message",
        context={"key": "value"},
    )
    assert error.step_name == "test_step"
    assert error.error_type == "TestError"
    assert error.message == "test message"
    assert error.context == {"key": "value"}


def test_pipeline_error_default_context() -> None:
    """Test PipelineError defaults context to empty dict."""
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
    )
    assert error.context == {}


def test_pipeline_error_is_frozen() -> None:
    """Test PipelineError is an immutable frozen dataclass."""
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
    )
    assert dataclasses.is_dataclass(error)
    assert type(error).__dataclass_params__.frozen  # type: ignore[attr-defined]

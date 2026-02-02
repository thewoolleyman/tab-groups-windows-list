"""Tests for PipelineError and error types."""
import dataclasses


def test_pipeline_error_construction() -> None:
    """RED: Will fail with ImportError because PipelineError is not yet defined in errors.py."""
    from adws.adw_modules.errors import PipelineError

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
    """RED: Will fail with ImportError because PipelineError is not yet defined in errors.py."""
    from adws.adw_modules.errors import PipelineError

    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
    )
    assert error.context == {}


def test_pipeline_error_is_frozen() -> None:
    """RED: Will fail with ImportError because PipelineError is not yet defined in errors.py."""
    from adws.adw_modules.errors import PipelineError

    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
    )
    assert dataclasses.is_dataclass(error)
    assert getattr(type(error), "__dataclass_params__").frozen

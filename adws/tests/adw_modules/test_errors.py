"""Tests for PipelineError and error types."""
import dataclasses
import json

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


def test_pipeline_error_to_dict_includes_all_fields() -> None:
    """RED: Will fail with AttributeError because to_dict does not exist yet."""
    error = PipelineError(
        step_name="test_step",
        error_type="TestError",
        message="something failed",
        context={"path": "/some/path"},
    )
    result = error.to_dict()
    assert result == {
        "step_name": "test_step",
        "error_type": "TestError",
        "message": "something failed",
        "context": {"path": "/some/path"},
    }


def test_pipeline_error_to_dict_empty_context() -> None:
    """RED: Will fail with AttributeError because to_dict does not exist yet."""
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
    )
    result = error.to_dict()
    assert result == {
        "step_name": "step",
        "error_type": "Error",
        "message": "msg",
        "context": {},
    }


def test_pipeline_error_to_dict_is_json_serializable() -> None:
    """RED: Will fail with AttributeError because to_dict does not exist yet."""
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
        context={"count": 42, "items": [1, 2, 3]},
    )
    result = error.to_dict()
    serialized = json.dumps(result)
    assert isinstance(serialized, str)
    assert json.loads(serialized) == result


def test_pipeline_error_str_contains_step_and_message() -> None:
    """RED: Will fail because __str__ is not yet customized."""
    error = PipelineError(
        step_name="execute_sdk_call",
        error_type="SdkError",
        message="Connection refused",
    )
    result = str(error)
    assert "execute_sdk_call" in result
    assert "SdkError" in result
    assert "Connection refused" in result
    # Must NOT be the default dataclass repr format
    assert result.startswith("PipelineError[")


def test_pipeline_error_str_with_context() -> None:
    """RED: Will fail because __str__ is not yet customized."""
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
        context={"key": "val"},
    )
    result = str(error)
    assert result.startswith("PipelineError[")
    assert "key" in result

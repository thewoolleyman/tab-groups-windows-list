"""Tests for track_file_operation and track_file_operation_safe steps."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.track_file_operation import (
    track_file_operation,
    track_file_operation_safe,
)
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- track_file_operation tests ---


def test_track_file_operation_success(
    mocker: MockerFixture,
) -> None:
    """track_file_operation constructs FileTrackEntry and writes bundle."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "session-abc123",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["file_tracked"] is True
    mock_write.assert_called_once()
    call_args = mock_write.call_args
    assert call_args[0][0] == "session-abc123"
    # Verify the JSONL contains expected fields
    jsonl = call_args[0][1]
    assert '"/some/file.py"' in jsonl
    assert '"read"' in jsonl
    assert '"session-abc123"' in jsonl
    assert '"file_tracker"' in jsonl


def test_track_file_operation_missing_file_path() -> None:
    """track_file_operation returns IOFailure when file_path missing."""
    ctx = WorkflowContext(
        inputs={
            "operation": "read",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingInputError"
    assert error.step_name == "track_file_operation"
    assert "file_path" in error.message


def test_track_file_operation_missing_operation() -> None:
    """track_file_operation returns IOFailure when operation missing."""
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingInputError"
    assert error.step_name == "track_file_operation"
    assert "operation" in error.message


def test_track_file_operation_invalid_operation() -> None:
    """track_file_operation returns IOFailure when operation invalid."""
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "delete",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "InvalidInputError"
    assert error.step_name == "track_file_operation"
    assert "read" in error.message
    assert "write" in error.message


def test_track_file_operation_missing_session_id(
    mocker: MockerFixture,
) -> None:
    """track_file_operation generates fallback session_id when missing."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOSuccess)
    call_args = mock_write.call_args
    session_id = call_args[0][0]
    assert session_id.startswith("unknown-")


def test_track_file_operation_missing_hook_name(
    mocker: MockerFixture,
) -> None:
    """track_file_operation defaults to 'file_tracker' when hook_name missing."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "write",
            "session_id": "sess-1",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOSuccess)
    jsonl = mock_write.call_args[0][1]
    assert '"file_tracker"' in jsonl


def test_track_file_operation_io_failure(
    mocker: MockerFixture,
) -> None:
    """track_file_operation returns IOFailure when io_ops fails."""
    io_error = PipelineError(
        step_name="io_ops.write_context_bundle",
        error_type="ContextBundleWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOFailure(io_error),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "track_file_operation"


def test_track_file_operation_write_operation(
    mocker: MockerFixture,
) -> None:
    """track_file_operation works with write operation."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/other/file.py",
            "operation": "write",
            "session_id": "sess-2",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation(ctx)
    assert isinstance(result, IOSuccess)
    jsonl = mock_write.call_args[0][1]
    assert '"write"' in jsonl
    assert '"/other/file.py"' in jsonl


# --- track_file_operation_safe tests ---


def test_track_file_operation_safe_success_passthrough(
    mocker: MockerFixture,
) -> None:
    """track_file_operation_safe passes through IOSuccess."""
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["file_tracked"] is True


def test_track_file_operation_safe_catches_failure(
    mocker: MockerFixture,
) -> None:
    """track_file_operation_safe catches IOFailure, returns IOSuccess."""
    io_error = PipelineError(
        step_name="io_ops.write_context_bundle",
        error_type="ContextBundleWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOFailure(io_error),
    )
    mock_stderr = mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_stderr",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["file_tracked"] is False
    assert "file_track_error" in out_ctx.outputs
    mock_stderr.assert_called_once()


def test_track_file_operation_safe_double_failure(
    mocker: MockerFixture,
) -> None:
    """track_file_operation_safe returns IOSuccess even on double failure."""
    io_error = PipelineError(
        step_name="io_ops.write_context_bundle",
        error_type="ContextBundleWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOFailure(io_error),
    )
    stderr_error = PipelineError(
        step_name="io_ops.write_stderr",
        error_type="StderrWriteError",
        message="broken pipe",
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_stderr",
        return_value=IOFailure(stderr_error),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["file_tracked"] is False


def test_track_file_operation_safe_catastrophic_failure(
    mocker: MockerFixture,
) -> None:
    """track_file_operation_safe returns IOSuccess on catastrophic failure.

    When unsafe_perform_io raises during error extraction,
    the try/except catches it and returns IOSuccess with
    a fallback error message (true fail-open defense).
    """
    io_error = PipelineError(
        step_name="io_ops.write_context_bundle",
        error_type="ContextBundleWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation.io_ops"
        ".write_context_bundle",
        return_value=IOFailure(io_error),
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".unsafe_perform_io",
        side_effect=RuntimeError("catastrophic"),
    )
    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-1",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["file_tracked"] is False
    assert "unknown error" in str(
        out_ctx.outputs["file_track_error"],
    )

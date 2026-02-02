"""Tests for log_hook_event and log_hook_event_safe steps."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.log_hook_event import (
    log_hook_event,
    log_hook_event_safe,
)
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- log_hook_event tests ---


def test_log_hook_event_success(
    mocker: MockerFixture,
) -> None:
    """log_hook_event constructs HookEvent and writes log."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "tool_logger",
            "session_id": "session-abc123",
            "payload": {
                "tool_name": "Bash",
                "command": "ls",
            },
        },
    )
    result = log_hook_event(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["hook_event_logged"] is True
    mock_write.assert_called_once()
    call_args = mock_write.call_args
    assert call_args[0][0] == "session-abc123"
    # Verify the JSONL contains expected fields
    jsonl = call_args[0][1]
    assert '"PreToolUse"' in jsonl
    assert '"tool_logger"' in jsonl
    assert '"session-abc123"' in jsonl


def test_log_hook_event_missing_event_type(
    mocker: MockerFixture,
) -> None:
    """log_hook_event returns IOFailure when event_type missing."""
    ctx = WorkflowContext(
        inputs={
            "hook_name": "tool_logger",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingInputError"
    assert error.step_name == "log_hook_event"
    assert "event_type" in error.message


def test_log_hook_event_missing_hook_name(
    mocker: MockerFixture,
) -> None:
    """log_hook_event returns IOFailure when hook_name missing."""
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingInputError"
    assert error.step_name == "log_hook_event"
    assert "hook_name" in error.message


def test_log_hook_event_missing_session_id(
    mocker: MockerFixture,
) -> None:
    """log_hook_event generates fallback session_id when missing."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
        },
    )
    result = log_hook_event(ctx)
    assert isinstance(result, IOSuccess)
    call_args = mock_write.call_args
    session_id = call_args[0][0]
    assert session_id.startswith("unknown-")


def test_log_hook_event_missing_payload(
    mocker: MockerFixture,
) -> None:
    """log_hook_event defaults to empty dict when payload missing."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "Notification",
            "hook_name": "notifier",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event(ctx)
    assert isinstance(result, IOSuccess)
    jsonl = mock_write.call_args[0][1]
    assert '"payload":{}' in jsonl


def test_log_hook_event_io_failure(
    mocker: MockerFixture,
) -> None:
    """log_hook_event returns IOFailure when io_ops fails."""
    io_error = PipelineError(
        step_name="io_ops.write_hook_log",
        error_type="HookLogWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOFailure(io_error),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "log_hook_event"


# --- log_hook_event_safe tests ---


def test_log_hook_event_safe_success_passthrough(
    mocker: MockerFixture,
) -> None:
    """log_hook_event_safe passes through IOSuccess."""
    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["hook_event_logged"] is True


def test_log_hook_event_safe_catches_failure(
    mocker: MockerFixture,
) -> None:
    """log_hook_event_safe catches IOFailure, returns IOSuccess."""
    io_error = PipelineError(
        step_name="io_ops.write_hook_log",
        error_type="HookLogWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOFailure(io_error),
    )
    mock_stderr = mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_stderr",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["hook_event_logged"] is False
    assert "hook_event_error" in out_ctx.outputs
    mock_stderr.assert_called_once()


def test_log_hook_event_safe_double_failure(
    mocker: MockerFixture,
) -> None:
    """log_hook_event_safe returns IOSuccess even on double failure."""
    io_error = PipelineError(
        step_name="io_ops.write_hook_log",
        error_type="HookLogWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOFailure(io_error),
    )
    stderr_error = PipelineError(
        step_name="io_ops.write_stderr",
        error_type="StderrWriteError",
        message="broken pipe",
    )
    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_stderr",
        return_value=IOFailure(stderr_error),
    )
    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "sess-1",
        },
    )
    result = log_hook_event_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["hook_event_logged"] is False

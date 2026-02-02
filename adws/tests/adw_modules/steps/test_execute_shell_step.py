"""Tests for execute_shell_step step module."""
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.execute_shell_step import execute_shell_step
from adws.adw_modules.types import ShellResult, WorkflowContext


def test_execute_shell_step_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test shell step places stdout/stderr into context outputs."""
    shell_result = ShellResult(
        return_code=0,
        stdout="all good\n",
        stderr="",
        command="echo hello",
    )
    mocker.patch(
        "adws.adw_modules.steps.execute_shell_step.run_shell_command",
        return_value=IOSuccess(shell_result),
    )
    ctx = WorkflowContext(inputs={"shell_command": "echo hello"})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOSuccess)
    updated_ctx = unsafe_perform_io(result.unwrap())
    assert updated_ctx.outputs["shell_stdout"] == "all good\n"
    assert updated_ctx.outputs["shell_stderr"] == ""
    assert updated_ctx.outputs["shell_return_code"] == 0


def test_execute_shell_step_nonzero_exit(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test nonzero exit produces IOFailure with context."""
    shell_result = ShellResult(
        return_code=1,
        stdout="",
        stderr="tests failed",
        command="npm test",
    )
    mocker.patch(
        "adws.adw_modules.steps.execute_shell_step.run_shell_command",
        return_value=IOSuccess(shell_result),
    )
    ctx = WorkflowContext(inputs={"shell_command": "npm test"})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ShellCommandFailed"
    assert error.context["return_code"] == 1
    assert error.context["stderr"] == "tests failed"


def test_execute_shell_step_missing_command() -> None:
    """Test missing shell_command in inputs produces IOFailure."""
    ctx = WorkflowContext(inputs={"other_key": "value"})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"
    assert "shell_command" in error.message


def test_execute_shell_step_empty_command() -> None:
    """Test empty string command produces IOFailure."""
    ctx = WorkflowContext(inputs={"shell_command": ""})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"


def test_execute_shell_step_io_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test io_ops failure propagates through bind."""
    mocker.patch(
        "adws.adw_modules.steps.execute_shell_step.run_shell_command",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.run_shell_command",
                error_type="TimeoutError",
                message="timed out",
            ),
        ),
    )
    ctx = WorkflowContext(inputs={"shell_command": "slow_cmd"})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "TimeoutError"


def test_execute_shell_step_non_string_command() -> None:
    """Test non-string command produces IOFailure."""
    ctx = WorkflowContext(inputs={"shell_command": 42})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "ValueError"


def test_execute_shell_step_whitespace_only_command() -> None:
    """Test whitespace-only command produces IOFailure."""
    ctx = WorkflowContext(inputs={"shell_command": "   "})
    result = execute_shell_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"

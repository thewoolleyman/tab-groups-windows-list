"""Tests for command dispatch module."""
from __future__ import annotations

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.commands.dispatch import run_command
from adws.adw_modules.commands.verify import VerifyCommandResult
from adws.adw_modules.engine.types import Workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import VerifyResult, WorkflowContext


def test_dispatch_verify_uses_specialized_handler(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('verify') routes to run_verify_command."""
    fake_wf = Workflow(
        name="verify",
        description="test",
        steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={
            "verify_jest": VerifyResult(
                tool_name="jest", passed=True,
            ),
        },
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    ctx = WorkflowContext()
    result = run_command("verify", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    vr = out.outputs.get("verify_result")
    assert isinstance(vr, VerifyCommandResult)
    assert vr.success is True


def test_run_command_build_executes_workflow(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('build') loads implement_close workflow."""
    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={"build_done": True},
    )
    mock_load = mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    ctx = WorkflowContext()
    result = run_command("build", ctx)
    assert isinstance(result, IOSuccess)
    mock_load.assert_called_once_with("implement_close")


def test_run_command_unknown_returns_failure() -> None:
    """run_command with unknown name returns IOFailure."""
    ctx = WorkflowContext()
    result = run_command("nonexistent", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "UnknownCommandError"
    assert "nonexistent" in error.message
    assert "available" in str(error.context).lower()


def test_run_command_workflow_not_found(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command returns IOFailure when workflow not found."""
    err = PipelineError(
        step_name="io_ops.load_command_workflow",
        error_type="WorkflowNotFoundError",
        message="Workflow 'verify' is not registered",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOFailure(err),
    )
    ctx = WorkflowContext()
    result = run_command("verify", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "WorkflowNotFoundError"


def test_run_command_no_workflow_returns_failure() -> None:
    """run_command for non-workflow command returns IOFailure."""
    ctx = WorkflowContext()
    result = run_command("prime", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "NoWorkflowError"
    assert "prime" in error.message


def test_run_command_load_bundle_no_workflow() -> None:
    """run_command for load_bundle (no workflow) returns IOFailure."""
    ctx = WorkflowContext()
    result = run_command("load_bundle", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "NoWorkflowError"


def test_run_command_execute_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command propagates execute failure for non-verify."""
    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement",
        error_type="StepError",
        message="implement failed",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    ctx = WorkflowContext()
    result = run_command("build", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is exec_err


def test_dispatch_verify_tool_failure_wraps_result(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('verify') wraps tool failure as success."""
    fake_wf = Workflow(
        name="verify",
        description="test",
        steps=[],
    )
    tool_err = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 1 error(s)",
        context={
            "tool_name": "jest",
            "errors": ["FAIL test"],
            "raw_output": "output",
        },
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(tool_err),
    )
    ctx = WorkflowContext()
    result = run_command("verify", ctx)
    # Tool failure -> IOSuccess with verify_result
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    vr = out.outputs.get("verify_result")
    assert isinstance(vr, VerifyCommandResult)
    assert vr.success is False


def test_dispatch_build_still_uses_generic_path(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('build') still uses generic workflow path."""
    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={"build_done": True},
    )
    mock_load = mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    ctx = WorkflowContext()
    result = run_command("build", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    # Build returns the context directly (generic path)
    assert out is result_ctx
    mock_load.assert_called_once_with("implement_close")

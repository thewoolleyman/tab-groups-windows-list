"""Tests for command dispatch module."""
from __future__ import annotations

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.commands.build import BuildCommandResult
from adws.adw_modules.commands.dispatch import run_command
from adws.adw_modules.commands.implement import (
    ImplementCommandResult,
)
from adws.adw_modules.commands.prime import PrimeContextResult
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


def test_dispatch_build_uses_specialized_handler(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('build') routes to run_build_command."""
    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={"done": True},
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-1"},
    )
    result = run_command("build", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    br = out.outputs.get("build_result")
    assert isinstance(br, BuildCommandResult)
    assert br.success is True
    assert br.finalize_action == "closed"


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
    result = run_command("load_bundle", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "NoWorkflowError"
    assert "load_bundle" in error.message


def test_run_command_execute_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command propagates execute failure for generic cmd."""
    fake_wf = Workflow(
        name="convert_stories_to_beads",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="convert",
        error_type="StepError",
        message="convert failed",
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
    result = run_command(
        "convert_stories_to_beads", ctx,
    )
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


def test_dispatch_build_workflow_failure_wraps(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('build') wraps wf failure as success."""
    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="timeout",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-2"},
    )
    result = run_command("build", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    br = out.outputs.get("build_result")
    assert isinstance(br, BuildCommandResult)
    assert br.success is False


# --- Prime dispatch tests (Story 4.3) ---


def test_dispatch_prime_uses_specialized_handler(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('prime') routes to run_prime_command."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("claude content"),
            IOSuccess("arch content"),
            IOSuccess("epics content"),
        ],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws tree"),
            IOSuccess("project tree"),
        ],
    )
    ctx = WorkflowContext()
    result = run_command("prime", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    pr = out.outputs.get("prime_result")
    assert isinstance(pr, PrimeContextResult)
    assert pr.success is True


def test_dispatch_prime_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('prime') propagates required file failure."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOFailure(
                PipelineError(
                    step_name="io_ops.read_prime_file",
                    error_type="FileNotFoundError",
                    message="Not found: CLAUDE.md",
                ),
            ),
        ],
    )
    ctx = WorkflowContext()
    result = run_command("prime", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "RequiredFileError"


def test_dispatch_load_bundle_still_returns_no_workflow_error() -> None:
    """load_bundle still returns NoWorkflowError (regression)."""
    ctx = WorkflowContext()
    result = run_command("load_bundle", ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "NoWorkflowError"
    assert "load_bundle" in error.message


def test_dispatch_verify_still_works(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """verify still routes to specialized handler (regression)."""
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
    vr = out.outputs.get("verify_result")
    assert isinstance(vr, VerifyCommandResult)


def test_dispatch_prime_still_works(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """prime still routes to specialized handler (regression)."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("claude content"),
            IOSuccess("arch content"),
            IOSuccess("epics content"),
        ],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws tree"),
            IOSuccess("project tree"),
        ],
    )
    ctx = WorkflowContext()
    result = run_command("prime", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    pr = out.outputs.get("prime_result")
    assert isinstance(pr, PrimeContextResult)


# --- Implement dispatch tests (Story 4.8) ---


def test_dispatch_implement_uses_specialized_handler(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('implement') routes to run_implement_command."""
    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={"done": True},
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("Issue description"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-1"},
    )
    result = run_command("implement", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    ir = out.outputs.get("implement_result")
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is True
    assert ir.finalize_action == "closed"


def test_dispatch_implement_wraps_result(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('implement') wraps result in context."""
    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext()
    result = run_command("implement", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    ir = out.outputs.get("implement_result")
    assert isinstance(ir, ImplementCommandResult)
    assert ir.finalize_action == "skipped"


def test_dispatch_implement_workflow_failure_wraps(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_command('implement') wraps wf failure as success."""
    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement_step",
        error_type="SdkCallError",
        message="timeout",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("desc"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-2"},
    )
    result = run_command("implement", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    ir = out.outputs.get("implement_result")
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is False

"""Tests for /implement command module."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 3: ImplementCommandResult tests ---


def test_implement_command_result_construction() -> None:
    """ImplementCommandResult can be constructed with all fields."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
    )

    result = ImplementCommandResult(
        success=True,
        workflow_executed="implement_verify_close",
        issue_id="TEST-1",
        finalize_action="closed",
        summary="Completed successfully",
        tdd_phases_completed=["RED", "GREEN", "REFACTOR"],
    )
    assert result.success is True
    assert result.workflow_executed == "implement_verify_close"
    assert result.issue_id == "TEST-1"
    assert result.finalize_action == "closed"
    assert result.summary == "Completed successfully"
    assert result.tdd_phases_completed == [
        "RED", "GREEN", "REFACTOR",
    ]


def test_implement_command_result_immutable() -> None:
    """ImplementCommandResult is a frozen dataclass."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
    )

    result = ImplementCommandResult(
        success=True,
        workflow_executed="implement_verify_close",
        issue_id=None,
        finalize_action="skipped",
        summary="Done",
        tdd_phases_completed=[],
    )
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


def test_implement_command_result_none_issue_id() -> None:
    """ImplementCommandResult allows None issue_id."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
    )

    result = ImplementCommandResult(
        success=False,
        workflow_executed="implement_verify_close",
        issue_id=None,
        finalize_action="skipped",
        summary="Failed",
        tdd_phases_completed=[],
    )
    assert result.issue_id is None


# --- Task 4: run_implement_command tests ---


def test_run_implement_command_calls_beads_show(
    mocker: MockerFixture,
) -> None:
    """run_implement_command calls io_ops.run_beads_show."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={"done": True},
    )
    mock_show = mocker.patch(
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
        inputs={"issue_id": "ISSUE-123"},
    )
    run_implement_command(ctx)
    mock_show.assert_called_once_with("ISSUE-123")


def test_run_implement_command_enriches_ctx(
    mocker: MockerFixture,
) -> None:
    """run_implement_command sets issue_description in ctx."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("Issue description"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mock_exec = mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(WorkflowContext()),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "ISSUE-123"},
    )
    run_implement_command(ctx)
    enriched_ctx = mock_exec.call_args[0][1]
    assert (
        enriched_ctx.inputs["issue_description"]
        == "Issue description"
    )


def test_run_implement_command_success(
    mocker: MockerFixture,
) -> None:
    """run_implement_command returns success on workflow success."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

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
        return_value=IOSuccess("Issue desc"),
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
        inputs={"issue_id": "ISSUE-123"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is True
    assert ir.workflow_executed == "implement_verify_close"
    assert ir.finalize_action == "closed"
    assert ir.issue_id == "ISSUE-123"
    assert ir.summary == "Completed successfully"


def test_run_implement_command_failure(
    mocker: MockerFixture,
) -> None:
    """run_implement_command returns failure on wf failure."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="write_failing_tests",
        error_type="SdkResponseError",
        message="Agent failed to produce tests",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("Issue desc"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    mock_update = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "ISSUE-123"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is False
    assert ir.finalize_action == "tagged_failure"
    # Verify bd update was called, NOT bd close
    mock_update.assert_called_once()
    notes = mock_update.call_args[0][1]
    assert "ADWS_FAILED" in notes
    assert "write_failing_tests" in notes


def test_run_implement_command_no_issue_id(
    mocker: MockerFixture,
) -> None:
    """run_implement_command works without issue_id."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

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
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert ir.finalize_action == "skipped"
    assert ir.issue_id is None


def test_run_implement_command_beads_show_failure(
    mocker: MockerFixture,
) -> None:
    """run_implement_command fails when beads_show fails."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )

    show_err = PipelineError(
        step_name="io_ops.run_beads_show",
        error_type="BeadsShowError",
        message="Issue not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOFailure(show_err),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "BAD-1"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert "Beads" in error.message or "beads" in error.message.lower()


def test_run_implement_command_workflow_not_found(
    mocker: MockerFixture,
) -> None:
    """run_implement_command fails when workflow not found."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )

    load_err = PipelineError(
        step_name="io_ops.load_command_workflow",
        error_type="WorkflowNotFoundError",
        message="Not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOFailure(load_err),
    )
    ctx = WorkflowContext()
    result = run_implement_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is load_err


def test_run_implement_command_double_failure(
    mocker: MockerFixture,
) -> None:
    """run_implement_command with wf fail + bd update fail."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

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
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.run_beads_update_notes",
                error_type="BeadsUpdateError",
                message="bd update failed",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "ISSUE-1"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert ir.success is False
    assert ir.finalize_action == "tag_failed"


def test_run_implement_command_close_failure(
    mocker: MockerFixture,
) -> None:
    """run_implement_command success but bd close fails."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
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
        return_value=IOSuccess(WorkflowContext()),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.run_beads_close",
                error_type="BeadsCloseError",
                message="bd close failed",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "ISSUE-1"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert ir.success is True
    assert ir.finalize_action == "close_failed"


# --- Task 8: Integration tests ---


def test_integration_implement_success_with_issue(
    mocker: MockerFixture,
) -> None:
    """Integration: full success path with issue_id."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )
    from adws.adw_modules.types import (  # noqa: PLC0415
        ShellResult,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
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
        return_value=IOSuccess(WorkflowContext()),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="closed",
                stderr="",
                command="bd close",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-1"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is True
    assert ir.workflow_executed == "implement_verify_close"
    assert ir.finalize_action == "closed"
    assert ir.issue_id == "TEST-1"


def test_integration_implement_red_failure(
    mocker: MockerFixture,
) -> None:
    """Integration: RED phase failure tags issue."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )
    from adws.adw_modules.types import (  # noqa: PLC0415
        ShellResult,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="write_failing_tests",
        error_type="SdkResponseError",
        message="Agent failed to produce tests",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("Issue desc"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    mock_update = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="updated",
                stderr="",
                command="bd update",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-2"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is False
    assert ir.finalize_action == "tagged_failure"
    notes = mock_update.call_args[0][1]
    assert "ADWS_FAILED" in notes
    assert "step=write_failing_tests" in notes


def test_integration_implement_green_failure(
    mocker: MockerFixture,
) -> None:
    """Integration: GREEN phase failure tags issue."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )
    from adws.adw_modules.types import (  # noqa: PLC0415
        ShellResult,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement_step",
        error_type="SdkCallError",
        message="Implementation failed",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("Issue desc"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    mock_update = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="updated",
                stderr="",
                command="bd update",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-3"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is False
    notes = mock_update.call_args[0][1]
    assert "step=implement_step" in notes


def test_integration_implement_refactor_failure(
    mocker: MockerFixture,
) -> None:
    """Integration: REFACTOR phase failure tags issue."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )
    from adws.adw_modules.types import (  # noqa: PLC0415
        ShellResult,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="refactor_step",
        error_type="SdkCallError",
        message="Refactor failed",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("Issue desc"),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(exec_err),
    )
    mock_update = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="updated",
                stderr="",
                command="bd update",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-4"},
    )
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.success is False
    notes = mock_update.call_args[0][1]
    assert "step=refactor_step" in notes


def test_integration_implement_finalize_always_runs(
    mocker: MockerFixture,
) -> None:
    """Integration: finalize always runs on failure path."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_verify_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement_step",
        error_type="SdkCallError",
        message="failed",
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
    mock_update = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "TEST-5"},
    )
    run_implement_command(ctx)
    # Verify run_beads_update_notes was called (finalize ran)
    mock_update.assert_called_once()


def test_integration_implement_success_no_issue(
    mocker: MockerFixture,
) -> None:
    """Integration: success without issue_id skips finalize."""
    from adws.adw_modules.commands.implement import (  # noqa: PLC0415
        ImplementCommandResult,
        run_implement_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

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
    result = run_implement_command(ctx)
    assert isinstance(result, IOSuccess)
    ir = unsafe_perform_io(result.unwrap())
    assert isinstance(ir, ImplementCommandResult)
    assert ir.finalize_action == "skipped"

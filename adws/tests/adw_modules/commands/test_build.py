"""Tests for /build command module.

Finalize helper tests (build_failure_metadata,
finalize_on_success, finalize_on_failure) live in
test_finalize.py since those functions were extracted
to the shared _finalize.py module.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 1: BuildCommandResult tests ---


def test_build_command_result_construction() -> None:
    """BuildCommandResult can be constructed with all fields."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
    )

    result = BuildCommandResult(
        success=True,
        workflow_executed="implement_close",
        issue_id="TEST-1",
        finalize_action="closed",
        summary="Completed successfully",
    )
    assert result.success is True
    assert result.workflow_executed == "implement_close"
    assert result.issue_id == "TEST-1"
    assert result.finalize_action == "closed"
    assert result.summary == "Completed successfully"


def test_build_command_result_immutable() -> None:
    """BuildCommandResult is a frozen dataclass."""
    import pytest  # noqa: PLC0415

    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
    )

    result = BuildCommandResult(
        success=True,
        workflow_executed="implement_close",
        issue_id=None,
        finalize_action="skipped",
        summary="Done",
    )
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


def test_build_command_result_none_issue_id() -> None:
    """BuildCommandResult allows None issue_id."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
    )

    result = BuildCommandResult(
        success=False,
        workflow_executed="implement_close",
        issue_id=None,
        finalize_action="skipped",
        summary="Failed",
    )
    assert result.issue_id is None


# --- run_build_command tests ---
# Note: Finalize helper tests (build_failure_metadata,
# finalize_on_success, finalize_on_failure) now live in
# test_finalize.py since those functions were extracted
# to the shared _finalize.py module in Story 4.8.


def test_run_build_command_success(    mocker: MockerFixture,
) -> None:
    """run_build_command returns success on workflow success."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

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
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert isinstance(br, BuildCommandResult)
    assert br.success is True
    assert br.workflow_executed == "implement_close"
    assert br.finalize_action == "closed"
    assert br.issue_id == "TEST-1"


def test_run_build_command_workflow_failure(    mocker: MockerFixture,
) -> None:
    """run_build_command returns success=False on wf failure."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="Model timeout",
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
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert isinstance(br, BuildCommandResult)
    assert br.success is False
    assert br.finalize_action == "tagged_failure"


def test_run_build_command_workflow_load_failure(    mocker: MockerFixture,
) -> None:
    """run_build_command returns IOFailure on load failure."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        run_build_command,
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
    result = run_build_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is load_err


def test_run_build_command_with_issue_id(    mocker: MockerFixture,
) -> None:
    """run_build_command passes issue_id to finalize."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_close",
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
    mock_close = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOSuccess(WorkflowContext()),
    )
    ctx = WorkflowContext(
        inputs={"issue_id": "BEADS-42"},
    )
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert br.issue_id == "BEADS-42"
    mock_close.assert_called_once_with(
        "BEADS-42", "Completed successfully",
    )


def test_run_build_command_no_issue_id(    mocker: MockerFixture,
) -> None:
    """run_build_command returns 'skipped' when no issue_id."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_close",
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
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert br.finalize_action == "skipped"
    assert br.issue_id is None


# --- Task 11: Integration tests ---


def test_integration_build_success_with_issue(    mocker: MockerFixture,
) -> None:
    """Integration: full success path with issue_id."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )
    from adws.adw_modules.types import (  # noqa: PLC0415
        ShellResult,
    )

    fake_wf = Workflow(
        name="implement_close",
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
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert isinstance(br, BuildCommandResult)
    assert br.success is True
    assert br.workflow_executed == "implement_close"
    assert br.finalize_action == "closed"
    assert br.issue_id == "TEST-1"


def test_integration_build_failure_with_issue(    mocker: MockerFixture,
) -> None:
    """Integration: workflow failure tags issue."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )
    from adws.adw_modules.types import (  # noqa: PLC0415
        ShellResult,
    )

    fake_wf = Workflow(
        name="implement_close",
        description="test",
        steps=[],
    )
    exec_err = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="Model timeout",
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
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert isinstance(br, BuildCommandResult)
    assert br.success is False
    assert br.finalize_action == "tagged_failure"
    # Verify metadata was passed
    notes = mock_update.call_args[0][1]
    assert "ADWS_FAILED" in notes
    assert "SdkCallError" in notes


def test_integration_build_success_no_issue(    mocker: MockerFixture,
) -> None:
    """Integration: success without issue_id skips finalize."""
    from adws.adw_modules.commands.build import (  # noqa: PLC0415
        BuildCommandResult,
        run_build_command,
    )
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    fake_wf = Workflow(
        name="implement_close",
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
    result = run_build_command(ctx)
    assert isinstance(result, IOSuccess)
    br = unsafe_perform_io(result.unwrap())
    assert isinstance(br, BuildCommandResult)
    assert br.finalize_action == "skipped"

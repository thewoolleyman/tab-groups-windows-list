"""Tests for adw_dispatch module -- dispatch policy enforcement."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.types import Step, Workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import ShellResult, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestDispatchWorkflow:
    """Tests for dispatch_workflow policy enforcer."""

    def test_success_dispatchable_workflow(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given issue with dispatchable workflow tag, returns IOSuccess."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Story content\n\n{implement_verify_close}",
            ),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOSuccess)
        ctx = unsafe_perform_io(result.unwrap())
        assert ctx.inputs["issue_id"] == "ISSUE-42"
        assert ctx.inputs["issue_description"] == (
            "Story content\n\n{implement_verify_close}"
        )
        assert ctx.inputs["workflow_tag"] == "implement_verify_close"
        assert ctx.inputs["workflow"] is not None

    def test_non_dispatchable_workflow_rejected(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given non-dispatchable workflow tag, returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{convert_stories_to_beads}",
            ),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "NonDispatchableError"
        assert error.step_name == "adw_dispatch"
        assert "convert_stories_to_beads" in error.message
        assert "not dispatchable" in error.message

    def test_unknown_workflow_tag(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given unknown workflow tag, returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{totally_unknown}",
            ),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "UnknownWorkflowTagError"
        assert "totally_unknown" in str(error.context.get("tag"))
        assert "available_workflows" in error.context
        # Dispatch errors should only list dispatchable workflows
        available = error.context["available_workflows"]
        assert isinstance(available, list)
        assert "convert_stories_to_beads" not in available
        assert "sample" not in available
        assert "verify" not in available

    def test_missing_tag_in_description(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given description with no tag, returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess("No tags at all"),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingWorkflowTagError"

    def test_io_ops_failure_propagates(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given io_ops failure, propagates IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        io_err = PipelineError(
            step_name="io_ops.read_issue_description",
            error_type="BeadsShowError",
            message="bd show failed",
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOFailure(io_err),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error is io_err

    def test_empty_issue_id(self) -> None:
        """Given empty issue_id, returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        result = dispatch_workflow("")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ValueError"
        assert error.step_name == "adw_dispatch"

    def test_whitespace_only_issue_id(self) -> None:
        """Given whitespace-only issue_id, returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        result = dispatch_workflow("   ")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ValueError"
        assert error.step_name == "adw_dispatch"

    def test_never_reads_bmad_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """dispatch_workflow never calls io_ops.read_bmad_file (NFR19)."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_verify_close}",
            ),
        )
        mock_bmad = mocker.patch(
            "adws.adw_dispatch.io_ops.read_bmad_file",
        )
        dispatch_workflow("ISSUE-42")
        mock_bmad.assert_not_called()


def _make_test_workflow() -> Workflow:
    """Create a minimal test workflow."""
    return Workflow(
        name="implement_verify_close",
        description="Test workflow",
        dispatchable=True,
        steps=[
            Step(
                name="test_step",
                function="check_sdk_available",
            ),
        ],
    )


def _make_dispatch_ctx(
    *,
    issue_id: str | None = "ISSUE-42",
    workflow: object | None = None,
) -> WorkflowContext:
    """Build a WorkflowContext as dispatch_workflow would."""
    inputs: dict[str, object] = {
        "issue_description": "Story content",
        "workflow_tag": "implement_verify_close",
    }
    if issue_id is not None:
        inputs["issue_id"] = issue_id
    if workflow is not None:
        inputs["workflow"] = workflow
    return WorkflowContext(inputs=inputs)


class TestExecuteDispatchedWorkflow:
    """Tests for execute_dispatched_workflow."""

    def test_success_executes_and_closes(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given valid ctx, executes workflow and closes issue."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(workflow=wf)
        result_ctx = WorkflowContext(
            inputs=ctx.inputs,
            outputs={"result": "done"},
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(result_ctx),
        )
        mock_close = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="closed",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert isinstance(der, DispatchExecutionResult)
        assert der.success is True
        assert der.workflow_executed == "implement_verify_close"
        assert der.issue_id == "ISSUE-42"
        assert der.finalize_action == "closed"
        assert "success" in der.summary.lower()
        mock_close.assert_called_once_with(
            "ISSUE-42", "Completed successfully",
        )

    def test_missing_workflow_input(self) -> None:
        """Given ctx missing 'workflow', returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        ctx = _make_dispatch_ctx(workflow=None)
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "execute_dispatched_workflow"

    def test_invalid_workflow_type(self) -> None:
        """Given ctx with non-Workflow 'workflow', returns IOFailure."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        ctx = _make_dispatch_ctx(workflow="not_a_workflow")
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "InvalidInputError"
        assert error.step_name == "execute_dispatched_workflow"

    def test_missing_issue_id_skips_finalize(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given ctx without issue_id, finalize is skipped."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(
            issue_id=None, workflow=wf,
        )
        result_ctx = WorkflowContext(
            inputs=ctx.inputs,
            outputs={"result": "done"},
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(result_ctx),
        )
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.finalize_action == "skipped"
        assert der.issue_id is None
        assert der.success is True

    def test_workflow_failure_tags_issue(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given workflow failure, tags issue with metadata."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(workflow=wf)
        exec_err = PipelineError(
            step_name="implement",
            error_type="SdkCallError",
            message="SDK timeout",
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOFailure(exec_err),
        )
        mock_update = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_update_notes",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="updated",
                    stderr="",
                    command="bd update",
                ),
            ),
        )
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is False
        assert der.finalize_action == "tagged_failure"
        assert "SDK timeout" in der.summary
        mock_update.assert_called_once()
        issue_arg = mock_update.call_args[0][0]
        notes_arg = mock_update.call_args[0][1]
        assert issue_arg == "ISSUE-42"
        assert notes_arg.startswith("ADWS_FAILED|")

    def test_workflow_failure_and_tag_fails(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given workflow fails AND bd update fails, returns tag_failed."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(workflow=wf)
        exec_err = PipelineError(
            step_name="implement",
            error_type="SdkCallError",
            message="SDK error",
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOFailure(exec_err),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_update_notes",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_beads_update_notes",
                    error_type="BeadsUpdateError",
                    message="bd update failed",
                ),
            ),
        )
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is False
        assert der.finalize_action == "tag_failed"

    def test_workflow_success_but_close_fails(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given workflow succeeds AND bd close fails, returns close_failed."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(workflow=wf)
        result_ctx = WorkflowContext(
            inputs=ctx.inputs,
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(result_ctx),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_beads_close",
                    error_type="BeadsCloseError",
                    message="bd close failed",
                ),
            ),
        )
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is True
        assert der.finalize_action == "close_failed"

    def test_workflow_failure_no_issue_id_skips(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given workflow fails and no issue_id, finalize skipped."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(
            issue_id=None, workflow=wf,
        )
        exec_err = PipelineError(
            step_name="implement",
            error_type="SdkCallError",
            message="SDK error",
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOFailure(exec_err),
        )
        result = execute_dispatched_workflow(ctx)
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is False
        assert der.finalize_action == "skipped"
        assert der.issue_id is None

    def test_never_reads_bmad_during_execution(
        self,
        mocker: MockerFixture,
    ) -> None:
        """execute_dispatched_workflow never calls read_bmad_file (NFR19)."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            execute_dispatched_workflow,
        )

        wf = _make_test_workflow()
        ctx = _make_dispatch_ctx(workflow=wf)
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(
                WorkflowContext(inputs=ctx.inputs),
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        mock_bmad = mocker.patch(
            "adws.adw_dispatch.io_ops.read_bmad_file",
        )
        execute_dispatched_workflow(ctx)
        mock_bmad.assert_not_called()


class TestDispatchAndExecute:
    """Tests for dispatch_and_execute orchestrator."""

    def test_success_dispatch_and_execute(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full pipeline: dispatch -> execute -> close."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
            dispatch_and_execute,
        )

        wf = _make_test_workflow()
        desc = "Story content\n\n{implement_verify_close}"
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(desc),
        )
        # dispatch_workflow puts workflow in ctx
        # execute_command_workflow runs the workflow
        result_ctx = WorkflowContext(
            inputs={
                "issue_id": "ISSUE-42",
                "issue_description": desc,
                "workflow_tag": "implement_verify_close",
                "workflow": wf,
            },
            outputs={"result": "done"},
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(result_ctx),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="closed",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        result = dispatch_and_execute("ISSUE-42")
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert isinstance(der, DispatchExecutionResult)
        assert der.success is True
        assert der.workflow_executed == "implement_verify_close"
        assert der.issue_id == "ISSUE-42"
        assert der.finalize_action == "closed"

    def test_dispatch_failure_propagates(
        self,
        mocker: MockerFixture,
    ) -> None:
        """When dispatch fails, IOFailure propagates without finalize."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_and_execute,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{totally_unknown}",
            ),
        )
        mock_exec = mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
        )
        mock_close = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
        )
        result = dispatch_and_execute("ISSUE-42")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "UnknownWorkflowTagError"
        mock_exec.assert_not_called()
        mock_close.assert_not_called()

    def test_dispatch_success_execution_fails(
        self,
        mocker: MockerFixture,
    ) -> None:
        """When dispatch succeeds but workflow fails, returns success=False."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_and_execute,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_verify_close}",
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOFailure(
                PipelineError(
                    step_name="implement",
                    error_type="SdkCallError",
                    message="SDK timeout",
                ),
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_update_notes",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="updated",
                    stderr="",
                    command="bd update",
                ),
            ),
        )
        result = dispatch_and_execute("ISSUE-42")
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is False
        assert der.finalize_action == "tagged_failure"

    def test_empty_issue_id(self) -> None:
        """Empty issue_id returns IOFailure from dispatch_workflow."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_and_execute,
        )

        result = dispatch_and_execute("")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ValueError"

    def test_never_reads_bmad_full_flow(
        self,
        mocker: MockerFixture,
    ) -> None:
        """dispatch_and_execute never calls read_bmad_file (NFR19)."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_and_execute,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_verify_close}",
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(
                WorkflowContext(
                    inputs={
                        "issue_id": "ISSUE-42",
                        "workflow_tag": "implement_verify_close",
                    },
                ),
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        mock_bmad = mocker.patch(
            "adws.adw_dispatch.io_ops.read_bmad_file",
        )
        dispatch_and_execute("ISSUE-42")
        mock_bmad.assert_not_called()


class TestBuildFailureMetadataFromDispatch:
    """Tests verifying failure metadata format compliance."""

    def test_metadata_format_compliance(self) -> None:
        """Verify metadata format for triage parser (Story 7.4)."""
        from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
            build_failure_metadata,
        )

        error = PipelineError(
            step_name="implement",
            error_type="SdkCallError",
            message="SDK timeout",
        )
        metadata = build_failure_metadata(error, 1)
        assert metadata.startswith("ADWS_FAILED|attempt=1|last_failure=")
        assert "|error_class=SdkCallError|" in metadata
        assert "|step=implement|" in metadata
        assert "|summary=SDK timeout" in metadata

    def test_metadata_pipe_escaping(self) -> None:
        """Verify pipe characters in messages are escaped."""
        from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
            build_failure_metadata,
        )

        error = PipelineError(
            step_name="step_a",
            error_type="Error",
            message="step A | step B failed",
        )
        metadata = build_failure_metadata(error, 1)
        assert "step A \\| step B failed" in metadata

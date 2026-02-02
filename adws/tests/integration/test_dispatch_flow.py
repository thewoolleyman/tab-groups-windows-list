"""Integration tests for full dispatch flow (Story 7.1 + 7.2).

Tests the complete dispatch path: issue read -> tag extract
-> workflow lookup -> dispatchable policy -> context build.
Story 7.2: dispatch -> execute -> finalize integration.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import ShellResult, WorkflowContext
from adws.workflows import WorkflowName

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestDispatchFlowSuccess:
    """Integration tests for successful dispatch."""

    def test_full_dispatch_implement_verify_close(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full dispatch flow with implement_verify_close tag."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        description = (
            "# Story 7.1: Issue Tag Extraction\n\n"
            "As a developer...\n\n"
            "## Acceptance Criteria\n\n"
            "1. Given a Beads issue...\n\n"
            "{implement_verify_close}"
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(description),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOSuccess)
        ctx = unsafe_perform_io(result.unwrap())

        # Verify all expected context fields
        assert ctx.inputs["issue_id"] == "ISSUE-42"
        assert ctx.inputs["issue_description"] == description
        assert ctx.inputs["workflow_tag"] == (
            WorkflowName.IMPLEMENT_VERIFY_CLOSE
        )
        workflow = ctx.inputs["workflow"]
        assert hasattr(workflow, "name")
        assert hasattr(workflow, "dispatchable")

    def test_full_dispatch_implement_close(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full dispatch flow with implement_close tag."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Story content\n\n{implement_close}",
            ),
        )
        result = dispatch_workflow("ISSUE-99")
        assert isinstance(result, IOSuccess)
        ctx = unsafe_perform_io(result.unwrap())
        assert ctx.inputs["workflow_tag"] == (
            WorkflowName.IMPLEMENT_CLOSE
        )


class TestDispatchFlowRejections:
    """Integration tests for dispatch rejections."""

    def test_non_dispatchable_workflow_rejected(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Dispatch rejects non-dispatchable workflow."""
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

    def test_unknown_tag_with_available_list(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Dispatch rejects unknown tag with available names."""
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
        available = error.context.get("available_workflows")
        assert isinstance(available, list)
        assert len(available) > 0
        # Dispatch errors should only list dispatchable workflows
        assert "convert_stories_to_beads" not in available
        assert "sample" not in available
        assert "verify" not in available

    def test_missing_tag_rejected(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Dispatch rejects description with no tag."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Just a plain description with no tags",
            ),
        )
        result = dispatch_workflow("ISSUE-42")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingWorkflowTagError"


class TestDispatchFlowNFR19:
    """Integration tests verifying NFR19 compliance."""

    def test_dispatch_never_reads_bmad_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """dispatch_workflow does NOT call io_ops.read_bmad_file (NFR19)."""
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

    def test_dispatch_never_reads_bmad_on_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """NFR19 holds even when dispatch fails."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_workflow,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess("No tags"),
        )
        mock_bmad = mocker.patch(
            "adws.adw_dispatch.io_ops.read_bmad_file",
        )
        dispatch_workflow("ISSUE-42")
        mock_bmad.assert_not_called()


class TestDispatchExecuteCloseFlow:
    """Integration tests for dispatch-execute-close (Story 7.2)."""

    def test_successful_dispatch_execute_close(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full success: dispatch -> execute -> close issue."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_and_execute,
        )

        desc = (
            "# Story\n\nAs a developer...\n\n"
            "{implement_verify_close}"
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(desc),
        )
        result_ctx = WorkflowContext(
            inputs={
                "issue_id": "ISSUE-42",
                "issue_description": desc,
                "workflow_tag": "implement_verify_close",
            },
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
        result = dispatch_and_execute("ISSUE-42")
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is True
        assert der.finalize_action == "closed"
        assert (
            der.workflow_executed
            == WorkflowName.IMPLEMENT_VERIFY_CLOSE
        )
        mock_close.assert_called_once_with(
            "ISSUE-42", "Completed successfully",
        )

    def test_dispatch_execute_failure_tags_issue(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Failure: dispatch -> execute fails -> tag issue."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            dispatch_and_execute,
        )

        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
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
        result = dispatch_and_execute("ISSUE-42")
        assert isinstance(result, IOSuccess)
        der = unsafe_perform_io(result.unwrap())
        assert der.success is False
        assert der.finalize_action == "tagged_failure"
        # Verify ADWS_FAILED metadata was passed to correct issue
        mock_update.assert_called_once()
        issue_arg = mock_update.call_args[0][0]
        notes_arg = mock_update.call_args[0][1]
        assert issue_arg == "ISSUE-42"
        assert notes_arg.startswith("ADWS_FAILED|")

    def test_close_not_called_on_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """On failure, run_beads_close is NOT called."""
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
                    message="error",
                ),
            ),
        )
        mock_close = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_update_notes",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                    command="bd update",
                ),
            ),
        )
        dispatch_and_execute("ISSUE-42")
        mock_close.assert_not_called()

    def test_update_notes_not_called_on_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """On success, run_beads_update_notes is NOT called."""
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
        mock_update = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_update_notes",
        )
        dispatch_and_execute("ISSUE-42")
        mock_update.assert_not_called()

    def test_dispatch_failure_no_execution_or_finalize(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Dispatch failure: no execute, no close, no update."""
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
        mock_update = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_update_notes",
        )
        result = dispatch_and_execute("ISSUE-42")
        assert isinstance(result, IOFailure)
        mock_exec.assert_not_called()
        mock_close.assert_not_called()
        mock_update.assert_not_called()

    def test_full_flow_never_reads_bmad(
        self,
        mocker: MockerFixture,
    ) -> None:
        """dispatch_and_execute never reads BMAD files (NFR19)."""
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

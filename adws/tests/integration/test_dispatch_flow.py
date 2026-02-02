"""Integration tests for full dispatch flow (Story 7.1).

Tests the complete dispatch path: issue read -> tag extract
-> workflow lookup -> dispatchable policy -> context build.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

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

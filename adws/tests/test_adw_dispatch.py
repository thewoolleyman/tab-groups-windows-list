"""Tests for adw_dispatch module -- dispatch policy enforcement."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError

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

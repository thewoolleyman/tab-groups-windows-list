"""Tests for read_and_extract step function."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Step registration tests ---


class TestStepRegistration:
    """Tests for step module registration."""

    def test_read_and_extract_importable(self) -> None:
        """read_and_extract is importable from steps package."""
        from adws.adw_modules.steps import (  # noqa: PLC0415
            read_and_extract as imported_fn,
        )
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        assert imported_fn is read_and_extract

    def test_read_and_extract_in_all(self) -> None:
        """read_and_extract appears in steps.__all__."""
        import adws.adw_modules.steps as steps_mod  # noqa: PLC0415

        assert "read_and_extract" in steps_mod.__all__

    def test_read_and_extract_in_step_registry(self) -> None:
        """read_and_extract is in _STEP_REGISTRY."""
        from adws.adw_modules.engine.executor import (  # noqa: PLC0415
            _STEP_REGISTRY,
        )
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        assert "read_and_extract" in _STEP_REGISTRY
        assert _STEP_REGISTRY["read_and_extract"] is read_and_extract


class TestReadAndExtract:
    """Tests for the read_and_extract step function."""

    def test_success_reads_and_extracts(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given issue_id, reads description and extracts tag."""
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        mocker.patch(
            "adws.adw_modules.steps.read_and_extract.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Story content\n\n{implement_verify_close}",
            ),
        )
        ctx = WorkflowContext(
            inputs={"issue_id": "ISSUE-42"},
        )
        result = read_and_extract(ctx)
        assert isinstance(result, IOSuccess)
        new_ctx = unsafe_perform_io(result.unwrap())
        assert new_ctx.outputs["issue_description"] == (
            "Story content\n\n{implement_verify_close}"
        )
        assert new_ctx.outputs["workflow_tag"] == "implement_verify_close"
        assert new_ctx.outputs["workflow"] is not None

    def test_missing_issue_id_input(self) -> None:
        """Given no issue_id in inputs, returns IOFailure."""
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        ctx = WorkflowContext(inputs={})
        result = read_and_extract(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "read_and_extract"

    def test_io_ops_failure_propagates(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given io_ops failure, propagates IOFailure."""
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        io_err = PipelineError(
            step_name="io_ops.read_issue_description",
            error_type="BeadsShowError",
            message="bd show failed",
        )
        mocker.patch(
            "adws.adw_modules.steps.read_and_extract.io_ops.read_issue_description",
            return_value=IOFailure(io_err),
        )
        ctx = WorkflowContext(
            inputs={"issue_id": "BAD-1"},
        )
        result = read_and_extract(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error is io_err

    def test_no_tag_in_description(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given description with no tag, returns IOFailure."""
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        mocker.patch(
            "adws.adw_modules.steps.read_and_extract.io_ops.read_issue_description",
            return_value=IOSuccess("No tags here"),
        )
        ctx = WorkflowContext(
            inputs={"issue_id": "ISSUE-42"},
        )
        result = read_and_extract(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingWorkflowTagError"

    def test_unknown_workflow_tag(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given description with unknown tag, returns IOFailure."""
        from adws.adw_modules.steps.read_and_extract import (  # noqa: PLC0415
            read_and_extract,
        )

        mocker.patch(
            "adws.adw_modules.steps.read_and_extract.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{totally_unknown}",
            ),
        )
        ctx = WorkflowContext(
            inputs={"issue_id": "ISSUE-42"},
        )
        result = read_and_extract(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "UnknownWorkflowTagError"

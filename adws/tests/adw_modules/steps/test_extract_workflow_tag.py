"""Tests for extract_workflow_tag pure function and extract_and_validate_tag step."""
from __future__ import annotations

from returns.io import IOFailure, IOSuccess
from returns.result import Failure, Success
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

# --- Step registration tests ---


class TestStepRegistration:
    """Tests for step module registration."""

    def test_extract_and_validate_tag_importable(self) -> None:
        """extract_and_validate_tag is importable from steps package."""
        from adws.adw_modules.steps import (  # noqa: PLC0415
            extract_and_validate_tag as imported_fn,
        )
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_and_validate_tag,
        )

        assert imported_fn is extract_and_validate_tag

    def test_extract_and_validate_tag_in_all(self) -> None:
        """extract_and_validate_tag appears in steps.__all__."""
        import adws.adw_modules.steps as steps_mod  # noqa: PLC0415

        assert "extract_and_validate_tag" in steps_mod.__all__

    def test_extract_and_validate_tag_in_step_registry(self) -> None:
        """extract_and_validate_tag is in _STEP_REGISTRY."""
        from adws.adw_modules.engine.executor import (  # noqa: PLC0415
            _STEP_REGISTRY,
        )
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_and_validate_tag,
        )

        assert "extract_and_validate_tag" in _STEP_REGISTRY
        assert _STEP_REGISTRY["extract_and_validate_tag"] is extract_and_validate_tag


# --- Task 1: extract_workflow_tag pure function tests ---


class TestExtractWorkflowTag:
    """Tests for the extract_workflow_tag pure function."""

    def test_extracts_single_tag(self) -> None:
        """Given description with {implement_verify_close}, returns Success."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_workflow_tag,
        )

        description = "Story content here\n\n{implement_verify_close}"
        result = extract_workflow_tag(description)
        assert isinstance(result, Success)
        assert result.unwrap() == "implement_verify_close"

    def test_missing_tag_returns_failure(self) -> None:
        """No {tag} returns Failure with MissingWorkflowTagError."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_workflow_tag,
        )

        description = "No tags in this description at all"
        result = extract_workflow_tag(description)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PipelineError)
        assert error.error_type == "MissingWorkflowTagError"
        assert error.step_name == "extract_workflow_tag"
        assert "No workflow tag found" in error.message

    def test_multiple_tags_returns_first(self) -> None:
        """Given multiple {tags}, returns Success with the first one."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_workflow_tag,
        )

        description = "Content\n{implement_verify_close}\nmore\n{sample}"
        result = extract_workflow_tag(description)
        assert isinstance(result, Success)
        assert result.unwrap() == "implement_verify_close"

    def test_empty_description_returns_failure(self) -> None:
        """Given empty string, returns Failure with MissingWorkflowTagError."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_workflow_tag,
        )

        result = extract_workflow_tag("")
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PipelineError)
        assert error.error_type == "MissingWorkflowTagError"

    def test_invalid_tag_characters_not_matched(self) -> None:
        """Tags with hyphens or spaces do NOT match (only \\w+ patterns)."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_workflow_tag,
        )

        description = "Content {invalid-name} and {has spaces}"
        result = extract_workflow_tag(description)
        assert isinstance(result, Failure)
        error = result.failure()
        assert error.error_type == "MissingWorkflowTagError"

    def test_tag_with_numbers_and_underscores(self) -> None:
        """Tags with numbers and underscores are valid \\w+ matches."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_workflow_tag,
        )

        description = "Content\n\n{workflow_v2_test}"
        result = extract_workflow_tag(description)
        assert isinstance(result, Success)
        assert result.unwrap() == "workflow_v2_test"


# --- Task 2: extract_and_validate_tag step tests ---


class TestExtractAndValidateTag:
    """Tests for the extract_and_validate_tag step function."""

    def test_success_extracts_and_validates(self) -> None:
        """Valid workflow tag returns IOSuccess with workflow."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_and_validate_tag,
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Story content\n\n{implement_verify_close}"
                ),
            },
        )
        result = extract_and_validate_tag(ctx)
        assert isinstance(result, IOSuccess)
        new_ctx = unsafe_perform_io(result.unwrap())
        assert new_ctx.outputs["workflow_tag"] == "implement_verify_close"
        assert new_ctx.outputs["workflow"] is not None

    def test_missing_issue_description_input(self) -> None:
        """Given no issue_description in inputs, returns IOFailure."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_and_validate_tag,
        )

        ctx = WorkflowContext(inputs={})
        result = extract_and_validate_tag(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "extract_and_validate_tag"

    def test_unknown_workflow_tag(self) -> None:
        """Given description with unknown tag, returns IOFailure."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_and_validate_tag,
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Content\n\n{nonexistent_workflow}",
            },
        )
        result = extract_and_validate_tag(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "UnknownWorkflowTagError"
        assert "nonexistent_workflow" in str(error.context.get("tag"))
        assert "available_workflows" in error.context

    def test_no_tag_in_description(self) -> None:
        """Given description with no tag, propagates MissingWorkflowTagError."""
        from adws.adw_modules.steps.extract_workflow_tag import (  # noqa: PLC0415
            extract_and_validate_tag,
        )

        ctx = WorkflowContext(
            inputs={"issue_description": "No tags here"},
        )
        result = extract_and_validate_tag(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingWorkflowTagError"

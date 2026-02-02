"""Tests for create_beads_issue step and private helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.result import Failure, Success
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.create_beads_issue import (
    _embed_workflow_tag,
    _get_valid_workflow_names,
    _validate_workflow_name,
    create_beads_issue,
)
from adws.adw_modules.types import BmadStory, WorkflowContext
from adws.workflows import WorkflowName

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Import/registration tests ---


class TestStepRegistration:
    """Tests for step module registration."""

    def test_importable_from_steps(self) -> None:
        """create_beads_issue is importable from steps package."""
        from adws.adw_modules.steps import (  # noqa: PLC0415
            create_beads_issue as imported_fn,
        )

        assert imported_fn is create_beads_issue

    def test_in_steps_all(self) -> None:
        """create_beads_issue appears in steps.__all__."""
        import adws.adw_modules.steps as steps_mod  # noqa: PLC0415

        assert "create_beads_issue" in steps_mod.__all__


# --- Fixtures ---


def _make_story(**overrides: object) -> BmadStory:
    """Create a BmadStory for testing with optional overrides."""
    defaults: dict[str, object] = {
        "epic_number": 6,
        "story_number": 2,
        "title": "Beads Issue Creator",
        "slug": "6-2-beads-issue-creator",
        "user_story": "As a dev, I want issues.",
        "acceptance_criteria": (
            "**Given** X **When** Y **Then** Z"
        ),
        "frs_covered": [],
        "raw_content": (
            "#### Story 6.2: Beads Issue Creator"
            "\n\nContent here."
        ),
    }
    defaults.update(overrides)
    return BmadStory(**defaults)  # type: ignore[arg-type]


# --- _embed_workflow_tag tests ---


class TestEmbedWorkflowTag:
    """Tests for _embed_workflow_tag helper."""

    def test_appends_tag_to_content(self) -> None:
        """Workflow tag is appended on new line after content."""
        result = _embed_workflow_tag(
            "Story content here.",
            "implement_verify_close",
        )
        assert result == (
            "Story content here."
            "\n\n{implement_verify_close}"
        )

    def test_strips_trailing_whitespace(self) -> None:
        """Trailing whitespace in content is stripped before tag."""
        result = _embed_workflow_tag(
            "Story content here.  \n\n",
            "implement_close",
        )
        assert result == (
            "Story content here."
            "\n\n{implement_close}"
        )

    def test_empty_content(self) -> None:
        """Empty content still gets tag appended."""
        result = _embed_workflow_tag(
            "",
            "implement_close",
        )
        assert result == "\n\n{implement_close}"

    def test_content_with_existing_tag(self) -> None:
        """Does NOT check for duplicates -- always appends."""
        content = (
            "Story content.\n\n"
            "{implement_close}"
        )
        result = _embed_workflow_tag(
            content, "implement_close",
        )
        # Should have TWO tags (no dedup)
        assert result.count("{implement_close}") == 2

    def test_multiline_content(self) -> None:
        """Multi-line content preserves internal structure."""
        content = "Line 1\nLine 2\n\nLine 4"
        result = _embed_workflow_tag(
            content, "verify",
        )
        assert result == (
            "Line 1\nLine 2\n\nLine 4"
            "\n\n{verify}"
        )


# --- _validate_workflow_name tests ---


class TestValidateWorkflowName:
    """Tests for _validate_workflow_name helper."""

    def test_valid_implement_close(self) -> None:
        """implement_close is a valid workflow name."""
        result = _validate_workflow_name("implement_close")
        assert isinstance(result, Success)
        assert result.unwrap() == "implement_close"

    def test_valid_implement_verify_close(self) -> None:
        """implement_verify_close is a valid workflow name."""
        result = _validate_workflow_name(
            "implement_verify_close",
        )
        assert isinstance(result, Success)
        assert result.unwrap() == "implement_verify_close"

    def test_valid_convert_stories_to_beads(self) -> None:
        """convert_stories_to_beads is a valid workflow name."""
        result = _validate_workflow_name(
            "convert_stories_to_beads",
        )
        assert isinstance(result, Success)

    def test_valid_sample(self) -> None:
        """sample is a valid workflow name."""
        result = _validate_workflow_name("sample")
        assert isinstance(result, Success)

    def test_valid_verify(self) -> None:
        """verify is a valid workflow name."""
        result = _validate_workflow_name("verify")
        assert isinstance(result, Success)

    def test_all_registry_names_valid(self) -> None:
        """All WorkflowName constants pass validation."""
        all_names = [
            WorkflowName.IMPLEMENT_CLOSE,
            WorkflowName.IMPLEMENT_VERIFY_CLOSE,
            WorkflowName.CONVERT_STORIES_TO_BEADS,
            WorkflowName.SAMPLE,
            WorkflowName.VERIFY,
        ]
        for name in all_names:
            result = _validate_workflow_name(name)
            assert isinstance(result, Success), (
                f"Expected {name} to be valid"
            )

    def test_invalid_name(self) -> None:
        """Invalid workflow name returns Failure."""
        result = _validate_workflow_name(
            "nonexistent_workflow",
        )
        assert isinstance(result, Failure)
        error = result.failure()
        assert error.error_type == "InvalidWorkflowNameError"
        assert error.step_name == "create_beads_issue"
        assert "nonexistent_workflow" in error.message
        assert "valid_names" in error.context

    def test_empty_string(self) -> None:
        """Empty string returns Failure."""
        result = _validate_workflow_name("")
        assert isinstance(result, Failure)
        error = result.failure()
        assert error.error_type == "InvalidWorkflowNameError"


# --- _get_valid_workflow_names tests ---


class TestGetValidWorkflowNames:
    """Tests for _get_valid_workflow_names helper."""

    def test_returns_frozenset(self) -> None:
        """Returns a frozenset of workflow names."""
        names = _get_valid_workflow_names()
        assert isinstance(names, frozenset)
        assert len(names) == 5

    def test_contains_all_constants(self) -> None:
        """Contains all WorkflowName constants."""
        names = _get_valid_workflow_names()
        assert WorkflowName.IMPLEMENT_CLOSE in names
        assert WorkflowName.IMPLEMENT_VERIFY_CLOSE in names
        assert WorkflowName.CONVERT_STORIES_TO_BEADS in names
        assert WorkflowName.SAMPLE in names
        assert WorkflowName.VERIFY in names


# --- create_beads_issue step function tests ---


class TestCreateBeadsIssue:
    """Tests for create_beads_issue step function."""

    def test_success(
        self, mocker: MockerFixture,
    ) -> None:
        """Successful creation returns IOSuccess with issue ID."""
        mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("ISSUE-42"),
        )
        story = _make_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_verify_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["beads_issue_id"] == "ISSUE-42"
        # current_story is NOT re-output; it flows via
        # engine promote_outputs_to_inputs to avoid collision
        assert "current_story" not in out.outputs

    def test_missing_current_story(self) -> None:
        """Returns IOFailure when current_story is missing."""
        ctx = WorkflowContext(
            inputs={
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "create_beads_issue"
        assert "current_story" in error.message

    def test_missing_workflow_name(self) -> None:
        """Returns IOFailure when workflow_name is missing."""
        story = _make_story()
        ctx = WorkflowContext(
            inputs={"current_story": story},
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert "workflow_name" in error.message

    def test_invalid_workflow_name(self) -> None:
        """Returns IOFailure when workflow_name is invalid."""
        story = _make_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "bogus_workflow",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "InvalidWorkflowNameError"

    def test_current_story_not_bmad_story(self) -> None:
        """Returns IOFailure when current_story is not BmadStory."""
        ctx = WorkflowContext(
            inputs={
                "current_story": {"title": "Not a BmadStory"},
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert "BmadStory" in error.message

    def test_current_story_is_string(self) -> None:
        """Returns IOFailure when current_story is a string."""
        ctx = WorkflowContext(
            inputs={
                "current_story": "just a string",
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"

    def test_io_ops_failure_propagates(
        self, mocker: MockerFixture,
    ) -> None:
        """IOFailure from io_ops.run_beads_create propagates."""
        create_err = PipelineError(
            step_name="io_ops.run_beads_create",
            error_type="BeadsCreateError",
            message="bd create failed",
        )
        mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOFailure(create_err),
        )
        story = _make_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error is create_err

    def test_description_contains_workflow_tag(
        self, mocker: MockerFixture,
    ) -> None:
        """Description passed to run_beads_create contains tag."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("ISSUE-99"),
        )
        story = _make_story(
            raw_content="Full story content here.",
        )
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_verify_close",
            },
        )
        create_beads_issue(ctx)
        call_args = mock_create.call_args
        description = call_args[0][1]
        assert "{implement_verify_close}" in description
        assert "Full story content here." in description

    def test_title_format(
        self, mocker: MockerFixture,
    ) -> None:
        """Title uses 'Story N.M: Title' format."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("ISSUE-1"),
        )
        story = _make_story(
            epic_number=6,
            story_number=2,
            title="Beads Issue Creator with Workflow Tags",
        )
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_close",
            },
        )
        create_beads_issue(ctx)
        call_args = mock_create.call_args
        title = call_args[0][0]
        assert title == (
            "Story 6.2: Beads Issue Creator"
            " with Workflow Tags"
        )

    def test_empty_raw_content(
        self, mocker: MockerFixture,
    ) -> None:
        """Empty raw_content still succeeds with just tag."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("ISSUE-E"),
        )
        story = _make_story(raw_content="")
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOSuccess)
        description = mock_create.call_args[0][1]
        assert "{implement_close}" in description

    def test_special_characters_in_title(
        self, mocker: MockerFixture,
    ) -> None:
        """Special characters in title are passed through."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("ISSUE-S"),
        )
        story = _make_story(
            title='Build & Test "Complex" Story',
        )
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOSuccess)
        title = mock_create.call_args[0][0]
        assert "&" in title
        assert '"' in title

    def test_workflow_name_empty_string(self) -> None:
        """Empty workflow_name returns MissingInputError."""
        story = _make_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"

    def test_workflow_name_not_string(self) -> None:
        """Non-string workflow_name returns MissingInputError."""
        story = _make_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": 42,
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"

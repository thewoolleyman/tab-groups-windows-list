"""Tests for write_beads_id step (Story 6.3).

Tests for _inject_beads_id, _has_beads_id, and write_beads_id step.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.write_beads_id import (
    _has_beads_id,
    _inject_beads_id,
    write_beads_id,
)
from adws.adw_modules.types import BmadStory, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- _inject_beads_id tests ---


class TestInjectBeadsId:
    """Tests for _inject_beads_id helper."""

    def test_adds_to_existing_front_matter(self) -> None:
        """Adds beads_id to existing front matter."""
        content = "---\nstatus: ready-for-dev\n---\n\n#### Story 6.1\ncontent"
        result = _inject_beads_id(content, "ISSUE-42")
        assert "beads_id: ISSUE-42" in result
        assert "status: ready-for-dev" in result
        assert result.startswith("---\n")
        assert "#### Story 6.1\ncontent" in result

    def test_prepends_front_matter_when_none(self) -> None:
        """Prepends front matter when none exists."""
        content = "#### Story 6.1: BMAD Markdown Parser\n...story content..."
        result = _inject_beads_id(content, "ISSUE-42")
        assert result.startswith("---\nbeads_id: ISSUE-42\n---\n")
        assert "#### Story 6.1: BMAD Markdown Parser" in result
        assert "...story content..." in result

    def test_replaces_existing_beads_id(self) -> None:
        """Replaces existing beads_id value."""
        content = "---\nstatus: ready-for-dev\nbeads_id: OLD-ID\n---\n\ncontent"
        result = _inject_beads_id(content, "ISSUE-42")
        assert "beads_id: ISSUE-42" in result
        assert "OLD-ID" not in result
        assert "status: ready-for-dev" in result

    def test_preserves_other_fields(self) -> None:
        """Preserves all other front matter fields."""
        content = (
            "---\n"
            "status: ready-for-dev\n"
            "stepsCompleted: 3\n"
            "priority: high\n"
            "---\n\n"
            "#### Story 6.1\ncontent"
        )
        result = _inject_beads_id(content, "ISSUE-42")
        assert "status: ready-for-dev" in result
        assert "stepsCompleted: 3" in result
        assert "priority: high" in result
        assert "beads_id: ISSUE-42" in result

    def test_empty_content(self) -> None:
        """Handles empty string content."""
        result = _inject_beads_id("", "ISSUE-42")
        assert result == "---\nbeads_id: ISSUE-42\n---\n"

    def test_body_contains_triple_dash(self) -> None:
        """Does not modify in-body --- separators."""
        content = (
            "---\nstatus: dev\n---\n\n"
            "Some content\n---\nMore content after dash"
        )
        result = _inject_beads_id(content, "ISSUE-42")
        assert "beads_id: ISSUE-42" in result
        assert "Some content\n---\nMore content after dash" in result

    def test_front_matter_only_beads_id(self) -> None:
        """Front matter with only beads_id to replace."""
        content = "---\nbeads_id: OLD\n---\n\ncontent"
        result = _inject_beads_id(content, "NEW-42")
        assert "beads_id: NEW-42" in result
        assert "OLD" not in result

    def test_unclosed_front_matter(self) -> None:
        """Prepends new front matter when --- starts but never closes."""
        content = "---\nstatus: dev\nno closing dashes"
        result = _inject_beads_id(content, "ISSUE-42")
        assert result.startswith("---\nbeads_id: ISSUE-42\n---\n")
        assert content in result


# --- _has_beads_id tests ---


class TestHasBeadsId:
    """Tests for _has_beads_id helper."""

    def test_returns_true_when_present(self) -> None:
        """Returns True when beads_id in front matter."""
        content = "---\nbeads_id: ISSUE-42\n---\n\ncontent"
        assert _has_beads_id(content) is True

    def test_returns_false_when_absent(self) -> None:
        """Returns False when front matter has no beads_id."""
        content = "---\nstatus: dev\n---\n\ncontent"
        assert _has_beads_id(content) is False

    def test_returns_false_no_front_matter(self) -> None:
        """Returns False when no front matter exists."""
        content = "#### Story 6.1\ncontent"
        assert _has_beads_id(content) is False

    def test_returns_false_empty_string(self) -> None:
        """Returns False for empty string."""
        assert _has_beads_id("") is False

    def test_beads_id_in_body_not_front_matter(self) -> None:
        """Returns False when beads_id is only in body, not front matter."""
        content = "---\nstatus: dev\n---\n\nbeads_id: ISSUE-42"
        assert _has_beads_id(content) is False

    def test_unclosed_front_matter(self) -> None:
        """Returns False when front matter starts but never closes."""
        content = "---\nbeads_id: ISSUE-42\nno closing"
        assert _has_beads_id(content) is False


# --- write_beads_id step tests ---


class TestWriteBeadsId:
    """Tests for write_beads_id step function."""

    def test_success(self, mocker: MockerFixture) -> None:
        """Writes beads_id to file and returns success."""
        story = BmadStory(
            epic_number=6,
            story_number=1,
            title="BMAD Markdown Parser",
            slug="6-1-bmad-markdown-parser",
            user_story="As a dev",
            acceptance_criteria="Given X",
            raw_content="#### Story 6.1",
        )
        file_content = "---\nstatus: dev\n---\n\n#### Story 6.1"
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(file_content),
        )
        mock_write = mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.write_bmad_file",
            return_value=IOSuccess(None),
        )
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "current_story": story,
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["beads_id_written"] is True
        assert out.outputs["story_slug"] == "6-1-bmad-markdown-parser"
        mock_write.assert_called_once()
        written = mock_write.call_args[0][1]
        assert "beads_id: ISSUE-42" in written

    def test_missing_beads_issue_id(self) -> None:
        """Returns IOFailure when beads_issue_id missing."""
        ctx = WorkflowContext(
            inputs={
                "current_story": BmadStory(
                    epic_number=1, story_number=1,
                    title="T", slug="s",
                    user_story="u", acceptance_criteria="a",
                ),
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "write_beads_id"

    def test_missing_current_story(self) -> None:
        """Returns IOFailure when current_story missing."""
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "write_beads_id"

    def test_current_story_wrong_type(self) -> None:
        """Returns IOFailure when current_story is not BmadStory."""
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "current_story": "not a story",
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"

    def test_missing_bmad_file_path(self) -> None:
        """Returns IOFailure when bmad_file_path missing."""
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "current_story": BmadStory(
                    epic_number=1, story_number=1,
                    title="T", slug="s",
                    user_story="u", acceptance_criteria="a",
                ),
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "write_beads_id"

    def test_read_failure_propagates(
        self, mocker: MockerFixture,
    ) -> None:
        """IOFailure from read_bmad_file propagates."""
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.read_bmad_file",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.read_bmad_file",
                    error_type="FileNotFoundError",
                    message="not found",
                ),
            ),
        )
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "current_story": BmadStory(
                    epic_number=1, story_number=1,
                    title="T", slug="s",
                    user_story="u", acceptance_criteria="a",
                ),
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "FileNotFoundError"

    def test_write_failure_propagates(
        self, mocker: MockerFixture,
    ) -> None:
        """IOFailure from write_bmad_file propagates."""
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess("---\nstatus: dev\n---\n\ncontent"),
        )
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.write_bmad_file",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.write_bmad_file",
                    error_type="PermissionError",
                    message="denied",
                ),
            ),
        )
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "current_story": BmadStory(
                    epic_number=1, story_number=1,
                    title="T", slug="s",
                    user_story="u", acceptance_criteria="a",
                ),
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "PermissionError"

    def test_idempotent_skip(
        self, mocker: MockerFixture,
    ) -> None:
        """Skips write when file already has beads_id."""
        file_content = "---\nbeads_id: ISSUE-42\n---\n\ncontent"
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(file_content),
        )
        mock_write = mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.write_bmad_file",
        )
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-42",
                "current_story": BmadStory(
                    epic_number=1, story_number=1,
                    title="T", slug="s",
                    user_story="u", acceptance_criteria="a",
                ),
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["beads_id_written"] is False
        assert out.outputs["skipped_reason"] == "already_has_beads_id"
        mock_write.assert_not_called()

    def test_special_chars_in_slug(
        self, mocker: MockerFixture,
    ) -> None:
        """Handles story slug with special characters."""
        story = BmadStory(
            epic_number=6,
            story_number=3,
            title="Bidirectional Tracking & Convert",
            slug="6-3-bidirectional-tracking-convert",
            user_story="As a dev",
            acceptance_criteria="Given X",
            raw_content="#### Story 6.3",
        )
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess("---\nstatus: dev\n---\n\ncontent"),
        )
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.write_bmad_file",
            return_value=IOSuccess(None),
        )
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "ISSUE-99",
                "current_story": story,
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["story_slug"] == "6-3-bidirectional-tracking-convert"
        assert out.outputs["beads_id_written"] is True

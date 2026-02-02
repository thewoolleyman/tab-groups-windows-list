"""Tests for convert_stories_orchestrator step (Story 6.3).

Tests orchestrator iteration, idempotency, partial failure,
and progress tracking.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.convert_stories_orchestrator import (
    convert_stories_orchestrator,
)
from adws.adw_modules.types import BmadStory, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _make_story(
    epic: int,
    num: int,
    title: str,
) -> BmadStory:
    """Create a BmadStory for testing."""
    slug = f"{epic}-{num}-{title.lower().replace(' ', '-')}"
    return BmadStory(
        epic_number=epic,
        story_number=num,
        title=title,
        slug=slug,
        user_story=f"As a dev, I want {title}.",
        acceptance_criteria=f"Given {title} When X Then Y",
        frs_covered=["FR1"],
        raw_content=f"#### Story {epic}.{num}: {title}\n\nContent",
    )


class TestConvertStoriesOrchestrator:
    """Tests for convert_stories_orchestrator step."""

    def test_success_two_stories(
        self, mocker: MockerFixture,
    ) -> None:
        """Creates issues for 2 stories, returns conversion_results."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
            side_effect=[
                IOSuccess("ISSUE-1"),
                IOSuccess("ISSUE-2"),
            ],
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.write_bmad_file",
            return_value=IOSuccess(None),
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        results = out.outputs["conversion_results"]
        assert len(results) == 2
        assert results[0]["status"] == "created"
        assert results[0]["beads_issue_id"] == "ISSUE-1"
        assert results[1]["status"] == "created"
        assert results[1]["beads_issue_id"] == "ISSUE-2"
        summary = out.outputs["summary"]
        assert summary["total"] == 2
        assert summary["created"] == 2
        assert summary["skipped"] == 0
        assert summary["failed"] == 0

    def test_idempotent_skip(
        self, mocker: MockerFixture,
    ) -> None:
        """Skips all stories when file already has beads_id."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
        ]
        # File already has beads_id -- all stories skipped
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nbeads_id: EXISTING-1\n---\n\ncontent",
            ),
        )
        mock_create = mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        results = out.outputs["conversion_results"]
        assert len(results) == 2
        assert results[0]["status"] == "skipped"
        assert results[0]["reason"] == "already_has_beads_id"
        assert results[1]["status"] == "skipped"
        assert results[1]["reason"] == "already_has_beads_id"
        mock_create.assert_not_called()
        summary = out.outputs["summary"]
        assert summary["skipped"] == 2
        assert summary["created"] == 0

    def test_partial_failure(
        self, mocker: MockerFixture,
    ) -> None:
        """One story fails, others continue."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
            _make_story(6, 3, "Tracker"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
            side_effect=[
                IOSuccess("ISSUE-1"),
                IOFailure(
                    PipelineError(
                        step_name="io_ops.run_beads_create",
                        error_type="BeadsCreateError",
                        message="bd create failed: timeout",
                    ),
                ),
                IOSuccess("ISSUE-3"),
            ],
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.write_bmad_file",
            return_value=IOSuccess(None),
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        results = out.outputs["conversion_results"]
        assert results[0]["status"] == "created"
        assert results[1]["status"] == "failed"
        assert "error" in results[1]
        assert results[2]["status"] == "created"
        summary = out.outputs["summary"]
        assert summary["created"] == 2
        assert summary["failed"] == 1

    def test_all_fail(
        self, mocker: MockerFixture,
    ) -> None:
        """All stories fail, step returns IOSuccess with all failed."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_beads_create",
                    error_type="BeadsCreateError",
                    message="bd create failed",
                ),
            ),
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        results = out.outputs["conversion_results"]
        assert all(r["status"] == "failed" for r in results)
        summary = out.outputs["summary"]
        assert summary["failed"] == 2
        assert summary["created"] == 0

    def test_empty_stories_list(
        self, mocker: MockerFixture,
    ) -> None:
        """Empty parsed_stories returns empty results."""
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": [],
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["conversion_results"] == []
        summary = out.outputs["summary"]
        assert summary["total"] == 0

    def test_missing_parsed_stories(self) -> None:
        """Missing parsed_stories returns IOFailure."""
        ctx = WorkflowContext(
            inputs={
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "convert_stories_orchestrator"

    def test_missing_workflow_name(self) -> None:
        """Missing workflow_name returns IOFailure."""
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": [],
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "convert_stories_orchestrator"

    def test_summary_counts(
        self, mocker: MockerFixture,
    ) -> None:
        """Summary has total, created, skipped, failed counts."""
        stories = [
            _make_story(6, 1, "Parser"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("ISSUE-1"),
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.write_bmad_file",
            return_value=IOSuccess(None),
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        summary = out.outputs["summary"]
        assert "total" in summary
        assert "created" in summary
        assert "skipped" in summary
        assert "failed" in summary
        assert summary["total"] == 1
        assert summary["created"] == 1

    def test_write_failure_marks_story_failed(
        self, mocker: MockerFixture,
    ) -> None:
        """Write failure marks story failed but preserves issue_id."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
            side_effect=[
                IOSuccess("ISSUE-1"),
                IOSuccess("ISSUE-2"),
            ],
        )
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.write_bmad_file",
            side_effect=[
                IOFailure(
                    PipelineError(
                        step_name="io_ops.write_bmad_file",
                        error_type="PermissionError",
                        message="denied",
                    ),
                ),
                IOSuccess(None),
            ],
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        results = out.outputs["conversion_results"]
        assert results[0]["status"] == "failed"
        # ISSUE 2 fix: preserve issue_id on write failure
        assert results[0]["beads_issue_id"] == "ISSUE-1"
        assert "writeback failed" in str(results[0]["error"])
        assert results[1]["status"] == "created"

    def test_read_failure_returns_iofailure(
        self, mocker: MockerFixture,
    ) -> None:
        """Read failure at file level returns IOFailure."""
        stories = [
            _make_story(6, 1, "Parser"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
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
                "parsed_stories": stories,
                "workflow_name": "implement_verify_close",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "FileNotFoundError"
        assert (
            error.step_name
            == "convert_stories_orchestrator"
        )

    def test_missing_bmad_file_path(self) -> None:
        """Missing bmad_file_path returns IOFailure."""
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": [],
                "workflow_name": "implement_verify_close",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "convert_stories_orchestrator"

    def test_invalid_workflow_name_marks_failed(
        self, mocker: MockerFixture,
    ) -> None:
        """Invalid workflow name marks stories as failed."""
        stories = [_make_story(6, 1, "Parser")]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nstatus: dev\n---\n\ncontent",
            ),
        )
        mock_create = mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
        )
        ctx = WorkflowContext(
            inputs={
                "parsed_stories": stories,
                "workflow_name": "invalid_workflow",
                "bmad_file_path": "epics.md",
            },
        )
        result = convert_stories_orchestrator(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        results = out.outputs["conversion_results"]
        assert results[0]["status"] == "failed"
        assert "invalid" in str(results[0]["error"]).lower()
        mock_create.assert_not_called()
        summary = out.outputs["summary"]
        assert summary["failed"] == 1

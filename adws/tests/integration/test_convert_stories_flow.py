"""Integration tests for the full convert_stories_to_beads flow (Story 6.3).

Tests the complete conversion pipeline: parse BMAD -> iterate stories
-> create issues -> write beads_ids, using realistic data and mocked I/O.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.convert_stories_orchestrator import (
    convert_stories_orchestrator,
)
from adws.adw_modules.steps.write_beads_id import (
    _has_beads_id,
    _inject_beads_id,
    write_beads_id,
)
from adws.adw_modules.types import BmadStory, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _make_story(
    epic: int,
    num: int,
    title: str,
) -> BmadStory:
    """Create a realistic BmadStory for integration tests."""
    slug = f"{epic}-{num}-{title.lower().replace(' ', '-')}"
    return BmadStory(
        epic_number=epic,
        story_number=num,
        title=title,
        slug=slug,
        user_story=f"As a dev, I want {title}.",
        acceptance_criteria=f"Given {title} When X Then Y",
        frs_covered=["FR1"],
        raw_content=(
            f"#### Story {epic}.{num}: {title}\n\n"
            f"As a dev, I want {title}.\n\n"
            f"**Acceptance Criteria:**\n\n"
            f"Given {title} When X Then Y"
        ),
    )


class TestFullConvertFlow:
    """Integration tests for the full conversion pipeline."""

    def test_full_flow_three_stories(
        self, mocker: MockerFixture,
    ) -> None:
        """Full flow: parse -> create 3 issues -> write beads_ids."""
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
        mock_create = mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.run_beads_create",
            side_effect=[
                IOSuccess("BEADS-1"),
                IOSuccess("BEADS-2"),
                IOSuccess("BEADS-3"),
            ],
        )
        mock_write = mocker.patch(
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
        assert len(results) == 3
        for i, r in enumerate(results, start=1):
            assert r["status"] == "created"
            assert r["beads_issue_id"] == f"BEADS-{i}"

        # Verify bd create was called 3 times
        assert mock_create.call_count == 3

        # Verify write_bmad_file was called 3 times
        assert mock_write.call_count == 3

        # Verify workflow tags were embedded in descriptions
        for call in mock_create.call_args_list:
            description = call[0][1]
            assert "{implement_verify_close}" in description

        summary = out.outputs["summary"]
        assert summary["total"] == 3
        assert summary["created"] == 3

    def test_idempotent_rerun_all_skipped(
        self, mocker: MockerFixture,
    ) -> None:
        """Second run with beads_ids already present skips all stories."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
        ]
        mocker.patch(
            "adws.adw_modules.steps.convert_stories_orchestrator"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "---\nbeads_id: EXISTING\n---\n\ncontent",
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
        assert all(r["status"] == "skipped" for r in results)
        mock_create.assert_not_called()
        summary = out.outputs["summary"]
        assert summary["skipped"] == 2
        assert summary["created"] == 0
        assert summary["failed"] == 0

    def test_mixed_results(
        self, mocker: MockerFixture,
    ) -> None:
        """3 stories: 2 succeed, 1 fails at create."""
        stories = [
            _make_story(6, 1, "Parser"),
            _make_story(6, 2, "Creator"),
            _make_story(6, 3, "Tracker"),
        ]
        # File has no beads_id -- all stories processed
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
                IOSuccess("BEADS-1"),
                IOFailure(
                    PipelineError(
                        step_name="io_ops.run_beads_create",
                        error_type="BeadsCreateError",
                        message="bd create failed",
                    ),
                ),
                IOSuccess("BEADS-3"),
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
        assert results[0]["beads_issue_id"] == "BEADS-1"
        assert results[1]["status"] == "failed"
        assert results[2]["status"] == "created"
        assert results[2]["beads_issue_id"] == "BEADS-3"
        summary = out.outputs["summary"]
        assert summary["created"] == 2
        assert summary["failed"] == 1

    def test_inject_beads_id_preserves_body_dashes(
        self,
    ) -> None:
        """_inject_beads_id with --- in body preserves body content."""
        content = (
            "---\nstatus: dev\n---\n\n"
            "Some content\n\n---\n\nMore content\n"
            "Another ---\nfinal"
        )
        result = _inject_beads_id(content, "BEADS-42")
        assert "beads_id: BEADS-42" in result
        assert "Some content" in result
        assert "More content" in result
        assert "Another ---" in result

    def test_write_beads_id_step_integration(
        self, mocker: MockerFixture,
    ) -> None:
        """write_beads_id step reads, injects, writes correctly."""
        story = _make_story(6, 1, "Parser")
        original_content = (
            "---\nstatus: ready-for-dev\n---\n\n"
            "#### Story 6.1: Parser\n"
            "Content here"
        )
        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(original_content),
        )
        written_content: list[str] = []

        def _capture_write(
            _path: str, content: str,
        ) -> IOResult[None, PipelineError]:
            written_content.append(content)
            return IOSuccess(None)

        mocker.patch(
            "adws.adw_modules.steps.write_beads_id"
            ".io_ops.write_bmad_file",
            side_effect=_capture_write,
        )
        ctx = WorkflowContext(
            inputs={
                "beads_issue_id": "BEADS-99",
                "current_story": story,
                "bmad_file_path": "epics.md",
            },
        )
        result = write_beads_id(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["beads_id_written"] is True

        # Verify the written content
        assert len(written_content) == 1
        final = written_content[0]
        assert "beads_id: BEADS-99" in final
        assert "status: ready-for-dev" in final
        assert "#### Story 6.1: Parser" in final
        assert _has_beads_id(final) is True

    def test_command_entry_point_integration(
        self, mocker: MockerFixture,
    ) -> None:
        """run_convert_stories_command builds correct context."""
        from adws.adw_modules.commands.convert_stories import (  # noqa: PLC0415
            run_convert_stories_command,
        )
        from adws.adw_modules.engine.types import (  # noqa: PLC0415
            Step,
            Workflow,
        )

        mock_wf = Workflow(
            name="convert_stories_to_beads",
            description="test",
            dispatchable=False,
            steps=[
                Step(
                    name="p",
                    function="parse_bmad_story",
                ),
            ],
        )
        mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.load_command_workflow",
            return_value=IOSuccess(mock_wf),
        )
        result_ctx = WorkflowContext(
            outputs={
                "conversion_results": [],
                "summary": {
                    "total": 0,
                    "created": 0,
                    "skipped": 0,
                    "failed": 0,
                },
            },
        )
        mock_exec = mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.execute_command_workflow",
            return_value=IOSuccess(result_ctx),
        )

        result = run_convert_stories_command(
            "my/epics.md",
            "implement_verify_close",
        )
        assert isinstance(result, IOSuccess)

        # Verify correct context was passed
        exec_ctx = mock_exec.call_args[0][1]
        assert exec_ctx.inputs["bmad_file_path"] == "my/epics.md"
        assert (
            exec_ctx.inputs["workflow_name"]
            == "implement_verify_close"
        )

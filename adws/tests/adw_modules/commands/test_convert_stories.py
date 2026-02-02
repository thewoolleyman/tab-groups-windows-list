"""Tests for convert_stories command (Story 6.3).

Tests for run_convert_stories_command entry point.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.commands.convert_stories import (
    run_convert_stories_command,
)
from adws.adw_modules.engine.types import Step, Workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestRunConvertStoriesCommand:
    """Tests for run_convert_stories_command."""

    def test_success(
        self, mocker: MockerFixture,
    ) -> None:
        """Loads workflow, executes, returns IOSuccess."""
        mock_wf = Workflow(
            name="convert_stories_to_beads",
            description="test",
            dispatchable=False,
            steps=[
                Step(
                    name="parse_bmad_story",
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
            outputs={"conversion_results": []},
        )
        mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.execute_command_workflow",
            return_value=IOSuccess(result_ctx),
        )

        result = run_convert_stories_command(
            "epics.md", "implement_verify_close",
        )
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert out.outputs["conversion_results"] == []

    def test_workflow_load_fails(
        self, mocker: MockerFixture,
    ) -> None:
        """Propagates IOFailure from workflow load."""
        mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.load_command_workflow",
            return_value=IOFailure(
                PipelineError(
                    step_name=(
                        "io_ops.load_command_workflow"
                    ),
                    error_type="WorkflowNotFoundError",
                    message="not found",
                ),
            ),
        )
        result = run_convert_stories_command(
            "epics.md", "implement_verify_close",
        )
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "WorkflowNotFoundError"

    def test_workflow_execution_fails(
        self, mocker: MockerFixture,
    ) -> None:
        """Propagates IOFailure from workflow execution."""
        mock_wf = Workflow(
            name="convert_stories_to_beads",
            description="test",
            dispatchable=False,
            steps=[],
        )
        mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.load_command_workflow",
            return_value=IOSuccess(mock_wf),
        )
        mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.execute_command_workflow",
            return_value=IOFailure(
                PipelineError(
                    step_name="executor",
                    error_type="StepError",
                    message="step failed",
                ),
            ),
        )
        result = run_convert_stories_command(
            "epics.md", "implement_verify_close",
        )
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "StepError"

    def test_passes_correct_inputs(
        self, mocker: MockerFixture,
    ) -> None:
        """Passes bmad_file_path and workflow_name as inputs."""
        mock_wf = Workflow(
            name="convert_stories_to_beads",
            description="test",
            dispatchable=False,
            steps=[],
        )
        mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.load_command_workflow",
            return_value=IOSuccess(mock_wf),
        )
        mock_exec = mocker.patch(
            "adws.adw_modules.commands.convert_stories"
            ".io_ops.execute_command_workflow",
            return_value=IOSuccess(WorkflowContext()),
        )
        run_convert_stories_command(
            "my/epics.md", "implement_close",
        )
        call_args = mock_exec.call_args
        ctx = call_args[0][1]
        assert ctx.inputs["bmad_file_path"] == "my/epics.md"
        assert ctx.inputs["workflow_name"] == "implement_close"

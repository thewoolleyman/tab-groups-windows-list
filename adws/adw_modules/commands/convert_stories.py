"""Convert stories command -- /convert-stories-to-beads (FR23).

Orchestrates the full BMAD-to-Beads conversion flow: parse BMAD
markdown, create Beads issues, embed workflow tags, write beads_id
back to source files.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from adws.adw_modules import io_ops
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from returns.io import IOResult

    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.errors import PipelineError


def run_convert_stories_command(
    bmad_file_path: str,
    workflow_name: str,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute /convert-stories-to-beads command (FR23).

    Loads the convert_stories_to_beads workflow and executes
    it with the provided bmad_file_path and workflow_name.
    """
    ctx = WorkflowContext(
        inputs={
            "bmad_file_path": bmad_file_path,
            "workflow_name": workflow_name,
        },
    )

    load_result = io_ops.load_command_workflow(
        "convert_stories_to_beads",
    )

    def _execute_workflow(
        workflow: Workflow,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return io_ops.execute_command_workflow(
            workflow, ctx,
        )

    return load_result.bind(_execute_workflow)

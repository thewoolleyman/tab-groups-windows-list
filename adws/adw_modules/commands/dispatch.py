"""Command dispatch -- central entry point for all commands (FR28).

Routes command names to their associated workflows via the
command registry. Uses io_ops boundary for workflow loading
and execution.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult

from adws.adw_modules import io_ops
from adws.adw_modules.commands.registry import (
    get_command,
    list_commands,
)
from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.types import WorkflowContext


def run_command(
    name: str,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch a command by name.

    Workflow-backed commands load and execute the associated
    workflow. Non-workflow commands return an IOFailure
    indicating custom logic is needed (added in later stories).
    Unknown commands return an IOFailure with available names.
    """
    spec = get_command(name)
    if spec is None:
        available = sorted(
            cmd.name for cmd in list_commands()
        )
        return IOFailure(
            PipelineError(
                step_name="commands.dispatch",
                error_type="UnknownCommandError",
                message=(
                    f"Unknown command '{name}'."
                    f" Available: {available}"
                ),
                context={
                    "command_name": name,
                    "available": available,
                },
            ),
        )

    if spec.workflow_name is None:
        return IOFailure(
            PipelineError(
                step_name="commands.dispatch",
                error_type="NoWorkflowError",
                message=(
                    f"Command '{name}' does not have an"
                    f" associated workflow"
                ),
                context={"command_name": name},
            ),
        )

    load_result = io_ops.load_command_workflow(
        spec.workflow_name,
    )

    def _execute_workflow(
        workflow: Workflow,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return io_ops.execute_command_workflow(
            workflow, ctx,
        )

    return load_result.bind(_execute_workflow)

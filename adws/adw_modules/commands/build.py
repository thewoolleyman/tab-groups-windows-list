"""Build command -- /build fast-track workflow (FR32).

Executes the implement_close workflow for trivial changes.
Handles Beads finalize: close on success, tag failure on
failure. TDD-exempt; 100% coverage is the safety net.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from returns.io import IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.commands._finalize import (
    finalize_on_failure,
    finalize_on_success,
)

if TYPE_CHECKING:
    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.errors import PipelineError
    from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class BuildCommandResult:
    """User-facing output of the /build command.

    success: True when workflow succeeded, False otherwise.
    workflow_executed: Name of the workflow that ran.
    issue_id: Beads issue ID if provided, None otherwise.
    finalize_action: "closed", "tagged_failure", or
    "skipped".
    summary: Human-readable one-line summary.
    """

    success: bool
    workflow_executed: str
    issue_id: str | None
    finalize_action: str
    summary: str


def run_build_command(
    ctx: WorkflowContext,
) -> IOResult[BuildCommandResult, PipelineError]:
    """Execute /build and return structured result (FR32).

    Loads the implement_close workflow, executes it, then
    finalizes: close on success, tag failure on failure.
    IOFailure is reserved for infrastructure errors
    (workflow not found). Workflow execution failures
    produce IOSuccess(BuildCommandResult(success=False)).
    """
    issue_id_raw = ctx.inputs.get("issue_id")
    issue_id: str | None = (
        str(issue_id_raw) if issue_id_raw else None
    )

    load_result = io_ops.load_command_workflow(
        "implement_close",
    )

    def _execute_and_finalize(
        workflow: Workflow,
    ) -> IOResult[BuildCommandResult, PipelineError]:
        exec_result = io_ops.execute_command_workflow(
            workflow, ctx,
        )

        def _on_success(
            _: WorkflowContext,
        ) -> IOResult[BuildCommandResult, PipelineError]:
            fin = finalize_on_success(issue_id)

            def _wrap_success(
                action: str,
            ) -> IOResult[
                BuildCommandResult, PipelineError
            ]:
                return IOSuccess(
                    BuildCommandResult(
                        success=True,
                        workflow_executed="implement_close",
                        issue_id=issue_id,
                        finalize_action=action,
                        summary="Completed successfully",
                    ),
                )

            return fin.bind(_wrap_success)

        def _on_failure(
            err: PipelineError,
        ) -> IOResult[BuildCommandResult, PipelineError]:
            fin = finalize_on_failure(
                issue_id, err, 1,
            )

            def _wrap_failure(
                action: str,
            ) -> IOResult[
                BuildCommandResult, PipelineError
            ]:
                return IOSuccess(
                    BuildCommandResult(
                        success=False,
                        workflow_executed="implement_close",
                        issue_id=issue_id,
                        finalize_action=action,
                        summary=f"Failed: {err.message}",
                    ),
                )

            return fin.bind(_wrap_failure)

        return exec_result.bind(_on_success).lash(
            _on_failure,
        )

    return load_result.bind(_execute_and_finalize)

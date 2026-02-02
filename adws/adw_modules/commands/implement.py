"""Implement command -- /implement TDD workflow (FR28).

Executes the implement_verify_close workflow for full
TDD-enforced development: RED -> GREEN -> REFACTOR.
Reads Beads issue via bd show, passes description as
context to the TDD workflow. Handles Beads finalize:
close on success, tag failure on failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.commands._finalize import (
    finalize_on_failure as _finalize_on_failure,
)
from adws.adw_modules.commands._finalize import (
    finalize_on_success as _finalize_on_success,
)
from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class ImplementCommandResult:
    """User-facing output of the /implement command.

    success: True when workflow succeeded, False otherwise.
    workflow_executed: Name of the workflow that ran.
    issue_id: Beads issue ID if provided, None otherwise.
    finalize_action: "closed", "tagged_failure", or
    "skipped".
    summary: Human-readable one-line summary.
    tdd_phases_completed: Which TDD phases completed.
    """

    success: bool
    workflow_executed: str
    issue_id: str | None
    finalize_action: str
    summary: str
    tdd_phases_completed: list[str] = field(
        default_factory=list,
    )


def run_implement_command(
    ctx: WorkflowContext,
) -> IOResult[ImplementCommandResult, PipelineError]:
    """Execute /implement and return structured result.

    Loads the implement_verify_close workflow, reads the
    Beads issue description (if issue_id provided), executes
    the TDD workflow, and finalizes: close on success, tag
    failure on failure. IOFailure is reserved for
    infrastructure errors (workflow not found, beads read
    failure). Workflow execution failures produce
    IOSuccess(ImplementCommandResult(success=False)).
    """
    issue_id_raw = ctx.inputs.get("issue_id")
    issue_id: str | None = (
        str(issue_id_raw) if issue_id_raw else None
    )

    # Step 1: Read Beads issue description if issue_id exists
    enriched_ctx = ctx
    if issue_id:
        show_result = io_ops.run_beads_show(issue_id)
        if isinstance(show_result, IOFailure):
            from returns.unsafe import (  # noqa: PLC0415
                unsafe_perform_io,
            )

            show_err = unsafe_perform_io(
                show_result.failure(),
            )
            return IOFailure(
                PipelineError(
                    step_name=(
                        "commands.implement.beads_show"
                    ),
                    error_type="BeadsShowError",
                    message=(
                        f"Failed to read Beads issue"
                        f" {issue_id}: {show_err.message}"
                    ),
                    context={
                        "issue_id": issue_id,
                        "original_error": show_err.message,
                    },
                ),
            )

        from returns.unsafe import (  # noqa: PLC0415
            unsafe_perform_io,
        )

        description = unsafe_perform_io(
            show_result.unwrap(),
        )
        enriched_ctx = ctx.with_updates(
            inputs={
                **ctx.inputs,
                "issue_description": description,
            },
        )

    # Step 2: Load workflow
    load_result = io_ops.load_command_workflow(
        "implement_verify_close",
    )

    def _execute_and_finalize(
        workflow: Workflow,
    ) -> IOResult[
        ImplementCommandResult, PipelineError
    ]:
        exec_result = io_ops.execute_command_workflow(
            workflow, enriched_ctx,
        )

        def _on_success(
            _: WorkflowContext,
        ) -> IOResult[
            ImplementCommandResult, PipelineError
        ]:
            fin = _finalize_on_success(issue_id)

            def _wrap_success(
                action: str,
            ) -> IOResult[
                ImplementCommandResult, PipelineError
            ]:
                return IOSuccess(
                    ImplementCommandResult(
                        success=True,
                        workflow_executed=(
                            "implement_verify_close"
                        ),
                        issue_id=issue_id,
                        finalize_action=action,
                        summary="Completed successfully",
                        tdd_phases_completed=[
                            "RED",
                            "GREEN",
                            "REFACTOR",
                        ],
                    ),
                )

            return fin.bind(_wrap_success)

        def _on_failure(
            err: PipelineError,
        ) -> IOResult[
            ImplementCommandResult, PipelineError
        ]:
            fin = _finalize_on_failure(
                issue_id, err, 1,
            )

            def _wrap_failure(
                action: str,
            ) -> IOResult[
                ImplementCommandResult, PipelineError
            ]:
                return IOSuccess(
                    ImplementCommandResult(
                        success=False,
                        workflow_executed=(
                            "implement_verify_close"
                        ),
                        issue_id=issue_id,
                        finalize_action=action,
                        summary=(
                            f"Failed: {err.message}"
                        ),
                        tdd_phases_completed=[],
                    ),
                )

            return fin.bind(_wrap_failure)

        return exec_result.bind(_on_success).lash(
            _on_failure,
        )

    return load_result.bind(_execute_and_finalize)

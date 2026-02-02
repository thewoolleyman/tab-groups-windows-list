"""Build command -- /build fast-track workflow (FR32).

Executes the implement_close workflow for trivial changes.
Handles Beads finalize: close on success, tag failure on
failure. TDD-exempt; 100% coverage is the safety net.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from returns.io import IOResult, IOSuccess

from adws.adw_modules import io_ops

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


def _build_failure_metadata(
    error: PipelineError,
    attempt_count: int,
) -> str:
    """Build structured failure metadata string (AC #4).

    Format: ADWS_FAILED|attempt=N|last_failure=ISO|
    error_class=X|step=Y|summary=Z

    Pipe characters in the summary are escaped as backslash
    pipe to prevent field boundary confusion during parsing.
    Attempt count is 1-indexed for human readability.
    """
    ts = datetime.now(tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )
    # 1-indexed: attempt_count=0 means first attempt
    attempt = max(attempt_count, 1)
    escaped_msg = error.message.replace("|", "\\|")
    return (
        f"ADWS_FAILED"
        f"|attempt={attempt}"
        f"|last_failure={ts}"
        f"|error_class={error.error_type}"
        f"|step={error.step_name}"
        f"|summary={escaped_msg}"
    )


def _finalize_on_success(
    issue_id: str | None,
) -> IOResult[str, PipelineError]:
    """Finalize on workflow success -- close Beads issue.

    Returns IOSuccess("closed") on success,
    IOSuccess("close_failed") if bd close fails,
    IOSuccess("skipped") if no issue_id.
    Uses .lash() for fail-open behavior (NFR3).
    """
    if not issue_id:
        return IOSuccess("skipped")

    result = io_ops.run_beads_close(
        issue_id, "Completed successfully",
    )

    def _on_close_ok(
        _: object,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("closed")

    def _on_close_fail(
        _: PipelineError,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("close_failed")

    return result.bind(_on_close_ok).lash(_on_close_fail)


def _finalize_on_failure(
    issue_id: str | None,
    error: PipelineError,
    attempt_count: int,
) -> IOResult[str, PipelineError]:
    """Finalize on workflow failure -- tag Beads issue.

    Returns IOSuccess("tagged_failure") on success,
    IOSuccess("tag_failed") if bd update fails,
    IOSuccess("skipped") if no issue_id.
    Uses .lash() for fail-open behavior (NFR3).
    """
    if not issue_id:
        return IOSuccess("skipped")

    metadata = _build_failure_metadata(error, attempt_count)
    result = io_ops.run_beads_update_notes(
        issue_id, metadata,
    )

    def _on_update_ok(
        _: object,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("tagged_failure")

    def _on_update_fail(
        _: PipelineError,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("tag_failed")

    return result.bind(_on_update_ok).lash(_on_update_fail)


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
            fin = _finalize_on_success(issue_id)

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
            fin = _finalize_on_failure(
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

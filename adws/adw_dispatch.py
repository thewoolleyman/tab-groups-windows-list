"""Workflow dispatch policy enforcer (FR19, Decision 5).

Reads a Beads issue, extracts the workflow tag, validates
the workflow exists and is dispatchable, and returns a
prepared WorkflowContext for execution. Executes dispatched
workflows and handles finalize (close/tag).

This module enforces the dispatchable flag policy. The
load_workflow() function in workflows/__init__.py is a
pure lookup that does NOT check dispatchable. Policy
enforcement lives here.

NFR19: Never reads BMAD files. Only Beads issue data.
"""
from __future__ import annotations

from dataclasses import dataclass

from returns.io import IOFailure, IOResult, IOSuccess
from returns.result import Failure
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.commands._finalize import (
    finalize_on_failure,
    finalize_on_success,
)
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.extract_workflow_tag import (
    extract_workflow_tag,
)
from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class DispatchExecutionResult:
    """Result of dispatch execution (Story 7.2).

    success: True when workflow succeeded.
    workflow_executed: Name of the executed workflow.
    issue_id: Beads issue ID if provided, None otherwise.
    finalize_action: "closed", "tagged_failure",
        "tag_failed", "close_failed", or "skipped".
    summary: Human-readable summary.
    """

    success: bool
    workflow_executed: str
    issue_id: str | None
    finalize_action: str
    summary: str


def dispatch_workflow(
    issue_id: str,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch a workflow based on Beads issue tag (FR19).

    Reads the issue description, extracts the workflow tag,
    validates the workflow exists and is dispatchable, and
    returns a prepared WorkflowContext.

    Does NOT execute the workflow. That is Story 7.2.
    """
    # Validate issue_id
    if not issue_id or not issue_id.strip():
        return IOFailure(
            PipelineError(
                step_name="adw_dispatch",
                error_type="ValueError",
                message=(
                    "Empty issue_id provided to"
                    " dispatch_workflow"
                ),
                context={"issue_id": issue_id},
            ),
        )

    # Read issue description via io_ops
    read_result = io_ops.read_issue_description(issue_id)
    if isinstance(read_result, IOFailure):
        return read_result

    description = unsafe_perform_io(read_result.unwrap())

    # Extract workflow tag
    tag_result = extract_workflow_tag(description)
    if isinstance(tag_result, Failure):
        return IOFailure(tag_result.failure())

    tag = tag_result.unwrap()

    # Look up workflow in registry
    from adws.workflows import (  # noqa: PLC0415
        list_dispatchable_workflows,
        load_workflow,
    )

    workflow = load_workflow(tag)
    if workflow is None:
        available = list_dispatchable_workflows()
        return IOFailure(
            PipelineError(
                step_name="adw_dispatch",
                error_type="UnknownWorkflowTagError",
                message=(
                    f"Workflow tag '{tag}' does not"
                    f" match any registered workflow."
                    f" Available: {available}"
                ),
                context={
                    "tag": tag,
                    "available_workflows": available,
                },
            ),
        )

    # Enforce dispatchable policy (Decision 5)
    if not workflow.dispatchable:
        return IOFailure(
            PipelineError(
                step_name="adw_dispatch",
                error_type="NonDispatchableError",
                message=(
                    f"Workflow '{workflow.name}' is"
                    f" not dispatchable. Only"
                    f" dispatchable workflows can be"
                    f" triggered via issue dispatch."
                ),
                context={
                    "workflow_name": workflow.name,
                    "dispatchable": workflow.dispatchable,
                },
            ),
        )

    # Build prepared WorkflowContext
    ctx = WorkflowContext(
        inputs={
            "issue_id": issue_id,
            "issue_description": description,
            "workflow_tag": tag,
            "workflow": workflow,
        },
    )
    return IOSuccess(ctx)


def execute_dispatched_workflow(
    ctx: WorkflowContext,
) -> IOResult[DispatchExecutionResult, PipelineError]:
    """Execute a dispatched workflow and finalize (FR20, FR46).

    Extracts the Workflow from ctx.inputs["workflow"],
    executes it via io_ops.execute_command_workflow,
    then finalizes: close on success, tag failure on failure.

    IOFailure is reserved for infrastructure errors
    (missing inputs, invalid workflow type). Workflow
    execution failures produce
    IOSuccess(DispatchExecutionResult(success=False)).
    """
    from adws.adw_modules.engine.types import (  # noqa: PLC0415
        Workflow,
    )

    # Validate workflow input exists
    workflow_raw = ctx.inputs.get("workflow")
    if workflow_raw is None:
        return IOFailure(
            PipelineError(
                step_name="execute_dispatched_workflow",
                error_type="MissingInputError",
                message=(
                    "WorkflowContext missing required"
                    " input 'workflow'"
                ),
                context={"available_inputs": list(ctx.inputs.keys())},
            ),
        )

    # Validate workflow type
    if not isinstance(workflow_raw, Workflow):
        return IOFailure(
            PipelineError(
                step_name="execute_dispatched_workflow",
                error_type="InvalidInputError",
                message=(
                    "Input 'workflow' must be a Workflow"
                    f" instance, got {type(workflow_raw).__name__}"
                ),
                context={"workflow_type": type(workflow_raw).__name__},
            ),
        )

    workflow: Workflow = workflow_raw
    workflow_tag_raw = ctx.inputs.get("workflow_tag", "")
    workflow_tag = str(workflow_tag_raw)
    issue_id_raw = ctx.inputs.get("issue_id")
    issue_id: str | None = (
        str(issue_id_raw) if issue_id_raw else None
    )

    # Execute workflow
    exec_result = io_ops.execute_command_workflow(
        workflow, ctx,
    )

    def _on_success(
        _: WorkflowContext,
    ) -> IOResult[DispatchExecutionResult, PipelineError]:
        fin = finalize_on_success(issue_id)

        def _wrap_success(
            action: str,
        ) -> IOResult[
            DispatchExecutionResult, PipelineError
        ]:
            return IOSuccess(
                DispatchExecutionResult(
                    success=True,
                    workflow_executed=workflow_tag,
                    issue_id=issue_id,
                    finalize_action=action,
                    summary="Completed successfully",
                ),
            )

        return fin.bind(_wrap_success)

    def _on_failure(
        err: PipelineError,
    ) -> IOResult[DispatchExecutionResult, PipelineError]:
        fin = finalize_on_failure(issue_id, err, 1)

        def _wrap_failure(
            action: str,
        ) -> IOResult[
            DispatchExecutionResult, PipelineError
        ]:
            return IOSuccess(
                DispatchExecutionResult(
                    success=False,
                    workflow_executed=workflow_tag,
                    issue_id=issue_id,
                    finalize_action=action,
                    summary=f"Failed: {err.message}",
                ),
            )

        return fin.bind(_wrap_failure)

    return exec_result.bind(_on_success).lash(
        _on_failure,
    )


def dispatch_and_execute(
    issue_id: str,
) -> IOResult[DispatchExecutionResult, PipelineError]:
    """Full orchestrator: dispatch -> execute -> finalize.

    Entry point for cron trigger (Story 7.3). Dispatches
    the workflow based on issue tag, then executes it.
    If dispatch fails (unknown tag, non-dispatchable, etc.),
    propagates the IOFailure directly -- no finalize needed
    because no workflow was started.
    """
    dispatch_result = dispatch_workflow(issue_id)
    if isinstance(dispatch_result, IOFailure):
        return dispatch_result

    ctx = unsafe_perform_io(dispatch_result.unwrap())
    return execute_dispatched_workflow(ctx)

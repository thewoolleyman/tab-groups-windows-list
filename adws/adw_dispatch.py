"""Workflow dispatch policy enforcer (FR19, Decision 5).

Reads a Beads issue, extracts the workflow tag, validates
the workflow exists and is dispatchable, and returns a
prepared WorkflowContext for execution.

This module enforces the dispatchable flag policy. The
load_workflow() function in workflows/__init__.py is a
pure lookup that does NOT check dispatchable. Policy
enforcement lives here.

NFR19: Never reads BMAD files. Only Beads issue data.
"""
from __future__ import annotations

from returns.io import IOFailure, IOResult, IOSuccess
from returns.result import Failure
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.extract_workflow_tag import (
    extract_workflow_tag,
)
from adws.adw_modules.types import WorkflowContext


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

"""Combined read + extract step for dispatch flow (FR18).

Reads issue description via io_ops, extracts and validates
the workflow tag against the registry.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.result import Failure
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.extract_workflow_tag import (
    extract_workflow_tag,
)

if TYPE_CHECKING:
    from adws.adw_modules.types import WorkflowContext


def read_and_extract(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Read issue description and extract workflow tag (step).

    Expects ctx.inputs to contain 'issue_id'.
    Produces ctx.outputs with 'issue_description',
    'workflow_tag', and 'workflow'.
    """
    issue_id = ctx.inputs.get("issue_id")
    if not isinstance(issue_id, str) or not issue_id:
        return IOFailure(
            PipelineError(
                step_name="read_and_extract",
                error_type="MissingInputError",
                message=(
                    "Required input 'issue_id'"
                    " is missing or not a string"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
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

    # Validate against workflow registry
    from adws.workflows import (  # noqa: PLC0415
        list_workflows,
        load_workflow,
    )

    workflow = load_workflow(tag)
    if workflow is None:
        available = sorted(
            w.name for w in list_workflows()
        )
        return IOFailure(
            PipelineError(
                step_name="read_and_extract",
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

    return IOSuccess(
        ctx.with_updates(
            outputs={
                "issue_description": description,
                "workflow_tag": tag,
                "workflow": workflow,
            },
        ),
    )

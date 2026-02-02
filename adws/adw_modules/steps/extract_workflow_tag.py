"""Workflow tag extraction from Beads issue descriptions (FR18).

Extracts {workflow_name} tags embedded by create_beads_issue step
and validates them against the workflow registry.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.result import Failure, Result, Success

from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from adws.adw_modules.types import WorkflowContext

_TAG_PATTERN = re.compile(r"\{(\w+)\}")


def extract_workflow_tag(
    description: str,
) -> Result[str, PipelineError]:
    """Extract workflow tag from issue description (pure function).

    Finds the first {workflow_name} pattern in the description.
    Returns Success(tag_name) or Failure(PipelineError).
    """
    match = _TAG_PATTERN.search(description)
    if match is None:
        snippet = description[:100] if description else "(empty)"
        return Failure(
            PipelineError(
                step_name="extract_workflow_tag",
                error_type="MissingWorkflowTagError",
                message=(
                    "No workflow tag found in"
                    " issue description"
                ),
                context={"description_snippet": snippet},
            ),
        )
    return Success(match.group(1))


def extract_and_validate_tag(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Extract and validate workflow tag from context (step function).

    Expects ctx.inputs to contain 'issue_description'.
    Produces ctx.outputs with 'workflow_tag' and 'workflow'.
    """
    issue_description = ctx.inputs.get("issue_description")
    if not isinstance(issue_description, str):
        return IOFailure(
            PipelineError(
                step_name="extract_and_validate_tag",
                error_type="MissingInputError",
                message=(
                    "Required input 'issue_description'"
                    " is missing or not a string"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
            ),
        )

    tag_result = extract_workflow_tag(issue_description)
    if isinstance(tag_result, Failure):
        return IOFailure(tag_result.failure())

    tag = tag_result.unwrap()

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
                step_name="extract_and_validate_tag",
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
                "workflow_tag": tag,
                "workflow": workflow,
            },
        ),
    )

"""Beads issue creator step with workflow tag embedding (FR25, FR26).

Creates Beads issues from parsed BMAD story content with embedded
workflow tags for automated dispatch.
"""
from __future__ import annotations

from returns.io import IOFailure, IOResult, IOSuccess
from returns.result import Failure, Result, Success

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import BmadStory, WorkflowContext


def _get_valid_workflow_names() -> frozenset[str]:
    """Return all valid workflow names from registry.

    Derives names dynamically from the workflow registry
    to avoid drift when new workflows are added.
    """
    from adws.workflows import (  # noqa: PLC0415
        list_workflows,
    )

    return frozenset(
        w.name for w in list_workflows()
    )


def _validate_workflow_name(
    name: str,
) -> Result[str, PipelineError]:
    """Validate workflow name against the registry.

    Returns Success(name) if valid, Failure(PipelineError) if
    the name is not in the WorkflowName registry.
    """
    valid_names = _get_valid_workflow_names()
    if name in valid_names:
        return Success(name)
    return Failure(
        PipelineError(
            step_name="create_beads_issue",
            error_type="InvalidWorkflowNameError",
            message=(
                f"Invalid workflow name '{name}'."
                f" Valid names: {sorted(valid_names)}"
            ),
            context={
                "workflow_name": name,
                "valid_names": sorted(valid_names),
            },
        ),
    )


def _embed_workflow_tag(
    content: str,
    workflow_name: str,
) -> str:
    """Embed a workflow tag at the end of content.

    Appends ``{workflow_name}`` tag on a new line after
    the content. Strips trailing whitespace from content
    before appending to avoid excessive blank lines.
    """
    stripped = content.rstrip()
    return f"{stripped}\n\n{{{workflow_name}}}"


def create_beads_issue(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Create a Beads issue from parsed story content (FR25, FR26).

    Expects ctx.inputs to contain:
    - current_story (BmadStory): Parsed story from parse_bmad_story
    - workflow_name (str): Workflow name to embed as tag

    Produces ctx.outputs containing:
    - beads_issue_id (str): ID of the created Beads issue

    Note: current_story is NOT re-output. It remains available
    to downstream steps via the engine's promote_outputs_to_inputs
    mechanism. Re-outputting it would cause a ContextCollisionError.
    """
    # Validate current_story input
    current_story = ctx.inputs.get("current_story")
    if not isinstance(current_story, BmadStory):
        return IOFailure(
            PipelineError(
                step_name="create_beads_issue",
                error_type="MissingInputError",
                message=(
                    "Required input 'current_story'"
                    " is missing or not a BmadStory"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
            ),
        )

    # Validate workflow_name input
    workflow_name = ctx.inputs.get("workflow_name")
    if not isinstance(workflow_name, str) or not workflow_name:
        return IOFailure(
            PipelineError(
                step_name="create_beads_issue",
                error_type="MissingInputError",
                message=(
                    "Required input 'workflow_name'"
                    " is missing or not a string"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
            ),
        )

    # Validate workflow name against registry
    validation = _validate_workflow_name(workflow_name)
    if isinstance(validation, Failure):
        inner = validation.failure()
        return IOFailure(inner)

    # Embed workflow tag in story content
    tagged_content = _embed_workflow_tag(
        current_story.raw_content, workflow_name,
    )

    # Build issue title
    title = (
        f"Story {current_story.epic_number}"
        f".{current_story.story_number}"
        f": {current_story.title}"
    )

    # Create Beads issue via io_ops
    create_result = io_ops.run_beads_create(
        title, tagged_content,
    )

    def _on_success(
        issue_id: str,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.with_updates(
                outputs={
                    "beads_issue_id": issue_id,
                },
            ),
        )

    return create_result.bind(_on_success)

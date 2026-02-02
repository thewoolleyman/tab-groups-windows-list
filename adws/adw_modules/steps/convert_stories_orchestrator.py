"""Convert stories orchestrator step (FR23, FR25, FR26, FR27).

Iterates over parsed BMAD stories, creating Beads issues and
writing beads_id back to source files. Provides per-story error
isolation so individual failures do not halt processing.
"""
from __future__ import annotations

from returns.io import IOFailure, IOResult, IOSuccess
from returns.result import Failure
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.create_beads_issue import (
    _embed_workflow_tag,
    _validate_workflow_name,
)
from adws.adw_modules.steps.write_beads_id import (
    _has_beads_id,
    _inject_beads_id,
)
from adws.adw_modules.types import BmadStory, WorkflowContext


def convert_stories_orchestrator(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Iterate over parsed stories, creating issues and writing beads_ids.

    Expects ctx.inputs to contain:
    - parsed_stories (list[BmadStory]): Stories from parse_bmad_story
    - workflow_name (str): Workflow name to embed as tag
    - bmad_file_path (str): Path to the BMAD file

    Per-story error isolation: failures do not halt other stories.
    Returns IOSuccess even when individual stories fail.
    """
    # Validate parsed_stories
    parsed_stories = ctx.inputs.get("parsed_stories")
    if not isinstance(parsed_stories, list):
        return IOFailure(
            PipelineError(
                step_name="convert_stories_orchestrator",
                error_type="MissingInputError",
                message=(
                    "Required input 'parsed_stories'"
                    " is missing or not a list"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
            ),
        )

    # Validate workflow_name
    workflow_name = ctx.inputs.get("workflow_name")
    if not isinstance(workflow_name, str) or not workflow_name:
        return IOFailure(
            PipelineError(
                step_name="convert_stories_orchestrator",
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

    # Validate bmad_file_path
    bmad_file_path = ctx.inputs.get("bmad_file_path")
    if not isinstance(bmad_file_path, str) or not bmad_file_path:
        return IOFailure(
            PipelineError(
                step_name="convert_stories_orchestrator",
                error_type="MissingInputError",
                message=(
                    "Required input 'bmad_file_path'"
                    " is missing or not a string"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
            ),
        )

    # Read file once before the loop to avoid re-reading
    # after each write (which would cause subsequent stories
    # to be incorrectly skipped due to file-level beads_id).
    initial_read = io_ops.read_bmad_file(bmad_file_path)
    if isinstance(initial_read, IOFailure):
        error = unsafe_perform_io(initial_read.failure())
        return IOFailure(
            PipelineError(
                step_name="convert_stories_orchestrator",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )
    initial_content = unsafe_perform_io(
        initial_read.unwrap(),
    )

    # File-level idempotency: if the file already has a
    # beads_id before we start, skip all stories.
    if _has_beads_id(initial_content):
        skip_results: list[dict[str, object]] = [
            {
                "story_slug": s.slug,
                "beads_issue_id": None,
                "status": "skipped",
                "reason": "already_has_beads_id",
            }
            for s in parsed_stories
            if isinstance(s, BmadStory)
        ]
        skip_total = len(skip_results)
        return IOSuccess(
            ctx.with_updates(
                outputs={
                    "conversion_results": skip_results,
                    "summary": {
                        "total": skip_total,
                        "created": 0,
                        "skipped": skip_total,
                        "failed": 0,
                    },
                },
            ),
        )

    # Process each story (no per-story skipping here;
    # file-level idempotency is checked above).
    conversion_results: list[dict[str, object]] = []
    created = 0
    failed = 0

    for story in parsed_stories:
        if not isinstance(story, BmadStory):
            continue  # pragma: no cover

        result_entry = _process_single_story(
            story, workflow_name, bmad_file_path,
            initial_content,
        )
        conversion_results.append(result_entry)

        if result_entry["status"] == "created":
            created += 1
        else:
            failed += 1

    total = len(conversion_results)
    summary: dict[str, object] = {
        "total": total,
        "created": created,
        "skipped": 0,
        "failed": failed,
    }

    return IOSuccess(
        ctx.with_updates(
            outputs={
                "conversion_results": conversion_results,
                "summary": summary,
            },
        ),
    )


def _process_single_story(
    story: BmadStory,
    workflow_name: str,
    bmad_file_path: str,
    file_content: str,
) -> dict[str, object]:
    """Process a single story: validate, create issue, write back.

    Accepts pre-read file_content to avoid re-reading the file
    per story (which would cause incorrect skips after the first
    story writes its beads_id to the file-level front matter).

    Returns a result dict with status, story_slug, and details.
    Never raises -- all errors are captured in the result dict.
    """
    slug = story.slug

    # Step 1: Validate workflow name and embed tag
    validation = _validate_workflow_name(workflow_name)
    if isinstance(validation, Failure):
        error = validation.failure()
        return {
            "story_slug": slug,
            "beads_issue_id": None,
            "status": "failed",
            "error": str(error.message),
        }

    tagged_content = _embed_workflow_tag(
        story.raw_content, workflow_name,
    )

    # Step 2: Create Beads issue
    title = (
        f"Story {story.epic_number}"
        f".{story.story_number}"
        f": {story.title}"
    )
    create_result = io_ops.run_beads_create(
        title, tagged_content,
    )
    if isinstance(create_result, IOFailure):
        error = unsafe_perform_io(create_result.failure())
        return {
            "story_slug": slug,
            "beads_issue_id": None,
            "status": "failed",
            "error": str(error.message),
        }

    issue_id = unsafe_perform_io(create_result.unwrap())

    # Step 3: Write beads_id back to file
    updated_content = _inject_beads_id(
        file_content, issue_id,
    )
    write_result = io_ops.write_bmad_file(
        bmad_file_path, updated_content,
    )
    if isinstance(write_result, IOFailure):
        error = unsafe_perform_io(write_result.failure())
        return {
            "story_slug": slug,
            "beads_issue_id": issue_id,
            "status": "failed",
            "error": (
                f"Issue created ({issue_id}) but"
                f" writeback failed: {error.message}"
            ),
        }

    return {
        "story_slug": slug,
        "beads_issue_id": issue_id,
        "status": "created",
    }

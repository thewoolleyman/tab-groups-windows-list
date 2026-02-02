"""Write beads_id back to BMAD story file (FR27).

Injects beads_id into the YAML front matter of a BMAD story
file for bidirectional tracking between BMAD and Beads.
"""
from __future__ import annotations

import re

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import BmadStory, WorkflowContext


def _has_beads_id(markdown: str) -> bool:
    """Check if markdown front matter contains a beads_id line.

    Only checks the YAML front matter block (between opening
    ``---`` at position 0 and closing ``\\n---`` on its own
    line). Does NOT detect beads_id in the body.
    """
    if not markdown.startswith("---"):
        return False
    end = markdown.find("\n---", 3)
    if end == -1:
        return False
    front_matter = markdown[3:end]
    return bool(
        re.search(r"^beads_id:", front_matter, re.MULTILINE),
    )


def _inject_beads_id(
    content: str,
    beads_id: str,
) -> str:
    """Insert or update beads_id in YAML front matter.

    If front matter exists and contains beads_id, replaces it.
    If front matter exists without beads_id, adds it before
    the closing ``---``. If no front matter exists, prepends one.
    """
    if not content:
        return f"---\nbeads_id: {beads_id}\n---\n"

    if not content.startswith("---"):
        return f"---\nbeads_id: {beads_id}\n---\n{content}"

    end = content.find("\n---", 3)
    if end == -1:
        return f"---\nbeads_id: {beads_id}\n---\n{content}"

    front_matter = content[3:end]
    rest = content[end + 4:]

    # Replace existing beads_id or add new one
    if re.search(r"^beads_id:", front_matter, re.MULTILINE):
        front_matter = re.sub(
            r"^beads_id:.*$",
            f"beads_id: {beads_id}",
            front_matter,
            flags=re.MULTILINE,
        )
    else:
        front_matter = front_matter + f"\nbeads_id: {beads_id}"

    return f"---{front_matter}\n---{rest}"


def write_beads_id(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Write beads_id back to source BMAD story file (FR27).

    Expects ctx.inputs to contain:
    - beads_issue_id (str): The Beads issue ID to write
    - current_story (BmadStory): The story being processed
    - bmad_file_path (str): Path to the BMAD file

    Idempotent: if the file already has a beads_id, skips
    the write and returns success with skipped_reason.
    """
    # Validate beads_issue_id
    beads_issue_id = ctx.inputs.get("beads_issue_id")
    if not isinstance(beads_issue_id, str) or not beads_issue_id:
        return IOFailure(
            PipelineError(
                step_name="write_beads_id",
                error_type="MissingInputError",
                message=(
                    "Required input 'beads_issue_id'"
                    " is missing or not a string"
                ),
                context={
                    "available_inputs": list(
                        ctx.inputs.keys(),
                    ),
                },
            ),
        )

    # Validate current_story
    current_story = ctx.inputs.get("current_story")
    if not isinstance(current_story, BmadStory):
        return IOFailure(
            PipelineError(
                step_name="write_beads_id",
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

    # Validate bmad_file_path
    bmad_file_path = ctx.inputs.get("bmad_file_path")
    if not isinstance(bmad_file_path, str) or not bmad_file_path:
        return IOFailure(
            PipelineError(
                step_name="write_beads_id",
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

    # Read the BMAD file
    read_result = io_ops.read_bmad_file(bmad_file_path)

    def _process_content(
        file_content: str,
    ) -> IOResult[WorkflowContext, PipelineError]:
        # Check idempotency
        if _has_beads_id(file_content):
            return IOSuccess(
                ctx.with_updates(
                    outputs={
                        "beads_id_written": False,
                        "skipped_reason": "already_has_beads_id",
                        "story_slug": current_story.slug,
                    },
                ),
            )

        # Inject beads_id
        updated_content = _inject_beads_id(
            file_content, beads_issue_id,
        )

        # Write back
        write_result = io_ops.write_bmad_file(
            bmad_file_path, updated_content,
        )

        def _on_write_success(
            _: None,
        ) -> IOResult[WorkflowContext, PipelineError]:
            return IOSuccess(
                ctx.with_updates(
                    outputs={
                        "beads_id_written": True,
                        "story_slug": current_story.slug,
                    },
                ),
            )

        return write_result.bind(_on_write_success)

    return read_result.bind(_process_content)

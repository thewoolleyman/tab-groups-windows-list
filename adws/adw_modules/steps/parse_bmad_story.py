"""BMAD markdown parser step (FR24).

Parses BMAD epic/story markdown files and extracts structured
story content for the BMAD-to-Beads converter pipeline.
"""
from __future__ import annotations

import re

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import (
    BmadEpic,
    BmadStory,
    WorkflowContext,
)


def _generate_slug(
    epic_number: int,
    story_number: int,
    title: str,
) -> str:
    """Generate URL-safe slug from epic/story number and title.

    Algorithm:
    1. Start with {epic_number}-{story_number}-{title}
    2. Convert to lowercase
    3. Replace non-alphanumeric characters with hyphens
    4. Collapse multiple hyphens to single hyphen
    5. Strip leading/trailing hyphens
    """
    raw = f"{epic_number}-{story_number}-{title}"
    slug = raw.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _strip_front_matter(markdown: str) -> str:
    """Remove YAML front matter (--- delimited block at top).

    Returns the markdown content after the front matter.
    If no front matter is found, returns the original text.
    The closing ``---`` must appear on its own line.
    """
    if not markdown.startswith("---"):
        return markdown
    # Find the closing --- on its own line
    end = markdown.find("\n---", 3)
    if end == -1:
        return markdown
    return markdown[end + 4 :].lstrip("\n")


def _split_into_epic_sections(
    markdown: str,
) -> list[str]:
    """Split markdown into individual epic sections.

    Each section starts at ``### Epic N:`` and ends just
    before the next ``###`` heading (epic or non-epic)
    or end of file. Non-epic ``###`` sections (e.g.,
    "### Dependency & Parallelism Map") are filtered out.
    """
    # Split on ALL ### boundaries to separate epics from non-epics
    parts = re.split(
        r"(?=^### )", markdown, flags=re.MULTILINE,
    )
    # Filter: only keep sections starting with ### Epic N:
    return [
        p.strip()
        for p in parts
        if re.match(r"^### Epic \d+:", p.strip())
    ]


def _split_into_story_blocks(
    epic_section: str,
) -> list[str]:
    """Split an epic section into individual story blocks.

    Each block starts at ``#### Story N.M:`` and ends
    before the next ``#### Story`` or end of section.

    Raises ValueError if a ``#### Story`` header exists
    but does not match the expected ``N.M:`` format.
    """
    # First check for malformed story headers
    malformed = re.findall(
        r"^#### Story (?!\d+\.\d+:).+",
        epic_section,
        flags=re.MULTILINE,
    )
    if malformed:
        msg = (
            f"Invalid story header format:"
            f" {malformed[0][:80]}"
        )
        raise ValueError(msg)

    parts = re.split(
        r"(?=^#### Story \d+\.\d+:)",
        epic_section,
        flags=re.MULTILINE,
    )
    return [
        p.strip()
        for p in parts
        if re.match(r"^#### Story \d+\.\d+:", p.strip())
    ]


def _parse_epic_header(
    header_text: str,
) -> tuple[int, str, str, list[str]]:
    """Parse an epic header block to extract metadata.

    Returns (epic_number, title, description, frs_covered).
    Raises ValueError if the header format is invalid.
    """
    header_match = re.match(
        r"^### Epic (\d+):\s*(.+)",
        header_text.strip(),
        flags=re.MULTILINE,
    )
    if not header_match:
        msg = f"Invalid epic header format: {header_text[:80]}"
        raise ValueError(msg)

    epic_number = int(header_match.group(1))
    title = header_match.group(2).strip()

    # Remove the header line itself
    rest = header_text[header_match.end() :].strip()

    # Extract FRs covered line
    frs_covered: list[str] = []
    frs_match = re.search(
        r"\*\*FRs covered:\*\*\s*(.+)",
        rest,
    )
    if frs_match:
        fr_text = frs_match.group(1).strip()
        frs_covered = [
            fr.strip()
            for fr in fr_text.split(",")
            if fr.strip()
        ]

    # Description is the text between the title and **FRs covered:**
    # or **Notes:** or the first story header, whichever comes first
    desc_end_patterns = [
        r"\*\*FRs covered:\*\*",
        r"\*\*Notes:\*\*",
        r"^#### Story",
    ]
    desc_text = rest
    for pattern in desc_end_patterns:
        match = re.search(pattern, desc_text, flags=re.MULTILINE)
        if match:
            desc_text = desc_text[: match.start()]
    description = desc_text.strip()

    return epic_number, title, description, frs_covered


def _parse_story_block(
    story_text: str,
    epic_number: int,
    epic_frs: list[str] | None = None,
) -> BmadStory:
    """Parse a story block to extract BmadStory metadata.

    Stories inherit ``frs_covered`` from their parent epic
    when ``epic_frs`` is provided.

    Raises ValueError if the story header format is invalid.
    """
    header_match = re.match(
        r"^#### Story (\d+)\.(\d+):\s*(.+)",
        story_text.strip(),
    )
    if not header_match:
        msg = (
            f"Invalid story header format:"
            f" {story_text[:80]}"
        )
        raise ValueError(msg)

    story_number = int(header_match.group(2))
    title = header_match.group(3).strip()

    # Extract user story (As a / I want / So that)
    user_story = ""
    us_match = re.search(
        r"(As an?\s.+?)(?=\n\n|\*\*Acceptance Criteria|\Z)",
        story_text,
        flags=re.DOTALL,
    )
    if us_match:
        user_story = us_match.group(1).strip()

    # Extract acceptance criteria
    acceptance_criteria = ""
    ac_match = re.search(
        r"\*\*Acceptance Criteria:\*\*\s*\n(.*)",
        story_text,
        flags=re.DOTALL,
    )
    if ac_match:
        acceptance_criteria = ac_match.group(1).strip()

    slug = _generate_slug(epic_number, story_number, title)

    return BmadStory(
        epic_number=epic_number,
        story_number=story_number,
        title=title,
        slug=slug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
        frs_covered=list(epic_frs) if epic_frs else [],
        raw_content=story_text.strip(),
    )


def parse_bmad_story(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Parse a BMAD epic/story markdown file (FR24).

    Reads the file at ctx.inputs['bmad_file_path'] via
    io_ops.read_bmad_file, parses epics and stories, and
    returns the parsed data in ctx.outputs.
    """
    bmad_file_path = ctx.inputs.get("bmad_file_path")
    if not isinstance(bmad_file_path, str) or not bmad_file_path:
        return IOFailure(
            PipelineError(
                step_name="parse_bmad_story",
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

    read_result = io_ops.read_bmad_file(bmad_file_path)

    def _process_content(
        content: str,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if not content.strip():
            return IOFailure(
                PipelineError(
                    step_name="parse_bmad_story",
                    error_type="ParseError",
                    message=(
                        "BMAD file is empty or contains"
                        " no content"
                    ),
                    context={
                        "bmad_file_path": bmad_file_path,
                    },
                ),
            )

        # Strip front matter
        cleaned = _strip_front_matter(content)

        # Split into epic sections
        epic_sections = _split_into_epic_sections(cleaned)
        if not epic_sections:
            return IOFailure(
                PipelineError(
                    step_name="parse_bmad_story",
                    error_type="ParseError",
                    message="No epics found in BMAD file",
                    context={
                        "bmad_file_path": bmad_file_path,
                    },
                ),
            )

        # Parse each epic and its stories
        parsed_epics: list[BmadEpic] = []
        all_stories: list[BmadStory] = []

        for section in epic_sections:
            try:
                # Extract the header part (before first story)
                story_blocks = _split_into_story_blocks(
                    section,
                )
                # Header is everything before the first story
                if story_blocks:
                    first_story_pos = section.find(
                        story_blocks[0],
                    )
                    header_text = section[:first_story_pos]
                else:
                    header_text = section

                epic_num, title, desc, frs = (
                    _parse_epic_header(header_text)
                )
            except ValueError as exc:
                return IOFailure(
                    PipelineError(
                        step_name="parse_bmad_story",
                        error_type="ParseError",
                        message=str(exc),
                        context={
                            "bmad_file_path": (
                                bmad_file_path
                            ),
                        },
                    ),
                )

            stories: list[BmadStory] = []
            for block in story_blocks:
                try:
                    story = _parse_story_block(
                        block, epic_num, frs,
                    )
                except ValueError as exc:
                    return IOFailure(
                        PipelineError(
                            step_name="parse_bmad_story",
                            error_type="ParseError",
                            message=str(exc),
                            context={
                                "bmad_file_path": (
                                    bmad_file_path
                                ),
                            },
                        ),
                    )
                stories.append(story)
                all_stories.append(story)

            epic = BmadEpic(
                epic_number=epic_num,
                title=title,
                description=desc,
                frs_covered=frs,
                stories=stories,
            )
            parsed_epics.append(epic)

        return IOSuccess(
            ctx.with_updates(
                outputs={
                    "parsed_epics": parsed_epics,
                    "parsed_stories": all_stories,
                },
            ),
        )

    return read_result.bind(_process_content)

"""Integration tests for BMAD markdown parser with realistic content."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from returns.io import IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.steps.parse_bmad_story import (
    parse_bmad_story,
)
from adws.adw_modules.types import (
    BmadEpic,
    BmadStory,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# Realistic BMAD content matching the actual epics.md format
_REALISTIC_BMAD = """\
---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-02-01'
---

# tab-groups-windows-list - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown.

## Requirements Inventory

### Functional Requirements

- FR1: Engine can execute a workflow
- FR23: Developer can convert BMAD stories

## Epic List

### Epic 1: Project Foundation & Developer Environment

Developer can clone the repo, install all dependencies via \
`mise install && uv sync && npm ci`, run quality gates locally.

**FRs covered:** FR41, FR42, FR43, FR44, FR45

**Notes:** Scaffold DoD from architecture.

#### Story 1.1: Project Scaffold & Dual-Toolchain Setup

As an ADWS developer,
I want the Python project scaffold with dual-toolchain support,
So that I have a reproducible development environment.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `mise install`
**Then** Python and Node.js are installed

**Given** mise has installed runtimes
**When** I run `uv sync`
**Then** all Python dependencies are installed

#### Story 1.2: Skeleton Layer Implementations & TDD Foundation

As an ADWS developer,
I want skeleton implementations across all four pipeline layers,
So that subsequent stories have established patterns to follow.

**Acceptance Criteria:**

**Given** the scaffold from Story 1.1
**When** I inspect `adws/adw_modules/errors.py`
**Then** `PipelineError` dataclass is defined

**Given** all skeleton modules exist
**When** I run `uv run pytest adws/tests/`
**Then** at least one test per layer passes

---

### Epic 6: BMAD-to-Beads Story Converter

Developer can convert BMAD stories to Beads issues via \
/convert-stories-to-beads, embedding workflow tags for dispatch \
and writing beads_id back into source BMAD files for tracking.

**FRs covered:** FR23, FR24, FR25, FR26, FR27

**Notes:** Track B -- depends on Epic 1 only.

#### Story 6.1: BMAD Markdown Parser

As an ADWS developer,
I want to parse BMAD epic/story markdown files and extract structured story content,
So that the converter can create Beads issues from planning artifacts.

**Acceptance Criteria:**

**Given** a BMAD epic markdown file with stories
**When** the parser processes it
**Then** it extracts each story's title, user story, and acceptance criteria

**Given** a malformed or incomplete BMAD file
**When** the parser encounters an error
**Then** it returns a clear PipelineError

#### Story 6.2: Beads Issue Creator with Workflow Tags

As an ADWS developer,
I want to create Beads issues from parsed story content with embedded workflow tags,
So that each issue is ready for automated dispatch.

**Acceptance Criteria:**

**Given** parsed story content from Story 6.1
**When** the creator generates a Beads issue
**Then** it calls `bd create` via io_ops shell function

---

### Dependency & Parallelism Map

| Epic | FRs | Count |
|------|-----|-------|
| 1: Foundation | FR41-45 | 5 |
"""


class TestBmadParserIntegration:
    """Integration tests with realistic BMAD content."""

    def test_realistic_multi_epic_parsing(
        self, mocker: MockerFixture,
    ) -> None:
        """Parses realistic BMAD content with 2 epics and multiple stories."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(_REALISTIC_BMAD),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())

        epics = out.outputs["parsed_epics"]
        stories = out.outputs["parsed_stories"]

        # Should have 2 epics (Dependency Map is excluded)
        assert len(epics) == 2
        assert isinstance(epics[0], BmadEpic)
        assert isinstance(epics[1], BmadEpic)

        # Epic 1 has 2 stories, Epic 6 has 2 stories
        assert epics[0].epic_number == 1
        assert epics[0].title == (
            "Project Foundation & Developer Environment"
        )
        assert len(epics[0].stories) == 2
        assert epics[0].frs_covered == [
            "FR41", "FR42", "FR43", "FR44", "FR45",
        ]

        assert epics[1].epic_number == 6
        assert epics[1].title == (
            "BMAD-to-Beads Story Converter"
        )
        assert len(epics[1].stories) == 2
        assert epics[1].frs_covered == [
            "FR23", "FR24", "FR25", "FR26", "FR27",
        ]

        # Total 4 stories
        assert len(stories) == 4
        assert all(
            isinstance(s, BmadStory)
            for s in stories
        )

        # Verify correct epic-to-story relationships
        assert stories[0].epic_number == 1
        assert stories[0].story_number == 1
        assert stories[1].epic_number == 1
        assert stories[1].story_number == 2
        assert stories[2].epic_number == 6
        assert stories[2].story_number == 1
        assert stories[3].epic_number == 6
        assert stories[3].story_number == 2

        # Verify titles
        assert stories[0].title == (
            "Project Scaffold & Dual-Toolchain Setup"
        )
        assert stories[2].title == "BMAD Markdown Parser"

        # Verify user stories extracted
        assert "ADWS developer" in stories[0].user_story
        assert "reproducible" in stories[0].user_story

        # Verify AC extracted
        assert "**Given**" in stories[0].acceptance_criteria
        assert "mise install" in stories[0].acceptance_criteria

        # Verify stories inherit frs_covered from epic
        assert stories[0].frs_covered == [
            "FR41", "FR42", "FR43", "FR44", "FR45",
        ]
        assert stories[1].frs_covered == [
            "FR41", "FR42", "FR43", "FR44", "FR45",
        ]
        assert stories[2].frs_covered == [
            "FR23", "FR24", "FR25", "FR26", "FR27",
        ]
        assert stories[3].frs_covered == [
            "FR23", "FR24", "FR25", "FR26", "FR27",
        ]

    def test_raw_content_preservation(
        self, mocker: MockerFixture,
    ) -> None:
        """raw_content contains the complete story text."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(_REALISTIC_BMAD),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        stories = out.outputs["parsed_stories"]

        for story in stories:
            # raw_content must start with the story header
            assert story.raw_content.startswith(
                f"#### Story {story.epic_number}"
                f".{story.story_number}:",
            )
            # raw_content must contain the title
            assert story.title in story.raw_content
            # raw_content must not be empty
            assert len(story.raw_content) > 20

    def test_slug_generation_for_all_stories(
        self, mocker: MockerFixture,
    ) -> None:
        """All slugs follow the correct pattern and are URL-safe."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(_REALISTIC_BMAD),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        stories = out.outputs["parsed_stories"]

        slug_pattern = re.compile(
            r"^\d+-\d+-[a-z0-9]+(-[a-z0-9]+)*$",
        )

        for story in stories:
            # Slug must match pattern
            assert slug_pattern.match(story.slug), (
                f"Invalid slug: {story.slug}"
            )
            # Slug must start with epic-story number
            assert story.slug.startswith(
                f"{story.epic_number}-{story.story_number}-",
            )
            # No uppercase, no special characters
            assert story.slug == story.slug.lower()
            assert " " not in story.slug
            assert "&" not in story.slug

        # Verify specific known slugs
        assert stories[0].slug == (
            "1-1-project-scaffold-dual-toolchain-setup"
        )
        assert stories[2].slug == (
            "6-1-bmad-markdown-parser"
        )

    def test_front_matter_skipped(
        self, mocker: MockerFixture,
    ) -> None:
        """YAML front matter at top of file is skipped."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(_REALISTIC_BMAD),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        stories = out.outputs["parsed_stories"]
        # No story should contain front matter content
        for story in stories:
            assert "stepsCompleted" not in story.raw_content
            assert "completedAt" not in story.raw_content

    def test_non_epic_sections_excluded(
        self, mocker: MockerFixture,
    ) -> None:
        """Non-epic ### sections are excluded from parsed results."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(_REALISTIC_BMAD),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        epics = out.outputs["parsed_epics"]

        # No epic should have "Dependency" as title
        for epic in epics:
            assert "Dependency" not in epic.title
            assert "Parallelism" not in epic.title


# --- Step export and registry tests ---


def test_parse_bmad_story_in_steps_all() -> None:
    """parse_bmad_story is importable from steps and in __all__."""
    from adws.adw_modules import steps  # noqa: PLC0415

    assert "parse_bmad_story" in steps.__all__
    assert hasattr(steps, "parse_bmad_story")


def test_parse_bmad_story_in_step_registry() -> None:
    """parse_bmad_story is registered in _STEP_REGISTRY."""
    from adws.adw_modules.engine.executor import (  # noqa: PLC0415
        _STEP_REGISTRY,
    )

    assert "parse_bmad_story" in _STEP_REGISTRY
    assert _STEP_REGISTRY["parse_bmad_story"] is parse_bmad_story

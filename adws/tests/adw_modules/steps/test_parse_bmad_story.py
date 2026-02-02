"""Tests for parse_bmad_story step and private helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.parse_bmad_story import (
    _generate_slug,
    _parse_epic_header,
    _parse_story_block,
    _split_into_epic_sections,
    _split_into_story_blocks,
    _strip_front_matter,
    parse_bmad_story,
)
from adws.adw_modules.types import (
    BmadEpic,
    BmadStory,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- _generate_slug tests ---


class TestGenerateSlug:
    """Tests for _generate_slug helper."""

    def test_basic_slug(self) -> None:
        """Standard title produces correct slug."""
        result = _generate_slug(6, 1, "BMAD Markdown Parser")
        assert result == "6-1-bmad-markdown-parser"

    def test_slug_with_special_characters(self) -> None:
        """Special characters are replaced with hyphens."""
        result = _generate_slug(
            6, 3,
            "Bidirectional Tracking & /convert-stories-to-beads Command",
        )
        assert result == (
            "6-3-bidirectional-tracking-convert-stories-to-beads-command"
        )

    def test_slug_with_ampersand(self) -> None:
        """Ampersand is replaced with hyphen."""
        result = _generate_slug(
            1, 1, "Project Scaffold & Dual-Toolchain Setup",
        )
        assert result == (
            "1-1-project-scaffold-dual-toolchain-setup"
        )

    def test_slug_collapses_hyphens(self) -> None:
        """Multiple consecutive hyphens collapse to one."""
        result = _generate_slug(1, 1, "A -- B")
        assert result == "1-1-a-b"

    def test_slug_strips_leading_trailing_hyphens(self) -> None:
        """Leading and trailing hyphens are stripped."""
        result = _generate_slug(1, 1, "  Title  ")
        assert result == "1-1-title"

    def test_slug_mixed_case(self) -> None:
        """Mixed case converts to lowercase."""
        result = _generate_slug(2, 1, "Error Types & WorkflowContext")
        assert result == (
            "2-1-error-types-workflowcontext"
        )

    def test_slug_with_parentheses(self) -> None:
        """Parentheses are removed/replaced."""
        result = _generate_slug(
            4, 4, "Build Command & implement_close Workflow",
        )
        assert "(" not in result
        assert ")" not in result

    def test_slug_with_underscores(self) -> None:
        """Underscores in title are converted to hyphens."""
        result = _generate_slug(
            4, 4, "Build Command & implement_close Workflow",
        )
        assert result == (
            "4-4-build-command-implement-close-workflow"
        )


# --- _strip_front_matter tests ---


class TestStripFrontMatter:
    """Tests for _strip_front_matter helper."""

    def test_strips_yaml_front_matter(self) -> None:
        """YAML front matter is removed."""
        content = (
            "---\nstatus: complete\n---\n\n# Title\n\nContent"
        )
        result = _strip_front_matter(content)
        assert result.startswith("# Title")
        assert "status: complete" not in result

    def test_no_front_matter(self) -> None:
        """Content without front matter passes through."""
        content = "# Title\n\nContent"
        result = _strip_front_matter(content)
        assert result == content

    def test_unclosed_front_matter(self) -> None:
        """Unclosed front matter returns original content."""
        content = "---\nstatus: complete\n# Title"
        result = _strip_front_matter(content)
        assert result == content


# --- _split_into_epic_sections tests ---


class TestSplitIntoEpicSections:
    """Tests for _split_into_epic_sections helper."""

    def test_splits_multiple_epics(self) -> None:
        """Multiple epics are split correctly."""
        markdown = (
            "## Epic List\n\n"
            "### Epic 1: Foundation\n\nDesc 1\n\n"
            "---\n\n"
            "### Epic 2: Engine\n\nDesc 2\n"
        )
        sections = _split_into_epic_sections(markdown)
        assert len(sections) == 2
        assert "Epic 1:" in sections[0]
        assert "Epic 2:" in sections[1]

    def test_single_epic(self) -> None:
        """Single epic returns a list with one element."""
        markdown = "### Epic 1: Foundation\n\nDesc 1\n"
        sections = _split_into_epic_sections(markdown)
        assert len(sections) == 1
        assert "Epic 1:" in sections[0]

    def test_filters_non_epic_sections(self) -> None:
        """Non-epic ### sections are excluded."""
        markdown = (
            "### Epic 1: Foundation\n\nDesc 1\n\n"
            "---\n\n"
            "### Dependency & Parallelism Map\n\nNot an epic\n"
        )
        sections = _split_into_epic_sections(markdown)
        assert len(sections) == 1
        assert "Epic 1:" in sections[0]
        assert "Dependency" not in sections[0]

    def test_no_epics(self) -> None:
        """Content with no epics returns empty list."""
        markdown = "# Title\n\n## Overview\n\nSome text"
        sections = _split_into_epic_sections(markdown)
        assert sections == []


# --- _split_into_story_blocks tests ---


class TestSplitIntoStoryBlocks:
    """Tests for _split_into_story_blocks helper."""

    def test_splits_multiple_stories(self) -> None:
        """Multiple stories are split correctly."""
        section = (
            "### Epic 1: Foundation\n\nDesc\n\n"
            "#### Story 1.1: Setup\n\nStory 1\n\n"
            "#### Story 1.2: Config\n\nStory 2\n"
        )
        blocks = _split_into_story_blocks(section)
        assert len(blocks) == 2
        assert "Story 1.1:" in blocks[0]
        assert "Story 1.2:" in blocks[1]

    def test_single_story(self) -> None:
        """Single story returns list with one element."""
        section = (
            "### Epic 1: Foundation\n\nDesc\n\n"
            "#### Story 1.1: Setup\n\nStory content\n"
        )
        blocks = _split_into_story_blocks(section)
        assert len(blocks) == 1
        assert "Story 1.1:" in blocks[0]

    def test_no_stories(self) -> None:
        """Epic with no stories returns empty list."""
        section = "### Epic 1: Foundation\n\nJust a description\n"
        blocks = _split_into_story_blocks(section)
        assert blocks == []


# --- _parse_epic_header tests ---


class TestParseEpicHeader:
    """Tests for _parse_epic_header helper."""

    def test_full_header(self) -> None:
        """Full epic header with FRs and notes is parsed."""
        header = (
            "### Epic 6: BMAD-to-Beads Story Converter\n\n"
            "Developer can convert BMAD stories to Beads issues.\n\n"
            "**FRs covered:** FR23, FR24, FR25, FR26, FR27\n\n"
            "**Notes:** Track B notes here.\n"
        )
        num, title, desc, frs = _parse_epic_header(header)
        assert num == 6
        assert title == "BMAD-to-Beads Story Converter"
        assert "convert" in desc.lower()
        assert frs == ["FR23", "FR24", "FR25", "FR26", "FR27"]
        # Notes should NOT be in description
        assert "Track B" not in desc

    def test_no_frs(self) -> None:
        """Epic without FRs covered returns empty list."""
        header = (
            "### Epic 1: Foundation\n\n"
            "A description paragraph.\n"
        )
        num, title, desc, frs = _parse_epic_header(header)
        assert num == 1
        assert title == "Foundation"
        assert "description" in desc.lower()
        assert frs == []

    def test_notes_excluded_from_description(self) -> None:
        """Notes section is not included in description."""
        header = (
            "### Epic 1: Foundation\n\n"
            "Description paragraph.\n\n"
            "**FRs covered:** FR41\n\n"
            "**Notes:** Some important notes.\n"
        )
        _, _, desc, _ = _parse_epic_header(header)
        assert "important notes" not in desc.lower()
        assert "description paragraph" in desc.lower()

    def test_invalid_header_raises(self) -> None:
        """Invalid epic header raises ValueError."""
        with pytest.raises(ValueError, match="Invalid epic header"):
            _parse_epic_header("### Not an epic format")

    def test_malformed_epic_number(self) -> None:
        """Non-numeric epic number raises ValueError."""
        with pytest.raises(ValueError, match="Invalid epic header"):
            _parse_epic_header("### Epic X: Bad Number")


# --- _parse_story_block tests ---


class TestParseStoryBlock:
    """Tests for _parse_story_block helper."""

    def test_full_story_block(self) -> None:
        """Full story with user story and AC is parsed."""
        block = (
            "#### Story 6.1: BMAD Markdown Parser\n\n"
            "As an ADWS developer,\n"
            "I want to parse BMAD files,\n"
            "So that the converter works.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** a file\n"
            "**When** parsed\n"
            "**Then** content extracted\n"
        )
        story = _parse_story_block(block, 6)
        assert story.epic_number == 6
        assert story.story_number == 1
        assert story.title == "BMAD Markdown Parser"
        assert story.slug == "6-1-bmad-markdown-parser"
        assert "ADWS developer" in story.user_story
        assert "**Given**" in story.acceptance_criteria
        assert "#### Story 6.1" in story.raw_content

    def test_missing_user_story(self) -> None:
        """Story without As a/I want/So that returns empty user_story."""
        block = (
            "#### Story 1.1: Setup\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** setup\n"
            "**When** run\n"
            "**Then** works\n"
        )
        story = _parse_story_block(block, 1)
        assert story.user_story == ""
        assert "**Given**" in story.acceptance_criteria

    def test_missing_acceptance_criteria(self) -> None:
        """Story without AC section returns empty acceptance_criteria."""
        block = (
            "#### Story 1.1: Setup\n\n"
            "As a developer,\n"
            "I want setup,\n"
            "So that it works.\n"
        )
        story = _parse_story_block(block, 1)
        assert story.acceptance_criteria == ""
        assert "developer" in story.user_story

    def test_multiple_ac_blocks(self) -> None:
        """Multiple AC blocks are all captured."""
        block = (
            "#### Story 1.1: Setup\n\n"
            "As a developer,\n"
            "I want setup,\n"
            "So that it works.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** condition 1\n"
            "**When** action 1\n"
            "**Then** result 1\n\n"
            "**Given** condition 2\n"
            "**When** action 2\n"
            "**Then** result 2\n"
        )
        story = _parse_story_block(block, 1)
        assert "condition 1" in story.acceptance_criteria
        assert "condition 2" in story.acceptance_criteria

    def test_raw_content_preserved(self) -> None:
        """raw_content contains the full story block text."""
        block = (
            "#### Story 6.1: Parser\n\n"
            "As a dev,\nI want to parse.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** X **When** Y **Then** Z\n"
        )
        story = _parse_story_block(block, 6)
        assert story.raw_content == block.strip()

    def test_invalid_story_header_raises(self) -> None:
        """Invalid story header raises ValueError."""
        with pytest.raises(ValueError, match="Invalid story header"):
            _parse_story_block(
                "#### Story X: Bad Number", 1,
            )


# --- parse_bmad_story step function tests ---


class TestParseBmadStory:
    """Tests for parse_bmad_story step function."""

    def test_single_epic_single_story(
        self, mocker: MockerFixture,
    ) -> None:
        """Parses one epic with one story."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n\n"
            "#### Story 1.1: Setup\n\n"
            "As a dev,\nI want setup,\nSo that it works.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** X\n**When** Y\n**Then** Z\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        epics = out.outputs["parsed_epics"]
        stories = out.outputs["parsed_stories"]
        assert isinstance(epics, list)
        assert isinstance(stories, list)
        assert len(epics) == 1
        assert len(stories) == 1
        assert isinstance(epics[0], BmadEpic)
        assert isinstance(stories[0], BmadStory)
        assert epics[0].epic_number == 1
        assert stories[0].story_number == 1

    def test_multi_epic_multi_story(
        self, mocker: MockerFixture,
    ) -> None:
        """Parses multiple epics with multiple stories."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Epic 1 desc.\n\n"
            "**FRs covered:** FR41, FR42\n\n"
            "#### Story 1.1: Setup\n\n"
            "As a dev,\nI want setup,\nSo that ready.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** X\n**When** Y\n**Then** Z\n\n"
            "#### Story 1.2: Config\n\n"
            "As a dev,\nI want config,\nSo that works.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** A\n**When** B\n**Then** C\n\n"
            "---\n\n"
            "### Epic 2: Engine\n\n"
            "Epic 2 desc.\n\n"
            "**FRs covered:** FR1, FR2\n\n"
            "#### Story 2.1: Core\n\n"
            "As a dev,\nI want engine,\nSo that runs.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** P\n**When** Q\n**Then** R\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        epics = out.outputs["parsed_epics"]
        stories = out.outputs["parsed_stories"]
        assert len(epics) == 2
        assert len(stories) == 3
        assert epics[0].epic_number == 1
        assert len(epics[0].stories) == 2
        assert epics[1].epic_number == 2
        assert len(epics[1].stories) == 1
        # Verify correct story assignment
        assert stories[0].epic_number == 1
        assert stories[1].epic_number == 1
        assert stories[2].epic_number == 2

    def test_missing_bmad_file_path(self) -> None:
        """Returns IOFailure when bmad_file_path is missing."""
        ctx = WorkflowContext(inputs={})
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"
        assert error.step_name == "parse_bmad_story"

    def test_bmad_file_path_not_string(self) -> None:
        """Returns IOFailure when bmad_file_path is not a string."""
        ctx = WorkflowContext(
            inputs={"bmad_file_path": 42},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"

    def test_bmad_file_path_empty_string(self) -> None:
        """Returns IOFailure when bmad_file_path is empty."""
        ctx = WorkflowContext(
            inputs={"bmad_file_path": ""},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputError"

    def test_file_read_failure(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns IOFailure when io_ops.read_bmad_file fails."""
        file_err = PipelineError(
            step_name="io_ops.read_file",
            error_type="FileNotFoundError",
            message="File not found",
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOFailure(file_err),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "missing.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)

    def test_empty_file(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns IOFailure when file is empty."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(""),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "empty.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ParseError"
        assert "empty" in error.message.lower()

    def test_whitespace_only_file(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns IOFailure when file is whitespace only."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess("   \n\n  "),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "blank.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ParseError"

    def test_no_epics_found(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns IOFailure when no epics are found."""
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(
                "# Title\n\n## Overview\n\nSome text"
            ),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "no-epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ParseError"
        assert "No epics" in error.message

    def test_with_front_matter(
        self, mocker: MockerFixture,
    ) -> None:
        """Front matter is skipped, parsing starts from content."""
        md = (
            "---\nstatus: complete\n---\n\n"
            "# Title\n\n"
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n\n"
            "#### Story 1.1: Setup\n\n"
            "As a dev,\nI want setup,\nSo that works.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** X\n**When** Y\n**Then** Z\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        assert len(out.outputs["parsed_epics"]) == 1

    def test_empty_ac_section(
        self, mocker: MockerFixture,
    ) -> None:
        """Story with empty AC header is parsed with empty AC."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n\n"
            "#### Story 1.1: Setup\n\n"
            "As a dev,\nI want setup,\nSo that works.\n\n"
            "**Acceptance Criteria:**\n\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        stories = out.outputs["parsed_stories"]
        assert stories[0].acceptance_criteria == ""

    def test_missing_user_story_with_ac(
        self, mocker: MockerFixture,
    ) -> None:
        """Story missing user story but having AC is parsed correctly."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n\n"
            "#### Story 1.1: Setup\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** X\n**When** Y\n**Then** Z\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        stories = out.outputs["parsed_stories"]
        assert stories[0].user_story == ""
        assert "**Given**" in stories[0].acceptance_criteria

    def test_malformed_epic_header(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns ParseError for malformed epic header."""
        md = "### Epic X: Missing Number\n\nDesc\n"
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "bad.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ParseError"

    def test_malformed_story_header(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns ParseError for malformed story header."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n\n"
            "#### Story X: Bad Number\n\nContent\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "bad.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ParseError"

    def test_parse_story_block_raises_value_error(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns ParseError when _parse_story_block raises ValueError."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n\n"
            "#### Story 1.1: Setup\n\n"
            "As a dev,\nI want setup,\nSo that works.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** X\n**When** Y\n**Then** Z\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            "._parse_story_block",
            side_effect=ValueError("mock parse error"),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ParseError"
        assert "mock parse error" in error.message

    def test_epic_with_no_stories(
        self, mocker: MockerFixture,
    ) -> None:
        """Epic with description but no stories produces empty stories list."""
        md = (
            "### Epic 1: Foundation\n\n"
            "Description.\n\n"
            "**FRs covered:** FR41\n"
        )
        mocker.patch(
            "adws.adw_modules.steps.parse_bmad_story"
            ".io_ops.read_bmad_file",
            return_value=IOSuccess(md),
        )
        ctx = WorkflowContext(
            inputs={"bmad_file_path": "epics.md"},
        )
        result = parse_bmad_story(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())
        epics = out.outputs["parsed_epics"]
        assert len(epics) == 1
        assert epics[0].stories == []

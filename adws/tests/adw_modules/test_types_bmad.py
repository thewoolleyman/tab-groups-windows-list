"""Tests for BmadStory and BmadEpic frozen dataclasses."""
from __future__ import annotations

import dataclasses

import pytest

from adws.adw_modules.types import BmadEpic, BmadStory

# --- BmadStory tests ---


class TestBmadStory:
    """Tests for BmadStory frozen dataclass."""

    def test_bmad_story_creation(self) -> None:
        """BmadStory can be created with all required fields."""
        story = BmadStory(
            epic_number=6,
            story_number=1,
            title="BMAD Markdown Parser",
            slug="6-1-bmad-markdown-parser",
            user_story=(
                "As an ADWS developer,\n"
                "I want to parse BMAD files,\n"
                "So that I can convert them."
            ),
            acceptance_criteria="**Given** a file **When** parsed **Then** extracted",
        )
        assert story.epic_number == 6
        assert story.story_number == 1
        assert story.title == "BMAD Markdown Parser"
        assert story.slug == "6-1-bmad-markdown-parser"
        assert "ADWS developer" in story.user_story
        assert "**Given**" in story.acceptance_criteria

    def test_bmad_story_defaults(self) -> None:
        """BmadStory has correct default values for optional fields."""
        story = BmadStory(
            epic_number=1,
            story_number=1,
            title="Test",
            slug="1-1-test",
            user_story="",
            acceptance_criteria="",
        )
        assert story.frs_covered == []
        assert story.raw_content == ""

    def test_bmad_story_with_frs_and_raw_content(self) -> None:
        """BmadStory accepts frs_covered and raw_content."""
        story = BmadStory(
            epic_number=6,
            story_number=1,
            title="Test",
            slug="6-1-test",
            user_story="user story",
            acceptance_criteria="ac",
            frs_covered=["FR24", "FR25"],
            raw_content="# Full markdown content",
        )
        assert story.frs_covered == ["FR24", "FR25"]
        assert story.raw_content == "# Full markdown content"

    def test_bmad_story_is_frozen(self) -> None:
        """BmadStory is immutable (frozen dataclass)."""
        story = BmadStory(
            epic_number=6,
            story_number=1,
            title="Test",
            slug="6-1-test",
            user_story="",
            acceptance_criteria="",
        )
        assert dataclasses.is_dataclass(story)
        with pytest.raises(dataclasses.FrozenInstanceError):
            story.title = "changed"  # type: ignore[misc]

    def test_bmad_story_equality(self) -> None:
        """Two BmadStory instances with same fields are equal."""
        story1 = BmadStory(
            epic_number=1,
            story_number=1,
            title="Test",
            slug="1-1-test",
            user_story="us",
            acceptance_criteria="ac",
        )
        story2 = BmadStory(
            epic_number=1,
            story_number=1,
            title="Test",
            slug="1-1-test",
            user_story="us",
            acceptance_criteria="ac",
        )
        assert story1 == story2


# --- BmadEpic tests ---


class TestBmadEpic:
    """Tests for BmadEpic frozen dataclass."""

    def test_bmad_epic_creation(self) -> None:
        """BmadEpic can be created with all required fields."""
        epic = BmadEpic(
            epic_number=6,
            title="BMAD-to-Beads Story Converter",
            description="Developer can convert BMAD stories to Beads issues.",
        )
        assert epic.epic_number == 6
        assert epic.title == "BMAD-to-Beads Story Converter"
        assert "convert" in epic.description

    def test_bmad_epic_defaults(self) -> None:
        """BmadEpic has correct default values for optional fields."""
        epic = BmadEpic(
            epic_number=1,
            title="Test",
            description="desc",
        )
        assert epic.frs_covered == []
        assert epic.stories == []

    def test_bmad_epic_with_stories_and_frs(self) -> None:
        """BmadEpic accepts stories list and frs_covered."""
        story = BmadStory(
            epic_number=6,
            story_number=1,
            title="Parser",
            slug="6-1-parser",
            user_story="us",
            acceptance_criteria="ac",
        )
        epic = BmadEpic(
            epic_number=6,
            title="Converter",
            description="desc",
            frs_covered=["FR23", "FR24"],
            stories=[story],
        )
        assert epic.frs_covered == ["FR23", "FR24"]
        assert len(epic.stories) == 1
        assert epic.stories[0].title == "Parser"

    def test_bmad_epic_is_frozen(self) -> None:
        """BmadEpic is immutable (frozen dataclass)."""
        epic = BmadEpic(
            epic_number=1,
            title="Test",
            description="desc",
        )
        assert dataclasses.is_dataclass(epic)
        with pytest.raises(dataclasses.FrozenInstanceError):
            epic.title = "changed"  # type: ignore[misc]

    def test_bmad_epic_equality(self) -> None:
        """Two BmadEpic instances with same fields are equal."""
        epic1 = BmadEpic(
            epic_number=1,
            title="Test",
            description="desc",
        )
        epic2 = BmadEpic(
            epic_number=1,
            title="Test",
            description="desc",
        )
        assert epic1 == epic2

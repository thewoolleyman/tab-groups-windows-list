"""Integration tests for beads issue creator (Story 6.2).

Tests the full flow: story content + tag embedding + bd create call
+ issue ID capture, using realistic BmadStory data.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.create_beads_issue import (
    create_beads_issue,
)
from adws.adw_modules.types import BmadStory, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _realistic_story() -> BmadStory:
    """Create a realistic BmadStory matching Story 6.1 parser output."""
    return BmadStory(
        epic_number=6,
        story_number=2,
        title="Beads Issue Creator with Workflow Tags",
        slug="6-2-beads-issue-creator-with-workflow-tags",
        user_story=(
            "As an ADWS developer,\n"
            "I want to create Beads issues from parsed "
            "story content with embedded workflow tags,\n"
            "so that each issue is ready for automated "
            "dispatch."
        ),
        acceptance_criteria=(
            "**Given** parsed story content from Story 6.1, "
            "**When** the creator generates a Beads issue, "
            "**Then** it calls bd create via io_ops.\n\n"
            "**Given** bd create succeeds, "
            "**When** the issue is created, "
            "**Then** the returned Beads issue ID is captured."
        ),
        frs_covered=["FR23", "FR24", "FR25", "FR26", "FR27"],
        raw_content=(
            "#### Story 6.2: Beads Issue Creator with "
            "Workflow Tags\n\n"
            "As an ADWS developer,\n"
            "I want to create Beads issues from parsed "
            "story content with embedded workflow tags,\n"
            "so that each issue is ready for automated "
            "dispatch.\n\n"
            "**Acceptance Criteria:**\n\n"
            "**Given** parsed story content from Story 6.1, "
            "**When** the creator generates a Beads issue, "
            "**Then** it calls bd create via io_ops.\n\n"
            "**Given** bd create succeeds, "
            "**When** the issue is created, "
            "**Then** the returned Beads issue ID is captured."
        ),
    )


class TestBeadsIssueCreatorIntegration:
    """Integration tests for the full beads issue creation flow."""

    def test_full_flow_with_realistic_story(
        self, mocker: MockerFixture,
    ) -> None:
        """Full flow: realistic story -> tagged desc -> issue ID."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("BEADS-62"),
        )
        story = _realistic_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_verify_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOSuccess)
        out = unsafe_perform_io(result.unwrap())

        # Issue ID captured
        assert out.outputs["beads_issue_id"] == "BEADS-62"

        # current_story is NOT re-output; it flows via
        # engine promote_outputs_to_inputs to avoid collision
        assert "current_story" not in out.outputs

        # Verify call args
        call_args = mock_create.call_args
        title = call_args[0][0]
        description = call_args[0][1]

        # Title format: Story N.M: Title
        assert title == (
            "Story 6.2: Beads Issue Creator"
            " with Workflow Tags"
        )

        # Description contains full story content
        assert "#### Story 6.2:" in description
        assert "ADWS developer" in description
        assert "Acceptance Criteria" in description

        # Description contains embedded workflow tag
        assert "{implement_verify_close}" in description

        # Tag is at the end
        assert description.endswith(
            "{implement_verify_close}",
        )

    def test_validate_tag_embed_chain(
        self, mocker: MockerFixture,
    ) -> None:
        """Validation -> tag embedding -> io_ops chain works."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("CHAIN-1"),
        )
        story = BmadStory(
            epic_number=1,
            story_number=1,
            title="Simple Story",
            slug="1-1-simple-story",
            user_story="As a dev, I want simple.",
            acceptance_criteria="Given X When Y Then Z",
            frs_covered=["FR1"],
            raw_content="Simple raw content.",
        )
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOSuccess)

        # Verify description has both content and tag
        description = mock_create.call_args[0][1]
        assert "Simple raw content." in description
        assert "{implement_close}" in description
        # Tag after content with blank line separator
        assert "\n\n{implement_close}" in description

    def test_failure_propagation_integration(
        self, mocker: MockerFixture,
    ) -> None:
        """IOFailure from bd create propagates through chain."""
        mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_beads_create",
                    error_type="BeadsCreateError",
                    message="bd create failed: timeout",
                    context={
                        "exit_code": 1,
                        "stderr": "timeout",
                    },
                ),
            ),
        )
        story = _realistic_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "implement_close",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "BeadsCreateError"
        assert "timeout" in error.message

    def test_invalid_workflow_blocks_creation(
        self, mocker: MockerFixture,
    ) -> None:
        """Invalid workflow name blocks issue creation entirely."""
        mock_create = mocker.patch(
            "adws.adw_modules.steps.create_beads_issue"
            ".io_ops.run_beads_create",
            return_value=IOSuccess("SHOULD-NOT-REACH"),
        )
        story = _realistic_story()
        ctx = WorkflowContext(
            inputs={
                "current_story": story,
                "workflow_name": "invalid_wf",
            },
        )
        result = create_beads_issue(ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "InvalidWorkflowNameError"
        # io_ops.run_beads_create should NOT have been called
        mock_create.assert_not_called()

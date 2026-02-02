"""Tests for dispatch guard module (Story 7.3)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestHasActiveFailureMetadata:
    """Tests for has_active_failure_metadata pure function."""

    def test_adws_failed_returns_true(self) -> None:
        """Given notes with ADWS_FAILED, returns True."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        notes = (
            "ADWS_FAILED|attempt=1|last_failure="
            "2026-02-01T00:00:00Z|error_class="
            "SdkCallError|step=implement|"
            "summary=timeout"
        )
        assert has_active_failure_metadata(notes) is True

    def test_empty_notes_returns_false(self) -> None:
        """Given empty notes, returns False."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        assert has_active_failure_metadata("") is False

    def test_needs_human_returns_true(self) -> None:
        """Given notes with needs_human, returns True."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        assert has_active_failure_metadata(
            "needs_human: review required",
        ) is True

    def test_clean_notes_returns_false(self) -> None:
        """Given clean notes without failure markers, returns False."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        notes = (
            "Normal issue notes without any"
            " failure markers"
        )
        assert has_active_failure_metadata(notes) is False

    def test_both_markers_returns_true(self) -> None:
        """Given notes with both ADWS_FAILED and needs_human, returns True."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        notes = "ADWS_FAILED|...\nneeds_human"
        assert has_active_failure_metadata(notes) is True

    def test_case_sensitive_adws_failed(self) -> None:
        """ADWS_FAILED check is case-sensitive (lowercase ignored)."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        assert (
            has_active_failure_metadata("adws_failed") is False
        )

    def test_case_sensitive_needs_human(self) -> None:
        """needs_human check is case-sensitive (uppercase ignored)."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            has_active_failure_metadata,
        )

        assert (
            has_active_failure_metadata("NEEDS_HUMAN")
            is False
        )


class TestCheckDispatchGuard:
    """Tests for check_dispatch_guard function."""

    def test_eligible_no_failure_metadata(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given no failure metadata in notes, returns IOSuccess(True)."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            check_dispatch_guard,
        )

        mocker.patch(
            "adws.adw_modules.steps.dispatch_guard.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        result = check_dispatch_guard("ISSUE-42")
        assert isinstance(result, IOSuccess)
        val = unsafe_perform_io(result.unwrap())
        assert val is True

    def test_skip_adws_failed(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given ADWS_FAILED in notes, returns IOSuccess(False)."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            check_dispatch_guard,
        )

        mocker.patch(
            "adws.adw_modules.steps.dispatch_guard.io_ops.read_issue_notes",
            return_value=IOSuccess(
                "ADWS_FAILED|attempt=1|...",
            ),
        )
        result = check_dispatch_guard("ISSUE-42")
        assert isinstance(result, IOSuccess)
        val = unsafe_perform_io(result.unwrap())
        assert val is False

    def test_fail_open_on_read_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given notes read fails, returns IOSuccess(True) (fail-open)."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            check_dispatch_guard,
        )

        mocker.patch(
            "adws.adw_modules.steps.dispatch_guard.io_ops.read_issue_notes",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.read_issue_notes",
                    error_type="BeadsShowNotesError",
                    message="bd show --notes failed",
                ),
            ),
        )
        result = check_dispatch_guard("ISSUE-42")
        assert isinstance(result, IOSuccess)
        val = unsafe_perform_io(result.unwrap())
        assert val is True


class TestParseIssueList:
    """Tests for parse_issue_list pure function."""

    def test_parses_newline_separated_ids(self) -> None:
        """Given newline-separated issue IDs, returns list."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            parse_issue_list,
        )

        result = parse_issue_list(
            "ISSUE-1\nISSUE-2\nISSUE-3\n",
        )
        assert result == [
            "ISSUE-1",
            "ISSUE-2",
            "ISSUE-3",
        ]

    def test_empty_input_returns_empty_list(self) -> None:
        """Given empty input, returns empty list."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            parse_issue_list,
        )

        assert parse_issue_list("") == []

    def test_whitespace_lines_filtered(self) -> None:
        """Given whitespace-only lines, they are filtered out."""
        from adws.adw_modules.steps.dispatch_guard import (  # noqa: PLC0415
            parse_issue_list,
        )

        result = parse_issue_list(
            "ISSUE-1\n  \n\nISSUE-2\n",
        )
        assert result == ["ISSUE-1", "ISSUE-2"]

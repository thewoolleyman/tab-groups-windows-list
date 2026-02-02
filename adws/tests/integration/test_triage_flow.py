"""Integration tests for triage workflow (Story 7.4)."""
from __future__ import annotations

from datetime import UTC, datetime

from returns.io import IOSuccess

from adws.adw_modules.types import AdwsResponse, ShellResult
from adws.adw_triage import (
    run_triage_cycle,
)


def _shell_ok() -> ShellResult:
    return ShellResult(
        return_code=0, stdout="ok", stderr="", command="bd",
    )


# --- Integration: Tier 1 retry flow ---


def test_integration_tier1_cooldown_retry(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full flow: Tier 1 issue with elapsed cooldown is cleared."""
    # Issue with old failure timestamp (cooldown elapsed)
    notes = (
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T10:00:00Z"
        "|error_class=SdkCallError|step=implement|summary=timeout"
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(notes),
    )
    mock_clear = mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.tier1_cleared == 1
    assert result.issues_found == 1
    mock_clear.assert_called_once_with("ISSUE-1")


def test_integration_tier1_cooldown_not_elapsed(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full flow: Tier 1 issue with recent failure stays pending."""
    # Recent failure (20 min ago, less than 30 min cooldown)
    notes = (
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:40:00Z"
        "|error_class=SdkCallError|step=implement|summary=timeout"
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(notes),
    )
    mock_clear = mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.tier1_pending == 1
    mock_clear.assert_not_called()


# --- Integration: Tier 2 AI triage ---


def test_integration_tier2_adjustment(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full flow: Tier 2 AI recommends adjust, metadata cleared."""
    notes = (
        "ADWS_FAILED|attempt=3|last_failure=2026-02-01T04:00:00Z"
        "|error_class=TestFailureError|step=verify|summary=test fail"
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(notes),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: adjust_parameters|DETAIL: Simplified scope",
                is_error=False,
            ),
        ),
    )
    mock_clear = mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.tier2_adjusted == 1
    mock_clear.assert_called_once()


def test_integration_tier2_split(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full flow: Tier 2 AI recommends split, sub-issues created."""
    notes = (
        "ADWS_FAILED|attempt=3|last_failure=2026-02-01T04:00:00Z"
        "|error_class=SdkCallError|step=implement|summary=repeated fail"
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(notes),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: split|DETAIL: Split into A and B",
                is_error=False,
            ),
        ),
    )
    mock_create = mocker.patch(
        "adws.adw_triage.io_ops.run_beads_create",
        side_effect=[IOSuccess("ISSUE-10"), IOSuccess("ISSUE-11")],
    )
    mock_close = mocker.patch(
        "adws.adw_triage.io_ops.run_beads_close",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.tier2_split == 1
    assert mock_create.call_count == 2
    mock_close.assert_called_once()
    close_reason = mock_close.call_args[0][1]
    assert "ISSUE-10" in close_reason
    assert "ISSUE-11" in close_reason


# --- Integration: Tier 3 human escalation ---


def test_integration_tier3_escalation(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full flow: Tier 3 unknown error tagged needs_human."""
    notes = (
        "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:00:00Z"
        "|error_class=unknown|step=implement|summary=something broke"
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(notes),
    )
    mock_tag = mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.tier3_escalated == 1
    mock_tag.assert_called_once()


# --- Integration: Mixed triage cycle ---


def test_integration_mixed_cycle(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full flow: 4 issues with mixed tiers processed correctly."""
    notes_map = {
        "I-1": (
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T10:00:00Z"
            "|error_class=SdkCallError|step=implement|summary=t1"
        ),
        "I-2": (
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:50:00Z"
            "|error_class=TimeoutError|step=implement|summary=t2"
        ),
        "I-3": (
            "ADWS_FAILED|attempt=3|last_failure=2026-02-01T04:00:00Z"
            "|error_class=TestFailureError|step=verify|summary=t3"
        ),
        "I-4": (
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:00:00Z"
            "|error_class=unknown|step=implement|summary=t4"
        ),
    }
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("I-1\nI-2\nI-3\nI-4\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        side_effect=lambda iid: IOSuccess(notes_map[iid]),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: adjust_parameters|DETAIL: Fixed",
                is_error=False,
            ),
        ),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.issues_found == 4
    assert result.tier1_cleared == 1
    assert result.tier1_pending == 1
    assert result.tier2_adjusted == 1
    assert result.tier3_escalated == 1


# --- Integration: NFR19 compliance ---


def test_integration_nfr19_no_bmad_reads(mocker) -> None:  # type: ignore[no-untyped-def]
    """Full triage flow never calls read_bmad_file (NFR19)."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T10:00:00Z"
            "|error_class=SdkCallError|step=implement|summary=t"
        ),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")
    mock_bmad = mocker.patch(
        "adws.adw_triage.io_ops.read_bmad_file",
    )

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    run_triage_cycle(now)
    mock_bmad.assert_not_called()

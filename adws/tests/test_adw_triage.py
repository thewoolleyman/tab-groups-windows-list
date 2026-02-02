"""Tests for triage workflow module (Story 7.4)."""
from __future__ import annotations

from datetime import UTC, datetime

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.triage import FailureMetadata
from adws.adw_modules.types import AdwsResponse, ShellResult
from adws.adw_triage import (
    TriageCandidate,
    TriageCycleResult,
    TriageResult,
    _build_triage_prompt,
    _parse_triage_response,
    format_triage_summary,
    handle_tier1,
    handle_tier2,
    handle_tier3,
    log_triage_result,
    poll_failed_issues,
    run_triage_cycle,
    run_triage_loop,
    triage_issue,
)

# --- Helper factories ---


def _make_metadata(
    *,
    attempt: int = 1,
    last_failure: str = "2026-02-01T12:00:00Z",
    error_class: str = "SdkCallError",
    step: str = "implement",
    summary: str = "timeout",
) -> FailureMetadata:
    return FailureMetadata(
        attempt=attempt,
        last_failure=last_failure,
        error_class=error_class,
        step=step,
        summary=summary,
    )


def _make_candidate(
    issue_id: str = "ISSUE-1",
    **kwargs: object,
) -> TriageCandidate:
    return TriageCandidate(
        issue_id=issue_id,
        metadata=_make_metadata(**kwargs),  # type: ignore[arg-type]
    )


def _shell_ok() -> ShellResult:
    return ShellResult(
        return_code=0, stdout="ok", stderr="", command="bd",
    )


# --- TriageCandidate tests ---


def test_triage_candidate_is_frozen() -> None:
    """TriageCandidate is a frozen dataclass."""
    c = _make_candidate()
    assert c.issue_id == "ISSUE-1"
    assert c.metadata.attempt == 1


# --- TriageResult tests ---


def test_triage_result_is_frozen() -> None:
    """TriageResult is a frozen dataclass."""
    r = TriageResult(
        issue_id="X-1", tier=1,
        action="cleared_for_retry", detail="ok",
    )
    assert r.issue_id == "X-1"
    assert r.tier == 1


# --- TriageCycleResult tests ---


def test_triage_cycle_result_defaults() -> None:
    """TriageCycleResult has default errors list."""
    r = TriageCycleResult(
        issues_found=0, tier1_cleared=0,
        tier1_pending=0, tier2_adjusted=0,
        tier2_split=0, tier3_escalated=0,
        triage_errors=0,
    )
    assert r.errors == []


# --- _parse_triage_response tests ---


def test_parse_triage_response_adjust() -> None:
    """Parse adjust_parameters action."""
    text = "ACTION: adjust_parameters|DETAIL: Simplified scope"
    result = _parse_triage_response(text)
    assert result is not None
    assert result[0] == "adjust_parameters"
    assert result[1] == "Simplified scope"


def test_parse_triage_response_split() -> None:
    """Parse split action."""
    text = "ACTION: split|DETAIL: Split into A and B"
    result = _parse_triage_response(text)
    assert result is not None
    assert result[0] == "split"
    assert result[1] == "Split into A and B"


def test_parse_triage_response_escalate() -> None:
    """Parse escalate action."""
    text = "ACTION: escalate|DETAIL: Cannot fix automatically"
    result = _parse_triage_response(text)
    assert result is not None
    assert result[0] == "escalate"


def test_parse_triage_response_no_action() -> None:
    """Returns None when no ACTION directive."""
    result = _parse_triage_response("Just some text")
    assert result is None


def test_parse_triage_response_multiline() -> None:
    """Finds ACTION line in multiline response."""
    text = (
        "Let me analyze this...\n"
        "ACTION: adjust_parameters|DETAIL: Fixed\n"
        "Done."
    )
    result = _parse_triage_response(text)
    assert result is not None
    assert result[0] == "adjust_parameters"


def test_parse_triage_response_no_detail() -> None:
    """ACTION without DETAIL returns empty detail string."""
    text = "ACTION: escalate"
    result = _parse_triage_response(text)
    assert result is not None
    assert result[0] == "escalate"
    assert result[1] == ""


# --- _build_triage_prompt tests ---


def test_build_triage_prompt_contains_context() -> None:
    """Triage prompt contains issue context."""
    c = _make_candidate(issue_id="ISSUE-42", attempt=3)
    prompt = _build_triage_prompt(c)
    assert "ISSUE-42" in prompt
    assert "3" in prompt
    assert "SdkCallError" in prompt


# --- poll_failed_issues tests ---


def test_poll_failed_issues_finds_failed(mocker) -> None:  # type: ignore[no-untyped-def]
    """poll_failed_issues returns candidates with ADWS_FAILED metadata."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\nISSUE-2\nISSUE-3\n"),
    )
    notes_map = {
        "ISSUE-1": (
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:00:00Z"
            "|error_class=SdkCallError|step=implement|summary=timeout"
        ),
        "ISSUE-2": "needs_human|reason=unresolvable",
        "ISSUE-3": "",
    }
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        side_effect=lambda iid: IOSuccess(notes_map[iid]),
    )
    result = poll_failed_issues()
    assert isinstance(result, IOSuccess)
    candidates = unsafe_perform_io(result.unwrap())
    assert len(candidates) == 1
    assert candidates[0].issue_id == "ISSUE-1"


def test_poll_failed_issues_empty(mocker) -> None:  # type: ignore[no-untyped-def]
    """No ADWS_FAILED issues returns empty list."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(""),
    )
    result = poll_failed_issues()
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) == []


def test_poll_failed_issues_list_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """IOFailure from run_beads_list propagates."""
    err = PipelineError(
        step_name="io_ops", error_type="BeadsListError",
        message="list failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOFailure(err),
    )
    result = poll_failed_issues()
    assert isinstance(result, IOFailure)


def test_poll_failed_issues_skips_unreadable(mocker) -> None:  # type: ignore[no-untyped-def]
    """Issues with read failures are skipped gracefully."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\nISSUE-2\nISSUE-3\n"),
    )
    err = PipelineError(
        step_name="io_ops", error_type="BeadsShowNotesError",
        message="read failed",
    )
    notes_side = [
        IOSuccess(
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:00:00Z"
            "|error_class=SdkCallError|step=implement|summary=t1"
        ),
        IOFailure(err),
        IOSuccess(
            "ADWS_FAILED|attempt=2|last_failure=2026-02-01T14:00:00Z"
            "|error_class=TimeoutError|step=verify|summary=t3"
        ),
    ]
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        side_effect=notes_side,
    )
    result = poll_failed_issues()
    assert isinstance(result, IOSuccess)
    candidates = unsafe_perform_io(result.unwrap())
    assert len(candidates) == 2
    assert candidates[0].issue_id == "ISSUE-1"
    assert candidates[1].issue_id == "ISSUE-3"


def test_poll_failed_issues_sorted_oldest_first(mocker) -> None:  # type: ignore[no-untyped-def]
    """Candidates sorted by last_failure ascending."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\nISSUE-2\n"),
    )
    notes_map = {
        "ISSUE-1": (
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T14:00:00Z"
            "|error_class=SdkCallError|step=implement|summary=late"
        ),
        "ISSUE-2": (
            "ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:00:00Z"
            "|error_class=SdkCallError|step=implement|summary=early"
        ),
    }
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        side_effect=lambda iid: IOSuccess(notes_map[iid]),
    )
    result = poll_failed_issues()
    candidates = unsafe_perform_io(result.unwrap())
    assert candidates[0].issue_id == "ISSUE-2"
    assert candidates[1].issue_id == "ISSUE-1"


def test_poll_failed_issues_empty_list(mocker) -> None:  # type: ignore[no-untyped-def]
    """Empty beads list returns empty candidates."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess(""),
    )
    result = poll_failed_issues()
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) == []


# --- handle_tier1 tests ---


def test_handle_tier1_cooldown_elapsed(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 1 with elapsed cooldown clears metadata."""
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=1,
        last_failure="2026-02-01T12:00:00Z",
    )
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = handle_tier1(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "cleared_for_retry"
    assert tr.tier == 1


def test_handle_tier1_cooldown_pending(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 1 with pending cooldown does not clear."""
    mock_clear = mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=1,
        last_failure="2026-02-01T12:00:00Z",
    )
    now = datetime(2026, 2, 1, 12, 20, 0, tzinfo=UTC)
    result = handle_tier1(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "cooldown_pending"
    mock_clear.assert_not_called()


def test_handle_tier1_clear_fails(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 1 clear failure degrades gracefully."""
    err = PipelineError(
        step_name="io_ops", error_type="BeadsClearMetadataError",
        message="clear failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOFailure(err),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=1,
        last_failure="2026-02-01T12:00:00Z",
    )
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = handle_tier1(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "clear_failed"


# --- handle_tier2 tests ---


def test_handle_tier2_adjust(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 adjust clears metadata and returns adjusted."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: adjust_parameters|DETAIL: Simplified test scope",
                is_error=False,
            ),
        ),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="TestFailureError",
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "adjusted"
    assert tr.detail == "Simplified test scope"


def test_handle_tier2_split(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 split creates sub-issues and closes original."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: split|DETAIL: Split into subtask A and subtask B",
                is_error=False,
            ),
        ),
    )
    create_side = [
        IOSuccess("ISSUE-10"),
        IOSuccess("ISSUE-11"),
    ]
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_create",
        side_effect=create_side,
    )
    mock_close = mocker.patch(
        "adws.adw_triage.io_ops.run_beads_close",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "split"
    assert "ISSUE-10" in tr.detail
    assert "ISSUE-11" in tr.detail
    mock_close.assert_called_once()
    close_reason = mock_close.call_args[0][1]
    assert "ISSUE-10" in close_reason
    assert "ISSUE-11" in close_reason


def test_handle_tier2_escalate(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 escalation returns escalated_to_tier3."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: escalate|DETAIL: Cannot determine fix automatically",
                is_error=False,
            ),
        ),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_tier3"
    assert "Cannot determine fix" in tr.detail


def test_handle_tier2_sdk_fails(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 SDK failure degrades gracefully."""
    err = PipelineError(
        step_name="io_ops", error_type="SdkCallError",
        message="sdk failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOFailure(err),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "triage_sdk_failed"


def test_handle_tier2_unparseable_response(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 unparseable response degrades gracefully."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="I don't know what to do.",
                is_error=False,
            ),
        ),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "triage_parse_failed"


def test_handle_tier2_split_create_fails(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 split with create failure degrades gracefully."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: split|DETAIL: Split it",
                is_error=False,
            ),
        ),
    )
    err = PipelineError(
        step_name="io_ops", error_type="BeadsCreateError",
        message="create failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_create",
        return_value=IOFailure(err),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "split_failed"


def test_handle_tier2_adjust_clear_fails(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 adjust with clear failure degrades gracefully."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: adjust_parameters|DETAIL: Fix it",
                is_error=False,
            ),
        ),
    )
    err = PipelineError(
        step_name="io_ops", error_type="BeadsClearMetadataError",
        message="clear failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOFailure(err),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "clear_failed"


def test_handle_tier2_split_close_fails(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 split succeeds even when close fails."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: split|DETAIL: Split it",
                is_error=False,
            ),
        ),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_create",
        side_effect=[IOSuccess("ISSUE-10"), IOSuccess("ISSUE-11")],
    )
    err = PipelineError(
        step_name="io_ops", error_type="BeadsCloseError",
        message="close failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_close",
        return_value=IOFailure(err),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
    )
    result = handle_tier2(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    # Split still reports success even when close fails
    assert tr.action == "split"
    assert "ISSUE-10" in tr.detail


# --- handle_tier3 tests ---


def test_handle_tier3_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 3 tags needs_human successfully."""
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", error_class="unknown",
    )
    result = handle_tier3(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_human"
    assert tr.tier == 3


def test_handle_tier3_tag_fails(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 3 tag failure degrades gracefully."""
    err = PipelineError(
        step_name="io_ops", error_type="BeadsTagHumanError",
        message="tag failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOFailure(err),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", error_class="unknown",
    )
    result = handle_tier3(candidate)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalation_failed"


# --- triage_issue tests ---


def test_triage_issue_tier1(mocker) -> None:  # type: ignore[no-untyped-def]
    """triage_issue delegates Tier 1 to handle_tier1."""
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=1,
        last_failure="2026-02-01T12:00:00Z",
    )
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.tier == 1
    assert tr.action == "cleared_for_retry"


def test_triage_issue_tier2(mocker) -> None:  # type: ignore[no-untyped-def]
    """triage_issue delegates Tier 2 to handle_tier2."""
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
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="TestFailureError",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "adjusted"


def test_triage_issue_tier3(mocker) -> None:  # type: ignore[no-untyped-def]
    """triage_issue delegates Tier 3 to handle_tier3."""
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", error_class="unknown",
    )
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.tier == 3
    assert tr.action == "escalated_to_human"


def test_triage_issue_tier2_escalates_to_tier3(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 escalation falls through to handle_tier3."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: escalate|DETAIL: Cannot fix",
                is_error=False,
            ),
        ),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="TestFailureError",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_human"
    assert tr.tier == 3


def test_triage_issue_tier2_sdk_fail_falls_to_tier3(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 SDK failure falls through to Tier 3."""
    err = PipelineError(
        step_name="io_ops", error_type="SdkCallError",
        message="sdk down",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOFailure(err),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="SdkCallError",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_human"


def test_triage_issue_tier2_parse_fail_falls_to_tier3(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 parse failure falls through to Tier 3."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(result="gibberish", is_error=False),
        ),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="SdkCallError",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_human"


def test_triage_issue_tier2_clear_failed_falls_to_tier3(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 adjust with clear failure escalates to Tier 3."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: adjust_parameters|DETAIL: Fix it",
                is_error=False,
            ),
        ),
    )
    err = PipelineError(
        step_name="io_ops", error_type="BeadsClearMetadataError",
        message="clear failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOFailure(err),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="SdkCallError",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_human"
    assert tr.tier == 3


def test_triage_issue_tier2_split_failed_falls_to_tier3(mocker) -> None:  # type: ignore[no-untyped-def]
    """Tier 2 split failure escalates to Tier 3."""
    mocker.patch(
        "adws.adw_triage.io_ops.execute_sdk_call",
        return_value=IOSuccess(
            AdwsResponse(
                result="ACTION: split|DETAIL: Split it",
                is_error=False,
            ),
        ),
    )
    err = PipelineError(
        step_name="io_ops", error_type="BeadsCreateError",
        message="create failed",
    )
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_create",
        return_value=IOFailure(err),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    candidate = _make_candidate(
        issue_id="ISSUE-1", attempt=3,
        error_class="SdkCallError",
    )
    now = datetime(2026, 2, 1, 21, 0, 0, tzinfo=UTC)
    result = triage_issue(candidate, now)
    assert isinstance(result, IOSuccess)
    tr = unsafe_perform_io(result.unwrap())
    assert tr.action == "escalated_to_human"
    assert tr.tier == 3


# --- run_triage_cycle tests ---


def test_run_triage_cycle_mixed(mocker) -> None:  # type: ignore[no-untyped-def]
    """Cycle with mixed results counts correctly."""
    candidates = [
        _make_candidate(
            issue_id="I-1", attempt=1,
            last_failure="2026-02-01T10:00:00Z",
        ),
        _make_candidate(
            issue_id="I-2", attempt=1,
            last_failure="2026-02-01T11:59:00Z",
            error_class="unknown",
        ),
    ]
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess(candidates),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.clear_failure_metadata",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.tag_needs_human",
        return_value=IOSuccess(_shell_ok()),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.issues_found == 2
    assert result.tier1_cleared == 1
    assert result.tier3_escalated == 1


def test_run_triage_cycle_poll_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """Poll failure returns error result."""
    err = PipelineError(
        step_name="io_ops", error_type="BeadsListError",
        message="poll failed",
    )
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOFailure(err),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.issues_found == 0
    assert "poll failed" in result.errors[0]


def test_run_triage_cycle_triage_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """triage_issue IOFailure is recorded, processing continues."""
    candidates = [
        _make_candidate(issue_id="I-1", attempt=1, last_failure="2026-02-01T10:00:00Z"),
        _make_candidate(issue_id="I-2", attempt=1, last_failure="2026-02-01T10:00:00Z"),
    ]
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess(candidates),
    )
    err = PipelineError(
        step_name="triage", error_type="Unexpected",
        message="oops",
    )
    triage_results = [
        IOFailure(err),
        IOSuccess(TriageResult(
            issue_id="I-2", tier=1,
            action="cleared_for_retry", detail="ok",
        )),
    ]
    mocker.patch(
        "adws.adw_triage.triage_issue",
        side_effect=triage_results,
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.issues_found == 2
    assert result.tier1_cleared == 1
    assert result.triage_errors == 1
    assert len(result.errors) == 1


def test_run_triage_cycle_all_types(mocker) -> None:  # type: ignore[no-untyped-def]
    """4 candidates with different results counted correctly."""
    candidates = [
        _make_candidate(
            issue_id="I-1", attempt=1,
            last_failure="2026-02-01T10:00:00Z",
        ),
        _make_candidate(
            issue_id="I-2", attempt=1,
            last_failure="2026-02-01T12:50:00Z",
        ),
        _make_candidate(
            issue_id="I-3", attempt=3,
            last_failure="2026-02-01T10:00:00Z",
        ),
        _make_candidate(
            issue_id="I-4", attempt=1,
            last_failure="2026-02-01T10:00:00Z",
            error_class="unknown",
        ),
    ]
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess(candidates),
    )
    triage_results = [
        IOSuccess(TriageResult(
            issue_id="I-1", tier=1,
            action="cleared_for_retry", detail="ok",
        )),
        IOSuccess(TriageResult(
            issue_id="I-2", tier=1,
            action="cooldown_pending", detail="wait",
        )),
        IOSuccess(TriageResult(
            issue_id="I-3", tier=2,
            action="adjusted", detail="fixed",
        )),
        IOSuccess(TriageResult(
            issue_id="I-4", tier=3,
            action="escalated_to_human", detail="human",
        )),
    ]
    mocker.patch(
        "adws.adw_triage.triage_issue",
        side_effect=triage_results,
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.issues_found == 4
    assert result.tier1_cleared == 1
    assert result.tier1_pending == 1
    assert result.tier2_adjusted == 1
    assert result.tier3_escalated == 1


def test_run_triage_cycle_empty(mocker) -> None:  # type: ignore[no-untyped-def]
    """Empty queue returns all zeros."""
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess([]),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.issues_found == 0
    assert result.tier1_cleared == 0
    assert result.tier1_pending == 0
    assert result.tier2_adjusted == 0
    assert result.tier2_split == 0
    assert result.tier3_escalated == 0
    assert result.triage_errors == 0


def test_run_triage_cycle_unknown_action_counted_as_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """Unknown triage action counted in triage_errors."""
    candidates = [
        _make_candidate(
            issue_id="I-1", attempt=1,
            last_failure="2026-02-01T10:00:00Z",
        ),
    ]
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess(candidates),
    )
    mocker.patch(
        "adws.adw_triage.triage_issue",
        return_value=IOSuccess(TriageResult(
            issue_id="I-1", tier=1, action="clear_failed",
            detail="unexpected",
        )),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.triage_errors == 1


def test_run_triage_cycle_split_counted(mocker) -> None:  # type: ignore[no-untyped-def]
    """Split action counted in tier2_split."""
    candidates = [_make_candidate(issue_id="I-1", attempt=3)]
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess(candidates),
    )
    mocker.patch(
        "adws.adw_triage.triage_issue",
        return_value=IOSuccess(TriageResult(
            issue_id="I-1", tier=2, action="split",
            detail="Split into subs",
        )),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    result = run_triage_cycle(now)
    assert result.tier2_split == 1


# --- format_triage_summary tests ---


def test_format_triage_summary_basic() -> None:
    """format_triage_summary contains key metrics."""
    result = TriageCycleResult(
        issues_found=3, tier1_cleared=1,
        tier1_pending=1, tier2_adjusted=0,
        tier2_split=0, tier3_escalated=1,
        triage_errors=0,
    )
    summary = format_triage_summary(result)
    assert "3 found" in summary
    assert "1 cleared" in summary
    assert "1 pending" in summary
    assert "1 escalated" in summary


def test_format_triage_summary_with_errors() -> None:
    """format_triage_summary includes error count."""
    result = TriageCycleResult(
        issues_found=1, tier1_cleared=0,
        tier1_pending=0, tier2_adjusted=0,
        tier2_split=0, tier3_escalated=0,
        triage_errors=0,
        errors=["Poll failed"],
    )
    summary = format_triage_summary(result)
    assert "1 error" in summary


def test_format_triage_summary_plural_errors() -> None:
    """format_triage_summary pluralizes errors correctly."""
    result = TriageCycleResult(
        issues_found=0, tier1_cleared=0,
        tier1_pending=0, tier2_adjusted=0,
        tier2_split=0, tier3_escalated=0,
        triage_errors=0,
        errors=["err1", "err2"],
    )
    summary = format_triage_summary(result)
    assert "2 errors" in summary


def test_format_triage_summary_combined_errors() -> None:
    """format_triage_summary combines triage_errors and errors list."""
    result = TriageCycleResult(
        issues_found=2, tier1_cleared=0,
        tier1_pending=0, tier2_adjusted=0,
        tier2_split=0, tier3_escalated=0,
        triage_errors=1,
        errors=["poll failed"],
    )
    summary = format_triage_summary(result)
    assert "2 errors" in summary


# --- log_triage_result tests ---


def test_log_triage_result_writes_stderr(mocker) -> None:  # type: ignore[no-untyped-def]
    """log_triage_result writes summary to stderr."""
    mock_stderr = mocker.patch(
        "adws.adw_triage.io_ops.write_stderr",
    )
    result = TriageCycleResult(
        issues_found=1, tier1_cleared=1,
        tier1_pending=0, tier2_adjusted=0,
        tier2_split=0, tier3_escalated=0,
        triage_errors=0,
    )
    log_triage_result(result)
    mock_stderr.assert_called_once()
    written = mock_stderr.call_args[0][0]
    assert "Triage cycle:" in written


# --- run_triage_loop tests ---


def test_run_triage_loop_two_cycles(mocker) -> None:  # type: ignore[no-untyped-def]
    """Loop with max_cycles=2 runs 2 cycles and sleeps once."""
    cycle_results = [
        TriageCycleResult(
            issues_found=1, tier1_cleared=1,
            tier1_pending=0, tier2_adjusted=0,
            tier2_split=0, tier3_escalated=0,
            triage_errors=0,
        ),
        TriageCycleResult(
            issues_found=0, tier1_cleared=0,
            tier1_pending=0, tier2_adjusted=0,
            tier2_split=0, tier3_escalated=0,
            triage_errors=0,
        ),
    ]
    mocker.patch(
        "adws.adw_triage.run_triage_cycle",
        side_effect=cycle_results,
    )
    mock_sleep = mocker.patch(
        "adws.adw_triage.io_ops.sleep_seconds",
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    results = run_triage_loop(60.0, max_cycles=2)
    assert len(results) == 2
    assert mock_sleep.call_count == 1


def test_run_triage_loop_single_cycle(mocker) -> None:  # type: ignore[no-untyped-def]
    """Loop with max_cycles=1 does not sleep."""
    mocker.patch(
        "adws.adw_triage.run_triage_cycle",
        return_value=TriageCycleResult(
            issues_found=0, tier1_cleared=0,
            tier1_pending=0, tier2_adjusted=0,
            tier2_split=0, tier3_escalated=0,
            triage_errors=0,
        ),
    )
    mock_sleep = mocker.patch(
        "adws.adw_triage.io_ops.sleep_seconds",
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    results = run_triage_loop(60.0, max_cycles=1)
    assert len(results) == 1
    mock_sleep.assert_not_called()


def test_run_triage_loop_exception_handled(mocker) -> None:  # type: ignore[no-untyped-def]
    """Exception in run_triage_cycle is caught and loop continues."""
    mocker.patch(
        "adws.adw_triage.run_triage_cycle",
        side_effect=RuntimeError("boom"),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")

    results = run_triage_loop(60.0, max_cycles=1)
    assert len(results) == 1
    assert "boom" in results[0].errors[0]


# --- NFR19 compliance tests ---


def test_poll_failed_issues_no_bmad_reads(mocker) -> None:  # type: ignore[no-untyped-def]
    """poll_failed_issues never calls read_bmad_file (NFR19)."""
    mocker.patch(
        "adws.adw_triage.io_ops.run_beads_list",
        return_value=IOSuccess("ISSUE-1\n"),
    )
    mocker.patch(
        "adws.adw_triage.io_ops.read_issue_notes",
        return_value=IOSuccess(""),
    )
    mock_bmad = mocker.patch(
        "adws.adw_triage.io_ops.read_bmad_file",
    )
    poll_failed_issues()
    mock_bmad.assert_not_called()


def test_run_triage_cycle_no_bmad_reads(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_triage_cycle never calls read_bmad_file (NFR19)."""
    mocker.patch(
        "adws.adw_triage.poll_failed_issues",
        return_value=IOSuccess([]),
    )
    mocker.patch("adws.adw_triage.io_ops.write_stderr")
    mock_bmad = mocker.patch(
        "adws.adw_triage.io_ops.read_bmad_file",
    )
    now = datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)
    run_triage_cycle(now)
    mock_bmad.assert_not_called()

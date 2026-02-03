#!/usr/bin/env python3
"""Triage workflow for self-healing failure recovery (FR48).

Polls Beads for issues with ADWS_FAILED metadata and evaluates
each through a three-tier escalation model:
  Tier 1: Automatic retry with exponential backoff
  Tier 2: AI triage agent analysis
  Tier 3: Human escalation (tags needs_human)

Usage:
    uv run adws/adw_triage.py                          # Run one triage cycle
    uv run adws/adw_triage.py --poll                   # Continuous triage loop
    uv run adws/adw_triage.py --dry-run                # Show failed issues
    uv run adws/adw_triage.py --poll --poll-interval 120   # Triage every 2 min
    uv run adws/adw_triage.py --poll --max-cycles 3    # Run exactly 3 cycles

Examples:
    # Start the autonomous triage loop in the background
    ./scripts/adw-triage.sh --poll &

    # Check what failed issues exist without taking action
    ./scripts/adw-triage.sh --dry-run

NFR19: Never reads BMAD files. Only Beads issue data.
"""
from __future__ import annotations

import sys
from pathlib import Path

# When run as a script, add the project root to sys.path so that
# absolute imports like "from adws.adw_modules..." resolve correctly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.steps.dispatch_guard import parse_issue_list
from adws.adw_modules.steps.triage import (
    FailureMetadata,
    check_cooldown_elapsed,
    classify_failure_tier,
    parse_failure_metadata,
)
from adws.adw_modules.types import AdwsRequest, AdwsResponse

if TYPE_CHECKING:
    from adws.adw_modules.errors import PipelineError

# Re-export for public API
__all__ = [
    "TriageCandidate",
    "TriageCycleResult",
    "TriageResult",
    "format_triage_summary",
    "handle_tier1",
    "handle_tier2",
    "handle_tier3",
    "log_triage_result",
    "poll_failed_issues",
    "run_triage_cycle",
    "run_triage_loop",
    "triage_issue",
]


@dataclass(frozen=True)
class TriageCandidate:
    """A failed issue ready for triage evaluation."""

    issue_id: str
    metadata: FailureMetadata


@dataclass(frozen=True)
class TriageResult:
    """Result of triaging a single issue."""

    issue_id: str
    tier: int
    action: str
    detail: str


@dataclass(frozen=True)
class TriageCycleResult:
    """Result of a single triage cycle."""

    issues_found: int
    tier1_cleared: int
    tier1_pending: int
    tier2_adjusted: int
    tier2_split: int
    tier3_escalated: int
    triage_errors: int
    errors: list[str] = field(default_factory=list)


# --- Tier 2 AI Triage ---

_TRIAGE_SYSTEM_PROMPT = (
    "You are an AI triage agent analyzing a failed workflow issue. "
    "Based on the failure context, recommend ONE of these actions:\n"
    "1. ACTION: adjust_parameters|DETAIL: <description>\n"
    "2. ACTION: split|DETAIL: <description>\n"
    "3. ACTION: escalate|DETAIL: <reason>\n"
    "Respond with exactly one ACTION line."
)


def _build_triage_prompt(candidate: TriageCandidate) -> str:
    """Build the triage agent prompt from failure context."""
    md = candidate.metadata
    return (
        f"Issue: {candidate.issue_id}\n"
        f"Attempt: {md.attempt}\n"
        f"Error class: {md.error_class}\n"
        f"Failed step: {md.step}\n"
        f"Summary: {md.summary}\n"
        f"Last failure: {md.last_failure}\n"
        "\nAnalyze this failure and recommend an action."
    )


def _parse_triage_response(
    result_text: str,
) -> tuple[str, str] | None:
    """Parse ACTION: directive from triage agent response.

    Returns (action, detail) tuple or None if unparseable.
    Simple substring matching for ACTION: prefix. Case-sensitive
    matching because the triage agent prompt specifies exact format.
    """
    for line in result_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ACTION:"):
            content = stripped[len("ACTION:"):].strip()
            if "|DETAIL:" in content:
                action, _, detail = content.partition("|DETAIL:")
                return action.strip(), detail.strip()
            return content.strip(), ""
    return None


# --- Polling ---


def poll_failed_issues() -> IOResult[
    list[TriageCandidate], PipelineError
]:
    """Poll for issues with ADWS_FAILED metadata (FR48).

    Lists open issues, reads notes for each, parses failure
    metadata. Returns candidates sorted by last_failure
    ascending (oldest first per AC #5). Gracefully skips
    issues whose notes cannot be read.
    """
    list_result = io_ops.run_beads_list("open")
    if isinstance(list_result, IOFailure):
        return list_result

    raw_output = unsafe_perform_io(list_result.unwrap())
    all_issues = parse_issue_list(raw_output)

    if not all_issues:
        return IOSuccess([])

    candidates: list[TriageCandidate] = []
    for issue_id in all_issues:
        notes_result = io_ops.read_issue_notes(issue_id)
        if isinstance(notes_result, IOFailure):
            continue  # Skip issues we cannot read

        notes = unsafe_perform_io(notes_result.unwrap())
        metadata = parse_failure_metadata(notes)
        if metadata is not None:
            candidates.append(
                TriageCandidate(
                    issue_id=issue_id,
                    metadata=metadata,
                ),
            )

    # Sort by last_failure ascending (oldest first)
    candidates.sort(key=lambda c: c.metadata.last_failure)
    return IOSuccess(candidates)


# --- Tier Handlers ---


def handle_tier1(
    candidate: TriageCandidate,
    now: datetime,
) -> IOResult[TriageResult, PipelineError]:
    """Handle Tier 1: automatic retry with exponential backoff.

    If cooldown has elapsed, clears ADWS_FAILED metadata so
    the issue re-enters the dispatch pool. If cooldown pending,
    returns a pending result. Degrades gracefully if clear fails.
    """
    if not check_cooldown_elapsed(candidate.metadata, now):
        return IOSuccess(
            TriageResult(
                issue_id=candidate.issue_id,
                tier=1,
                action="cooldown_pending",
                detail=(
                    "Cooldown not elapsed. "
                    f"Attempt {candidate.metadata.attempt}, "
                    "waiting for backoff period."
                ),
            ),
        )

    clear_result = io_ops.clear_failure_metadata(
        candidate.issue_id,
    )
    if isinstance(clear_result, IOFailure):
        err = unsafe_perform_io(clear_result.failure())
        return IOSuccess(
            TriageResult(
                issue_id=candidate.issue_id,
                tier=1,
                action="clear_failed",
                detail=(
                    f"Failed to clear metadata: {err.message}"
                ),
            ),
        )

    return IOSuccess(
        TriageResult(
            issue_id=candidate.issue_id,
            tier=1,
            action="cleared_for_retry",
            detail=(
                "Cooldown elapsed, cleared ADWS_FAILED metadata"
            ),
        ),
    )


def handle_tier2(
    candidate: TriageCandidate,
) -> IOResult[TriageResult, PipelineError]:
    """Handle Tier 2: AI triage agent analysis.

    Calls execute_sdk_call with triage system prompt. Parses
    the response for action directives:
      - adjust_parameters: clear metadata, re-enter dispatch
      - split: create sub-issues, close original
      - escalate: fall through to Tier 3

    Degrades gracefully on SDK failure or unparseable response.
    """
    prompt = _build_triage_prompt(candidate)
    request = AdwsRequest(
        system_prompt=_TRIAGE_SYSTEM_PROMPT,
        prompt=prompt,
    )

    sdk_result = io_ops.execute_sdk_call(request)
    if isinstance(sdk_result, IOFailure):
        err = unsafe_perform_io(sdk_result.failure())
        return IOSuccess(
            TriageResult(
                issue_id=candidate.issue_id,
                tier=2,
                action="triage_sdk_failed",
                detail=f"SDK call failed: {err.message}",
            ),
        )

    response: AdwsResponse = unsafe_perform_io(
        sdk_result.unwrap(),
    )
    result_text = response.result or ""
    parsed = _parse_triage_response(result_text)

    if parsed is None:
        return IOSuccess(
            TriageResult(
                issue_id=candidate.issue_id,
                tier=2,
                action="triage_parse_failed",
                detail=(
                    "Could not parse ACTION directive"
                    f" from response: {result_text[:200]}"
                ),
            ),
        )

    action, detail = parsed

    if action == "adjust_parameters":
        clear_result = io_ops.clear_failure_metadata(
            candidate.issue_id,
        )
        if isinstance(clear_result, IOFailure):
            err = unsafe_perform_io(clear_result.failure())
            return IOSuccess(
                TriageResult(
                    issue_id=candidate.issue_id,
                    tier=2,
                    action="clear_failed",
                    detail=(
                        "Adjust recommended but clear"
                        f" failed: {err.message}"
                    ),
                ),
            )
        return IOSuccess(
            TriageResult(
                issue_id=candidate.issue_id,
                tier=2,
                action="adjusted",
                detail=detail,
            ),
        )

    if action == "split":
        return _handle_tier2_split(candidate, detail)

    # action == "escalate" or unknown action
    return IOSuccess(
        TriageResult(
            issue_id=candidate.issue_id,
            tier=2,
            action="escalated_to_tier3",
            detail=detail or "AI triage recommended escalation",
        ),
    )


def _handle_tier2_split(
    candidate: TriageCandidate,
    detail: str,
) -> IOResult[TriageResult, PipelineError]:
    """Handle Tier 2 split action: create sub-issues, close original."""
    # Create two sub-issues from the split recommendation
    sub_ids: list[str] = []
    for i in range(2):
        create_result = io_ops.run_beads_create(
            f"Sub-task {i + 1} from {candidate.issue_id}",
            f"Split from {candidate.issue_id}: {detail}",
        )
        if isinstance(create_result, IOFailure):
            err = unsafe_perform_io(create_result.failure())
            return IOSuccess(
                TriageResult(
                    issue_id=candidate.issue_id,
                    tier=2,
                    action="split_failed",
                    detail=(
                        f"Failed to create sub-issue: {err.message}"
                    ),
                ),
            )
        sub_id = unsafe_perform_io(create_result.unwrap())
        sub_ids.append(sub_id)

    # Close original
    sub_list = ", ".join(sub_ids)
    close_result = io_ops.run_beads_close(
        candidate.issue_id,
        f"Split into sub-issues: {sub_list}",
    )
    if isinstance(close_result, IOFailure):
        # Sub-issues created but close failed -- still report split
        pass

    return IOSuccess(
        TriageResult(
            issue_id=candidate.issue_id,
            tier=2,
            action="split",
            detail=f"Split into sub-issues: {sub_list}",
        ),
    )


def handle_tier3(
    candidate: TriageCandidate,
) -> IOResult[TriageResult, PipelineError]:
    """Handle Tier 3: human escalation.

    Tags the issue with needs_human metadata. This is the
    ONLY path requiring human attention. Degrades gracefully
    if tagging fails.
    """
    reason = (
        f"Unresolvable failure: {candidate.metadata.error_class}"
        f" at step {candidate.metadata.step}"
        f" (attempt {candidate.metadata.attempt})"
        f" - {candidate.metadata.summary}"
    )
    tag_result = io_ops.tag_needs_human(
        candidate.issue_id, reason,
    )
    if isinstance(tag_result, IOFailure):
        err = unsafe_perform_io(tag_result.failure())
        return IOSuccess(
            TriageResult(
                issue_id=candidate.issue_id,
                tier=3,
                action="escalation_failed",
                detail=(
                    f"Failed to tag needs_human: {err.message}"
                ),
            ),
        )

    return IOSuccess(
        TriageResult(
            issue_id=candidate.issue_id,
            tier=3,
            action="escalated_to_human",
            detail=f"Tagged needs_human: {reason}",
        ),
    )


# --- Orchestrator ---

# Actions that indicate Tier 2 should fall through to Tier 3.
# Includes partial failures (clear_failed, split_failed) to prevent
# expensive repeated SDK calls on issues stuck in Tier 2.
_TIER2_ESCALATION_ACTIONS: frozenset[str] = frozenset({
    "escalated_to_tier3",
    "triage_sdk_failed",
    "triage_parse_failed",
    "clear_failed",
    "split_failed",
})


def triage_issue(
    candidate: TriageCandidate,
    now: datetime,
) -> IOResult[TriageResult, PipelineError]:
    """Classify and dispatch to the appropriate tier handler.

    Classifies the failure, delegates to the tier handler,
    and handles Tier 2 to Tier 3 escalation when the AI
    triage agent recommends it or fails.
    """
    tier = classify_failure_tier(candidate.metadata)

    if tier == 1:
        return handle_tier1(candidate, now)

    if tier == 2:  # noqa: PLR2004
        result = handle_tier2(candidate)
        triage_result: TriageResult = unsafe_perform_io(
            result.unwrap(),
        )
        if triage_result.action in _TIER2_ESCALATION_ACTIONS:
            return handle_tier3(candidate)
        return result

    return handle_tier3(candidate)


# --- Cycle Management ---


def _count_action(
    result: TriageResult,
    counts: dict[str, int],
) -> None:
    """Update cycle counts based on triage result action."""
    action = result.action
    if action == "cleared_for_retry":
        counts["tier1_cleared"] += 1
    elif action == "cooldown_pending":
        counts["tier1_pending"] += 1
    elif action == "adjusted":
        counts["tier2_adjusted"] += 1
    elif action == "split":
        counts["tier2_split"] += 1
    elif action == "escalated_to_human":
        counts["tier3_escalated"] += 1
    else:
        counts["triage_errors"] += 1


def run_triage_cycle(
    now: datetime,
) -> TriageCycleResult:
    """Execute one triage cycle (FR48).

    Polls for failed issues, triages each sequentially.
    Failure on one issue does not prevent processing others.
    """
    poll_result = poll_failed_issues()
    if isinstance(poll_result, IOFailure):
        err = unsafe_perform_io(poll_result.failure())
        return TriageCycleResult(
            issues_found=0,
            tier1_cleared=0,
            tier1_pending=0,
            tier2_adjusted=0,
            tier2_split=0,
            tier3_escalated=0,
            triage_errors=0,
            errors=[str(err.message)],
        )

    candidates = unsafe_perform_io(poll_result.unwrap())
    found = len(candidates)

    if found == 0:
        return TriageCycleResult(
            issues_found=0,
            tier1_cleared=0,
            tier1_pending=0,
            tier2_adjusted=0,
            tier2_split=0,
            tier3_escalated=0,
            triage_errors=0,
            errors=[],
        )

    counts: dict[str, int] = {
        "tier1_cleared": 0,
        "tier1_pending": 0,
        "tier2_adjusted": 0,
        "tier2_split": 0,
        "tier3_escalated": 0,
        "triage_errors": 0,
    }
    errors: list[str] = []

    for candidate in candidates:
        result = triage_issue(candidate, now)
        if isinstance(result, IOFailure):
            err = unsafe_perform_io(result.failure())
            errors.append(str(err.message))
            counts["triage_errors"] += 1
            continue

        triage_result = unsafe_perform_io(result.unwrap())
        _count_action(triage_result, counts)

    return TriageCycleResult(
        issues_found=found,
        tier1_cleared=counts["tier1_cleared"],
        tier1_pending=counts["tier1_pending"],
        tier2_adjusted=counts["tier2_adjusted"],
        tier2_split=counts["tier2_split"],
        tier3_escalated=counts["tier3_escalated"],
        triage_errors=counts["triage_errors"],
        errors=errors,
    )


# --- Terminal Output ---


def format_triage_summary(
    result: TriageCycleResult,
) -> str:
    """Format a TriageCycleResult as a human-readable summary.

    Pure function -- no I/O. Includes all tracked metrics.
    """
    total_errors = result.triage_errors + len(result.errors)
    parts = [
        f"{result.issues_found} found",
        f"{result.tier1_cleared} cleared",
        f"{result.tier1_pending} pending",
        f"{result.tier2_adjusted} adjusted",
        f"{result.tier2_split} split",
        f"{result.tier3_escalated} escalated",
        f"{total_errors} error"
        f"{'s' if total_errors != 1 else ''}",
    ]
    return "Triage cycle: " + ", ".join(parts)


def log_triage_result(
    result: TriageCycleResult,
) -> None:
    """Log a TriageCycleResult to stderr via io_ops."""
    summary = format_triage_summary(result)
    io_ops.write_stderr(summary)


# --- Loop ---


def run_triage_loop(
    poll_interval_seconds: float,
    max_cycles: int | None = None,
) -> list[TriageCycleResult]:
    """Run the triage loop (FR48).

    Repeats triage cycles with sleep between them.
    max_cycles enables testing (avoids infinite loop).
    When max_cycles=None, loops indefinitely.
    """
    results: list[TriageCycleResult] = []
    cycle_count = 0

    while True:
        cycle_count += 1
        try:
            now = datetime.now(tz=UTC)
            cycle_result = run_triage_cycle(now)
        except Exception as exc:  # noqa: BLE001
            cycle_result = TriageCycleResult(
                issues_found=0,
                tier1_cleared=0,
                tier1_pending=0,
                tier2_adjusted=0,
                tier2_split=0,
                tier3_escalated=0,
                triage_errors=0,
                errors=[str(exc)],
            )
        results.append(cycle_result)
        log_triage_result(cycle_result)

        if max_cycles is not None and cycle_count >= max_cycles:
            break

        io_ops.sleep_seconds(poll_interval_seconds)

    return results


# --- CLI Entry Point ---

import click  # noqa: E402


@click.command()
@click.option("--poll", is_flag=True, help="Continuous triage loop")
@click.option(
    "--poll-interval",
    default=300,
    help="Seconds between triage cycles (default: 300)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show failed issues without taking action",
)
@click.option(
    "--max-cycles",
    default=None,
    type=int,
    help="Max triage cycles (default: unlimited in --poll mode, 1 otherwise)",
)
def main(
    poll: bool,
    poll_interval: int,
    dry_run: bool,
    max_cycles: int | None,
) -> None:
    """Poll Beads for failed issues and run triage."""
    if dry_run:
        io_ops.write_stderr("Dry-run mode: showing failed issues")
        poll_result = poll_failed_issues()
        if isinstance(poll_result, IOFailure):
            err = unsafe_perform_io(poll_result.failure())
            io_ops.write_stderr(f"Poll failed: {err.message}")
            sys.exit(1)
        candidates = unsafe_perform_io(poll_result.unwrap())
        if not candidates:
            io_ops.write_stderr("No failed issues found")
        else:
            for c in candidates:
                io_ops.write_stderr(
                    f"  Failed: {c.issue_id}"
                    f" (attempt {c.metadata.attempt},"
                    f" {c.metadata.error_class})"
                )
        return

    cycles = max_cycles
    if cycles is None and not poll:
        cycles = 1

    results = run_triage_loop(
        poll_interval_seconds=float(poll_interval),
        max_cycles=cycles,
    )
    any_errors = any(r.errors for r in results)
    if any_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Cron trigger for autonomous workflow execution (FR21, FR22).

Polls Beads for open issues with dispatchable workflow tags,
applies the dispatch guard to exclude failed/needs-human
issues, and dispatches each ready issue sequentially via
dispatch_and_execute from Story 7.2.

NFR19: Never reads BMAD files. Only Beads issue data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_dispatch import (
    DispatchExecutionResult,
    dispatch_and_execute,
)
from adws.adw_modules import io_ops
from adws.adw_modules.steps.dispatch_guard import (
    check_dispatch_guard,
    parse_issue_list,
)
from adws.adw_modules.steps.extract_workflow_tag import (
    extract_workflow_tag,
)

if TYPE_CHECKING:
    from adws.adw_modules.errors import PipelineError


@dataclass(frozen=True)
class CronCycleResult:
    """Result of a single poll-dispatch cycle.

    issues_found: Number of ready issues found by poll.
    issues_dispatched: Number sent to dispatch_and_execute.
    issues_succeeded: Number with success=True result.
    issues_failed: Number with success=False result.
    issues_skipped: Number with IOFailure from dispatch.
    errors: Error messages from poll or dispatch failures.
    """

    issues_found: int
    issues_dispatched: int
    issues_succeeded: int
    issues_failed: int
    issues_skipped: int
    errors: list[str] = field(default_factory=list)


def _is_dispatchable_issue(
    issue_id: str,
) -> bool:
    """Check if issue has a dispatchable workflow tag.

    Reads description, extracts tag, checks against registry.
    Returns False on any failure (graceful skip).
    """
    from returns.result import Failure  # noqa: PLC0415

    from adws.workflows import (  # noqa: PLC0415
        load_workflow,
    )

    desc_result = io_ops.read_issue_description(issue_id)
    if isinstance(desc_result, IOFailure):
        return False

    description = unsafe_perform_io(desc_result.unwrap())
    tag_result = extract_workflow_tag(description)
    if isinstance(tag_result, Failure):
        return False

    tag = tag_result.unwrap()
    workflow = load_workflow(tag)
    if workflow is None:
        return False

    return workflow.dispatchable


def _passes_dispatch_guard(
    issue_id: str,
) -> bool:
    """Check if issue passes the dispatch guard.

    Returns True if eligible for dispatch, False if should
    be skipped. check_dispatch_guard handles fail-open
    internally via .lash(), always returning IOSuccess.
    """
    guard_result = check_dispatch_guard(issue_id)
    return bool(unsafe_perform_io(guard_result.unwrap()))


def poll_ready_issues() -> IOResult[
    list[str], PipelineError
]:
    """Poll for issues ready for autonomous dispatch (FR21).

    Lists open issues, filters to those with dispatchable
    workflow tags, and applies the dispatch guard.
    """
    list_result = io_ops.run_beads_list("open")
    if isinstance(list_result, IOFailure):
        return list_result

    raw_output = unsafe_perform_io(list_result.unwrap())
    all_issues = parse_issue_list(raw_output)

    if not all_issues:
        return IOSuccess([])

    ready: list[str] = []
    for issue_id in all_issues:
        if not _is_dispatchable_issue(issue_id):
            continue
        if not _passes_dispatch_guard(issue_id):
            continue
        ready.append(issue_id)

    return IOSuccess(ready)


def run_poll_cycle() -> CronCycleResult:
    """Execute one poll-dispatch cycle (FR22).

    Polls for ready issues, dispatches each sequentially.
    Failure on one issue does not prevent processing others.
    """
    poll_result = poll_ready_issues()
    if isinstance(poll_result, IOFailure):
        err = unsafe_perform_io(poll_result.failure())
        return CronCycleResult(
            issues_found=0,
            issues_dispatched=0,
            issues_succeeded=0,
            issues_failed=0,
            issues_skipped=0,
            errors=[str(err.message)],
        )

    ready_issues = unsafe_perform_io(poll_result.unwrap())
    found = len(ready_issues)

    if found == 0:
        return CronCycleResult(
            issues_found=0,
            issues_dispatched=0,
            issues_succeeded=0,
            issues_failed=0,
            issues_skipped=0,
            errors=[],
        )

    succeeded = 0
    failed = 0
    skipped = 0
    dispatched = 0
    errors: list[str] = []

    for issue_id in ready_issues:
        dispatched += 1
        result = dispatch_and_execute(issue_id)
        if isinstance(result, IOFailure):
            skipped += 1
            err = unsafe_perform_io(result.failure())
            errors.append(str(err.message))
            continue

        der: DispatchExecutionResult = unsafe_perform_io(
            result.unwrap(),
        )
        if der.success:
            succeeded += 1
        else:
            failed += 1

    return CronCycleResult(
        issues_found=found,
        issues_dispatched=dispatched,
        issues_succeeded=succeeded,
        issues_failed=failed,
        issues_skipped=skipped,
        errors=errors,
    )


def format_cycle_summary(
    result: CronCycleResult,
) -> str:
    """Format a CronCycleResult as a human-readable summary.

    Pure function -- no I/O.
    """
    parts = [
        f"{result.issues_found} found",
        f"{result.issues_dispatched} dispatched",
        f"{result.issues_succeeded} succeeded",
        f"{result.issues_failed} failed",
        f"{result.issues_skipped} skipped",
    ]
    if result.errors:
        parts.append(
            f"{len(result.errors)} error"
            f"{'s' if len(result.errors) != 1 else ''}"
        )
    return "Cycle complete: " + ", ".join(parts)


def log_cycle_result(
    result: CronCycleResult,
) -> None:
    """Log a CronCycleResult to stderr via io_ops."""
    summary = format_cycle_summary(result)
    io_ops.write_stderr(summary)


def run_trigger_loop(
    poll_interval_seconds: float,
    max_cycles: int | None = None,
) -> list[CronCycleResult]:
    """Run the cron trigger loop (FR22).

    Repeats poll-dispatch cycles with sleep between them.
    max_cycles enables testing (avoids infinite loop).
    When max_cycles=None, loops indefinitely.
    """
    results: list[CronCycleResult] = []
    cycle_count = 0

    while True:
        cycle_count += 1
        try:
            cycle_result = run_poll_cycle()
        except Exception as exc:  # noqa: BLE001
            cycle_result = CronCycleResult(
                issues_found=0,
                issues_dispatched=0,
                issues_succeeded=0,
                issues_failed=0,
                issues_skipped=0,
                errors=[str(exc)],
            )
        results.append(cycle_result)
        log_cycle_result(cycle_result)

        if max_cycles is not None and cycle_count >= max_cycles:
            break

        io_ops.sleep_seconds(poll_interval_seconds)

    return results

"""Dispatch guard for cron trigger (FR47, NFR21).

Checks whether an issue should be skipped based on its
notes metadata. Issues with ADWS_FAILED or needs_human
markers are excluded from dispatch until triage clears
the metadata or a human resolves the issue.

Pure logic in has_active_failure_metadata and parse_issue_list.
IO-dependent logic in check_dispatch_guard.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from returns.io import IOResult, IOSuccess

from adws.adw_modules import io_ops

if TYPE_CHECKING:
    from adws.adw_modules.errors import PipelineError


def has_active_failure_metadata(notes: str) -> bool:
    """Check whether notes contain active failure markers.

    Pure function -- no I/O. Returns True if ADWS_FAILED
    or needs_human is found in the notes string.

    Uses substring matching (case-sensitive). This is safe
    because notes are written by ADWS via build_failure_metadata
    which uses the exact "ADWS_FAILED" prefix, and needs_human
    is a controlled marker set by triage. Both checks are
    case-sensitive to avoid false positives.
    """
    return "ADWS_FAILED" in notes or "needs_human" in notes


def check_dispatch_guard(
    issue_id: str,
) -> IOResult[bool, PipelineError]:
    """Check if an issue is eligible for dispatch (FR47).

    Reads the issue's notes via io_ops and checks for
    failure metadata. Returns IOSuccess(True) if eligible,
    IOSuccess(False) if the issue should be skipped.

    Fail-open behavior: if reading notes fails, assumes
    no failure metadata and allows dispatch (NFR4).
    """
    notes_result = io_ops.read_issue_notes(issue_id)

    def _check_notes(
        notes: str,
    ) -> IOResult[bool, PipelineError]:
        if has_active_failure_metadata(notes):
            return IOSuccess(False)  # noqa: FBT003
        return IOSuccess(True)  # noqa: FBT003

    def _fail_open(
        _: PipelineError,
    ) -> IOResult[bool, PipelineError]:
        return IOSuccess(True)  # noqa: FBT003

    return notes_result.bind(_check_notes).lash(_fail_open)


def parse_issue_list(raw_output: str) -> list[str]:
    """Parse raw bd list JSON stdout into a list of issue IDs.

    Pure function -- no I/O. Parses JSON list of issue objects
    and extracts the 'id' field from each.
    """
    try:
        issues = json.loads(raw_output)
    except json.JSONDecodeError:
        return []

    if not isinstance(issues, list):
        return []

    return [
        str(issue.get("id", "")).strip()
        for issue in issues
        if isinstance(issue, dict) and issue.get("id")
    ]

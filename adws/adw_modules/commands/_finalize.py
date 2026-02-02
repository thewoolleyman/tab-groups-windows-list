"""Shared finalize helpers for command modules (NFR3).

Extracted from build.py to avoid duplication between
/build and /implement commands. Handles Beads issue
close (success) and failure metadata tagging (failure).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from returns.io import IOResult, IOSuccess

from adws.adw_modules import io_ops

if TYPE_CHECKING:
    from adws.adw_modules.errors import PipelineError


def build_failure_metadata(
    error: PipelineError,
    attempt_count: int,
) -> str:
    """Build structured failure metadata string (AC #4).

    Format: ADWS_FAILED|attempt=N|last_failure=ISO|
    error_class=X|step=Y|summary=Z

    Pipe characters in the summary are escaped as backslash
    pipe to prevent field boundary confusion during parsing.
    Attempt count is 1-indexed for human readability.
    """
    ts = datetime.now(tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )
    attempt = max(attempt_count, 1)
    escaped_msg = error.message.replace("|", "\\|")
    return (
        f"ADWS_FAILED"
        f"|attempt={attempt}"
        f"|last_failure={ts}"
        f"|error_class={error.error_type}"
        f"|step={error.step_name}"
        f"|summary={escaped_msg}"
    )


def finalize_on_success(
    issue_id: str | None,
) -> IOResult[str, PipelineError]:
    """Finalize on workflow success -- close Beads issue.

    Returns IOSuccess("closed") on success,
    IOSuccess("close_failed") if bd close fails,
    IOSuccess("skipped") if no issue_id.
    Uses .lash() for fail-open behavior (NFR3).
    """
    if not issue_id:
        return IOSuccess("skipped")

    result = io_ops.run_beads_close(
        issue_id, "Completed successfully",
    )

    def _on_close_ok(
        _: object,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("closed")

    def _on_close_fail(
        _: PipelineError,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("close_failed")

    return result.bind(_on_close_ok).lash(_on_close_fail)


def finalize_on_failure(
    issue_id: str | None,
    error: PipelineError,
    attempt_count: int,
) -> IOResult[str, PipelineError]:
    """Finalize on workflow failure -- tag Beads issue.

    Returns IOSuccess("tagged_failure") on success,
    IOSuccess("tag_failed") if bd update fails,
    IOSuccess("skipped") if no issue_id.
    Uses .lash() for fail-open behavior (NFR3).
    """
    if not issue_id:
        return IOSuccess("skipped")

    metadata = build_failure_metadata(error, attempt_count)
    result = io_ops.run_beads_update_notes(
        issue_id, metadata,
    )

    def _on_update_ok(
        _: object,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("tagged_failure")

    def _on_update_fail(
        _: PipelineError,
    ) -> IOResult[str, PipelineError]:
        return IOSuccess("tag_failed")

    return result.bind(_on_update_ok).lash(_on_update_fail)

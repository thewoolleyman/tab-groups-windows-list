"""Load bundle command -- reload previous session context (FR35).

Reads context bundles from agents/context_bundles/ and parses
JSONL entries produced by FileTrackEntry.to_jsonl(). Non-workflow
command with custom logic, following the /prime pattern.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class LoadBundleResult:
    """User-facing output of the /load_bundle command.

    success: True when bundle loaded successfully.
    session_id: The session ID whose bundle was loaded.
    file_entries: Parsed JSONL entries (list of dicts).
    summary: Human-readable description of what was loaded.
    available_bundles: Populated when bundle not found (AC #2).
    """

    success: bool
    session_id: str
    file_entries: list[dict[str, object]]
    summary: str
    available_bundles: list[str] = field(
        default_factory=list,
    )


def _parse_bundle_content(
    content: str,
) -> list[dict[str, object]]:
    """Parse JSONL bundle content into list of dicts.

    Splits on newlines, skips blank lines, parses each
    line with json.loads(). Skips malformed lines gracefully.
    Skips non-dict JSON values (type validation).
    """
    entries: list[dict[str, object]] = []
    for line in content.splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        entries.append(parsed)
    return entries


def _get_available_bundles() -> list[str]:
    """Get available bundles, returning [] on failure.

    Graceful degradation: listing failure should not
    mask the primary error.
    """
    list_result = io_ops.list_context_bundles()
    if isinstance(list_result, IOSuccess):
        from returns.unsafe import (  # noqa: PLC0415
            unsafe_perform_io,
        )

        return list(
            unsafe_perform_io(list_result.unwrap()),
        )
    return []


def run_load_bundle_command(
    ctx: WorkflowContext,
) -> IOResult[LoadBundleResult, PipelineError]:
    """Execute /load_bundle and return structured result.

    Extracts session_id from ctx.inputs. Reads the bundle
    via io_ops.read_context_bundle. Parses JSONL content.
    Returns LoadBundleResult on success. Lists available
    bundles on missing/not-found session_id (FR28, FR35).
    """
    session_id = ctx.inputs.get("session_id")

    # Validate session_id presence and type
    if (
        not isinstance(session_id, str)
        or not session_id.strip()
    ):
        available = _get_available_bundles()
        return IOFailure(
            PipelineError(
                step_name="commands.load_bundle",
                error_type="MissingSessionIdError",
                message=(
                    "No session_id provided."
                    " Available bundles:"
                    f" {available}"
                ),
                context={
                    "available_bundles": available,
                },
            ),
        )

    sid = str(session_id)
    read_result = io_ops.read_context_bundle(sid)

    if isinstance(read_result, IOFailure):
        from returns.unsafe import (  # noqa: PLC0415
            unsafe_perform_io,
        )

        error = unsafe_perform_io(
            read_result.failure(),
        )

        # For not-found and read errors, list alternatives
        available = _get_available_bundles()
        return IOFailure(
            PipelineError(
                step_name=error.step_name,
                error_type=error.error_type,
                message=error.message,
                context={
                    **error.context,
                    "available_bundles": available,
                },
            ),
        )

    from returns.unsafe import (  # noqa: PLC0415
        unsafe_perform_io,
    )

    content = str(
        unsafe_perform_io(read_result.unwrap()),
    )
    entries = _parse_bundle_content(content)
    count = len(entries)
    noun = "entry" if count == 1 else "entries"
    summary = f"Loaded {count} file {noun} from session {sid}"

    return IOSuccess(
        LoadBundleResult(
            success=True,
            session_id=sid,
            file_entries=entries,
            summary=summary,
            available_bundles=[],
        ),
    )

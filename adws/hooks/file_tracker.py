"""CLI entry point for file tracking.

Invoked by .claude/hooks/file_tracker.sh via:
  uv run python -m adws.hooks.file_tracker

Reads file operation JSON from stdin, tracks it via the shared
track_file_operation_safe step function. Fail-open: any error
is printed to stderr and exits 0 (NFR4).
"""
from __future__ import annotations

import json
import sys

from adws.adw_modules.steps.track_file_operation import (
    track_file_operation_safe,
)
from adws.adw_modules.types import WorkflowContext


def main() -> None:
    """Read stdin JSON, track file operation, exit 0 always (fail-open)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.stderr.write(
                "file_tracker: empty stdin\n",
            )
            return
        data = json.loads(raw)
        if not isinstance(data, dict):
            sys.stderr.write(
                "file_tracker: expected JSON object\n",
            )
            return
        ctx = WorkflowContext(inputs=data)
        track_file_operation_safe(ctx)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"file_tracker: invalid JSON: {exc}\n",
        )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            f"file_tracker: unexpected error: {exc}\n",
        )


def create_file_tracker_hook_matcher() -> (
    dict[str, object]
):
    """Create HookMatcher config for SDK integration (FR36).

    Returns a dict with hook configuration that the SDK
    engine can use to register this hook. The handler
    callable delegates to track_file_operation_safe -- same
    function as the CLI path.
    """

    def _handler(
        event_data: dict[str, object],
        session_id: str,
    ) -> None:
        """Handle SDK hook event (fail-open)."""
        try:
            inputs = {
                **event_data,
                "session_id": session_id,
            }
            ctx = WorkflowContext(inputs=inputs)
            track_file_operation_safe(ctx)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"file_tracker handler: {exc}\n",
            )

    return {
        "hook_name": "file_tracker",
        "hook_types": [
            "PreToolUse",
            "PostToolUse",
        ],
        "handler": _handler,
    }


if __name__ == "__main__":
    main()

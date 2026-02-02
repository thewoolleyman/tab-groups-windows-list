"""CLI entry point for hook event logging.

Invoked by .claude/hooks/hook_logger.sh via:
  uv run python -m adws.hooks.event_logger

Reads hook event JSON from stdin, logs it via the shared
log_hook_event_safe step function. Fail-open: any error
is printed to stderr and exits 0 (NFR4).
"""
from __future__ import annotations

import json
import sys

from adws.adw_modules.steps.log_hook_event import (
    log_hook_event_safe,
)
from adws.adw_modules.types import WorkflowContext


def main() -> None:
    """Read stdin JSON, log event, exit 0 always (fail-open)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.stderr.write(
                "event_logger: empty stdin\n",
            )
            return
        data = json.loads(raw)
        ctx = WorkflowContext(inputs=data)
        log_hook_event_safe(ctx)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"event_logger: invalid JSON: {exc}\n",
        )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            f"event_logger: unexpected error: {exc}\n",
        )


def create_event_logger_hook_matcher() -> (
    dict[str, object]
):
    """Create HookMatcher config for SDK integration (FR36).

    Returns a dict with hook configuration that the SDK
    engine can use to register this hook. The handler
    callable delegates to log_hook_event_safe -- same
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
            log_hook_event_safe(ctx)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"event_logger handler: {exc}\n",
            )

    return {
        "hook_name": "event_logger",
        "hook_types": [
            "PreToolUse",
            "PostToolUse",
            "Notification",
        ],
        "handler": _handler,
    }


if __name__ == "__main__":
    main()

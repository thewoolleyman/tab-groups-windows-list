"""CLI entry point for dangerous command blocking.

Invoked by .claude/hooks/command_blocker.sh via:
  uv run python -m adws.hooks.command_blocker

Reads command JSON from stdin, checks against dangerous patterns
via the shared block_dangerous_command_safe step function.
Fail-open: any error is printed to stderr and exits 0 (NFR4).
"""
from __future__ import annotations

import json
import sys

from returns.io import IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.steps.block_dangerous_command import (
    block_dangerous_command_safe,
)
from adws.adw_modules.types import WorkflowContext


def main() -> None:
    """Read stdin JSON, check command, exit 0 always (fail-open)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.stderr.write(
                "command_blocker: empty stdin\n",
            )
            return
        data = json.loads(raw)
        if not isinstance(data, dict):
            sys.stderr.write(
                "command_blocker:"
                " expected JSON object\n",
            )
            return
        ctx = WorkflowContext(inputs=data)
        result = block_dangerous_command_safe(ctx)
        if isinstance(result, IOSuccess):
            out_ctx = unsafe_perform_io(result.unwrap())
            if out_ctx.outputs.get("blocked"):
                output = {
                    "blocked": True,
                    "reason": out_ctx.outputs.get(
                        "reason", "",
                    ),
                    "alternative": out_ctx.outputs.get(
                        "alternative", "",
                    ),
                }
                sys.stdout.write(
                    json.dumps(output) + "\n",
                )
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"command_blocker: invalid JSON: {exc}\n",
        )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            f"command_blocker:"
            f" unexpected error: {exc}\n",
        )


def create_command_blocker_hook_matcher() -> (
    dict[str, object]
):
    """Create HookMatcher config for SDK integration (FR40).

    Returns a dict with hook configuration that the SDK
    engine can use to register this hook. The handler
    callable delegates to block_dangerous_command_safe --
    same function as the CLI path.
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
            block_dangerous_command_safe(ctx)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"command_blocker handler: {exc}\n",
            )

    return {
        "hook_name": "command_blocker",
        "hook_types": ["PreToolUse"],
        "handler": _handler,
    }


if __name__ == "__main__":
    main()

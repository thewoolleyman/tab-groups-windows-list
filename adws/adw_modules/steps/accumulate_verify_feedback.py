"""Extract structured feedback from verify step failures."""
from __future__ import annotations

from typing import TYPE_CHECKING

from adws.adw_modules.types import VerifyFeedback

if TYPE_CHECKING:
    from adws.adw_modules.errors import PipelineError


def accumulate_verify_feedback(
    error: PipelineError,
    attempt: int,
) -> VerifyFeedback:
    """Extract structured feedback from a verify step failure.

    Parses PipelineError.context for tool_name, errors,
    raw_output. Falls back to PipelineError fields when
    context keys are missing. Works for both VerifyFailed
    errors and other error types.
    """
    ctx = error.context
    tool_name = str(ctx.get("tool_name", "unknown"))
    raw_errors = ctx.get("errors", [])
    errors: list[str] = (
        [str(e) for e in raw_errors]
        if isinstance(raw_errors, list)
        else []
    )
    raw_output = str(ctx.get("raw_output", ""))

    return VerifyFeedback(
        tool_name=tool_name,
        errors=errors,
        raw_output=raw_output,
        attempt=attempt,
        step_name=error.step_name,
    )

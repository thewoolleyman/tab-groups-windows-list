"""Append verify failure feedback to workflow context."""
from __future__ import annotations

from typing import TYPE_CHECKING

from adws.adw_modules.steps.accumulate_verify_feedback import (
    accumulate_verify_feedback,
)

if TYPE_CHECKING:
    from adws.adw_modules.errors import PipelineError
    from adws.adw_modules.types import WorkflowContext


def _escape_field(value: str) -> str:
    """Escape pipe and double-semicolon in field values."""
    return value.replace("|", "\\x7C").replace(
        ";;", "\\x3B\\x3B"
    )


def _serialize_feedback(
    tool_name: str,
    attempt: int,
    step_name: str,
    errors: list[str],
    raw_output: str,
) -> str:
    """Serialize VerifyFeedback to structured string format.

    Format: VERIFY_FEEDBACK|tool=<name>|attempt=<n>|
    step=<step>|errors=<err1>;;<err2>|raw=<output>

    Fields before ``raw`` are escaped so that ``|`` and
    ``;;`` inside values do not corrupt the delimited
    format.  ``raw`` is always last so its value may
    contain unescaped ``|`` characters.
    """
    escaped_errors = [_escape_field(e) for e in errors]
    errors_str = ";;".join(escaped_errors)
    return (
        f"VERIFY_FEEDBACK"
        f"|tool={_escape_field(tool_name)}"
        f"|attempt={attempt}"
        f"|step={_escape_field(step_name)}"
        f"|errors={errors_str}"
        f"|raw={raw_output}"
    )


def add_verify_feedback_to_context(
    ctx: WorkflowContext,
    error: PipelineError,
    attempt: int,
) -> WorkflowContext:
    """Accumulate a verify failure as feedback in context.

    Creates VerifyFeedback from the error, serializes it,
    and appends to ctx.feedback via add_feedback().
    Returns new WorkflowContext (immutable update).
    """
    feedback = accumulate_verify_feedback(error, attempt)
    serialized = _serialize_feedback(
        tool_name=feedback.tool_name,
        attempt=feedback.attempt,
        step_name=feedback.step_name,
        errors=feedback.errors,
        raw_output=feedback.raw_output,
    )
    return ctx.add_feedback(serialized)

"""Hook event logging step functions (FR33, NFR4).

Provides log_hook_event() for core logging and
log_hook_event_safe() for fail-open wrapper behavior.
"""
from __future__ import annotations

from datetime import UTC, datetime

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import HookEvent, WorkflowContext


def log_hook_event(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Log a hook event to session-specific JSONL file.

    Validates required inputs (event_type, hook_name),
    constructs a HookEvent, and delegates to io_ops.
    Returns IOSuccess with hook_event_logged=True on
    success.
    """
    event_type = ctx.inputs.get("event_type")
    if not isinstance(event_type, str) or not event_type:
        return IOFailure(
            PipelineError(
                step_name="log_hook_event",
                error_type="MissingInputError",
                message=(
                    "Required input 'event_type'"
                    " is missing"
                ),
                context={"available_inputs": list(
                    ctx.inputs.keys(),
                )},
            ),
        )

    hook_name = ctx.inputs.get("hook_name")
    if not isinstance(hook_name, str) or not hook_name:
        return IOFailure(
            PipelineError(
                step_name="log_hook_event",
                error_type="MissingInputError",
                message=(
                    "Required input 'hook_name'"
                    " is missing"
                ),
                context={"available_inputs": list(
                    ctx.inputs.keys(),
                )},
            ),
        )

    session_id = ctx.inputs.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        ts = datetime.now(tz=UTC).strftime(
            "%Y%m%d%H%M%S",
        )
        session_id = f"unknown-{ts}"

    payload_raw = ctx.inputs.get("payload")
    payload: dict[str, object] = (
        payload_raw
        if isinstance(payload_raw, dict)
        else {}
    )

    event = HookEvent(
        timestamp=datetime.now(tz=UTC).isoformat(),
        event_type=event_type,
        hook_name=hook_name,
        session_id=session_id,
        payload=payload,
    )

    write_result = io_ops.write_hook_log(
        session_id, event.to_jsonl(),
    )

    def _on_write_failure(
        error: PipelineError,
    ) -> IOResult[None, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="log_hook_event",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )

    def _on_write_success(
        _: None,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.with_updates(
                outputs={"hook_event_logged": True},
            ),
        )

    return (
        write_result
        .lash(_on_write_failure)
        .bind(_on_write_success)
    )


def log_hook_event_safe(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Fail-open wrapper for hook event logging (NFR4).

    Calls log_hook_event(). On failure, logs to stderr
    and returns IOSuccess with failure info in outputs.
    NEVER returns IOFailure -- fail-open means never
    blocking the observed operation.
    """
    result = log_hook_event(ctx)
    if isinstance(result, IOSuccess):
        return result

    error = unsafe_perform_io(result.failure())
    error_msg = str(error)

    io_ops.write_stderr(
        f"log_hook_event_safe: {error_msg}\n",
    )

    return IOSuccess(
        ctx.with_updates(
            outputs={
                "hook_event_logged": False,
                "hook_event_error": error_msg,
            },
        ),
    )

"""File tracking step functions (FR34, NFR4).

Provides track_file_operation() for core file tracking and
track_file_operation_safe() for fail-open wrapper behavior.
"""
from __future__ import annotations

from datetime import UTC, datetime

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import FileTrackEntry, WorkflowContext


def track_file_operation(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Track a file operation to session-specific context bundle.

    Validates required inputs (file_path, operation),
    constructs a FileTrackEntry, and delegates to io_ops.
    Returns IOSuccess with file_tracked=True on success.
    """
    file_path = ctx.inputs.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return IOFailure(
            PipelineError(
                step_name="track_file_operation",
                error_type="MissingInputError",
                message=(
                    "Required input 'file_path'"
                    " is missing"
                ),
                context={"available_inputs": list(
                    ctx.inputs.keys(),
                )},
            ),
        )

    operation = ctx.inputs.get("operation")
    if not isinstance(operation, str) or not operation:
        return IOFailure(
            PipelineError(
                step_name="track_file_operation",
                error_type="MissingInputError",
                message=(
                    "Required input 'operation'"
                    " is missing"
                ),
                context={"available_inputs": list(
                    ctx.inputs.keys(),
                )},
            ),
        )

    valid_operations = {"read", "write"}
    if operation not in valid_operations:
        return IOFailure(
            PipelineError(
                step_name="track_file_operation",
                error_type="InvalidInputError",
                message=(
                    f"Invalid operation '{operation}'."
                    f" Valid operations are"
                    f" 'read' and 'write'"
                ),
                context={
                    "operation": operation,
                    "valid_operations": sorted(
                        valid_operations,
                    ),
                },
            ),
        )

    session_id = ctx.inputs.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        ts = datetime.now(tz=UTC).strftime(
            "%Y%m%d%H%M%S",
        )
        session_id = f"unknown-{ts}"

    hook_name = ctx.inputs.get("hook_name")
    if not isinstance(hook_name, str) or not hook_name:
        hook_name = "file_tracker"

    entry = FileTrackEntry(
        timestamp=datetime.now(tz=UTC).isoformat(),
        file_path=file_path,
        operation=operation,
        session_id=session_id,
        hook_name=hook_name,
    )

    write_result = io_ops.write_context_bundle(
        session_id, entry.to_jsonl(),
    )

    def _on_write_failure(
        error: PipelineError,
    ) -> IOResult[None, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="track_file_operation",
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
                outputs={"file_tracked": True},
            ),
        )

    return (
        write_result
        .lash(_on_write_failure)
        .bind(_on_write_success)
    )


def track_file_operation_safe(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Fail-open wrapper for file tracking (NFR4).

    Calls track_file_operation(). On failure, logs to stderr
    and returns IOSuccess with failure info in outputs.
    NEVER returns IOFailure -- fail-open means never
    blocking the observed operation.
    """
    result = track_file_operation(ctx)
    if isinstance(result, IOSuccess):
        return result

    try:
        error = unsafe_perform_io(result.failure())
        error_msg = str(error)

        io_ops.write_stderr(
            f"track_file_operation_safe: {error_msg}\n",
        )
    except Exception:  # noqa: BLE001
        error_msg = "unknown error (fail-open)"

    return IOSuccess(
        ctx.with_updates(
            outputs={
                "file_tracked": False,
                "file_track_error": error_msg,
            },
        ),
    )

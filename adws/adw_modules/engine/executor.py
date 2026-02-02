"""Engine executor -- sequential step execution with ROP error handling.

Tier 2: orchestrates step execution using IOResult internally.
Workflow definitions (Tier 1) never see ROP internals.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import sleep_seconds
from adws.adw_modules.steps import check_sdk_available, execute_shell_step

if TYPE_CHECKING:
    from adws.adw_modules.engine.types import (
        Step,
        StepFunction,
        Workflow,
    )
    from adws.adw_modules.types import WorkflowContext

_STEP_REGISTRY: dict[str, StepFunction] = {
    "check_sdk_available": check_sdk_available,
    "execute_shell_step": execute_shell_step,
}


def _resolve_step_function(
    function_name: str,
) -> IOResult[StepFunction, PipelineError]:
    """Map function name string to actual step callable.

    Returns IOFailure with helpful error for unknown names.
    """
    step_fn = _STEP_REGISTRY.get(function_name)
    if step_fn is not None:
        return IOSuccess(step_fn)
    available = sorted(_STEP_REGISTRY.keys())
    return IOFailure(
        PipelineError(
            step_name="executor",
            error_type="UnknownStepFunction",
            message=(
                f"Unknown step function '{function_name}'."
                f" Available: {available}"
            ),
            context={
                "function_name": function_name,
                "available": available,
            },
        ),
    )


def run_step(
    step: Step,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute a single step with the given context.

    Dispatches shell steps to execute_shell_step (injecting
    shell_command into context). SDK steps resolve from registry.
    """
    if step.shell:
        shell_ctx = ctx.with_updates(
            inputs={**ctx.inputs, "shell_command": step.command},
        )
        return execute_shell_step(shell_ctx)

    resolved = _resolve_step_function(step.function)
    if isinstance(resolved, IOFailure):
        # Enrich error with the actual step name
        err = unsafe_perform_io(resolved.failure())
        return IOFailure(
            PipelineError(
                step_name=step.name,
                error_type=err.error_type,
                message=err.message,
                context=err.context,
            ),
        )

    step_fn = unsafe_perform_io(resolved.unwrap())
    return step_fn(ctx)


def _run_step_with_retry(
    step: Step,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute step with retry logic.

    Retries up to step.max_attempts times on failure.
    Accumulates failure feedback in context between retries.
    Calls io_ops.sleep_seconds between retry attempts.
    """
    current_ctx = ctx
    last_failure: PipelineError | None = None

    for attempt in range(step.max_attempts):
        result = run_step(step, current_ctx)
        if isinstance(result, IOSuccess):
            return result

        last_failure = unsafe_perform_io(result.failure())

        if attempt < step.max_attempts - 1:
            feedback_entry = (
                f"Retry {attempt + 1}/{step.max_attempts}"
                f" for step '{step.name}':"
                f" {last_failure.message}"
            )
            current_ctx = current_ctx.add_feedback(
                feedback_entry,
            )

            if step.retry_delay_seconds > 0:
                sleep_seconds(step.retry_delay_seconds)

    # All retries exhausted
    assert last_failure is not None  # noqa: S101
    return IOFailure(last_failure)


def run_workflow(
    workflow: Workflow,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute workflow steps sequentially with always_run.

    Normal steps halt on failure. always_run steps execute
    regardless. Retry logic applies to both via
    _run_step_with_retry.
    """
    current_ctx = ctx
    pipeline_failure: PipelineError | None = None
    always_run_failures: list[dict[str, object]] = []

    for i, step in enumerate(workflow.steps):
        if pipeline_failure is not None and not step.always_run:
            continue

        result = _run_step_with_retry(step, current_ctx)

        if isinstance(result, IOFailure):
            error = unsafe_perform_io(result.failure())
            if pipeline_failure is None:
                pipeline_failure = error
            else:
                # Only always_run steps reach here (normal
                # steps are skipped when pipeline has failed)
                always_run_failures.append(
                    error.to_dict(),
                )
            continue

        current_ctx = unsafe_perform_io(result.unwrap())

        if i < len(workflow.steps) - 1:
            try:
                current_ctx = (
                    current_ctx.promote_outputs_to_inputs()
                )
            except ValueError as exc:
                collision = PipelineError(
                    step_name=step.name,
                    error_type="ContextCollisionError",
                    message=str(exc),
                    context={
                        "step_index": i,
                        "step_name": step.name,
                    },
                )
                if pipeline_failure is None:
                    pipeline_failure = collision
                continue

    if pipeline_failure is not None:
        if always_run_failures:
            pipeline_failure = PipelineError(
                step_name=pipeline_failure.step_name,
                error_type=pipeline_failure.error_type,
                message=pipeline_failure.message,
                context={
                    **pipeline_failure.context,
                    "always_run_failures": (
                        always_run_failures
                    ),
                },
            )
        return IOFailure(pipeline_failure)
    return IOSuccess(current_ctx)

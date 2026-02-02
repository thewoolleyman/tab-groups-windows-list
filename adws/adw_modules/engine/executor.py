"""Engine executor -- sequential step execution with ROP error handling.

Tier 2: orchestrates step execution using IOResult internally.
Workflow definitions (Tier 1) never see ROP internals.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
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


def run_workflow(
    workflow: Workflow,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute workflow steps sequentially, halt on failure.

    On success, promotes outputs to inputs between steps.
    On failure, halts and returns PipelineError immediately.

    This story implements ONLY sequential execution and
    halt-on-failure. always_run and retry are Story 2.5.
    """
    current_ctx = ctx
    for i, step in enumerate(workflow.steps):
        result = run_step(step, current_ctx)
        if isinstance(result, IOFailure):
            return result

        current_ctx = unsafe_perform_io(result.unwrap())

        # Promote outputs to inputs for the next step
        # (skip for last step -- no next step needs them)
        if i < len(workflow.steps) - 1:
            try:
                current_ctx = (
                    current_ctx.promote_outputs_to_inputs()
                )
            except ValueError as exc:
                return IOFailure(
                    PipelineError(
                        step_name=step.name,
                        error_type="ContextCollisionError",
                        message=str(exc),
                        context={
                            "step_index": i,
                            "step_name": step.name,
                        },
                    ),
                )

    return IOSuccess(current_ctx)

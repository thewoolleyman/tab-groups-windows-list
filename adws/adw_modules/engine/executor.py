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
from adws.adw_modules.steps import (
    check_sdk_available,
    execute_shell_step,
    implement_step,
    log_hook_event,
    log_hook_event_safe,
    refactor_step,
    run_jest_step,
    run_mypy_step,
    run_playwright_step,
    run_ruff_step,
    track_file_operation,
    track_file_operation_safe,
    verify_tests_fail,
    write_failing_tests,
)

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
    "implement_step": implement_step,
    "log_hook_event": log_hook_event,
    "log_hook_event_safe": log_hook_event_safe,
    "refactor_step": refactor_step,
    "run_jest_step": run_jest_step,
    "run_playwright_step": run_playwright_step,
    "run_mypy_step": run_mypy_step,
    "run_ruff_step": run_ruff_step,
    "track_file_operation": track_file_operation,
    "track_file_operation_safe": track_file_operation_safe,
    "verify_tests_fail": verify_tests_fail,
    "write_failing_tests": write_failing_tests,
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


def _resolve_input_from(
    step: Step,
    ctx: WorkflowContext,
    data_flow_registry: dict[str, dict[str, object]],
) -> IOResult[WorkflowContext, PipelineError]:
    """Resolve input_from mappings and return updated context.

    Returns IOSuccess with updated context on success.
    Returns IOFailure with PipelineError on missing source
    or key collision.
    """
    if step.input_from is None:
        return IOSuccess(ctx)

    resolved_inputs = dict(ctx.inputs)
    for source_name, target_key in step.input_from.items():
        if source_name not in data_flow_registry:
            available = sorted(data_flow_registry.keys())
            return IOFailure(
                PipelineError(
                    step_name=step.name,
                    error_type="MissingInputFromError",
                    message=(
                        f"Step '{step.name}' references"
                        f" output '{source_name}' via"
                        f" input_from, but no step has"
                        f" produced output with that"
                        f" name. Available: {available}"
                    ),
                    context={
                        "source_name": source_name,
                        "available": available,
                        "step_name": step.name,
                    },
                ),
            )
        if target_key in resolved_inputs:
            return IOFailure(
                PipelineError(
                    step_name=step.name,
                    error_type="InputFromCollisionError",
                    message=(
                        f"Step '{step.name}' input_from"
                        f" maps '{source_name}' to key"
                        f" '{target_key}' which already"
                        f" exists in context inputs"
                    ),
                    context={
                        "source_name": source_name,
                        "target_key": target_key,
                        "step_name": step.name,
                    },
                ),
            )
        resolved_inputs[target_key] = (
            data_flow_registry[source_name]
        )

    return IOSuccess(ctx.with_updates(inputs=resolved_inputs))


_SKIP_STEP = True
_RUN_STEP = False


def _should_skip_step(
    step: Step,
    ctx: WorkflowContext,
    pipeline_failure: PipelineError | None,
) -> IOResult[bool, PipelineError]:
    """Determine whether a step should be skipped.

    Returns IOSuccess(True) to skip, IOSuccess(False) to run.
    Returns IOFailure if condition predicate raises.

    Skip rules:
    - Non-always_run steps after pipeline failure: skipped.
    - Steps whose condition predicate returns False: skipped
      (including always_run steps in the failure path).
    """
    if pipeline_failure is not None and not step.always_run:
        return IOSuccess(_SKIP_STEP)
    if step.condition is not None:
        try:
            if not step.condition(ctx):
                return IOSuccess(_SKIP_STEP)
        except Exception as exc:  # noqa: BLE001
            return IOFailure(
                PipelineError(
                    step_name=step.name,
                    error_type="ConditionEvaluationError",
                    message=(
                        f"Step '{step.name}' condition"
                        f" predicate raised: {exc}"
                    ),
                    context={
                        "step_name": step.name,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                ),
            )
    return IOSuccess(_RUN_STEP)


def _record_failure(
    error: PipelineError,
    pipeline_failure: PipelineError | None,
    always_run_failures: list[dict[str, object]],
) -> PipelineError:
    """Record a step or resolution failure.

    Returns the current pipeline failure (original or new).
    """
    if pipeline_failure is None:
        return error
    always_run_failures.append(error.to_dict())
    return pipeline_failure


def _finalize_workflow(
    pipeline_failure: PipelineError | None,
    always_run_failures: list[dict[str, object]],
    current_ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Build final workflow result, attaching always_run info."""
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


def run_workflow(
    workflow: Workflow,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute workflow steps sequentially with data flow.

    Normal steps halt on failure. always_run steps execute
    regardless. Supports condition predicates, output
    registration, and input_from data flow resolution.
    """
    current_ctx = ctx
    pipeline_failure: PipelineError | None = None
    always_run_failures: list[dict[str, object]] = []
    data_flow_registry: dict[str, dict[str, object]] = {}

    for i, step in enumerate(workflow.steps):
        skip_result = _should_skip_step(
            step, current_ctx, pipeline_failure,
        )
        if isinstance(skip_result, IOFailure):
            error = unsafe_perform_io(
                skip_result.failure(),
            )
            pipeline_failure = _record_failure(
                error, pipeline_failure, always_run_failures,
            )
            continue
        if unsafe_perform_io(skip_result.unwrap()):
            continue

        # Resolve input_from mappings
        resolve_result = _resolve_input_from(
            step, current_ctx, data_flow_registry,
        )
        if isinstance(resolve_result, IOFailure):
            error = unsafe_perform_io(
                resolve_result.failure(),
            )
            pipeline_failure = _record_failure(
                error, pipeline_failure, always_run_failures,
            )
            continue
        current_ctx = unsafe_perform_io(
            resolve_result.unwrap(),
        )

        # Execute step with retry
        result = _run_step_with_retry(step, current_ctx)
        if isinstance(result, IOFailure):
            error = unsafe_perform_io(result.failure())
            pipeline_failure = _record_failure(
                error, pipeline_failure, always_run_failures,
            )
            continue

        current_ctx = unsafe_perform_io(result.unwrap())

        # Register output in data flow registry
        if step.output is not None:
            data_flow_registry[step.output] = dict(
                current_ctx.outputs,
            )

        # Promote outputs to inputs for next step
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
                pipeline_failure = _record_failure(
                    collision,
                    pipeline_failure,
                    always_run_failures,
                )
                continue

    return _finalize_workflow(
        pipeline_failure, always_run_failures, current_ctx,
    )

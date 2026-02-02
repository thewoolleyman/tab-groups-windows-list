"""Workflow combinators -- pure data composition (Tier 2).

Combinators produce Workflow/Step dataclasses (Tier 1 types).
They do NOT execute steps or touch ROP. The executor handles
execution. This keeps combinators trivially testable.
"""
from __future__ import annotations

from adws.adw_modules.engine.types import Step, Workflow


def with_verification(
    main_step: Step,
    verify_step: Step,
    *,
    verify_max_attempts: int = 1,
    output_name: str | None = None,
) -> Workflow:
    """Compose a step with its verification step.

    Returns a Workflow where the main step executes first,
    then the verify step runs. The verify step can be
    configured with retry for retry-on-verify-failure.

    Combinators are composable: the returned Workflow
    can be passed to sequence() or other combinators.
    """
    effective_verify = Step(
        name=verify_step.name,
        function=verify_step.function,
        always_run=verify_step.always_run,
        max_attempts=verify_max_attempts,
        retry_delay_seconds=verify_step.retry_delay_seconds,
        shell=verify_step.shell,
        command=verify_step.command,
        output=verify_step.output,
        input_from=verify_step.input_from,
        condition=verify_step.condition,
    )

    name = output_name or f"{main_step.name}_with_verification"
    return Workflow(
        name=name,
        description=f"{main_step.name} with verification",
        steps=[main_step, effective_verify],
        dispatchable=False,
    )


def sequence(
    workflow_a: Workflow,
    workflow_b: Workflow,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Workflow:
    """Compose two workflows into a sequential workflow.

    Returns a new Workflow with steps from A followed
    by steps from B. Context propagates across the
    boundary via the engine's promote_outputs_to_inputs.
    """
    effective_name = name or (
        f"{workflow_a.name}_then_{workflow_b.name}"
    )
    effective_desc = description or (
        f"Sequence: {workflow_a.name} -> {workflow_b.name}"
    )
    return Workflow(
        name=effective_name,
        description=effective_desc,
        steps=[*workflow_a.steps, *workflow_b.steps],
        dispatchable=False,
    )

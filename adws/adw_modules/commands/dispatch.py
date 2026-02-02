"""Command dispatch -- central entry point for all commands (FR28).

Routes command names to their associated workflows via the
command registry. Uses io_ops boundary for workflow loading
and execution. The "verify", "prime", "build", "implement",
and "load_bundle" commands route to specialized handlers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.commands.build import (
    BuildCommandResult,
    run_build_command,
)
from adws.adw_modules.commands.convert_stories import (
    run_convert_stories_command,
)
from adws.adw_modules.commands.implement import (
    ImplementCommandResult,
    run_implement_command,
)
from adws.adw_modules.commands.load_bundle import (
    LoadBundleResult,
    run_load_bundle_command,
)
from adws.adw_modules.commands.prime import (
    PrimeContextResult,
    run_prime_command,
)
from adws.adw_modules.commands.registry import (
    get_command,
    list_commands,
)
from adws.adw_modules.commands.verify import (
    VerifyCommandResult,
    run_verify_command,
)
from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from collections.abc import Callable

    from adws.adw_modules.commands.types import CommandSpec
    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.types import WorkflowContext


def _dispatch_verify(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch /verify to specialized handler."""

    def _wrap(
        vr: VerifyCommandResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs({"verify_result": vr}),
        )

    return run_verify_command(ctx).bind(_wrap)


def _dispatch_prime(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch /prime to specialized handler."""

    def _wrap(
        pr: PrimeContextResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs({"prime_result": pr}),
        )

    return run_prime_command(ctx).bind(_wrap)


def _dispatch_build(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch /build to specialized handler."""

    def _wrap(
        br: BuildCommandResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs({"build_result": br}),
        )

    return run_build_command(ctx).bind(_wrap)


def _dispatch_implement(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch /implement to specialized handler."""

    def _wrap(
        ir: ImplementCommandResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs(
                {"implement_result": ir},
            ),
        )

    return run_implement_command(ctx).bind(_wrap)


def _dispatch_load_bundle(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch /load_bundle to specialized handler."""

    def _wrap(
        lbr: LoadBundleResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs(
                {"load_bundle_result": lbr},
            ),
        )

    return run_load_bundle_command(ctx).bind(_wrap)


def _dispatch_convert_stories(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch /convert_stories_to_beads to command."""
    bmad_file_path = ctx.inputs.get(
        "bmad_file_path", "",
    )
    workflow_name = ctx.inputs.get(
        "workflow_name", "implement_verify_close",
    )
    return run_convert_stories_command(
        str(bmad_file_path),
        str(workflow_name),
    )


_SPECIALIZED_HANDLERS: dict[
    str,
    Callable[
        [WorkflowContext],
        IOResult[WorkflowContext, PipelineError],
    ],
] = {
    "verify": _dispatch_verify,
    "prime": _dispatch_prime,
    "build": _dispatch_build,
    "implement": _dispatch_implement,
    "load_bundle": _dispatch_load_bundle,
    "convert_stories_to_beads": (
        _dispatch_convert_stories
    ),
}


def _dispatch_specialized(
    spec: CommandSpec,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError] | None:
    """Route to specialized handler if applicable.

    Returns None if no specialized handler matches.
    Uses a registry dict to avoid excessive complexity.
    """
    handler = _SPECIALIZED_HANDLERS.get(spec.name)
    if handler is not None:
        return handler(ctx)
    return None


def run_command(
    name: str,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Dispatch a command by name.

    Specialized commands route to their handlers.
    Other workflow-backed commands use the generic
    workflow path. Non-workflow commands without
    specialized handlers return IOFailure. Unknown
    commands return IOFailure with available names.
    """
    spec = get_command(name)
    if spec is None:
        available = sorted(
            cmd.name for cmd in list_commands()
        )
        return IOFailure(
            PipelineError(
                step_name="commands.dispatch",
                error_type="UnknownCommandError",
                message=(
                    f"Unknown command '{name}'."
                    f" Available: {available}"
                ),
                context={
                    "command_name": name,
                    "available": available,
                },
            ),
        )

    # Try specialized handlers first
    specialized = _dispatch_specialized(spec, ctx)
    if specialized is not None:
        return specialized

    # Non-workflow commands without specialized handlers
    if spec.workflow_name is None:
        return IOFailure(
            PipelineError(
                step_name="commands.dispatch",
                error_type="NoWorkflowError",
                message=(
                    f"Command '{name}' does not have an"
                    f" associated workflow"
                ),
                context={"command_name": name},
            ),
        )

    # Generic workflow path for other commands
    load_result = io_ops.load_command_workflow(
        spec.workflow_name,
    )

    def _execute_workflow(
        workflow: Workflow,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return io_ops.execute_command_workflow(
            workflow, ctx,
        )

    return load_result.bind(_execute_workflow)

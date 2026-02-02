"""Verify command -- specialized /verify entry point (FR30).

Provides structured result formatting on top of the verify
workflow from Epic 3. Tool failures produce a success report
(the command succeeded in running the quality gate), not a
command failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from returns.io import IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.types import VerifyResult

if TYPE_CHECKING:
    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.errors import PipelineError
    from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class VerifyCommandResult:
    """User-facing output of the /verify command.

    success: True when all tools passed, False otherwise.
    tool_results: Mapping of tool name to pass/fail.
    summary: Human-readable one-line summary.
    failure_details: Per-tool error descriptions (empty on
    success).
    """

    success: bool
    tool_results: dict[str, bool]
    summary: str
    failure_details: list[str] = field(
        default_factory=list,
    )


def format_verify_success(
    ctx: WorkflowContext,
) -> VerifyCommandResult:
    """Build a success report from workflow context outputs.

    Iterates ctx.outputs values, collects all VerifyResult
    instances, and maps each tool name to its pass status.
    """
    tool_results: dict[str, bool] = {}
    for value in ctx.outputs.values():
        if isinstance(value, VerifyResult):
            tool_results[value.tool_name] = value.passed

    count = len(tool_results)
    summary = f"All {count} check(s) passed"
    return VerifyCommandResult(
        success=True,
        tool_results=tool_results,
        summary=summary,
    )


def _format_tool_detail(
    tool_name: str,
    errors: list[str],
) -> str:
    """Format a single tool failure for the report.

    Compatible with feedback accumulation pattern:
    includes tool name and error list.
    """
    err_list = "; ".join(errors) if errors else "no details"
    return (
        f"{tool_name}: {len(errors)} error(s)"
        f" -- {err_list}"
    )


def format_verify_failure(
    error: PipelineError,
) -> VerifyCommandResult:
    """Build a failure report from a PipelineError.

    Parses the primary failure and any always_run_failures
    to produce a complete report of all failed tools.
    """
    tool_results: dict[str, bool] = {}
    failure_details: list[str] = []

    # Extract primary failure tool info
    tool_name = error.context.get("tool_name")
    if isinstance(tool_name, str):
        tool_results[tool_name] = False
        errors = error.context.get("errors", [])
        error_list = (
            list(errors) if isinstance(errors, list) else []
        )
        failure_details.append(
            _format_tool_detail(tool_name, error_list),
        )

    # Extract always_run_failures
    arf = error.context.get("always_run_failures")
    if isinstance(arf, list):
        for failure_dict in arf:
            if not isinstance(failure_dict, dict):
                continue
            failure_ctx = failure_dict.get("context", {})
            if not isinstance(failure_ctx, dict):
                continue
            f_tool = failure_ctx.get("tool_name")
            if isinstance(f_tool, str):
                tool_results[f_tool] = False
                f_errors = failure_ctx.get("errors", [])
                f_error_list = (
                    list(f_errors)
                    if isinstance(f_errors, list)
                    else []
                )
                failure_details.append(
                    _format_tool_detail(
                        f_tool, f_error_list,
                    ),
                )

    # Fallback: no tool info, just use the error message
    if not tool_results and not failure_details:
        failure_details.append(error.message)

    failed_count = sum(
        1 for v in tool_results.values() if not v
    )
    summary = f"{failed_count} check(s) failed"
    return VerifyCommandResult(
        success=False,
        tool_results=tool_results,
        summary=summary,
        failure_details=failure_details,
    )


def _format_success_result(
    result_ctx: WorkflowContext,
) -> IOResult[VerifyCommandResult, PipelineError]:
    """Wrap format_verify_success in IOSuccess for .bind()."""
    return IOSuccess(format_verify_success(result_ctx))


def _format_failure_result(
    error: PipelineError,
) -> IOResult[VerifyCommandResult, PipelineError]:
    """Convert tool failure to IOSuccess with failure report.

    Tool failures produce a command success (IOSuccess) with
    a VerifyCommandResult indicating which tools failed.
    Uses .lash() to convert IOFailure -> IOSuccess.
    """
    return IOSuccess(format_verify_failure(error))


def run_verify_command(
    ctx: WorkflowContext,
) -> IOResult[VerifyCommandResult, PipelineError]:
    """Execute /verify and return structured result.

    Loads the verify workflow, executes it, and formats
    the result. Tool failures are reported as IOSuccess
    with success=False. IOFailure is reserved for
    infrastructure errors (workflow not found, etc.).
    """
    load_result = io_ops.load_command_workflow("verify")

    def _execute_and_format(
        workflow: Workflow,
    ) -> IOResult[VerifyCommandResult, PipelineError]:
        return (
            io_ops.execute_command_workflow(workflow, ctx)
            .bind(_format_success_result)
            .lash(_format_failure_result)
        )

    return load_result.bind(_execute_and_format)

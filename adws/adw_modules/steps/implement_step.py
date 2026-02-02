"""Implement step -- GREEN phase TDD agent."""
from __future__ import annotations

import re

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsRequest,
    AdwsResponse,
    WorkflowContext,
)

GREEN_PHASE_SYSTEM_PROMPT = (
    "You are a TDD Implementation Agent in the GREEN"
    " phase. Your ONLY job is to write the minimum"
    " code to make failing tests pass.\n"
    "\n"
    "## Rules\n"
    "1. Write MINIMUM implementation code to make all"
    " tests pass.\n"
    "2. Do NOT refactor. Do NOT add features beyond"
    " what tests require.\n"
    "3. Do NOT modify any test files.\n"
    "4. All tests must pass after your changes.\n"
    "5. Maintain 100% line and branch coverage.\n"
    "\n"
    "## Implementation Conventions\n"
    "- All I/O must go through"
    " adws/adw_modules/io_ops.py (NFR10)\n"
    "- Use absolute imports:"
    " from adws.adw_modules.X import Y\n"
    "- One public function per step module"
    " matching the filename\n"
    "- Follow existing patterns in the codebase\n"
    "- File writes use bypassPermissions mode\n"
    "\n"
    "## Output\n"
    "List all source files you created or modified,"
    " one per line, with their full paths."
)


def _build_green_phase_request(
    ctx: WorkflowContext,
) -> AdwsRequest:
    """Build AdwsRequest for the GREEN phase SDK call.

    Pure function: constructs request from context inputs.
    """
    description = ctx.inputs.get("issue_description")
    if isinstance(description, str) and description.strip():
        prompt = (
            "Implement the minimum code to make"
            " all failing tests pass for the"
            " following story:\n\n"
            f"{description}"
        )
    else:
        prompt = (
            "No issue description was provided."
            " Implement the minimum code to make"
            " all failing tests pass based on"
            " the project context you can read"
            " from the repository."
        )

    test_files = ctx.inputs.get("test_files")
    if isinstance(test_files, list) and test_files:
        files_text = "\n".join(str(f) for f in test_files)
        prompt += (
            "\n\n## Test Files to Make Pass\n"
            f"{files_text}"
        )

    if ctx.feedback:
        feedback_text = "\n".join(ctx.feedback)
        prompt += (
            "\n\n## Previous Feedback\n"
            f"{feedback_text}"
        )

    return AdwsRequest(
        model=DEFAULT_CLAUDE_MODEL,
        system_prompt=GREEN_PHASE_SYSTEM_PROMPT,
        prompt=prompt,
        permission_mode="bypassPermissions",
    )


_IMPL_FILE_PATTERN = re.compile(
    r"(adws/adw_modules/\S+\.py)",
)


def _extract_implementation_files(
    response: AdwsResponse,
) -> list[str]:
    """Extract source file paths from SDK response.

    Pure function: uses regex to find adws/adw_modules/
    paths. Returns deduplicated list preserving insertion
    order. Handles None result gracefully.
    """
    if response.result is None:
        return []

    matches = _IMPL_FILE_PATTERN.findall(
        response.result,
    )
    seen: set[str] = set()
    result: list[str] = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


def _process_implement_response(
    response: AdwsResponse,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Process SDK response into updated WorkflowContext.

    Returns IOFailure if response has is_error=True.
    Otherwise extracts implementation files and returns
    IOSuccess.
    """
    if response.is_error:
        return IOFailure(
            PipelineError(
                step_name="implement_step",
                error_type="SdkResponseError",
                message=(
                    "SDK returned error:"
                    f" {response.error_message}"
                ),
                context={
                    "error_message": (
                        response.error_message or ""
                    ),
                },
            ),
        )

    impl_files = _extract_implementation_files(response)
    return IOSuccess(
        ctx.with_updates(
            outputs={
                "implementation_files": impl_files,
                "green_phase_complete": True,
            },
        ),
    )


def implement_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute GREEN phase: implement via SDK agent.

    Builds a GREEN-phase-specific request, calls the SDK,
    and extracts implementation file paths from the
    response.
    """
    request = _build_green_phase_request(ctx)
    sdk_result = io_ops.execute_sdk_call(request)

    def _on_failure(
        error: PipelineError,
    ) -> IOResult[AdwsResponse, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="implement_step",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )

    return (
        sdk_result
        .lash(_on_failure)
        .bind(
            lambda resp: _process_implement_response(
                resp, ctx,
            ),
        )
    )

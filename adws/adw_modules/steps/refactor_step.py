"""Refactor step -- REFACTOR phase TDD agent."""
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

REFACTOR_PHASE_SYSTEM_PROMPT = (
    "You are a TDD Refactor Agent in the REFACTOR"
    " phase. Your ONLY job is to clean up code"
    " without changing behavior.\n"
    "\n"
    "## Rules\n"
    "1. Refactor only. Do NOT change behavior.\n"
    "2. All tests must still pass after your changes.\n"
    "3. Maintain 100% line and branch coverage.\n"
    "4. Improve readability, reduce duplication,"
    " simplify.\n"
    "5. Follow established project patterns.\n"
    "\n"
    "## Refactoring Conventions\n"
    "- All I/O must remain behind"
    " adws/adw_modules/io_ops.py (NFR10)\n"
    "- Use absolute imports:"
    " from adws.adw_modules.X import Y\n"
    "- Preserve existing function signatures\n"
    "- Do NOT add new features or change test"
    " expectations\n"
    "- File writes use bypassPermissions mode\n"
    "\n"
    "## Output\n"
    "List all files you modified, one per line,"
    " with their full paths."
)


def _build_refactor_phase_request(
    ctx: WorkflowContext,
) -> AdwsRequest:
    """Build AdwsRequest for the REFACTOR phase SDK call.

    Pure function: constructs request from context inputs.
    """
    description = ctx.inputs.get("issue_description")
    if isinstance(description, str) and description.strip():
        prompt = (
            "Refactor the implementation for the"
            " following story without changing"
            " behavior:\n\n"
            f"{description}"
        )
    else:
        prompt = (
            "No issue description was provided."
            " Refactor the recently implemented code"
            " without changing behavior, based on"
            " the project context you can read"
            " from the repository."
        )

    impl_files = ctx.inputs.get("implementation_files")
    if isinstance(impl_files, list) and impl_files:
        files_text = "\n".join(
            str(f) for f in impl_files
        )
        prompt += (
            "\n\n## Implementation Files to Refactor\n"
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
        system_prompt=REFACTOR_PHASE_SYSTEM_PROMPT,
        prompt=prompt,
        permission_mode="bypassPermissions",
    )


_REFACTOR_FILE_PATTERN = re.compile(
    r"(adws/\S+\.py)",
)


def _extract_refactored_files(
    response: AdwsResponse,
) -> list[str]:
    """Extract file paths from SDK response.

    Pure function: uses regex to find adws/ paths
    (both source and test files). Returns deduplicated
    list preserving insertion order. Handles None result
    gracefully.
    """
    if response.result is None:
        return []

    matches = _REFACTOR_FILE_PATTERN.findall(
        response.result,
    )
    seen: set[str] = set()
    result: list[str] = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


def _process_refactor_response(
    response: AdwsResponse,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Process SDK response into updated WorkflowContext.

    Returns IOFailure if response has is_error=True.
    Otherwise extracts refactored files and returns
    IOSuccess.
    """
    if response.is_error:
        return IOFailure(
            PipelineError(
                step_name="refactor_step",
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

    refactored = _extract_refactored_files(response)
    return IOSuccess(
        ctx.with_updates(
            outputs={
                "refactored_files": refactored,
                "refactor_phase_complete": True,
            },
        ),
    )


def refactor_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute REFACTOR phase: clean up via SDK agent.

    Builds a REFACTOR-phase-specific request, calls the
    SDK, and extracts refactored file paths from the
    response.
    """
    request = _build_refactor_phase_request(ctx)
    sdk_result = io_ops.execute_sdk_call(request)

    def _on_failure(
        error: PipelineError,
    ) -> IOResult[AdwsResponse, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="refactor_step",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )

    return (
        sdk_result
        .lash(_on_failure)
        .bind(
            lambda resp: _process_refactor_response(
                resp, ctx,
            ),
        )
    )

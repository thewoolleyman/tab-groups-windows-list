"""Write failing tests step -- RED phase TDD agent."""
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

RED_PHASE_SYSTEM_PROMPT = (
    "You are a TDD Test Agent in the RED phase. Your ONLY"
    " job is to write failing tests.\n"
    "\n"
    "## Rules\n"
    "1. Write tests ONLY. Do NOT implement any production"
    " code.\n"
    '2. Every test MUST have a docstring starting with:'
    ' """RED: <expected failure reason>"""\n'
    "3. Tests should fail for EXPECTED reasons:\n"
    "   - ImportError (module does not exist yet)\n"
    "   - AssertionError (function returns wrong value)\n"
    "   - NotImplementedError (function is a stub)\n"
    "   - AttributeError (class missing expected"
    " attribute)\n"
    "4. Tests must NOT fail for BROKEN reasons:\n"
    "   - SyntaxError (your test code is broken)\n"
    "   - IndentationError (your test code is broken)\n"
    "   - NameError in test code (your test code is"
    " broken)\n"
    "\n"
    "## Testing Conventions\n"
    "- Place tests in adws/tests/ mirroring the source"
    " structure\n"
    "- Use pytest as the test framework\n"
    "- Mock all I/O at the adws.adw_modules.io_ops"
    " boundary\n"
    "- Follow test naming: test_<function>_<scenario>\n"
    "- One test file per source module\n"
    "\n"
    "## Output\n"
    "List all test files you created, one per line,"
    " with their full paths."
)


def _build_red_phase_request(
    ctx: WorkflowContext,
) -> AdwsRequest:
    """Build AdwsRequest for the RED phase SDK call.

    Pure function: constructs request from context inputs.
    """
    description = ctx.inputs.get("issue_description")
    if isinstance(description, str) and description.strip():
        prompt = (
            "Write failing tests for the following"
            " story acceptance criteria:\n\n"
            f"{description}"
        )
    else:
        prompt = (
            "No issue description was provided."
            " Write tests based on the project"
            " context you can read from the"
            " repository."
        )

    if ctx.feedback:
        feedback_text = "\n".join(ctx.feedback)
        prompt += (
            "\n\n## Previous Feedback\n"
            f"{feedback_text}"
        )

    return AdwsRequest(
        model=DEFAULT_CLAUDE_MODEL,
        system_prompt=RED_PHASE_SYSTEM_PROMPT,
        prompt=prompt,
        permission_mode="bypassPermissions",
    )


_TEST_FILE_PATTERN = re.compile(r"(adws/tests/\S+\.py)")


def _extract_test_files(
    response: AdwsResponse,
) -> list[str]:
    """Extract test file paths from SDK response.

    Pure function: uses regex to find adws/tests/ paths.
    Returns deduplicated list. Handles None result gracefully.
    """
    if response.result is None:
        return []

    matches = _TEST_FILE_PATTERN.findall(response.result)
    seen: set[str] = set()
    result: list[str] = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    return result


def _process_sdk_response(
    response: AdwsResponse,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Process SDK response into updated WorkflowContext.

    Returns IOFailure if response has is_error=True.
    Otherwise extracts test files and returns IOSuccess.
    """
    if response.is_error:
        return IOFailure(
            PipelineError(
                step_name="write_failing_tests",
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

    test_files = _extract_test_files(response)
    return IOSuccess(
        ctx.with_updates(
            outputs={
                "test_files": test_files,
                "red_phase_complete": True,
            },
        ),
    )


def write_failing_tests(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute RED phase: write failing tests via SDK agent.

    Builds a RED-phase-specific request, calls the SDK,
    and extracts test file paths from the response.
    """
    request = _build_red_phase_request(ctx)
    sdk_result = io_ops.execute_sdk_call(request)

    def _on_failure(
        error: PipelineError,
    ) -> IOResult[AdwsResponse, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="write_failing_tests",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )

    return (
        sdk_result
        .lash(_on_failure)
        .bind(
            lambda resp: _process_sdk_response(resp, ctx),
        )
    )

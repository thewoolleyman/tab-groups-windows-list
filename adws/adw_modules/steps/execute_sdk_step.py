"""Execute generic SDK call step."""
from __future__ import annotations

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsRequest,
    AdwsResponse,
    WorkflowContext,
)

GENERIC_SYSTEM_PROMPT = (
    "You are an expert software engineer assistant. "
    "Your goal is to fulfill the user's request efficiently "
    "and correctly. "
    "All I/O must go through adws/adw_modules/io_ops.py."
)

def execute_sdk_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute generic SDK call from context description."""
    description = ctx.inputs.get("issue_description")
    if not isinstance(description, str) or not description.strip():
        # Try finding description elsewhere or default
        description = "No description provided."

    prompt = description

    request = AdwsRequest(
        model=DEFAULT_CLAUDE_MODEL,
        system_prompt=GENERIC_SYSTEM_PROMPT,
        prompt=prompt,
        permission_mode="bypassPermissions", # Standard for internal tools
    )

    sdk_result = io_ops.execute_sdk_call(request)

    def _on_success(
        response: AdwsResponse,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if response.is_error:
             return IOFailure(
                PipelineError(
                    step_name="execute_sdk_step",
                    error_type="SdkResponseError",
                    message=f"SDK Error: {response.error_message}",
                    context={"error": response.error_message},
                )
             )
        # We don't have structured output extraction here, just pass through
        return IOSuccess(ctx.with_updates(outputs={"sdk_response": response.result}))

    def _on_failure(
        error: PipelineError,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="execute_sdk_step",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )

    return sdk_result.bind(_on_success).lash(_on_failure)

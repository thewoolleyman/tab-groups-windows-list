"""Execute ruff quality gate and capture result in workflow context."""
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import run_ruff_check
from adws.adw_modules.types import VerifyResult, WorkflowContext


def run_ruff_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute ruff and capture VerifyResult in context outputs."""
    result = run_ruff_check()

    def _handle_result(
        verify_result: VerifyResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if not verify_result.passed:
            return IOFailure(
                PipelineError(
                    step_name="run_ruff_step",
                    error_type="VerifyFailed",
                    message=(
                        "ruff check failed:"
                        f" {len(verify_result.errors)}"
                        " error(s)"
                    ),
                    context={
                        "tool_name": verify_result.tool_name,
                        "errors": verify_result.errors,
                        "raw_output": verify_result.raw_output,
                    },
                ),
            )
        return IOSuccess(
            ctx.merge_outputs(
                {"verify_ruff": verify_result},
            ),
        )

    return result.bind(_handle_result)

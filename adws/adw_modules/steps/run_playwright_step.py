"""Execute Playwright quality gate and capture result in workflow context."""
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import run_playwright_tests
from adws.adw_modules.types import VerifyResult, WorkflowContext


def run_playwright_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute Playwright and capture VerifyResult in context outputs."""
    result = run_playwright_tests()

    def _handle_result(
        verify_result: VerifyResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if not verify_result.passed:
            return IOFailure(
                PipelineError(
                    step_name="run_playwright_step",
                    error_type="VerifyFailed",
                    message=(
                        "playwright check failed:"
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
                {"verify_playwright": verify_result},
            ),
        )

    return result.bind(_handle_result)

"""Execute mypy quality gate and capture result in workflow context."""
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import run_mypy_check
from adws.adw_modules.types import VerifyResult, WorkflowContext


def run_mypy_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute mypy and capture VerifyResult in context outputs."""
    result = run_mypy_check()

    def _handle_result(
        verify_result: VerifyResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if not verify_result.passed:
            return IOFailure(
                PipelineError(
                    step_name="run_mypy_step",
                    error_type="VerifyFailed",
                    message=(
                        "mypy check failed:"
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
                {"verify_mypy": verify_result},
            ),
        )

    return result.bind(_handle_result)

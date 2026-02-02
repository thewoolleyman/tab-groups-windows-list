"""Check that the Claude SDK is importable and available."""
from returns.io import IOResult

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import check_sdk_import
from adws.adw_modules.types import WorkflowContext


def check_sdk_available(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Verify Claude SDK is available. Calls io_ops for the actual import check."""
    return check_sdk_import().map(lambda _: ctx)

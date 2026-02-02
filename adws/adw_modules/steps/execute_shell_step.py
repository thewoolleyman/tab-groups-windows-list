"""Execute a shell command and capture results in workflow context."""
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import run_shell_command
from adws.adw_modules.types import ShellResult, WorkflowContext


def execute_shell_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute shell command from context, capture output.

    Reads ``shell_command`` from ctx.inputs. On success (return code 0),
    merges stdout/stderr/return_code into ctx.outputs. On nonzero exit,
    returns IOFailure with full context for debugging.
    """
    command = ctx.inputs.get("shell_command")
    if not isinstance(command, str) or not command.strip():
        return IOFailure(
            PipelineError(
                step_name="execute_shell_step",
                error_type="ValueError",
                message="No shell_command found in context inputs",
                context={"inputs_keys": list(ctx.inputs.keys())},
            ),
        )

    result = run_shell_command(command)

    def _handle_success(
        shell_result: ShellResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if shell_result.return_code != 0:
            return IOFailure(
                PipelineError(
                    step_name="execute_shell_step",
                    error_type="ShellCommandFailed",
                    message=(
                        "Command exited with code"
                        f" {shell_result.return_code}"
                    ),
                    context={
                        "command": command,
                        "return_code": shell_result.return_code,
                        "stdout": shell_result.stdout,
                        "stderr": shell_result.stderr,
                    },
                ),
            )
        return IOSuccess(
            ctx.merge_outputs(
                {
                    "shell_stdout": shell_result.stdout,
                    "shell_stderr": shell_result.stderr,
                    "shell_return_code": shell_result.return_code,
                },
            ),
        )

    return result.bind(_handle_success)

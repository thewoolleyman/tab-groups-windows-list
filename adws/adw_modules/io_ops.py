"""I/O boundary module -- ALL external I/O goes through here (NFR10).

This is the single mock point for the entire test suite.
Steps never import I/O directly; they call io_ops functions.
"""
from __future__ import annotations

import asyncio
import subprocess
import time
from typing import TYPE_CHECKING

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    ResultMessage,
    query,
)
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import (
    AdwsRequest,
    AdwsResponse,
    ShellResult,
    VerifyResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from adws.adw_modules.engine.types import Workflow
    from adws.adw_modules.types import WorkflowContext


def read_file(path: Path) -> IOResult[str, PipelineError]:
    """Read file contents. Returns IOResult, never raises."""
    try:
        return IOSuccess(path.read_text())
    except FileNotFoundError:
        return IOFailure(
            PipelineError(
                step_name="io_ops.read_file",
                error_type="FileNotFoundError",
                message=f"File not found: {path}",
                context={"path": str(path)},
            ),
        )
    except PermissionError:
        return IOFailure(
            PipelineError(
                step_name="io_ops.read_file",
                error_type="PermissionError",
                message=f"Permission denied: {path}",
                context={"path": str(path)},
            ),
        )
    except OSError as exc:
        return IOFailure(
            PipelineError(
                step_name="io_ops.read_file",
                error_type=type(exc).__name__,
                message=f"OS error reading {path}: {exc}",
                context={"path": str(path)},
            ),
        )


def check_sdk_import() -> IOResult[bool, PipelineError]:
    """Check if claude-agent-sdk is importable. Returns IOResult, never raises."""
    try:
        import claude_agent_sdk as _  # noqa: F401, PLC0415

        return IOSuccess(True)  # noqa: FBT003
    except ImportError:
        return IOFailure(
            PipelineError(
                step_name="io_ops.check_sdk_import",
                error_type="ImportError",
                message="claude-agent-sdk is not installed or importable",
                context={},
            ),
        )


class _NoResultError(Exception):
    """Internal exception when SDK yields no ResultMessage."""


async def _execute_sdk_call_async(
    request: AdwsRequest,
) -> AdwsResponse:
    """Internal async helper for SDK call."""
    options = ClaudeAgentOptions(
        system_prompt=request.system_prompt,
        model=request.model,
        allowed_tools=request.allowed_tools or [],
        disallowed_tools=request.disallowed_tools or [],
        max_turns=request.max_turns,
        permission_mode=request.permission_mode,
    )

    result_msg: ResultMessage | None = None
    async for message in query(prompt=request.prompt, options=options):
        if isinstance(message, ResultMessage):
            result_msg = message

    if result_msg is None:
        msg = "No ResultMessage received from SDK"
        raise _NoResultError(msg)

    return AdwsResponse(
        result=result_msg.result,
        cost_usd=result_msg.total_cost_usd,
        duration_ms=result_msg.duration_ms,
        session_id=result_msg.session_id,
        is_error=result_msg.is_error,
        num_turns=result_msg.num_turns,
    )


def execute_sdk_call(
    request: AdwsRequest,
) -> IOResult[AdwsResponse, PipelineError]:
    """Execute SDK call. Synchronous wrapper around async SDK."""
    try:
        response = asyncio.run(_execute_sdk_call_async(request))
    except _NoResultError as exc:
        return IOFailure(
            PipelineError(
                step_name="io_ops.execute_sdk_call",
                error_type="NoResultError",
                message=str(exc),
                context={"prompt": request.prompt},
            ),
        )
    except ClaudeSDKError as exc:
        return IOFailure(
            PipelineError(
                step_name="io_ops.execute_sdk_call",
                error_type=type(exc).__name__,
                message=str(exc),
                context={"prompt": request.prompt},
            ),
        )
    else:
        return IOSuccess(response)


def run_shell_command(
    command: str,
    *,
    timeout: int | None = None,
    cwd: str | None = None,
) -> IOResult[ShellResult, PipelineError]:
    """Execute shell command. Returns IOResult, never raises.

    Uses shell=True intentionally -- this function executes shell command
    strings (e.g. "npm test", "uv run pytest") as pipeline steps.
    Nonzero exit codes are valid results, not errors. The calling step
    decides the policy for nonzero return codes.
    """
    try:
        result = subprocess.run(  # noqa: S602
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return IOFailure(
            PipelineError(
                step_name="io_ops.run_shell_command",
                error_type="TimeoutError",
                message=f"Command timed out after {timeout}s: {command}",
                context={"command": command, "timeout": timeout},
            ),
        )
    except FileNotFoundError:
        return IOFailure(
            PipelineError(
                step_name="io_ops.run_shell_command",
                error_type="FileNotFoundError",
                message=f"Command not found: {command}",
                context={"command": command},
            ),
        )
    except OSError as exc:
        return IOFailure(
            PipelineError(
                step_name="io_ops.run_shell_command",
                error_type=type(exc).__name__,
                message=f"OS error running command: {exc}",
                context={"command": command},
            ),
        )
    else:
        return IOSuccess(
            ShellResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                command=command,
            ),
        )


def sleep_seconds(
    seconds: float,
) -> IOResult[None, PipelineError]:
    """Sleep for specified seconds. Returns IOResult, never raises."""
    try:
        time.sleep(seconds)
    except OSError as exc:
        return IOFailure(
            PipelineError(
                step_name="io_ops.sleep_seconds",
                error_type=type(exc).__name__,
                message=f"Sleep interrupted: {exc}",
                context={"seconds": seconds},
            ),
        )
    else:
        return IOSuccess(None)


# --- Verify pipeline io_ops (Story 3.1) ---


def _build_verify_result(
    shell_result: ShellResult,
    tool_name: str,
    error_filter: Callable[[str], bool],
) -> VerifyResult:
    """Build a VerifyResult from a ShellResult.

    Shared helper for verify io_ops functions. Combines stdout
    and stderr, determines pass/fail from return code, and
    filters error lines using the tool-specific predicate.
    """
    raw = shell_result.stdout + shell_result.stderr
    passed = shell_result.return_code == 0
    errors: list[str] = []
    if not passed:
        errors = [
            line for line in raw.splitlines()
            if error_filter(line)
        ]
    return VerifyResult(
        tool_name=tool_name,
        passed=passed,
        errors=errors,
        raw_output=raw,
    )


def run_jest_tests() -> IOResult[VerifyResult, PipelineError]:
    """Execute npm test (Jest) and return structured result (FR13)."""
    result = run_shell_command("npm test")

    def _handle_result(
        shell_result: ShellResult,
    ) -> IOResult[VerifyResult, PipelineError]:
        return IOSuccess(
            _build_verify_result(
                shell_result,
                "jest",
                lambda line: line.startswith("FAIL "),
            ),
        )

    return result.bind(_handle_result)


def run_playwright_tests() -> IOResult[VerifyResult, PipelineError]:
    """Execute npm run test:e2e (Playwright) and return result (FR14)."""
    result = run_shell_command("npm run test:e2e")

    def _handle_result(
        shell_result: ShellResult,
    ) -> IOResult[VerifyResult, PipelineError]:
        def _pw_filter(line: str) -> bool:
            stripped = line.strip()
            return "failed" in stripped or "Error:" in stripped

        return IOSuccess(
            _build_verify_result(
                shell_result, "playwright", _pw_filter,
            ),
        )

    return result.bind(_handle_result)


def run_mypy_check() -> IOResult[VerifyResult, PipelineError]:
    """Execute uv run mypy adws/ and return result (FR15)."""
    result = run_shell_command("uv run mypy adws/")

    def _handle_result(
        shell_result: ShellResult,
    ) -> IOResult[VerifyResult, PipelineError]:
        return IOSuccess(
            _build_verify_result(
                shell_result,
                "mypy",
                lambda line: ": error:" in line,
            ),
        )

    return result.bind(_handle_result)


def run_ruff_check() -> IOResult[VerifyResult, PipelineError]:
    """Execute uv run ruff check adws/ and return result (FR15)."""
    result = run_shell_command("uv run ruff check adws/")

    def _handle_result(
        shell_result: ShellResult,
    ) -> IOResult[VerifyResult, PipelineError]:
        def _ruff_filter(line: str) -> bool:
            parts = line.split(":")
            return (
                len(parts) >= 4  # noqa: PLR2004
                and parts[1].strip().isdigit()
                and parts[2].strip().isdigit()
            )

        return IOSuccess(
            _build_verify_result(
                shell_result, "ruff", _ruff_filter,
            ),
        )

    return result.bind(_handle_result)


# --- Command infrastructure io_ops (Story 4.1) ---


def load_command_workflow(
    workflow_name: str,
) -> IOResult[Workflow, PipelineError]:
    """Load a workflow by name for command execution.

    Returns IOSuccess(Workflow) or IOFailure(PipelineError)
    if the workflow is not registered.
    """
    from adws.workflows import (  # noqa: PLC0415
        load_workflow,
    )

    workflow = load_workflow(workflow_name)
    if workflow is None:
        return IOFailure(
            PipelineError(
                step_name="io_ops.load_command_workflow",
                error_type="WorkflowNotFoundError",
                message=(
                    f"Workflow '{workflow_name}'"
                    f" is not registered"
                ),
                context={"workflow_name": workflow_name},
            ),
        )
    return IOSuccess(workflow)


def execute_command_workflow(
    workflow: Workflow,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute a workflow through the engine.

    Delegates to run_workflow and returns the result
    as-is (already an IOResult).
    """
    from adws.adw_modules.engine.executor import (  # noqa: PLC0415
        run_workflow,
    )

    return run_workflow(workflow, ctx)

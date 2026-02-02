"""I/O boundary module -- ALL external I/O goes through here (NFR10).

This is the single mock point for the entire test suite.
Steps never import I/O directly; they call io_ops functions.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    ResultMessage,
    query,
)
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import AdwsRequest, AdwsResponse

if TYPE_CHECKING:
    from pathlib import Path


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

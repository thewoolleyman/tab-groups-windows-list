"""I/O boundary module -- ALL external I/O goes through here (NFR10).

This is the single mock point for the entire test suite.
Steps never import I/O directly; they call io_ops functions.
"""
from pathlib import Path

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError


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

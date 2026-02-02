"""Tests for CLI and SDK event_logger entry points."""
from __future__ import annotations

import stat
from pathlib import Path
from typing import TYPE_CHECKING

from returns.io import IOSuccess

from adws.adw_modules.types import WorkflowContext
from adws.hooks.event_logger import (
    create_event_logger_hook_matcher,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- hook_logger.sh tests ---


def _project_root() -> Path:
    """Find project root from test file location."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return current  # pragma: no cover


def test_hook_logger_sh_exists() -> None:
    """hook_logger.sh script exists."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "hook_logger.sh"
    )
    assert script_path.is_file(), (
        f"hook_logger.sh not found at {script_path}"
    )


def test_hook_logger_sh_is_executable() -> None:
    """hook_logger.sh script is executable."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "hook_logger.sh"
    )
    st = script_path.stat()
    assert st.st_mode & stat.S_IXUSR, (
        "hook_logger.sh is not executable"
    )


# --- adws/hooks/__init__.py tests ---


def test_hooks_package_exists() -> None:
    """adws.hooks package is importable."""
    import adws.hooks as _hooks  # noqa: F401, PLC0415


# --- event_logger main() tests ---


def test_event_logger_main_success(
    mocker: MockerFixture,
) -> None:
    """main() reads stdin JSON and calls log_hook_event_safe."""
    stdin_json = (
        '{"event_type": "PreToolUse",'
        ' "hook_name": "tool_logger",'
        ' "session_id": "sess-1",'
        ' "payload": {"tool": "Bash"}}'
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        return_value=stdin_json,
    )
    mock_safe = mocker.patch(
        "adws.hooks.event_logger.log_hook_event_safe",
        return_value=IOSuccess(WorkflowContext()),
    )
    from adws.hooks.event_logger import main  # noqa: PLC0415

    main()
    mock_safe.assert_called_once()
    ctx_arg = mock_safe.call_args[0][0]
    assert isinstance(ctx_arg, WorkflowContext)
    assert ctx_arg.inputs["event_type"] == "PreToolUse"
    assert ctx_arg.inputs["hook_name"] == "tool_logger"


def test_event_logger_main_invalid_json(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr on invalid JSON, exits 0."""
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        return_value="not valid json{{{",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.event_logger.sys.stderr",
    )
    from adws.hooks.event_logger import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "invalid JSON" in msg


def test_event_logger_main_empty_stdin(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr on empty stdin, exits 0."""
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        return_value="",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.event_logger.sys.stderr",
    )
    from adws.hooks.event_logger import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "empty stdin" in msg


def test_event_logger_main_whitespace_stdin(
    mocker: MockerFixture,
) -> None:
    """main() treats whitespace-only stdin as empty."""
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        return_value="   \n  ",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.event_logger.sys.stderr",
    )
    from adws.hooks.event_logger import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "empty stdin" in msg


def test_event_logger_main_unexpected_error(
    mocker: MockerFixture,
) -> None:
    """main() catches unexpected errors, writes to stderr."""
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        side_effect=RuntimeError("boom"),
    )
    mock_stderr = mocker.patch(
        "adws.hooks.event_logger.sys.stderr",
    )
    from adws.hooks.event_logger import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "unexpected error" in msg


def test_event_logger_dunder_main(
    mocker: MockerFixture,
) -> None:
    """__main__ block calls main() when run as script."""
    import runpy  # noqa: PLC0415

    import adws.hooks.event_logger as mod  # noqa: PLC0415

    mocker.patch.object(mod, "main")
    # Direct test: call via runpy
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        return_value="",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stderr",
    )

    runpy.run_module(
        "adws.hooks.event_logger",
        run_name="__main__",
    )


# --- create_event_logger_hook_matcher tests ---


def test_hook_matcher_returns_dict() -> None:
    """create_event_logger_hook_matcher returns a dict."""
    matcher = create_event_logger_hook_matcher()
    assert isinstance(matcher, dict)


def test_hook_matcher_has_hook_name() -> None:
    """HookMatcher has hook_name="event_logger"."""
    matcher = create_event_logger_hook_matcher()
    assert matcher["hook_name"] == "event_logger"


def test_hook_matcher_has_hook_types() -> None:
    """HookMatcher has expected hook_types list."""
    matcher = create_event_logger_hook_matcher()
    hook_types = matcher["hook_types"]
    assert isinstance(hook_types, list)
    assert "PreToolUse" in hook_types
    assert "PostToolUse" in hook_types
    assert "Notification" in hook_types


def test_hook_matcher_has_callable_handler() -> None:
    """HookMatcher handler is callable."""
    matcher = create_event_logger_hook_matcher()
    assert callable(matcher["handler"])


def test_hook_matcher_handler_calls_safe(
    mocker: MockerFixture,
) -> None:
    """HookMatcher handler calls log_hook_event_safe."""
    mock_safe = mocker.patch(
        "adws.hooks.event_logger.log_hook_event_safe",
        return_value=IOSuccess(WorkflowContext()),
    )
    matcher = create_event_logger_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    event_data: dict[str, object] = {
        "event_type": "PreToolUse",
        "tool_name": "Bash",
    }
    handler(event_data, "sess-1")
    mock_safe.assert_called_once()
    ctx_arg = mock_safe.call_args[0][0]
    assert isinstance(ctx_arg, WorkflowContext)
    assert ctx_arg.inputs["event_type"] == "PreToolUse"
    assert ctx_arg.inputs["session_id"] == "sess-1"


def test_hook_matcher_handler_fail_open(
    mocker: MockerFixture,
) -> None:
    """HookMatcher handler catches exceptions, fail-open."""
    mocker.patch(
        "adws.hooks.event_logger.log_hook_event_safe",
        side_effect=RuntimeError("unexpected"),
    )
    mock_stderr = mocker.patch(
        "adws.hooks.event_logger.sys.stderr",
    )
    matcher = create_event_logger_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    # Should not raise
    handler(
        {"event_type": "PreToolUse"}, "sess-1",
    )
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "unexpected" in msg

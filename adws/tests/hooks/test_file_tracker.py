"""Tests for CLI and SDK file_tracker entry points."""
from __future__ import annotations

import stat
from pathlib import Path
from typing import TYPE_CHECKING

from returns.io import IOSuccess

from adws.adw_modules.types import WorkflowContext
from adws.hooks.file_tracker import (
    create_file_tracker_hook_matcher,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- file_tracker.sh tests ---


def _project_root() -> Path:
    """Find project root from test file location."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return current  # pragma: no cover


def test_file_tracker_sh_exists() -> None:
    """file_tracker.sh script exists."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "file_tracker.sh"
    )
    assert script_path.is_file(), (
        f"file_tracker.sh not found at {script_path}"
    )


def test_file_tracker_sh_is_executable() -> None:
    """file_tracker.sh script is executable."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "file_tracker.sh"
    )
    st = script_path.stat()
    assert st.st_mode & stat.S_IXUSR, (
        "file_tracker.sh is not executable"
    )


# --- file_tracker main() tests ---


def test_file_tracker_main_success(
    mocker: MockerFixture,
) -> None:
    """main() reads stdin JSON and calls track_file_operation_safe."""
    stdin_json = (
        '{"file_path": "/some/file.py",'
        ' "operation": "read",'
        ' "session_id": "sess-1",'
        ' "hook_name": "file_tracker"}'
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value=stdin_json,
    )
    mock_safe = mocker.patch(
        "adws.hooks.file_tracker.track_file_operation_safe",
        return_value=IOSuccess(WorkflowContext()),
    )
    from adws.hooks.file_tracker import main  # noqa: PLC0415

    main()
    mock_safe.assert_called_once()
    ctx_arg = mock_safe.call_args[0][0]
    assert isinstance(ctx_arg, WorkflowContext)
    assert ctx_arg.inputs["file_path"] == "/some/file.py"
    assert ctx_arg.inputs["operation"] == "read"


def test_file_tracker_main_invalid_json(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr on invalid JSON, exits 0."""
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value="not valid json{{{",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )
    from adws.hooks.file_tracker import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "invalid JSON" in msg


def test_file_tracker_main_empty_stdin(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr on empty stdin, exits 0."""
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value="",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )
    from adws.hooks.file_tracker import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "empty stdin" in msg


def test_file_tracker_main_whitespace_stdin(
    mocker: MockerFixture,
) -> None:
    """main() treats whitespace-only stdin as empty."""
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value="   \n  ",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )
    from adws.hooks.file_tracker import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "empty stdin" in msg


def test_file_tracker_main_non_dict_json(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr when JSON is not a dict."""
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value="[1, 2, 3]",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )
    from adws.hooks.file_tracker import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "expected JSON object" in msg


def test_file_tracker_main_unexpected_error(
    mocker: MockerFixture,
) -> None:
    """main() catches unexpected errors, writes to stderr."""
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        side_effect=RuntimeError("boom"),
    )
    mock_stderr = mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )
    from adws.hooks.file_tracker import main  # noqa: PLC0415

    # Should not raise
    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "unexpected error" in msg


def test_file_tracker_dunder_main(
    mocker: MockerFixture,
) -> None:
    """__main__ block calls main() when run as script."""
    import runpy  # noqa: PLC0415

    import adws.hooks.file_tracker as mod  # noqa: PLC0415

    mocker.patch.object(mod, "main")
    # Direct test: call via runpy
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value="",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )

    runpy.run_module(
        "adws.hooks.file_tracker",
        run_name="__main__",
    )


# --- create_file_tracker_hook_matcher tests ---


def test_hook_matcher_returns_dict() -> None:
    """create_file_tracker_hook_matcher returns a dict."""
    matcher = create_file_tracker_hook_matcher()
    assert isinstance(matcher, dict)


def test_hook_matcher_has_hook_name() -> None:
    """HookMatcher has hook_name="file_tracker"."""
    matcher = create_file_tracker_hook_matcher()
    assert matcher["hook_name"] == "file_tracker"


def test_hook_matcher_has_hook_types() -> None:
    """HookMatcher has expected hook_types list."""
    matcher = create_file_tracker_hook_matcher()
    hook_types = matcher["hook_types"]
    assert isinstance(hook_types, list)
    assert "PreToolUse" in hook_types
    assert "PostToolUse" in hook_types


def test_hook_matcher_has_callable_handler() -> None:
    """HookMatcher handler is callable."""
    matcher = create_file_tracker_hook_matcher()
    assert callable(matcher["handler"])


def test_hook_matcher_handler_calls_safe(
    mocker: MockerFixture,
) -> None:
    """HookMatcher handler calls track_file_operation_safe."""
    mock_safe = mocker.patch(
        "adws.hooks.file_tracker.track_file_operation_safe",
        return_value=IOSuccess(WorkflowContext()),
    )
    matcher = create_file_tracker_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    event_data: dict[str, object] = {
        "file_path": "/some/file.py",
        "operation": "write",
    }
    handler(event_data, "sess-1")
    mock_safe.assert_called_once()
    ctx_arg = mock_safe.call_args[0][0]
    assert isinstance(ctx_arg, WorkflowContext)
    assert ctx_arg.inputs["file_path"] == "/some/file.py"
    assert ctx_arg.inputs["session_id"] == "sess-1"


def test_hook_matcher_handler_fail_open(
    mocker: MockerFixture,
) -> None:
    """HookMatcher handler catches exceptions, fail-open."""
    mocker.patch(
        "adws.hooks.file_tracker.track_file_operation_safe",
        side_effect=RuntimeError("unexpected"),
    )
    mock_stderr = mocker.patch(
        "adws.hooks.file_tracker.sys.stderr",
    )
    matcher = create_file_tracker_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    # Should not raise
    handler(
        {"file_path": "/some/file.py", "operation": "read"},
        "sess-1",
    )
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "unexpected" in msg

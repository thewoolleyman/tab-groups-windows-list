"""Tests for CLI and SDK command_blocker entry points."""
from __future__ import annotations

import stat
from pathlib import Path
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext
from adws.hooks.command_blocker import (
    create_command_blocker_hook_matcher,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- command_blocker.sh tests ---


def _project_root() -> Path:
    """Find project root from test file location."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return current  # pragma: no cover


def test_command_blocker_sh_exists() -> None:
    """command_blocker.sh script exists."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "command_blocker.sh"
    )
    assert script_path.is_file(), (
        f"command_blocker.sh not found at {script_path}"
    )


def test_command_blocker_sh_is_executable() -> None:
    """command_blocker.sh script is executable."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "command_blocker.sh"
    )
    st = script_path.stat()
    assert st.st_mode & stat.S_IXUSR, (
        "command_blocker.sh is not executable"
    )


def test_command_blocker_sh_delegates_to_python() -> None:
    """command_blocker.sh delegates to Python module."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "command_blocker.sh"
    )
    content = script_path.read_text()
    assert (
        "uv run python -m adws.hooks.command_blocker"
        in content
    )
    assert "|| true" in content


def test_command_blocker_sh_no_standalone_logic() -> None:
    """command_blocker.sh has no standalone logic (NFR20)."""
    script_path = (
        _project_root()
        / ".claude" / "hooks" / "command_blocker.sh"
    )
    content = script_path.read_text()
    lines = [
        line.strip()
        for line in content.strip().splitlines()
        if line.strip()
        and not line.strip().startswith("#")
        and not line.strip().startswith("#!/")
    ]
    # Only one non-comment line: the uv run command
    assert len(lines) == 1
    assert "adws.hooks.command_blocker" in lines[0]


# --- command_blocker main() tests ---


def test_command_blocker_main_dangerous(
    mocker: MockerFixture,
) -> None:
    """main() blocks dangerous command and writes to stdout."""
    stdin_json = '{"command": "rm -rf /"}'
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value=stdin_json,
    )
    mock_safe = mocker.patch(
        "adws.hooks.command_blocker"
        ".block_dangerous_command_safe",
        return_value=IOSuccess(
            WorkflowContext(
                outputs={
                    "blocked": True,
                    "reason": "Dangerous",
                    "alternative": "Safer way",
                },
            ),
        ),
    )
    mock_stdout = mocker.patch(
        "adws.hooks.command_blocker.sys.stdout",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_safe.assert_called_once()
    ctx_arg = mock_safe.call_args[0][0]
    assert isinstance(ctx_arg, WorkflowContext)
    assert ctx_arg.inputs["command"] == "rm -rf /"
    mock_stdout.write.assert_called_once()
    written = mock_stdout.write.call_args[0][0]
    assert "blocked" in written
    assert "true" in written.lower()


def test_command_blocker_main_result_not_io_success(
    mocker: MockerFixture,
) -> None:
    """main() handles non-IOSuccess result gracefully."""
    stdin_json = '{"command": "npm test"}'
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value=stdin_json,
    )
    mocker.patch(
        "adws.hooks.command_blocker"
        ".block_dangerous_command_safe",
        return_value=IOFailure(
            PipelineError(
                step_name="test",
                error_type="TestError",
                message="simulated",
            ),
        ),
    )
    mock_stdout = mocker.patch(
        "adws.hooks.command_blocker.sys.stdout",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stdout.write.assert_not_called()


def test_command_blocker_main_safe(
    mocker: MockerFixture,
) -> None:
    """main() does not write to stdout for safe commands."""
    stdin_json = '{"command": "npm test"}'
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value=stdin_json,
    )
    mocker.patch(
        "adws.hooks.command_blocker"
        ".block_dangerous_command_safe",
        return_value=IOSuccess(
            WorkflowContext(
                outputs={"blocked": False},
            ),
        ),
    )
    mock_stdout = mocker.patch(
        "adws.hooks.command_blocker.sys.stdout",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stdout.write.assert_not_called()


def test_command_blocker_main_empty_stdin(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr on empty stdin."""
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value="",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "empty stdin" in msg


def test_command_blocker_main_whitespace_stdin(
    mocker: MockerFixture,
) -> None:
    """main() treats whitespace-only stdin as empty."""
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value="   \n  ",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "empty stdin" in msg


def test_command_blocker_main_invalid_json(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr on invalid JSON."""
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value="not valid json{{{",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "invalid JSON" in msg


def test_command_blocker_main_non_dict_json(
    mocker: MockerFixture,
) -> None:
    """main() writes error to stderr when JSON is not a dict."""
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value="[1, 2, 3]",
    )
    mock_stderr = mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "expected JSON object" in msg


def test_command_blocker_main_unexpected_error(
    mocker: MockerFixture,
) -> None:
    """main() catches unexpected errors, writes to stderr."""
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        side_effect=RuntimeError("boom"),
    )
    mock_stderr = mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )
    from adws.hooks.command_blocker import main  # noqa: PLC0415

    main()
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "unexpected error" in msg


def test_command_blocker_dunder_main(
    mocker: MockerFixture,
) -> None:
    """__main__ block calls main() when run as script."""
    import runpy  # noqa: PLC0415

    import adws.hooks.command_blocker as mod  # noqa: PLC0415

    mocker.patch.object(mod, "main")
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stdin.read",
        return_value="",
    )
    mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )

    runpy.run_module(
        "adws.hooks.command_blocker",
        run_name="__main__",
    )


# --- create_command_blocker_hook_matcher tests ---


def test_hook_matcher_returns_dict() -> None:
    """create_command_blocker_hook_matcher returns a dict."""
    matcher = create_command_blocker_hook_matcher()
    assert isinstance(matcher, dict)


def test_hook_matcher_has_hook_name() -> None:
    """HookMatcher has hook_name="command_blocker"."""
    matcher = create_command_blocker_hook_matcher()
    assert matcher["hook_name"] == "command_blocker"


def test_hook_matcher_has_hook_types() -> None:
    """HookMatcher has expected hook_types list."""
    matcher = create_command_blocker_hook_matcher()
    hook_types = matcher["hook_types"]
    assert isinstance(hook_types, list)
    assert "PreToolUse" in hook_types


def test_hook_matcher_has_callable_handler() -> None:
    """HookMatcher handler is callable."""
    matcher = create_command_blocker_hook_matcher()
    assert callable(matcher["handler"])


def test_hook_matcher_handler_calls_safe(
    mocker: MockerFixture,
) -> None:
    """HookMatcher handler calls block_dangerous_command_safe."""
    mock_safe = mocker.patch(
        "adws.hooks.command_blocker"
        ".block_dangerous_command_safe",
        return_value=IOSuccess(WorkflowContext()),
    )
    matcher = create_command_blocker_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    event_data: dict[str, object] = {
        "command": "rm -rf /",
    }
    handler(event_data, "sess-1")
    mock_safe.assert_called_once()
    ctx_arg = mock_safe.call_args[0][0]
    assert isinstance(ctx_arg, WorkflowContext)
    assert ctx_arg.inputs["command"] == "rm -rf /"
    assert ctx_arg.inputs["session_id"] == "sess-1"


def test_hook_matcher_handler_fail_open(
    mocker: MockerFixture,
) -> None:
    """HookMatcher handler catches exceptions, fail-open."""
    mocker.patch(
        "adws.hooks.command_blocker"
        ".block_dangerous_command_safe",
        side_effect=RuntimeError("unexpected"),
    )
    mock_stderr = mocker.patch(
        "adws.hooks.command_blocker.sys.stderr",
    )
    matcher = create_command_blocker_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    # Should not raise
    handler(
        {"command": "rm -rf /"},
        "sess-1",
    )
    mock_stderr.write.assert_called_once()
    msg = mock_stderr.write.call_args[0][0]
    assert "unexpected" in msg

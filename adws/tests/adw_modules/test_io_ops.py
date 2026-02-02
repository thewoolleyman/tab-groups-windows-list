"""Tests for I/O boundary module."""
from __future__ import annotations

import builtins
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import (
    ClaudeSDKError,
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
    ResultMessage,
)
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import (
    _build_verify_result,
    check_sdk_import,
    execute_sdk_call,
    read_file,
    run_jest_tests,
    run_mypy_check,
    run_playwright_tests,
    run_ruff_check,
    run_shell_command,
    sleep_seconds,
)
from adws.adw_modules.types import (
    AdwsRequest,
    AdwsResponse,
    ShellResult,
    VerifyResult,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_read_file_success(tmp_path: Path) -> None:
    """Test read_file returns IOSuccess with file contents."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    result = read_file(test_file)
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) == "hello world"


def test_read_file_not_found(tmp_path: Path) -> None:
    """Test read_file returns IOFailure when file does not exist."""
    result = read_file(tmp_path / "nonexistent.txt")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "FileNotFoundError"
    assert "nonexistent.txt" in error.message


def test_read_file_permission_error(tmp_path: Path) -> None:
    """Test read_file returns IOFailure on permission error."""
    test_file = tmp_path / "noperm.txt"
    test_file.write_text("secret")
    test_file.chmod(0o000)
    result = read_file(test_file)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "PermissionError"
    test_file.chmod(0o644)


def test_read_file_is_a_directory(tmp_path: Path) -> None:
    """Test read_file returns IOFailure when path is a directory."""
    result = read_file(tmp_path)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "IsADirectoryError"


def test_check_sdk_import_success() -> None:
    """Test check_sdk_import returns IOSuccess when SDK is installed."""
    result = check_sdk_import()
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is True


def test_check_sdk_import_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test check_sdk_import returns IOFailure when SDK import fails."""
    real_import = builtins.__import__

    def fail_sdk_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "claude_agent_sdk":
            msg = "mocked: sdk not installed"
            raise ImportError(msg)
        return real_import(name, *args, **kwargs)  # pragma: no cover

    mocker.patch("builtins.__import__", side_effect=fail_sdk_import)

    result = check_sdk_import()
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ImportError"


# --- execute_sdk_call tests ---


def _make_result_message(**overrides: Any) -> ResultMessage:
    """Create a real ResultMessage with test defaults."""
    return ResultMessage(
        subtype=overrides.get("subtype", "result"),
        duration_ms=overrides.get("duration_ms", 1500),
        duration_api_ms=overrides.get("duration_api_ms", 1200),
        is_error=overrides.get("is_error", False),
        num_turns=overrides.get("num_turns", 2),
        session_id=overrides.get("session_id", "sess-abc"),
        total_cost_usd=overrides.get("total_cost_usd", 0.003),
        result=overrides.get("result", "Hello from Claude"),
        usage=overrides.get("usage"),
        structured_output=overrides.get("structured_output"),
    )


@dataclass
class FakeOtherMessage:
    """Non-result message (e.g. AssistantMessage) the iterator yields."""

    subtype: str = "assistant"
    role: str = "assistant"
    content: str = "thinking..."


def test_execute_sdk_call_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns IOSuccess with AdwsResponse."""
    fake_result = _make_result_message()

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        yield FakeOtherMessage()
        yield fake_result

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOSuccess)
    response = unsafe_perform_io(result.unwrap())
    assert isinstance(response, AdwsResponse)
    assert response.result == "Hello from Claude"
    assert response.cost_usd == 0.003
    assert response.duration_ms == 1500
    assert response.session_id == "sess-abc"
    assert response.is_error is False
    assert response.num_turns == 2


def test_execute_sdk_call_passes_options(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call translates AdwsRequest fields to SDK options."""
    captured_opts: list[Any] = []

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        captured_opts.append(options)
        yield _make_result_message()

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(
        system_prompt="sys",
        prompt="hello",
        model="claude-haiku-3-5-20241022",
        allowed_tools=["bash"],
        max_turns=3,
        permission_mode="bypassPermissions",
    )
    execute_sdk_call(request)

    assert len(captured_opts) == 1
    opts = captured_opts[0]
    assert opts.system_prompt == "sys"
    assert opts.model == "claude-haiku-3-5-20241022"
    assert opts.allowed_tools == ["bash"]
    assert opts.max_turns == 3
    assert opts.permission_mode == "bypassPermissions"


def test_execute_sdk_call_no_result_message(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns error when no ResultMessage."""

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        yield FakeOtherMessage()

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "NoResultError"
    assert "No ResultMessage" in error.message


def test_execute_sdk_call_process_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns IOFailure on ProcessError."""

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        msg = "process failed"
        raise ProcessError(msg, exit_code=1, stderr="boom")
        yield  # pragma: no cover

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ProcessError"


def test_execute_sdk_call_connection_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns IOFailure on CLIConnectionError."""

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        msg = "connection refused"
        raise CLIConnectionError(msg)
        yield  # pragma: no cover

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "CLIConnectionError"


def test_execute_sdk_call_cli_not_found(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns IOFailure on CLINotFoundError."""

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        msg = "CLI not installed"
        raise CLINotFoundError(msg)
        yield  # pragma: no cover

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "CLINotFoundError"


def test_execute_sdk_call_json_decode_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns IOFailure on CLIJSONDecodeError."""

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        msg = "bad json line"
        raise CLIJSONDecodeError(msg, ValueError("parse"))
        yield  # pragma: no cover

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "CLIJSONDecodeError"


def test_execute_sdk_call_base_sdk_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test execute_sdk_call returns IOFailure on base ClaudeSDKError."""

    async def fake_query(
        *, prompt: str, options: object = None
    ) -> Any:
        msg = "unknown sdk error"
        raise ClaudeSDKError(msg)
        yield  # pragma: no cover

    mocker.patch("adws.adw_modules.io_ops.query", side_effect=fake_query)

    request = AdwsRequest(system_prompt="sys", prompt="hello")
    result = execute_sdk_call(request)

    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ClaudeSDKError"


# --- run_shell_command tests ---


def test_run_shell_command_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: run_shell_command does not exist yet."""
    fake_completed = subprocess.CompletedProcess(
        args="echo hello",
        returncode=0,
        stdout="hello\n",
        stderr="",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        return_value=fake_completed,
    )
    result = run_shell_command("echo hello")
    assert isinstance(result, IOSuccess)
    shell_result = unsafe_perform_io(result.unwrap())
    assert isinstance(shell_result, ShellResult)
    assert shell_result.return_code == 0
    assert shell_result.stdout == "hello\n"
    assert shell_result.stderr == ""
    assert shell_result.command == "echo hello"


def test_run_shell_command_nonzero_exit(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: Nonzero exit is still IOSuccess with ShellResult."""
    fake_completed = subprocess.CompletedProcess(
        args="false",
        returncode=1,
        stdout="",
        stderr="error msg",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        return_value=fake_completed,
    )
    result = run_shell_command("false")
    assert isinstance(result, IOSuccess)
    shell_result = unsafe_perform_io(result.unwrap())
    assert shell_result.return_code == 1
    assert shell_result.stderr == "error msg"


def test_run_shell_command_with_cwd(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: Verify cwd parameter is passed to subprocess."""
    mock_run = mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args="ls", returncode=0, stdout="", stderr=""
        ),
    )
    run_shell_command("ls", cwd="/some/dir")
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("cwd") == "/some/dir"


def test_run_shell_command_with_timeout(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: Verify timeout parameter is passed to subprocess."""
    mock_run = mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args="sleep 1", returncode=0, stdout="", stderr=""
        ),
    )
    run_shell_command("sleep 1", timeout=30)
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("timeout") == 30


def test_run_shell_command_timeout(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: Timeout raises subprocess.TimeoutExpired -> IOFailure."""
    mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd="slow_cmd", timeout=10
        ),
    )
    result = run_shell_command("slow_cmd", timeout=10)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "TimeoutError"
    assert "timed out" in error.message
    assert error.context["command"] == "slow_cmd"
    assert error.context["timeout"] == 10


def test_run_shell_command_file_not_found(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: FileNotFoundError -> IOFailure."""
    mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        side_effect=FileNotFoundError("no such cmd"),
    )
    result = run_shell_command("nonexistent_cmd")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "FileNotFoundError"
    assert "nonexistent_cmd" in error.message


def test_run_shell_command_os_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: OSError -> IOFailure."""
    mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        side_effect=OSError("disk error"),
    )
    result = run_shell_command("some_cmd")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "OSError"
    assert "disk error" in error.message


def test_run_shell_command_passes_critical_flags(mocker) -> None:  # type: ignore[no-untyped-def]
    """Verify subprocess.run gets critical safety flags."""
    mock_run = mocker.patch(
        "adws.adw_modules.io_ops.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args="echo ok", returncode=0, stdout="ok", stderr=""
        ),
    )
    run_shell_command("echo ok")
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["shell"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False


# --- sleep_seconds tests (Story 2.5) ---


def test_sleep_seconds_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """sleep_seconds wraps time.sleep, returns IOSuccess(None)."""
    mock_sleep = mocker.patch(
        "adws.adw_modules.io_ops.time.sleep",
    )
    result = sleep_seconds(2.5)
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is None
    mock_sleep.assert_called_once_with(2.5)


def test_sleep_seconds_os_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """sleep_seconds returns IOFailure on OSError."""
    mocker.patch(
        "adws.adw_modules.io_ops.time.sleep",
        side_effect=OSError("interrupted"),
    )
    result = sleep_seconds(1.0)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "OSError"
    assert "interrupted" in error.message
    assert error.context["seconds"] == 1.0


# --- _build_verify_result helper tests ---


def test_build_verify_result_success_path() -> None:
    """Test helper builds passing VerifyResult for exit code 0."""
    sr = ShellResult(
        return_code=0,
        stdout="all good\n",
        stderr="",
        command="test-tool",
    )
    vr = _build_verify_result(
        sr, "test-tool", lambda line: "ERROR" in line,
    )
    assert vr.tool_name == "test-tool"
    assert vr.passed is True
    assert vr.errors == []
    assert vr.raw_output == "all good\n"


def test_build_verify_result_failure_path() -> None:
    """Test helper builds failing VerifyResult with parsed errors."""
    sr = ShellResult(
        return_code=1,
        stdout="ok line\nERROR: bad thing\nERROR: worse\n",
        stderr="",
        command="test-tool",
    )

    def _filter(line: str) -> bool:
        return "ERROR" in line

    vr = _build_verify_result(sr, "test-tool", _filter)
    assert vr.tool_name == "test-tool"
    assert vr.passed is False
    assert len(vr.errors) == 2
    assert "ERROR: bad thing" in vr.errors[0]
    assert "ERROR: worse" in vr.errors[1]


def test_build_verify_result_combines_stdout_stderr() -> None:
    """Test helper combines stdout and stderr in raw_output."""
    sr = ShellResult(
        return_code=1,
        stdout="out\n",
        stderr="err\n",
        command="tool",
    )

    def _filter(line: str) -> bool:
        return "err" in line

    vr = _build_verify_result(sr, "tool", _filter)
    assert vr.raw_output == "out\nerr\n"
    assert len(vr.errors) == 1


# --- run_jest_tests tests ---

JEST_SUCCESS_OUTPUT = (
    "Test Suites: 5 passed, 5 total\n"
    "Tests:       23 passed, 23 total\n"
)

JEST_FAILURE_OUTPUT = (
    "FAIL src/tests/popup.test.ts\n"
    "  Tab Groups\n"
    "    > should handle empty groups\n"
    "      expect(received).toBe(expected)\n"
    "Test Suites: 1 failed, 4 passed, 5 total\n"
    "Tests:       1 failed, 22 passed, 23 total\n"
)


def test_run_jest_tests_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: run_jest_tests does not exist yet."""
    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout=JEST_SUCCESS_OUTPUT,
                stderr="",
                command="npm test",
            ),
        ),
    )
    result = run_jest_tests()
    mock_shell.assert_called_once_with("npm test")
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "jest"
    assert vr.passed is True
    assert vr.errors == []
    assert JEST_SUCCESS_OUTPUT in vr.raw_output


def test_run_jest_tests_failure_with_errors(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_jest_tests failure path does not exist yet."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout=JEST_FAILURE_OUTPUT,
                stderr="",
                command="npm test",
            ),
        ),
    )
    result = run_jest_tests()
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "jest"
    assert vr.passed is False
    assert len(vr.errors) > 0
    assert any("FAIL" in e for e in vr.errors)
    assert JEST_FAILURE_OUTPUT in vr.raw_output


def test_run_jest_tests_shell_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_jest_tests IOFailure propagation does not exist."""
    shell_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="TimeoutError",
        message="Command timed out",
        context={"command": "npm test"},
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_error),
    )
    result = run_jest_tests()
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_error


# --- run_playwright_tests tests ---

PLAYWRIGHT_SUCCESS_OUTPUT = (
    "  6 passed (3.2s)\n"
)

PLAYWRIGHT_FAILURE_OUTPUT = (
    "  1) chromium > example.spec.ts:5:1\n"
    "     > should display title\n"
    "     Error: expect(received).toBe(expected)\n"
    "  1 failed\n"
    "  5 passed (3.2s)\n"
)


def test_run_playwright_tests_success(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_playwright_tests does not exist yet."""
    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout=PLAYWRIGHT_SUCCESS_OUTPUT,
                stderr="",
                command="npm run test:e2e",
            ),
        ),
    )
    result = run_playwright_tests()
    mock_shell.assert_called_once_with("npm run test:e2e")
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "playwright"
    assert vr.passed is True
    assert vr.errors == []
    assert PLAYWRIGHT_SUCCESS_OUTPUT in vr.raw_output


def test_run_playwright_tests_failure_with_errors(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_playwright_tests failure path does not exist."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout=PLAYWRIGHT_FAILURE_OUTPUT,
                stderr="",
                command="npm run test:e2e",
            ),
        ),
    )
    result = run_playwright_tests()
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "playwright"
    assert vr.passed is False
    assert len(vr.errors) > 0
    assert any("Error:" in e for e in vr.errors)
    assert any("failed" in e for e in vr.errors)
    assert PLAYWRIGHT_FAILURE_OUTPUT in vr.raw_output


def test_run_playwright_tests_shell_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_playwright_tests IOFailure propagation."""
    shell_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="Command not found",
        context={"command": "npm run test:e2e"},
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_error),
    )
    result = run_playwright_tests()
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_error


# --- run_mypy_check tests ---

MYPY_SUCCESS_OUTPUT = (
    "Success: no issues found in 31 source files\n"
)

MYPY_FAILURE_OUTPUT = (
    "adws/adw_modules/types.py:5: error:"
    " Missing return statement  [return]\n"
    "adws/adw_modules/io_ops.py:42: error:"
    " Incompatible types  [arg-type]\n"
    "Found 2 errors in 2 files"
    " (checked 31 source files)\n"
)


def test_run_mypy_check_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: run_mypy_check does not exist yet."""
    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout=MYPY_SUCCESS_OUTPUT,
                stderr="",
                command="uv run mypy adws/",
            ),
        ),
    )
    result = run_mypy_check()
    mock_shell.assert_called_once_with("uv run mypy adws/")
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "mypy"
    assert vr.passed is True
    assert vr.errors == []
    assert MYPY_SUCCESS_OUTPUT in vr.raw_output


def test_run_mypy_check_failure_with_errors(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_mypy_check failure parsing does not exist."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout=MYPY_FAILURE_OUTPUT,
                stderr="",
                command="uv run mypy adws/",
            ),
        ),
    )
    result = run_mypy_check()
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "mypy"
    assert vr.passed is False
    assert len(vr.errors) == 2
    assert any("Missing return" in e for e in vr.errors)
    assert any("Incompatible types" in e for e in vr.errors)
    assert MYPY_FAILURE_OUTPUT in vr.raw_output


def test_run_mypy_check_shell_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_mypy_check IOFailure propagation."""
    shell_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="TimeoutError",
        message="Command timed out",
        context={"command": "uv run mypy adws/"},
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_error),
    )
    result = run_mypy_check()
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_error


# --- run_ruff_check tests ---

RUFF_SUCCESS_OUTPUT = "All checks passed!\n"

RUFF_FAILURE_OUTPUT = (
    "adws/adw_modules/types.py:10:1:"
    " E501 Line too long (120 > 88)\n"
    "adws/adw_modules/io_ops.py:5:1:"
    " F401 `os` imported but unused\n"
    "Found 2 errors.\n"
)


def test_run_ruff_check_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """RED: run_ruff_check does not exist yet."""
    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout=RUFF_SUCCESS_OUTPUT,
                stderr="",
                command="uv run ruff check adws/",
            ),
        ),
    )
    result = run_ruff_check()
    mock_shell.assert_called_once_with("uv run ruff check adws/")
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "ruff"
    assert vr.passed is True
    assert vr.errors == []
    assert RUFF_SUCCESS_OUTPUT in vr.raw_output


def test_run_ruff_check_failure_with_errors(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_ruff_check failure parsing does not exist."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout=RUFF_FAILURE_OUTPUT,
                stderr="",
                command="uv run ruff check adws/",
            ),
        ),
    )
    result = run_ruff_check()
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyResult)
    assert vr.tool_name == "ruff"
    assert vr.passed is False
    assert len(vr.errors) == 2
    assert any("E501" in e for e in vr.errors)
    assert any("F401" in e for e in vr.errors)
    assert RUFF_FAILURE_OUTPUT in vr.raw_output


def test_run_ruff_check_shell_failure_propagates(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """RED: run_ruff_check IOFailure propagation."""
    shell_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="OSError",
        message="OS error running command",
        context={"command": "uv run ruff check adws/"},
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_error),
    )
    result = run_ruff_check()
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_error


RUFF_FAILURE_WITH_NOISE = (
    "warning: unexpected config\n"
    "adws/adw_modules/types.py:10:1:"
    " E501 Line too long (120 > 88)\n"
    "Found 1 error.\n"
)


def test_run_ruff_check_filters_noise_lines(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """Verify ruff filter only captures file:line:col violation lines."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout=RUFF_FAILURE_WITH_NOISE,
                stderr="",
                command="uv run ruff check adws/",
            ),
        ),
    )
    result = run_ruff_check()
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert vr.passed is False
    assert len(vr.errors) == 1
    assert "E501" in vr.errors[0]
    assert "warning" not in vr.errors[0]

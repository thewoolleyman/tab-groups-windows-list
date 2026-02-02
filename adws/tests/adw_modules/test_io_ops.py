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

from adws.adw_modules.engine.types import Workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import (
    _build_tree_lines,
    _build_verify_result,
    _find_project_root,
    _sanitize_session_id,
    check_sdk_import,
    execute_command_workflow,
    execute_sdk_call,
    get_directory_tree,
    list_context_bundles,
    load_command_workflow,
    read_bmad_file,
    read_context_bundle,
    read_file,
    read_issue_description,
    read_prime_file,
    run_beads_show,
    run_jest_tests,
    run_mypy_check,
    run_playwright_tests,
    run_ruff_check,
    run_shell_command,
    sleep_seconds,
    write_context_bundle,
    write_hook_log,
    write_security_log,
    write_stderr,
)
from adws.adw_modules.types import (
    AdwsRequest,
    AdwsResponse,
    ShellResult,
    VerifyResult,
    WorkflowContext,
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


# --- load_command_workflow tests (Story 4.1) ---


def test_load_command_workflow_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """load_command_workflow returns IOSuccess with Workflow."""
    fake_wf = Workflow(
        name="verify",
        description="test",
        steps=[],
    )
    mocker.patch(
        "adws.workflows.load_workflow",
        return_value=fake_wf,
    )
    result = load_command_workflow("verify")
    assert isinstance(result, IOSuccess)
    wf = unsafe_perform_io(result.unwrap())
    assert wf is fake_wf


def test_load_command_workflow_not_found(mocker) -> None:  # type: ignore[no-untyped-def]
    """load_command_workflow returns IOFailure when not found."""
    mocker.patch(
        "adws.workflows.load_workflow",
        return_value=None,
    )
    result = load_command_workflow("nonexistent")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "WorkflowNotFoundError"
    assert "nonexistent" in error.message


# --- execute_command_workflow tests (Story 4.1) ---


def test_execute_command_workflow_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """execute_command_workflow returns IOSuccess with ctx."""
    fake_wf = Workflow(
        name="verify",
        description="test",
        steps=[],
    )
    ctx = WorkflowContext()
    result_ctx = WorkflowContext(
        outputs={"done": True},
    )
    mocker.patch(
        "adws.adw_modules.engine.executor.run_workflow",
        return_value=IOSuccess(result_ctx),
    )
    result = execute_command_workflow(fake_wf, ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx is result_ctx


def test_execute_command_workflow_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """execute_command_workflow propagates IOFailure."""
    fake_wf = Workflow(
        name="verify",
        description="test",
        steps=[],
    )
    ctx = WorkflowContext()
    err = PipelineError(
        step_name="jest",
        error_type="StepError",
        message="jest failed",
    )
    mocker.patch(
        "adws.adw_modules.engine.executor.run_workflow",
        return_value=IOFailure(err),
    )
    result = execute_command_workflow(fake_wf, ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is err


# --- _find_project_root tests (Story 4.3) ---


def test_find_project_root_returns_directory() -> None:
    """_find_project_root returns the directory with pyproject.toml."""
    root = _find_project_root()
    assert (root / "pyproject.toml").exists()


def test_find_project_root_is_absolute() -> None:
    """_find_project_root returns an absolute path."""
    root = _find_project_root()
    assert root.is_absolute()


# --- read_prime_file tests (Story 4.3) ---


def test_read_prime_file_success(tmp_path: Path) -> None:
    """read_prime_file returns IOSuccess with file content."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test content")
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_prime_file("test.md")
    assert isinstance(result, IOSuccess)
    content = unsafe_perform_io(result.unwrap())
    assert content == "# Test content"


def test_read_prime_file_not_found(tmp_path: Path) -> None:
    """read_prime_file returns IOFailure for missing file."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_prime_file("nonexistent.md")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "FileNotFoundError"


def test_read_prime_file_permission_error(
    tmp_path: Path,
) -> None:
    """read_prime_file returns IOFailure on permission error."""
    test_file = tmp_path / "noperm.md"
    test_file.write_text("secret")
    test_file.chmod(0o000)
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_prime_file("noperm.md")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "PermissionError"
    test_file.chmod(0o644)


# --- get_directory_tree tests (Story 4.3) ---


def test_get_directory_tree_success(tmp_path: Path) -> None:
    """get_directory_tree returns tree string for valid dir."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "README.md").touch()
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = get_directory_tree("src", max_depth=2)
    assert isinstance(result, IOSuccess)
    tree = unsafe_perform_io(result.unwrap())
    assert "main.py" in tree


def test_get_directory_tree_excludes_hidden(
    tmp_path: Path,
) -> None:
    """get_directory_tree excludes __pycache__ and .git dirs."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / "src" / ".git").mkdir()
    (tmp_path / "src" / "main.py").touch()
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = get_directory_tree("src", max_depth=2)
    assert isinstance(result, IOSuccess)
    tree = unsafe_perform_io(result.unwrap())
    assert "__pycache__" not in tree
    assert ".git" not in tree
    assert "main.py" in tree


def test_get_directory_tree_invalid_directory(
    tmp_path: Path,
) -> None:
    """get_directory_tree returns IOFailure for nonexistent dir."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = get_directory_tree("nonexistent")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "NotADirectoryError"


def test_get_directory_tree_respects_max_depth(
    tmp_path: Path,
) -> None:
    """get_directory_tree limits traversal to max_depth."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "a" / "b" / "c").mkdir()
    (tmp_path / "a" / "b" / "c" / "deep.py").touch()
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = get_directory_tree("a", max_depth=1)
    assert isinstance(result, IOSuccess)
    tree = unsafe_perform_io(result.unwrap())
    # At max_depth=1, should show b/ but not recurse into it
    assert "b/" in tree
    assert "deep.py" not in tree


def test_get_directory_tree_shows_nested_structure(
    tmp_path: Path,
) -> None:
    """get_directory_tree shows nested files/dirs properly."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").touch()
    (tmp_path / "pkg" / "sub").mkdir()
    (tmp_path / "pkg" / "sub" / "mod.py").touch()
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = get_directory_tree("pkg", max_depth=3)
    assert isinstance(result, IOSuccess)
    tree = unsafe_perform_io(result.unwrap())
    assert "__init__.py" in tree
    assert "sub/" in tree
    assert "mod.py" in tree


def test_get_directory_tree_excludes_all_known_dirs(
    tmp_path: Path,
) -> None:
    """get_directory_tree excludes all configured directories."""
    excluded = [
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "htmlcov",
    ]
    (tmp_path / "src").mkdir()
    for d in excluded:
        (tmp_path / "src" / d).mkdir()
    (tmp_path / "src" / "real.py").touch()
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = get_directory_tree("src", max_depth=2)
    assert isinstance(result, IOSuccess)
    tree = unsafe_perform_io(result.unwrap())
    for d in excluded:
        assert d not in tree
    assert "real.py" in tree


def test_get_directory_tree_os_error(
    tmp_path: Path, mocker: Any,
) -> None:
    """get_directory_tree returns IOFailure on OSError."""
    (tmp_path / "src").mkdir()
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch(
            "adws.adw_modules.io_ops._build_tree_lines",
            side_effect=OSError("disk error"),
        )
        result = get_directory_tree("src")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "OSError"


def test_build_tree_lines_iterdir_os_error(
    tmp_path: Path, mocker: Any,
) -> None:
    """_build_tree_lines returns empty on iterdir OSError."""
    from pathlib import Path as PathCls  # noqa: PLC0415

    target = PathCls(str(tmp_path))
    mocker.patch.object(
        PathCls, "iterdir",
        side_effect=OSError("permission denied"),
    )
    result = _build_tree_lines(target, 3, 0)
    assert result == []


# --- run_beads_close tests (Story 4.4) ---


def test_run_beads_close_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_close calls bd close and returns IOSuccess."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_close,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="Issue closed",
                stderr="",
                command="bd close ISSUE-1 --reason Done",
            ),
        ),
    )
    result = run_beads_close("ISSUE-1", "Done")
    assert isinstance(result, IOSuccess)
    sr = unsafe_perform_io(result.unwrap())
    assert isinstance(sr, ShellResult)
    assert sr.return_code == 0
    mock_shell.assert_called_once()
    cmd = mock_shell.call_args[0][0]
    assert "bd close" in cmd
    assert "ISSUE-1" in cmd
    assert "Done" in cmd


def test_run_beads_close_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_close returns IOFailure on nonzero exit."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_close,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout="",
                stderr="not found",
                command="bd close BAD-1 --reason x",
            ),
        ),
    )
    result = run_beads_close("BAD-1", "x")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsCloseError"
    assert "BAD-1" in str(error.context)


def test_run_beads_close_shell_safe(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_close uses shlex.quote to prevent injection."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_close,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ok",
                stderr="",
                command="bd close x",
            ),
        ),
    )
    # Dangerous issue_id with shell metacharacters
    run_beads_close('X"; rm -rf / #', "reason")
    cmd = mock_shell.call_args[0][0]
    # shlex.quote wraps in single quotes
    assert "rm -rf" not in cmd.split("'")[0]
    assert "'" in cmd


def test_run_beads_update_notes_shell_safe(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_update_notes uses shlex.quote for safety."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_update_notes,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ok",
                stderr="",
                command="bd update x",
            ),
        ),
    )
    # Dangerous notes with shell metacharacters
    run_beads_update_notes(
        "ISSUE-1", 'data"; rm -rf / #',
    )
    cmd = mock_shell.call_args[0][0]
    # shlex.quote wraps in single quotes
    assert "rm -rf" not in cmd.split("'")[0]
    assert "'" in cmd


def test_run_beads_close_shell_error(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_close propagates shell errors as IOFailure."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_close,
    )

    shell_err = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="bd not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_err),
    )
    result = run_beads_close("X-1", "reason")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_err


# --- run_beads_update_notes tests (Story 4.4) ---


def test_run_beads_update_notes_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_update_notes calls bd update and returns IOSuccess."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_update_notes,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="Updated",
                stderr="",
                command="bd update ISSUE-2 --notes info",
            ),
        ),
    )
    result = run_beads_update_notes("ISSUE-2", "info")
    assert isinstance(result, IOSuccess)
    sr = unsafe_perform_io(result.unwrap())
    assert isinstance(sr, ShellResult)
    assert sr.return_code == 0
    mock_shell.assert_called_once()
    cmd = mock_shell.call_args[0][0]
    assert "bd update" in cmd
    assert "ISSUE-2" in cmd
    assert "info" in cmd


def test_run_beads_update_notes_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_update_notes returns IOFailure on nonzero exit."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_update_notes,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout="",
                stderr="error",
                command="bd update BAD-2 --notes y",
            ),
        ),
    )
    result = run_beads_update_notes("BAD-2", "y")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsUpdateError"
    assert "BAD-2" in str(error.context)


# --- run_beads_show tests (Story 4.8) ---


def test_run_beads_show_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_show calls bd show and returns IOSuccess with stdout."""
    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="Issue description content...",
                stderr="",
                command="bd show ISSUE-1",
            ),
        ),
    )
    result = run_beads_show("ISSUE-1")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "Issue description content..."
    mock_shell.assert_called_once()
    cmd = mock_shell.call_args[0][0]
    assert "bd show" in cmd
    assert "ISSUE-1" in cmd


def test_run_beads_show_nonzero_exit(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_show returns IOFailure on nonzero exit."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout="",
                stderr="not found",
                command="bd show BAD-1",
            ),
        ),
    )
    result = run_beads_show("BAD-1")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsShowError"
    assert "BAD-1" in str(error.context)
    assert error.context["exit_code"] == 1
    assert error.context["stderr"] == "not found"


def test_run_beads_show_shell_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_show propagates shell command IOFailure."""
    shell_err = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="bd not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_err),
    )
    result = run_beads_show("X-1")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_err


def test_run_beads_show_shell_safe(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_show uses shlex.quote to prevent injection."""
    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ok",
                stderr="",
                command="bd show x",
            ),
        ),
    )
    run_beads_show('X"; rm -rf / #')
    cmd = mock_shell.call_args[0][0]
    assert "rm -rf" not in cmd.split("'")[0]
    assert "'" in cmd


# --- write_hook_log tests (Story 5.1) ---


def test_write_hook_log_success(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_hook_log appends event_json to session file."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_hook_log(
            "session-abc123",
            '{"event":"test"}',
        )
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is None
    log_file = (
        tmp_path / "agents" / "hook_logs"
        / "session-abc123.jsonl"
    )
    assert log_file.exists()
    content = log_file.read_text()
    assert content == '{"event":"test"}\n'


def test_write_hook_log_appends_to_existing(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_hook_log appends to existing session file."""
    from unittest.mock import patch  # noqa: PLC0415

    log_dir = tmp_path / "agents" / "hook_logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / "sess-1.jsonl"
    log_file.write_text('{"first":"entry"}\n')

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_hook_log(
            "sess-1", '{"second":"entry"}',
        )
    assert isinstance(result, IOSuccess)
    content = log_file.read_text()
    assert content == (
        '{"first":"entry"}\n{"second":"entry"}\n'
    )


def test_write_hook_log_creates_directory(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_hook_log creates agents/hook_logs/ if missing."""
    from unittest.mock import patch  # noqa: PLC0415

    log_dir = tmp_path / "agents" / "hook_logs"
    assert not log_dir.exists()

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_hook_log(
            "sess-new", '{"data":"val"}',
        )
    assert isinstance(result, IOSuccess)
    assert log_dir.exists()


def test_write_hook_log_permission_error(
    mocker: Any,
) -> None:
    """write_hook_log returns IOFailure on PermissionError."""
    from unittest.mock import patch  # noqa: PLC0415

    mock_path = mocker.MagicMock()
    mock_path.__truediv__ = mocker.MagicMock(
        return_value=mock_path,
    )
    mock_path.mkdir.side_effect = PermissionError(
        "no permission",
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=mock_path,
    ):
        result = write_hook_log("sess-1", '{"a":"b"}')
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "HookLogWriteError"
    assert error.step_name == "io_ops.write_hook_log"


def test_write_hook_log_os_error_on_write(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_hook_log returns IOFailure on file write OSError."""
    from pathlib import Path as PathCls  # noqa: PLC0415
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch.object(
            PathCls, "open",
            side_effect=OSError("disk full"),
        )
        result = write_hook_log("sess-1", '{"a":"b"}')
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "HookLogWriteError"
    assert error.step_name == "io_ops.write_hook_log"
    assert "disk full" in error.message


# --- _sanitize_session_id tests (Story 5.1 review fix) ---


def test_sanitize_session_id_normal() -> None:
    """Normal session_id passes through unchanged."""
    assert _sanitize_session_id("session-abc123") == (
        "session-abc123"
    )


def test_sanitize_session_id_path_traversal() -> None:
    """Path traversal attempt is stripped to final component."""
    assert _sanitize_session_id(
        "../../etc/passwd",
    ) == "passwd"


def test_sanitize_session_id_slash_prefix() -> None:
    """Absolute path is stripped to final component."""
    assert _sanitize_session_id(
        "/var/data/malicious",
    ) == "malicious"


def test_sanitize_session_id_empty() -> None:
    """Empty session_id becomes fallback name."""
    assert _sanitize_session_id("") == (
        "invalid-session"
    )


def test_sanitize_session_id_dot_only() -> None:
    """Dot-only session_id becomes fallback name."""
    assert _sanitize_session_id(".") == (
        "invalid-session"
    )
    assert _sanitize_session_id("..") == (
        "invalid-session"
    )


def test_write_hook_log_path_traversal_blocked(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_hook_log sanitizes traversal session_ids."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_hook_log(
            "../../etc/passwd",
            '{"event":"test"}',
        )
    assert isinstance(result, IOSuccess)
    # File should be in hook_logs/, NOT traversing out
    log_dir = tmp_path / "agents" / "hook_logs"
    assert (log_dir / "passwd.jsonl").exists()
    # Verify no file was written outside hook_logs
    assert not (tmp_path / "etc").exists()


# --- write_stderr tests (Story 5.1) ---


def test_write_stderr_success(mocker: Any) -> None:
    """write_stderr writes message to sys.stderr."""
    mock_stderr = mocker.patch(
        "adws.adw_modules.io_ops.sys.stderr",
    )
    result = write_stderr("error message\n")
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is None
    mock_stderr.write.assert_called_once_with(
        "error message\n",
    )


def test_write_stderr_os_error(mocker: Any) -> None:
    """write_stderr returns IOFailure when stderr.write raises."""
    mock_stderr = mocker.patch(
        "adws.adw_modules.io_ops.sys.stderr",
    )
    mock_stderr.write.side_effect = OSError("broken pipe")
    result = write_stderr("error message\n")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "io_ops.write_stderr"
    assert "broken pipe" in error.message


# --- write_context_bundle tests (Story 5.2) ---


def test_write_context_bundle_success(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_context_bundle appends entry_json to session file."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_context_bundle(
            "session-abc123",
            '{"file_path":"/some/file.py"}',
        )
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is None
    bundle_file = (
        tmp_path / "agents" / "context_bundles"
        / "session-abc123.jsonl"
    )
    assert bundle_file.exists()
    content = bundle_file.read_text()
    assert content == '{"file_path":"/some/file.py"}\n'


def test_write_context_bundle_appends_to_existing(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_context_bundle appends to existing session file."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)
    bundle_file = bundle_dir / "sess-1.jsonl"
    bundle_file.write_text('{"first":"entry"}\n')

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_context_bundle(
            "sess-1", '{"second":"entry"}',
        )
    assert isinstance(result, IOSuccess)
    content = bundle_file.read_text()
    assert content == (
        '{"first":"entry"}\n{"second":"entry"}\n'
    )


def test_write_context_bundle_creates_directory(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_context_bundle creates agents/context_bundles/ if missing."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    assert not bundle_dir.exists()

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_context_bundle(
            "sess-new", '{"data":"val"}',
        )
    assert isinstance(result, IOSuccess)
    assert bundle_dir.exists()


def test_write_context_bundle_permission_error(
    mocker: Any,
) -> None:
    """write_context_bundle returns IOFailure on PermissionError."""
    from unittest.mock import patch  # noqa: PLC0415

    mock_path = mocker.MagicMock()
    mock_path.__truediv__ = mocker.MagicMock(
        return_value=mock_path,
    )
    mock_path.mkdir.side_effect = PermissionError(
        "no permission",
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=mock_path,
    ):
        result = write_context_bundle(
            "sess-1", '{"a":"b"}',
        )
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ContextBundleWriteError"
    assert error.step_name == "io_ops.write_context_bundle"


def test_write_context_bundle_os_error_on_write(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_context_bundle returns IOFailure on file write OSError."""
    from pathlib import Path as PathCls  # noqa: PLC0415
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch.object(
            PathCls, "open",
            side_effect=OSError("disk full"),
        )
        result = write_context_bundle(
            "sess-1", '{"a":"b"}',
        )
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ContextBundleWriteError"
    assert error.step_name == "io_ops.write_context_bundle"
    assert "disk full" in error.message


def test_write_context_bundle_path_traversal_blocked(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_context_bundle sanitizes traversal session_ids."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_context_bundle(
            "../../etc/passwd",
            '{"event":"test"}',
        )
    assert isinstance(result, IOSuccess)
    # File should be in context_bundles/, NOT traversing out
    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    assert (bundle_dir / "passwd.jsonl").exists()
    # Verify no file was written outside context_bundles
    assert not (tmp_path / "etc").exists()


# --- read_context_bundle tests (Story 5.3) ---


def test_read_context_bundle_success(
    tmp_path: Path, mocker: Any,
) -> None:
    """read_context_bundle reads bundle file content."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)
    bundle_file = bundle_dir / "session-abc123.jsonl"
    bundle_file.write_text(
        '{"file_path":"/a.py"}\n'
        '{"file_path":"/b.py"}\n'
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_context_bundle("session-abc123")
    assert isinstance(result, IOSuccess)
    content = unsafe_perform_io(result.unwrap())
    assert '{"file_path":"/a.py"}' in content
    assert '{"file_path":"/b.py"}' in content


def test_read_context_bundle_not_found(
    tmp_path: Path, mocker: Any,
) -> None:
    """read_context_bundle returns IOFailure for missing file."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_context_bundle("nonexistent")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ContextBundleNotFoundError"
    assert error.step_name == (
        "io_ops.read_context_bundle"
    )
    assert "nonexistent" in error.message


def test_read_context_bundle_permission_error(
    tmp_path: Path, mocker: Any,
) -> None:
    """read_context_bundle returns IOFailure on PermissionError."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)
    bundle_file = bundle_dir / "session-noperm.jsonl"
    bundle_file.write_text("data")
    bundle_file.chmod(0o000)

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_context_bundle("session-noperm")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ContextBundleReadError"
    assert error.step_name == (
        "io_ops.read_context_bundle"
    )
    bundle_file.chmod(0o644)


def test_read_context_bundle_os_error(
    tmp_path: Path, mocker: Any,
) -> None:
    """read_context_bundle returns IOFailure on OSError."""
    from pathlib import Path as PathCls  # noqa: PLC0415
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)
    bundle_file = bundle_dir / "session-oserr.jsonl"
    bundle_file.write_text("data")

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch.object(
            PathCls, "read_text",
            side_effect=OSError("disk error"),
        )
        result = read_context_bundle("session-oserr")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ContextBundleReadError"
    assert "disk error" in error.message


def test_read_context_bundle_path_traversal_blocked(
    tmp_path: Path, mocker: Any,
) -> None:
    """read_context_bundle sanitizes traversal session_ids."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_context_bundle(
            "../../etc/passwd",
        )
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "ContextBundleNotFoundError"


# --- list_context_bundles tests (Story 5.3) ---


def test_list_context_bundles_success(
    tmp_path: Path, mocker: Any,
) -> None:
    """list_context_bundles returns sorted session IDs."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "session-def.jsonl").touch()
    (bundle_dir / "session-abc.jsonl").touch()

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = list_context_bundles()
    assert isinstance(result, IOSuccess)
    bundles = unsafe_perform_io(result.unwrap())
    assert bundles == ["session-abc", "session-def"]


def test_list_context_bundles_dir_not_exists(
    tmp_path: Path, mocker: Any,
) -> None:
    """list_context_bundles returns empty list when dir missing."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = list_context_bundles()
    assert isinstance(result, IOSuccess)
    bundles = unsafe_perform_io(result.unwrap())
    assert bundles == []


def test_list_context_bundles_empty_dir(
    tmp_path: Path, mocker: Any,
) -> None:
    """list_context_bundles returns empty list when dir empty."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = list_context_bundles()
    assert isinstance(result, IOSuccess)
    bundles = unsafe_perform_io(result.unwrap())
    assert bundles == []


def test_list_context_bundles_ignores_non_jsonl(
    tmp_path: Path, mocker: Any,
) -> None:
    """list_context_bundles only lists .jsonl files."""
    from unittest.mock import patch  # noqa: PLC0415

    bundle_dir = (
        tmp_path / "agents" / "context_bundles"
    )
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "session-abc.jsonl").touch()
    (bundle_dir / "readme.txt").touch()

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = list_context_bundles()
    assert isinstance(result, IOSuccess)
    bundles = unsafe_perform_io(result.unwrap())
    assert bundles == ["session-abc"]


def test_list_context_bundles_permission_error(
    mocker: Any,
) -> None:
    """list_context_bundles returns IOFailure on PermissionError."""
    from unittest.mock import patch  # noqa: PLC0415

    mock_path = mocker.MagicMock()
    mock_path.__truediv__ = mocker.MagicMock(
        return_value=mock_path,
    )
    mock_path.is_dir.return_value = True
    mock_path.iterdir.side_effect = PermissionError(
        "no permission",
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=mock_path,
    ):
        result = list_context_bundles()
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ContextBundleListError"
    assert error.step_name == (
        "io_ops.list_context_bundles"
    )


# --- write_security_log tests (Story 5.4) ---


def test_write_security_log_success(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_security_log appends entry_json to session file."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_security_log(
            "session-abc123",
            '{"command":"rm -rf /"}',
        )
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is None
    log_file = (
        tmp_path / "agents" / "security_logs"
        / "session-abc123.jsonl"
    )
    assert log_file.exists()
    content = log_file.read_text()
    assert content == '{"command":"rm -rf /"}\n'


def test_write_security_log_appends_to_existing(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_security_log appends to existing session file."""
    from unittest.mock import patch  # noqa: PLC0415

    log_dir = tmp_path / "agents" / "security_logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / "sess-1.jsonl"
    log_file.write_text('{"first":"entry"}\n')

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_security_log(
            "sess-1", '{"second":"entry"}',
        )
    assert isinstance(result, IOSuccess)
    content = log_file.read_text()
    assert content == (
        '{"first":"entry"}\n{"second":"entry"}\n'
    )


def test_write_security_log_creates_directory(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_security_log creates agents/security_logs/ if missing."""
    from unittest.mock import patch  # noqa: PLC0415

    log_dir = tmp_path / "agents" / "security_logs"
    assert not log_dir.exists()

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_security_log(
            "sess-new", '{"data":"val"}',
        )
    assert isinstance(result, IOSuccess)
    assert log_dir.exists()


def test_write_security_log_permission_error(
    mocker: Any,
) -> None:
    """write_security_log returns IOFailure on PermissionError."""
    from unittest.mock import patch  # noqa: PLC0415

    mock_path = mocker.MagicMock()
    mock_path.__truediv__ = mocker.MagicMock(
        return_value=mock_path,
    )
    mock_path.mkdir.side_effect = PermissionError(
        "no permission",
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=mock_path,
    ):
        result = write_security_log(
            "sess-1", '{"a":"b"}',
        )
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "SecurityLogWriteError"
    assert error.step_name == (
        "io_ops.write_security_log"
    )


def test_write_security_log_os_error_on_write(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_security_log returns IOFailure on file write OSError."""
    from pathlib import Path as PathCls  # noqa: PLC0415
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch.object(
            PathCls, "open",
            side_effect=OSError("disk full"),
        )
        result = write_security_log(
            "sess-1", '{"a":"b"}',
        )
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "SecurityLogWriteError"
    assert error.step_name == (
        "io_ops.write_security_log"
    )
    assert "disk full" in error.message


def test_write_security_log_path_traversal_blocked(
    tmp_path: Path, mocker: Any,
) -> None:
    """write_security_log sanitizes traversal session_ids."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_security_log(
            "../../etc/passwd",
            '{"event":"test"}',
        )
    assert isinstance(result, IOSuccess)
    # File should be in security_logs/, NOT traversing out
    log_dir = tmp_path / "agents" / "security_logs"
    assert (log_dir / "passwd.jsonl").exists()
    # Verify no file was written outside security_logs
    assert not (tmp_path / "etc").exists()


# --- read_bmad_file tests (Story 6.1) ---


def test_read_bmad_file_success(
    tmp_path: Path,
) -> None:
    """read_bmad_file returns IOSuccess with file content."""
    test_file = tmp_path / "epics.md"
    test_file.write_text("# Epic content")
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_bmad_file("epics.md")
    assert isinstance(result, IOSuccess)
    content = unsafe_perform_io(result.unwrap())
    assert content == "# Epic content"


def test_read_bmad_file_not_found(
    tmp_path: Path,
) -> None:
    """read_bmad_file returns IOFailure for missing file."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_bmad_file("nonexistent.md")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "FileNotFoundError"


def test_read_bmad_file_permission_error(
    tmp_path: Path,
) -> None:
    """read_bmad_file returns IOFailure on permission error."""
    from unittest.mock import patch  # noqa: PLC0415

    test_file = tmp_path / "noperm.md"
    test_file.write_text("secret")
    test_file.chmod(0o000)

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = read_bmad_file("noperm.md")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "PermissionError"
    test_file.chmod(0o644)


def test_read_bmad_file_empty_path() -> None:
    """read_bmad_file returns IOFailure for empty string path."""
    result = read_bmad_file("")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "io_ops.read_bmad_file"
    assert error.error_type == "ValueError"
    assert "empty" in error.message.lower()


# --- run_beads_create tests (Story 6.2) ---


def test_run_beads_create_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create calls bd create and returns IOSuccess with issue ID."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="Created issue: ISSUE-123\n",
                stderr="",
                command="bd create --title t --description d",
            ),
        ),
    )
    result = run_beads_create("My Title", "My Description")
    assert isinstance(result, IOSuccess)
    issue_id = unsafe_perform_io(result.unwrap())
    assert issue_id == "ISSUE-123"
    mock_shell.assert_called_once()
    cmd = mock_shell.call_args[0][0]
    assert "bd create" in cmd
    assert "--title" in cmd
    assert "--description" in cmd


def test_run_beads_create_nonzero_exit(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create returns IOFailure on nonzero exit code."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout="",
                stderr="Error: failed to create",
                command="bd create ...",
            ),
        ),
    )
    result = run_beads_create("Title", "Desc")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsCreateError"
    assert error.step_name == "io_ops.run_beads_create"
    assert "failed to create" in str(error.context["stderr"])


def test_run_beads_create_unparseable_stdout(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create returns IOFailure when stdout has no issue ID."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="",
                stderr="",
                command="bd create ...",
            ),
        ),
    )
    result = run_beads_create("Title", "Desc")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsCreateParseError"
    assert error.step_name == "io_ops.run_beads_create"


def test_run_beads_create_shell_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create propagates shell command IOFailure."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    shell_err = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="bd not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_err),
    )
    result = run_beads_create("Title", "Desc")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_err


def test_run_beads_create_shell_safe(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create uses shlex.quote for safety."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ISSUE-1\n",
                stderr="",
                command="bd create ...",
            ),
        ),
    )
    run_beads_create(
        'Title"; rm -rf /',
        'Desc"; drop table',
    )
    cmd = mock_shell.call_args[0][0]
    # shlex.quote wraps in single quotes
    assert "rm -rf" not in cmd.split("'")[0]
    assert "'" in cmd


def test_run_beads_create_parses_first_line(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create parses issue ID from first non-empty stdout line."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ABC-42\nExtra output\n",
                stderr="",
                command="bd create ...",
            ),
        ),
    )
    result = run_beads_create("Title", "Desc")
    assert isinstance(result, IOSuccess)
    issue_id = unsafe_perform_io(result.unwrap())
    assert issue_id == "ABC-42"


def test_run_beads_create_whitespace_only_stdout(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_create returns IOFailure when stdout is whitespace only."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_create,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="  \n  \n",
                stderr="",
                command="bd create ...",
            ),
        ),
    )
    result = run_beads_create("Title", "Desc")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsCreateParseError"


# --- _parse_beads_issue_id tests (Story 6.2) ---


def test_parse_beads_issue_id_simple() -> None:
    """_parse_beads_issue_id extracts plain ID."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        _parse_beads_issue_id,
    )

    assert _parse_beads_issue_id("ISSUE-123\n") == "ISSUE-123"


def test_parse_beads_issue_id_with_prefix() -> None:
    """_parse_beads_issue_id extracts ID after ': ' prefix."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        _parse_beads_issue_id,
    )

    assert _parse_beads_issue_id(
        "Created issue: BEADS-42\n",
    ) == "BEADS-42"


def test_parse_beads_issue_id_empty() -> None:
    """_parse_beads_issue_id returns empty for empty stdout."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        _parse_beads_issue_id,
    )

    assert _parse_beads_issue_id("") == ""


def test_parse_beads_issue_id_whitespace_only() -> None:
    """_parse_beads_issue_id returns empty for whitespace stdout."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        _parse_beads_issue_id,
    )

    assert _parse_beads_issue_id("  \n  \n") == ""


# --- write_bmad_file tests (Story 6.3) ---


def test_write_bmad_file_success(
    tmp_path: Path,
) -> None:
    """write_bmad_file returns IOSuccess(None) on success."""
    from unittest.mock import patch  # noqa: PLC0415

    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        write_bmad_file,
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        result = write_bmad_file("story.md", "# Content")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val is None
    written = (tmp_path / "story.md").read_text()
    assert written == "# Content"


def test_write_bmad_file_empty_path() -> None:
    """write_bmad_file returns IOFailure for empty path."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        write_bmad_file,
    )

    result = write_bmad_file("", "content")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "io_ops.write_bmad_file"
    assert error.error_type == "ValueError"
    assert "empty" in error.message.lower()


def test_write_bmad_file_permission_error(
    tmp_path: Path,
    mocker: Any,
) -> None:
    """write_bmad_file returns IOFailure on PermissionError."""
    from unittest.mock import patch  # noqa: PLC0415

    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        write_bmad_file,
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch(
            "adws.adw_modules.io_ops._Path.write_text",
            side_effect=PermissionError("denied"),
        )
        result = write_bmad_file("story.md", "content")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "io_ops.write_bmad_file"
    assert error.error_type == "PermissionError"


def test_write_bmad_file_os_error(
    tmp_path: Path,
    mocker: Any,
) -> None:
    """write_bmad_file returns IOFailure on OSError."""
    from unittest.mock import patch  # noqa: PLC0415

    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        write_bmad_file,
    )

    with patch(
        "adws.adw_modules.io_ops._find_project_root",
        return_value=tmp_path,
    ):
        mocker.patch(
            "adws.adw_modules.io_ops._Path.write_text",
            side_effect=OSError("disk full"),
        )
        result = write_bmad_file("story.md", "content")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "io_ops.write_bmad_file"
    assert error.error_type == "OSError"


def test_parse_beads_issue_id_colon_only() -> None:
    """_parse_beads_issue_id returns the raw line when no ': ' found."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        _parse_beads_issue_id,
    )

    # After strip, "prefix:" has no ": " so returns the line itself
    assert _parse_beads_issue_id("prefix:\n") == "prefix:"


def test_parse_beads_issue_id_multiline() -> None:
    """_parse_beads_issue_id uses first line only."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        _parse_beads_issue_id,
    )

    assert _parse_beads_issue_id(
        "FIRST-1\nSECOND-2\n",
    ) == "FIRST-1"


# --- read_issue_description tests (Story 7.1) ---


def test_read_issue_description_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """read_issue_description delegates to run_beads_show and returns IOSuccess."""
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOSuccess("issue description text"),
    )
    result = read_issue_description("ISSUE-42")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "issue description text"


def test_read_issue_description_empty_id() -> None:
    """read_issue_description returns IOFailure for empty issue_id."""
    result = read_issue_description("")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"
    assert error.step_name == "io_ops.read_issue_description"


def test_read_issue_description_whitespace_only_id() -> None:
    """read_issue_description returns IOFailure for whitespace-only issue_id."""
    result = read_issue_description("   ")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"
    assert error.step_name == "io_ops.read_issue_description"


def test_read_issue_description_failure_propagates(mocker) -> None:  # type: ignore[no-untyped-def]
    """read_issue_description propagates IOFailure from run_beads_show."""
    show_err = PipelineError(
        step_name="io_ops.run_beads_show",
        error_type="BeadsShowError",
        message="bd show failed",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_show",
        return_value=IOFailure(show_err),
    )
    result = read_issue_description("BAD-1")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is show_err


# --- run_beads_list tests (Story 7.3) ---


def test_run_beads_list_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_list calls bd list and returns IOSuccess with stdout."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_list,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ISSUE-1\nISSUE-2\n",
                stderr="",
                command="bd list --status=open",
            ),
        ),
    )
    result = run_beads_list("open")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "ISSUE-1\nISSUE-2\n"
    mock_shell.assert_called_once()
    cmd = mock_shell.call_args[0][0]
    assert "bd list" in cmd
    assert "--status=" in cmd
    assert "open" in cmd


def test_run_beads_list_nonzero_exit(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_list returns IOFailure on nonzero exit code."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_list,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout="",
                stderr="No issues found",
                command="bd list --status=open",
            ),
        ),
    )
    result = run_beads_list("open")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsListError"
    assert error.step_name == "io_ops.run_beads_list"


def test_run_beads_list_shell_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_list propagates shell command IOFailure via bind."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_list,
    )

    shell_err = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="bd not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_err),
    )
    result = run_beads_list("open")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_err


def test_run_beads_list_shell_safe(mocker) -> None:  # type: ignore[no-untyped-def]
    """run_beads_list uses shlex.quote to prevent injection."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        run_beads_list,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="",
                stderr="",
                command="bd list",
            ),
        ),
    )
    run_beads_list('open"; rm -rf / #')
    cmd = mock_shell.call_args[0][0]
    assert "rm -rf" not in cmd.split("'")[0]
    assert "'" in cmd


# --- read_issue_notes tests (Story 7.3) ---


def test_read_issue_notes_success(mocker) -> None:  # type: ignore[no-untyped-def]
    """read_issue_notes calls bd show --notes and returns IOSuccess."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        read_issue_notes,
    )

    mock_shell = mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=0,
                stdout="ADWS_FAILED|attempt=1|...",
                stderr="",
                command="bd show ISSUE-42 --notes",
            ),
        ),
    )
    result = read_issue_notes("ISSUE-42")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "ADWS_FAILED|attempt=1|..."
    mock_shell.assert_called_once()
    cmd = mock_shell.call_args[0][0]
    assert "bd show" in cmd
    assert "ISSUE-42" in cmd
    assert "--notes" in cmd


def test_read_issue_notes_empty_id() -> None:
    """read_issue_notes returns IOFailure for empty issue_id."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        read_issue_notes,
    )

    result = read_issue_notes("")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"
    assert error.step_name == "io_ops.read_issue_notes"


def test_read_issue_notes_whitespace_only_id() -> None:
    """read_issue_notes returns IOFailure for whitespace-only issue_id."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        read_issue_notes,
    )

    result = read_issue_notes("   ")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ValueError"
    assert error.step_name == "io_ops.read_issue_notes"


def test_read_issue_notes_nonzero_exit(mocker) -> None:  # type: ignore[no-untyped-def]
    """read_issue_notes returns IOFailure on nonzero exit code."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        read_issue_notes,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOSuccess(
            ShellResult(
                return_code=1,
                stdout="",
                stderr="not found",
                command="bd show ISSUE-42 --notes",
            ),
        ),
    )
    result = read_issue_notes("ISSUE-42")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "BeadsShowNotesError"
    assert error.step_name == "io_ops.read_issue_notes"


def test_read_issue_notes_shell_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """read_issue_notes propagates shell command IOFailure via bind."""
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        read_issue_notes,
    )

    shell_err = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="bd not found",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.run_shell_command",
        return_value=IOFailure(shell_err),
    )
    result = read_issue_notes("ISSUE-42")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is shell_err

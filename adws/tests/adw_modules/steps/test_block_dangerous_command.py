"""Tests for block_dangerous_command step functions."""
from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.block_dangerous_command import (
    DANGEROUS_PATTERNS,
    BlockResult,
    _check_command,
    block_dangerous_command,
    block_dangerous_command_safe,
)
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- DangerousPattern tests ---


def test_dangerous_pattern_is_frozen() -> None:
    """DangerousPattern is a frozen dataclass."""
    dp = DANGEROUS_PATTERNS[0]
    assert dataclasses.is_dataclass(dp)
    assert type(dp).__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_dangerous_pattern_has_required_fields() -> None:
    """DangerousPattern has name, pattern, reason, alternative."""
    for dp in DANGEROUS_PATTERNS:
        assert isinstance(dp.name, str)
        assert dp.pattern is not None
        assert isinstance(dp.reason, str)
        assert isinstance(dp.alternative, str)


def test_dangerous_patterns_is_list() -> None:
    """DANGEROUS_PATTERNS is a non-empty list."""
    assert isinstance(DANGEROUS_PATTERNS, list)
    assert len(DANGEROUS_PATTERNS) > 0


def test_dangerous_patterns_minimum_count() -> None:
    """DANGEROUS_PATTERNS includes at least 13 patterns."""
    assert len(DANGEROUS_PATTERNS) >= 13


def test_dangerous_patterns_unique_names() -> None:
    """All pattern names are unique."""
    names = [dp.name for dp in DANGEROUS_PATTERNS]
    assert len(names) == len(set(names))


# --- BlockResult tests ---


def test_block_result_construction() -> None:
    """BlockResult stores all fields correctly."""
    br = BlockResult(
        blocked=True,
        command="rm -rf /",
        pattern_name="rm_rf_root",
        reason="Dangerous",
        alternative="Use explicit path",
    )
    assert br.blocked is True
    assert br.command == "rm -rf /"
    assert br.pattern_name == "rm_rf_root"
    assert br.reason == "Dangerous"
    assert br.alternative == "Use explicit path"


def test_block_result_is_frozen() -> None:
    """BlockResult is a frozen dataclass."""
    br = BlockResult(
        blocked=True,
        command="rm -rf /",
        pattern_name="rm_rf_root",
        reason="Dangerous",
        alternative="Safer approach",
    )
    assert dataclasses.is_dataclass(br)
    assert type(br).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        br.blocked = False  # type: ignore[misc]


# --- _check_command tests ---


def test_check_command_blocks_rm_rf_root() -> None:
    """_check_command blocks rm -rf /."""
    result = _check_command("rm -rf /")
    assert result is not None
    assert result.blocked is True
    assert result.pattern_name == "rm_rf_root"
    assert result.command == "rm -rf /"
    assert result.reason != ""
    assert result.alternative != ""


def test_check_command_safe_ls() -> None:
    """_check_command returns None for safe commands."""
    result = _check_command("ls -la")
    assert result is None


def test_check_command_safe_rm_file() -> None:
    """_check_command does not block rm file.txt."""
    result = _check_command("rm file.txt")
    assert result is None


def test_check_command_safe_git_push() -> None:
    """_check_command does not block git push (no force)."""
    result = _check_command("git push origin feature-branch")
    assert result is None


def test_check_command_safe_git_push_force_feature() -> None:
    """_check_command does not block force-push to feature branch."""
    result = _check_command(
        "git push origin feature-branch --force"
    )
    assert result is None


def test_check_command_safe_chmod_644() -> None:
    """_check_command does not block chmod 644."""
    result = _check_command("chmod 644 file.txt")
    assert result is None


def test_check_command_safe_curl_no_pipe() -> None:
    """_check_command does not block curl without pipe."""
    result = _check_command("curl https://example.com")
    assert result is None


def test_check_command_safe_wget_no_pipe() -> None:
    """_check_command does not block wget to file."""
    result = _check_command("wget file.tar.gz")
    assert result is None


def test_check_command_safe_dd_file() -> None:
    """_check_command does not block dd to file."""
    result = _check_command("dd if=input.iso of=output.iso")
    assert result is None


def test_check_command_safe_git_add() -> None:
    """_check_command does not block git add."""
    result = _check_command("git add .")
    assert result is None


def test_check_command_safe_npm_test() -> None:
    """_check_command does not block npm test."""
    result = _check_command("npm test")
    assert result is None


def test_check_command_safe_uv_run_pytest() -> None:
    """_check_command does not block uv run pytest."""
    result = _check_command("uv run pytest")
    assert result is None


def test_check_command_with_sudo_prefix() -> None:
    """_check_command detects dangerous commands with sudo."""
    result = _check_command("sudo rm -rf /")
    assert result is not None
    assert result.blocked is True


def test_check_command_with_extra_whitespace() -> None:
    """_check_command handles extra whitespace."""
    result = _check_command("rm   -rf   /")
    assert result is not None
    assert result.blocked is True


# --- _check_command edge cases ---


def test_check_command_git_push_f_main() -> None:
    """_check_command blocks git push -f main."""
    result = _check_command("git push -f origin main")
    assert result is not None
    assert result.pattern_name == "git_push_force_main"


def test_check_command_git_push_force_master() -> None:
    """_check_command blocks git push --force master."""
    result = _check_command("git push --force origin master")
    assert result is not None
    assert result.pattern_name == "git_push_force_main"


def test_check_command_rm_fr_root() -> None:
    """_check_command blocks rm -fr / (reversed flags)."""
    result = _check_command("rm -fr /")
    assert result is not None
    assert result.pattern_name == "rm_rf_root"


# --- block_dangerous_command tests ---


def test_block_dangerous_command_blocked(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command returns IOSuccess with blocked=True."""
    mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_security_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "command": "rm -rf /",
            "session_id": "sess-1",
        },
    )
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is True
    assert out_ctx.outputs["pattern_name"] == "rm_rf_root"
    assert "reason" in out_ctx.outputs
    assert "alternative" in out_ctx.outputs
    assert out_ctx.outputs["security_log_written"] is True


def test_block_dangerous_command_safe_command(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command returns blocked=False for safe cmd."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_security_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "command": "npm test",
            "session_id": "sess-1",
        },
    )
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is False
    mock_write.assert_not_called()


def test_block_dangerous_command_missing_command() -> None:
    """block_dangerous_command returns IOFailure without command."""
    ctx = WorkflowContext(inputs={})
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingInputError"
    assert error.step_name == "block_dangerous_command"
    assert "command" in error.message


def test_block_dangerous_command_non_string_command() -> None:
    """block_dangerous_command returns IOFailure for non-string."""
    ctx = WorkflowContext(
        inputs={"command": 12345},
    )
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingInputError"


def test_block_dangerous_command_empty_command() -> None:
    """block_dangerous_command returns IOFailure for empty str."""
    ctx = WorkflowContext(
        inputs={"command": ""},
    )
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "MissingInputError"


def test_block_dangerous_command_log_write_failure(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command still blocks when log write fails."""
    mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_security_log",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.write_security_log",
                error_type="SecurityLogWriteError",
                message="disk full",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={
            "command": "rm -rf /",
            "session_id": "sess-1",
        },
    )
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is True
    assert out_ctx.outputs["security_log_written"] is False


def test_block_dangerous_command_missing_session_id(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command generates fallback session_id."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_security_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={"command": "rm -rf /"},
    )
    result = block_dangerous_command(ctx)
    assert isinstance(result, IOSuccess)
    call_args = mock_write.call_args
    session_id = call_args[0][0]
    assert session_id.startswith("unknown-")


def test_block_dangerous_command_writes_jsonl(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command writes correct JSONL to log."""
    mock_write = mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_security_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "command": "rm -rf /",
            "session_id": "sess-1",
        },
    )
    block_dangerous_command(ctx)
    mock_write.assert_called_once()
    jsonl = mock_write.call_args[0][1]
    assert '"rm -rf /"' in jsonl
    assert '"rm_rf_root"' in jsonl
    assert '"blocked"' in jsonl


# --- block_dangerous_command_safe tests ---


def test_block_dangerous_command_safe_success(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command_safe passes through IOSuccess."""
    mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_security_log",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={
            "command": "rm -rf /",
            "session_id": "sess-1",
        },
    )
    result = block_dangerous_command_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is True


def test_block_dangerous_command_safe_catches_failure(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command_safe catches IOFailure."""
    mock_stderr = mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_stderr",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(inputs={})
    result = block_dangerous_command_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is False
    assert "blocker_error" in out_ctx.outputs
    mock_stderr.assert_called_once()


def test_block_dangerous_command_safe_catches_exception(
    mocker: MockerFixture,
) -> None:
    """block_dangerous_command_safe catches unexpected exceptions."""
    mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".block_dangerous_command",
        side_effect=RuntimeError("unexpected boom"),
    )
    mock_stderr = mocker.patch(
        "adws.adw_modules.steps.block_dangerous_command"
        ".io_ops.write_stderr",
        return_value=IOSuccess(None),
    )
    ctx = WorkflowContext(
        inputs={"command": "ls"},
    )
    result = block_dangerous_command_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is False
    assert "blocker_error" in out_ctx.outputs
    assert "unexpected" in str(out_ctx.outputs["blocker_error"])
    mock_stderr.assert_called_once()


def test_steps_init_exports_block_dangerous_command() -> None:
    """block_dangerous_command importable from steps __init__."""
    from adws.adw_modules.steps import (  # noqa: PLC0415
        block_dangerous_command as bdc,
    )

    assert callable(bdc)


def test_steps_init_exports_block_dangerous_command_safe() -> None:
    """block_dangerous_command_safe importable from steps __init__."""
    from adws.adw_modules.steps import (  # noqa: PLC0415
        block_dangerous_command_safe as bdcs,
    )

    assert callable(bdcs)


def test_steps_init_all_contains_exports() -> None:
    """steps __all__ contains both block_dangerous_command exports."""
    from adws.adw_modules import steps  # noqa: PLC0415

    assert "block_dangerous_command" in steps.__all__
    assert "block_dangerous_command_safe" in steps.__all__


def test_block_dangerous_command_safe_safe_passthrough() -> None:
    """block_dangerous_command_safe passes safe commands through."""
    ctx = WorkflowContext(
        inputs={
            "command": "npm test",
            "session_id": "sess-1",
        },
    )
    result = block_dangerous_command_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["blocked"] is False

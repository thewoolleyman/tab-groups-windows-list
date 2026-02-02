"""Integration tests for hook event logging end-to-end."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.log_hook_event import (
    log_hook_event_safe,
)
from adws.adw_modules.types import WorkflowContext
from adws.hooks.event_logger import (
    create_event_logger_hook_matcher,
    main,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Integration: CLI path ---


def test_cli_path_end_to_end(
    mocker: MockerFixture,
) -> None:
    """CLI path: stdin JSON -> context -> log_hook_event_safe."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_hook_log(
        session_id: str, event_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append((session_id, event_json))
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        side_effect=fake_write_hook_log,
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.event_logger.sys.stdin.read",
        return_value=json.dumps({
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "sess-cli-1",
            "payload": {
                "tool_name": "Bash",
                "command": "ls",
            },
        }),
    )
    main()

    assert len(captured_calls) == 1
    session_id, jsonl = captured_calls[0]
    assert session_id == "sess-cli-1"
    parsed = json.loads(jsonl)
    assert parsed["event_type"] == "PreToolUse"
    assert parsed["hook_name"] == "event_logger"
    assert parsed["session_id"] == "sess-cli-1"
    assert parsed["payload"]["tool_name"] == "Bash"
    assert "timestamp" in parsed


# --- Integration: SDK HookMatcher path ---


def test_sdk_hook_matcher_end_to_end(
    mocker: MockerFixture,
) -> None:
    """SDK path: HookMatcher handler -> log_hook_event_safe."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_hook_log(
        session_id: str, event_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append((session_id, event_json))
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        side_effect=fake_write_hook_log,
    )

    matcher = create_event_logger_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    handler(
        {
            "event_type": "PostToolUse",
            "hook_name": "event_logger",
            "payload": {"exit_code": 0},
        },
        "sess-sdk-1",
    )

    assert len(captured_calls) == 1
    session_id, jsonl = captured_calls[0]
    assert session_id == "sess-sdk-1"
    parsed = json.loads(jsonl)
    assert parsed["event_type"] == "PostToolUse"
    assert parsed["session_id"] == "sess-sdk-1"


# --- Integration: fail-open end-to-end ---


def test_fail_open_end_to_end(
    mocker: MockerFixture,
) -> None:
    """Fail-open: write failure -> IOSuccess with error info."""
    io_error = PipelineError(
        step_name="io_ops.write_hook_log",
        error_type="HookLogWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        return_value=IOFailure(io_error),
    )
    mock_stderr = mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_stderr",
        return_value=IOSuccess(None),
    )

    ctx = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "sess-fail",
        },
    )
    result = log_hook_event_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["hook_event_logged"] is False
    assert "hook_event_error" in out_ctx.outputs
    mock_stderr.assert_called_once()


# --- Integration: session-specific routing ---


def test_session_specific_routing(
    mocker: MockerFixture,
) -> None:
    """Two different session_ids produce separate calls."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_hook_log(
        session_id: str, event_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append((session_id, event_json))
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.log_hook_event.io_ops"
        ".write_hook_log",
        side_effect=fake_write_hook_log,
    )

    ctx_a = WorkflowContext(
        inputs={
            "event_type": "PreToolUse",
            "hook_name": "event_logger",
            "session_id": "session-aaa",
        },
    )
    ctx_b = WorkflowContext(
        inputs={
            "event_type": "PostToolUse",
            "hook_name": "event_logger",
            "session_id": "session-bbb",
        },
    )
    log_hook_event_safe(ctx_a)
    log_hook_event_safe(ctx_b)

    assert len(captured_calls) == 2
    assert captured_calls[0][0] == "session-aaa"
    assert captured_calls[1][0] == "session-bbb"

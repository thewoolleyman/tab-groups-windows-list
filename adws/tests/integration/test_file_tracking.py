"""Integration tests for file tracking end-to-end."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.track_file_operation import (
    track_file_operation_safe,
)
from adws.adw_modules.types import WorkflowContext
from adws.hooks.file_tracker import (
    create_file_tracker_hook_matcher,
    main,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Integration: CLI path ---


def test_cli_path_end_to_end(
    mocker: MockerFixture,
) -> None:
    """CLI path: stdin JSON -> context -> track_file_operation_safe."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_context_bundle(
        session_id: str, entry_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append(
            (session_id, entry_json),
        )
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".io_ops.write_context_bundle",
        side_effect=fake_write_context_bundle,
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin",
    )
    mocker.patch(
        "adws.hooks.file_tracker.sys.stdin.read",
        return_value=json.dumps({
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-cli-1",
            "hook_name": "file_tracker",
        }),
    )
    main()

    assert len(captured_calls) == 1
    session_id, jsonl = captured_calls[0]
    assert session_id == "sess-cli-1"
    parsed = json.loads(jsonl)
    assert parsed["file_path"] == "/some/file.py"
    assert parsed["operation"] == "read"
    assert parsed["session_id"] == "sess-cli-1"
    assert parsed["hook_name"] == "file_tracker"
    assert "timestamp" in parsed


# --- Integration: SDK HookMatcher path ---


def test_sdk_hook_matcher_end_to_end(
    mocker: MockerFixture,
) -> None:
    """SDK path: HookMatcher handler -> track_file_operation_safe."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_context_bundle(
        session_id: str, entry_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append(
            (session_id, entry_json),
        )
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".io_ops.write_context_bundle",
        side_effect=fake_write_context_bundle,
    )

    matcher = create_file_tracker_hook_matcher()
    handler = matcher["handler"]
    assert callable(handler)
    handler(
        {
            "file_path": "/other/file.py",
            "operation": "write",
            "hook_name": "file_tracker",
        },
        "sess-sdk-1",
    )

    assert len(captured_calls) == 1
    session_id, jsonl = captured_calls[0]
    assert session_id == "sess-sdk-1"
    parsed = json.loads(jsonl)
    assert parsed["file_path"] == "/other/file.py"
    assert parsed["operation"] == "write"
    assert parsed["session_id"] == "sess-sdk-1"


# --- Integration: fail-open end-to-end ---


def test_fail_open_end_to_end(
    mocker: MockerFixture,
) -> None:
    """Fail-open: write failure -> IOSuccess with error info."""
    io_error = PipelineError(
        step_name="io_ops.write_context_bundle",
        error_type="ContextBundleWriteError",
        message="disk full",
    )
    mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".io_ops.write_context_bundle",
        return_value=IOFailure(io_error),
    )
    mock_stderr = mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".io_ops.write_stderr",
        return_value=IOSuccess(None),
    )

    ctx = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-fail",
            "hook_name": "file_tracker",
        },
    )
    result = track_file_operation_safe(ctx)
    assert isinstance(result, IOSuccess)
    out_ctx = unsafe_perform_io(result.unwrap())
    assert out_ctx.outputs["file_tracked"] is False
    assert "file_track_error" in out_ctx.outputs
    mock_stderr.assert_called_once()


# --- Integration: session-specific routing ---


def test_session_specific_routing(
    mocker: MockerFixture,
) -> None:
    """Two different session_ids produce separate calls."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_context_bundle(
        session_id: str, entry_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append(
            (session_id, entry_json),
        )
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".io_ops.write_context_bundle",
        side_effect=fake_write_context_bundle,
    )

    ctx_a = WorkflowContext(
        inputs={
            "file_path": "/file_a.py",
            "operation": "read",
            "session_id": "session-aaa",
            "hook_name": "file_tracker",
        },
    )
    ctx_b = WorkflowContext(
        inputs={
            "file_path": "/file_b.py",
            "operation": "write",
            "session_id": "session-bbb",
            "hook_name": "file_tracker",
        },
    )
    track_file_operation_safe(ctx_a)
    track_file_operation_safe(ctx_b)

    assert len(captured_calls) == 2
    assert captured_calls[0][0] == "session-aaa"
    assert captured_calls[1][0] == "session-bbb"


# --- Integration: mixed read and write operations ---


def test_mixed_operations_same_session(
    mocker: MockerFixture,
) -> None:
    """Two events (read, write) for same session produce two calls."""
    captured_calls: list[tuple[str, str]] = []

    def fake_write_context_bundle(
        session_id: str, entry_json: str,
    ) -> IOSuccess[None]:
        captured_calls.append(
            (session_id, entry_json),
        )
        return IOSuccess(None)

    mocker.patch(
        "adws.adw_modules.steps.track_file_operation"
        ".io_ops.write_context_bundle",
        side_effect=fake_write_context_bundle,
    )

    ctx_read = WorkflowContext(
        inputs={
            "file_path": "/some/file.py",
            "operation": "read",
            "session_id": "sess-mixed",
            "hook_name": "file_tracker",
        },
    )
    ctx_write = WorkflowContext(
        inputs={
            "file_path": "/other/file.py",
            "operation": "write",
            "session_id": "sess-mixed",
            "hook_name": "file_tracker",
        },
    )
    track_file_operation_safe(ctx_read)
    track_file_operation_safe(ctx_write)

    assert len(captured_calls) == 2
    assert captured_calls[0][0] == "sess-mixed"
    assert captured_calls[1][0] == "sess-mixed"

    parsed_read = json.loads(captured_calls[0][1])
    parsed_write = json.loads(captured_calls[1][1])
    assert parsed_read["operation"] == "read"
    assert parsed_read["file_path"] == "/some/file.py"
    assert parsed_write["operation"] == "write"
    assert parsed_write["file_path"] == "/other/file.py"

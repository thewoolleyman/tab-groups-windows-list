"""Integration tests for /load_bundle command (Story 5.3).

End-to-end scenarios covering success, not-found, missing-id,
dispatch routing, and malformed line tolerance. All io_ops
calls are mocked per NFR10.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.commands.dispatch import run_command
from adws.adw_modules.commands.load_bundle import (
    LoadBundleResult,
    run_load_bundle_command,
)
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Integration: full success path ---


def test_integration_full_load_bundle_success(
    mocker: MockerFixture,
) -> None:
    """Full success: load bundle with multiple entries."""
    content = (
        '{"timestamp":"2026-02-02T10:30:00+00:00",'
        '"file_path":"/path/to/file.py",'
        '"operation":"read",'
        '"session_id":"session-abc123",'
        '"hook_name":"file_tracker"}\n'
        '{"timestamp":"2026-02-02T10:30:01+00:00",'
        '"file_path":"/path/to/other.py",'
        '"operation":"write",'
        '"session_id":"session-abc123",'
        '"hook_name":"file_tracker"}\n'
    )
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOSuccess(content),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-abc123"},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOSuccess)
    lbr = unsafe_perform_io(result.unwrap())
    assert isinstance(lbr, LoadBundleResult)
    assert lbr.success is True
    assert lbr.session_id == "session-abc123"
    assert len(lbr.file_entries) == 2
    assert lbr.file_entries[0]["file_path"] == (
        "/path/to/file.py"
    )
    assert lbr.file_entries[0]["operation"] == "read"
    assert lbr.file_entries[1]["file_path"] == (
        "/path/to/other.py"
    )
    assert lbr.file_entries[1]["operation"] == "write"
    assert "2" in lbr.summary
    assert lbr.available_bundles == []


# --- Integration: bundle not found with listing ---


def test_integration_bundle_not_found_with_listing(
    mocker: MockerFixture,
) -> None:
    """Not found with available alternatives listed."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.read_context_bundle",
                error_type="ContextBundleNotFoundError",
                message=(
                    "Context bundle not found"
                    " for session: session-missing"
                ),
                context={
                    "session_id": "session-missing",
                },
            ),
        ),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOSuccess(
            ["session-old", "session-recent"],
        ),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-missing"},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "ContextBundleNotFoundError"
    assert "session-missing" in error.message
    available = error.context.get("available_bundles")
    assert available == [
        "session-old",
        "session-recent",
    ]


# --- Integration: no session_id provided ---


def test_integration_missing_session_id(
    mocker: MockerFixture,
) -> None:
    """Missing session_id lists available bundles."""
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOSuccess(
            ["session-old", "session-recent"],
        ),
    )
    ctx = WorkflowContext(inputs={})
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "MissingSessionIdError"
    available = error.context.get("available_bundles")
    assert available == [
        "session-old",
        "session-recent",
    ]


# --- Integration: dispatch routing ---


def test_integration_dispatch_routing(
    mocker: MockerFixture,
) -> None:
    """Dispatch routes load_bundle correctly."""
    content = (
        '{"file_path":"/a.py","operation":"read"}\n'
    )
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOSuccess(content),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-abc"},
    )
    result = run_command("load_bundle", ctx)
    assert isinstance(result, IOSuccess)
    out = unsafe_perform_io(result.unwrap())
    assert isinstance(out, WorkflowContext)
    lbr = out.outputs.get("load_bundle_result")
    assert isinstance(lbr, LoadBundleResult)
    assert lbr.success is True
    assert lbr.session_id == "session-abc"
    assert len(lbr.file_entries) == 1


# --- Integration: malformed lines ---


def test_integration_malformed_lines_tolerance(
    mocker: MockerFixture,
) -> None:
    """Malformed lines are skipped, valid entries returned."""
    content = (
        '{"file_path":"/a.py","operation":"read"}\n'
        "this is not json at all\n"
        '{"file_path":"/b.py","operation":"write"}\n'
    )
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOSuccess(content),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-mixed"},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOSuccess)
    lbr = unsafe_perform_io(result.unwrap())
    assert lbr.success is True
    assert len(lbr.file_entries) == 2
    assert lbr.file_entries[0]["file_path"] == "/a.py"
    assert lbr.file_entries[1]["file_path"] == "/b.py"
    assert "2" in lbr.summary

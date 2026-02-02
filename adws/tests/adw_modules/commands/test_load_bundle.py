"""Tests for /load_bundle command (Story 5.3).

Tests cover LoadBundleResult, _parse_bundle_content,
run_load_bundle_command. All io_ops calls are mocked per NFR10.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.commands.load_bundle import (
    LoadBundleResult,
    _parse_bundle_content,
    run_load_bundle_command,
)
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 2: LoadBundleResult tests ---


def test_load_bundle_result_construction() -> None:
    """LoadBundleResult can be constructed with all fields."""
    result = LoadBundleResult(
        success=True,
        session_id="session-abc",
        file_entries=[{"file_path": "/a.py"}],
        summary="Loaded 1 file entry",
        available_bundles=[],
    )
    assert result.success is True
    assert result.session_id == "session-abc"
    assert result.file_entries == [{"file_path": "/a.py"}]
    assert result.summary == "Loaded 1 file entry"
    assert result.available_bundles == []


def test_load_bundle_result_immutable() -> None:
    """LoadBundleResult is frozen -- no attribute reassignment."""
    result = LoadBundleResult(
        success=True,
        session_id="s",
        file_entries=[],
        summary="test",
    )
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


def test_load_bundle_result_default_available_bundles() -> None:
    """LoadBundleResult defaults available_bundles to empty."""
    result = LoadBundleResult(
        success=True,
        session_id="s",
        file_entries=[],
        summary="test",
    )
    assert result.available_bundles == []


# --- Task 3: _parse_bundle_content tests ---


def test_parse_bundle_content_valid_jsonl() -> None:
    """_parse_bundle_content parses valid JSONL lines."""
    content = (
        '{"file_path":"/a.py","operation":"read"}\n'
        '{"file_path":"/b.py","operation":"write"}\n'
    )
    entries = _parse_bundle_content(content)
    assert len(entries) == 2
    assert entries[0]["file_path"] == "/a.py"
    assert entries[0]["operation"] == "read"
    assert entries[1]["file_path"] == "/b.py"
    assert entries[1]["operation"] == "write"


def test_parse_bundle_content_skips_malformed_line() -> None:
    """_parse_bundle_content skips malformed JSON lines."""
    content = (
        '{"file_path":"/a.py"}\n'
        "not valid json\n"
        '{"file_path":"/b.py"}\n'
    )
    entries = _parse_bundle_content(content)
    assert len(entries) == 2
    assert entries[0]["file_path"] == "/a.py"
    assert entries[1]["file_path"] == "/b.py"


def test_parse_bundle_content_empty_string() -> None:
    """_parse_bundle_content returns empty list for empty string."""
    entries = _parse_bundle_content("")
    assert entries == []


def test_parse_bundle_content_trailing_newlines() -> None:
    """_parse_bundle_content skips blank lines."""
    content = (
        '{"file_path":"/a.py"}\n'
        "\n"
        "\n"
        '{"file_path":"/b.py"}\n'
        "\n"
    )
    entries = _parse_bundle_content(content)
    assert len(entries) == 2


def test_parse_bundle_content_validates_dict_type() -> None:
    """_parse_bundle_content skips non-dict JSON values."""
    content = (
        '{"file_path":"/a.py"}\n'
        '"just a string"\n'
        "[1, 2, 3]\n"
        '{"file_path":"/b.py"}\n'
    )
    entries = _parse_bundle_content(content)
    assert len(entries) == 2
    assert entries[0]["file_path"] == "/a.py"
    assert entries[1]["file_path"] == "/b.py"


# --- Task 4: run_load_bundle_command tests ---


def test_run_load_bundle_command_success(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command returns IOSuccess for valid bundle."""
    content = (
        '{"file_path":"/a.py","operation":"read",'
        '"timestamp":"2026-01-01","session_id":"s",'
        '"hook_name":"file_tracker"}\n'
        '{"file_path":"/b.py","operation":"write",'
        '"timestamp":"2026-01-01","session_id":"s",'
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
    assert "2" in lbr.summary
    assert lbr.available_bundles == []


def test_run_load_bundle_command_missing_session_id(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command errors when session_id missing."""
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
    assert isinstance(error, PipelineError)
    assert error.error_type == "MissingSessionIdError"
    assert "session-old" in str(error.context)
    assert "session-recent" in str(error.context)


def test_run_load_bundle_command_empty_session_id(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command treats empty string as missing."""
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOSuccess([]),
    )
    ctx = WorkflowContext(
        inputs={"session_id": ""},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "MissingSessionIdError"


def test_run_load_bundle_command_whitespace_session_id(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command treats whitespace-only as missing."""
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOSuccess([]),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "   "},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "MissingSessionIdError"


def test_run_load_bundle_command_non_string_session_id(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command rejects non-string session_id."""
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOSuccess([]),
    )
    ctx = WorkflowContext(
        inputs={"session_id": 12345},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "MissingSessionIdError"


def test_run_load_bundle_command_bundle_not_found(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command lists bundles when not found."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.read_context_bundle",
                error_type="ContextBundleNotFoundError",
                message="Not found: session-missing",
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
    assert "session-old" in str(error.context)
    assert "session-recent" in str(error.context)


def test_run_load_bundle_command_list_fails_gracefully(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command degrades when list fails."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.read_context_bundle",
                error_type="ContextBundleNotFoundError",
                message="Not found",
            ),
        ),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOFailure(
            PipelineError(
                step_name=(
                    "io_ops.list_context_bundles"
                ),
                error_type="ContextBundleListError",
                message="Permission denied",
            ),
        ),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-missing"},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "ContextBundleNotFoundError"
    assert error.context.get("available_bundles") == []


def test_run_load_bundle_command_empty_bundle(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command handles empty bundle content."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOSuccess(""),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-empty"},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOSuccess)
    lbr = unsafe_perform_io(result.unwrap())
    assert lbr.success is True
    assert lbr.file_entries == []
    assert "0" in lbr.summary


def test_run_load_bundle_command_read_error(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command propagates read errors."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_context_bundle",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.read_context_bundle",
                error_type="ContextBundleReadError",
                message="Permission denied",
            ),
        ),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOSuccess([]),
    )
    ctx = WorkflowContext(
        inputs={"session_id": "session-noperm"},
    )
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "ContextBundleReadError"


def test_run_load_bundle_command_list_fails_on_missing_id(
    mocker: MockerFixture,
) -> None:
    """run_load_bundle_command degrades when list fails and id missing."""
    mocker.patch(
        "adws.adw_modules.io_ops.list_context_bundles",
        return_value=IOFailure(
            PipelineError(
                step_name=(
                    "io_ops.list_context_bundles"
                ),
                error_type="ContextBundleListError",
                message="Permission denied",
            ),
        ),
    )
    ctx = WorkflowContext(inputs={})
    result = run_load_bundle_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "MissingSessionIdError"
    assert error.context.get("available_bundles") == []

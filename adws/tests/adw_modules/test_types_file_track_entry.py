"""Tests for FileTrackEntry data model."""
from __future__ import annotations

import dataclasses
import json

import pytest

from adws.adw_modules.types import FileTrackEntry


def test_file_track_entry_construction() -> None:
    """FileTrackEntry stores all fields correctly."""
    entry = FileTrackEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        file_path="/some/file.py",
        operation="read",
        session_id="session-abc123",
        hook_name="file_tracker",
    )
    assert entry.timestamp == "2026-02-02T10:30:00+00:00"
    assert entry.file_path == "/some/file.py"
    assert entry.operation == "read"
    assert entry.session_id == "session-abc123"
    assert entry.hook_name == "file_tracker"


def test_file_track_entry_is_frozen() -> None:
    """FileTrackEntry is an immutable frozen dataclass."""
    entry = FileTrackEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        file_path="/some/file.py",
        operation="read",
        session_id="sess-1",
        hook_name="file_tracker",
    )
    assert dataclasses.is_dataclass(entry)
    assert type(entry).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.file_path = "/other/file.py"  # type: ignore[misc]


def test_file_track_entry_to_jsonl_returns_valid_json() -> None:
    """to_jsonl() produces valid JSON."""
    entry = FileTrackEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        file_path="/some/file.py",
        operation="read",
        session_id="session-abc123",
        hook_name="file_tracker",
    )
    jsonl = entry.to_jsonl()
    parsed = json.loads(jsonl)
    assert isinstance(parsed, dict)


def test_file_track_entry_to_jsonl_is_single_line() -> None:
    """to_jsonl() output is a single line (no embedded newlines)."""
    entry = FileTrackEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        file_path="/some/file.py",
        operation="read",
        session_id="session-abc123",
        hook_name="file_tracker",
    )
    jsonl = entry.to_jsonl()
    assert "\n" not in jsonl


def test_file_track_entry_to_jsonl_contains_all_fields() -> None:
    """to_jsonl() output contains all fields."""
    entry = FileTrackEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        file_path="/some/file.py",
        operation="write",
        session_id="session-abc123",
        hook_name="file_tracker",
    )
    jsonl = entry.to_jsonl()
    parsed = json.loads(jsonl)
    assert parsed["timestamp"] == "2026-02-02T10:30:00+00:00"
    assert parsed["file_path"] == "/some/file.py"
    assert parsed["operation"] == "write"
    assert parsed["session_id"] == "session-abc123"
    assert parsed["hook_name"] == "file_tracker"

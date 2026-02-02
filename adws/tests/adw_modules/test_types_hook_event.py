"""Tests for HookEvent data model."""
from __future__ import annotations

import dataclasses
import json

import pytest

from adws.adw_modules.types import HookEvent


def test_hook_event_construction() -> None:
    """HookEvent stores all fields correctly."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="PreToolUse",
        hook_name="event_logger",
        session_id="session-abc123",
        payload={"tool_name": "Bash", "command": "ls"},
    )
    assert event.timestamp == "2026-02-02T10:30:00+00:00"
    assert event.event_type == "PreToolUse"
    assert event.hook_name == "event_logger"
    assert event.session_id == "session-abc123"
    assert event.payload == {
        "tool_name": "Bash",
        "command": "ls",
    }


def test_hook_event_is_frozen() -> None:
    """HookEvent is an immutable frozen dataclass."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="PreToolUse",
        hook_name="event_logger",
        session_id="sess-1",
        payload={},
    )
    assert dataclasses.is_dataclass(event)
    assert type(event).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.event_type = "PostToolUse"  # type: ignore[misc]


def test_hook_event_to_jsonl_returns_valid_json() -> None:
    """to_jsonl() produces valid JSON."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="PreToolUse",
        hook_name="event_logger",
        session_id="session-abc123",
        payload={"tool_name": "Bash", "command": "ls"},
    )
    jsonl = event.to_jsonl()
    parsed = json.loads(jsonl)
    assert isinstance(parsed, dict)


def test_hook_event_to_jsonl_is_single_line() -> None:
    """to_jsonl() output is a single line (no embedded newlines)."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="PreToolUse",
        hook_name="event_logger",
        session_id="session-abc123",
        payload={"tool_name": "Bash", "command": "ls"},
    )
    jsonl = event.to_jsonl()
    assert "\n" not in jsonl


def test_hook_event_to_jsonl_contains_all_fields() -> None:
    """to_jsonl() output contains all fields."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="PreToolUse",
        hook_name="event_logger",
        session_id="session-abc123",
        payload={"tool_name": "Bash", "command": "ls"},
    )
    jsonl = event.to_jsonl()
    parsed = json.loads(jsonl)
    assert parsed["timestamp"] == "2026-02-02T10:30:00+00:00"
    assert parsed["event_type"] == "PreToolUse"
    assert parsed["hook_name"] == "event_logger"
    assert parsed["session_id"] == "session-abc123"
    assert parsed["payload"] == {
        "tool_name": "Bash",
        "command": "ls",
    }


def test_hook_event_to_jsonl_empty_payload() -> None:
    """to_jsonl() works with empty payload dict."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="Notification",
        hook_name="notifier",
        session_id="sess-1",
        payload={},
    )
    jsonl = event.to_jsonl()
    parsed = json.loads(jsonl)
    assert parsed["payload"] == {}


def test_hook_event_to_jsonl_serializable_payload() -> None:
    """to_jsonl() handles various JSON-serializable payload values."""
    event = HookEvent(
        timestamp="2026-02-02T10:30:00+00:00",
        event_type="PostToolUse",
        hook_name="event_logger",
        session_id="sess-2",
        payload={
            "exit_code": 0,
            "success": True,
            "tags": ["a", "b"],
        },
    )
    jsonl = event.to_jsonl()
    parsed = json.loads(jsonl)
    assert parsed["payload"]["exit_code"] == 0
    assert parsed["payload"]["success"] is True
    assert parsed["payload"]["tags"] == ["a", "b"]

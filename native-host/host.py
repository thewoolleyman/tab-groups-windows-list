#!/usr/bin/env python3
"""Chrome native messaging host for window name reading.

Self-contained script — no external imports beyond stdlib.
Implements the Chrome native messaging protocol (4-byte
length-prefix stdin/stdout framing) to communicate with
the Tab Groups Windows List extension.

Supported actions:
  - get_window_names: Returns window names, bounds, active
    tab titles, and hasCustomName flag for the detected
    Chromium browser (Brave Browser or Google Chrome).
"""
from __future__ import annotations

import json
import struct
import subprocess
import sys
from typing import Any

_HEADER_SIZE = 4


# -- Protocol framing --


def _encode_message(msg: dict[str, Any]) -> bytes:
    """Encode a dict as a length-prefixed native message."""
    body = json.dumps(msg).encode("utf-8")
    header = struct.pack("<I", len(body))
    return header + body


def _decode_message(raw: bytes) -> dict[str, Any] | None:
    """Decode a length-prefixed native message.

    Returns parsed dict, or None if empty/truncated.
    """
    if len(raw) < _HEADER_SIZE:
        return None
    length = struct.unpack("<I", raw[:_HEADER_SIZE])[0]
    body = raw[_HEADER_SIZE:]
    if len(body) < length:
        return None
    try:
        result: dict[str, Any] = json.loads(body[:length])
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in native message: {exc}"
        raise ValueError(msg) from exc
    return result


# -- I/O --


def _read_stdin_message() -> bytes:
    """Read a length-prefixed message from stdin."""
    header: bytes = sys.stdin.buffer.read(_HEADER_SIZE)
    if len(header) < _HEADER_SIZE:
        return b""
    length = struct.unpack("<I", header)[0]
    body: bytes = sys.stdin.buffer.read(length)
    return header + body


def _write_stdout_message(msg: dict[str, Any]) -> None:
    """Write a length-prefixed JSON message to stdout."""
    body = json.dumps(msg).encode("utf-8")
    header = struct.pack("<I", len(body))
    sys.stdout.buffer.write(header + body)
    sys.stdout.buffer.flush()


# -- Browser detection and window querying --


def _detect_browser() -> str:
    """Detect which Chromium browser is running."""
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to '
         'get name of first process whose '
         'name contains "Brave"'],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode == 0 and "Brave" in result.stdout:
        return "Brave Browser"
    return "Google Chrome"


def _build_osascript_command(browser: str) -> str:
    """Build osascript command for querying window info."""
    return (
        f'osascript -l JavaScript -e \''
        f'var app = Application("{browser}");'
        f"var wins = app.windows();"
        f"var result = [];"
        f"for (var i = 0; i < wins.length; i++) {{"
        f"  var w = wins[i];"
        f"  result.push({{"
        f"    name: w.name(),"
        f"    bounds: w.bounds(),"
        f"    activeTabTitle: w.activeTab().title()"
        f"  }});"
        f"}}"
        f"JSON.stringify(result);"
        f"'"
    )


def _parse_osascript_output(raw: str) -> list[dict[str, Any]]:
    """Parse osascript JSON output and add hasCustomName."""
    if not raw or not raw.strip():
        return []
    try:
        windows: list[dict[str, Any]] = json.loads(raw.strip())
    except (json.JSONDecodeError, TypeError):
        return []
    for win in windows:
        name = win.get("name", "")
        active_title = win.get("activeTabTitle", "")
        win["hasCustomName"] = name != active_title
    return windows


def _get_window_names() -> list[dict[str, Any]]:
    """Get window names for the detected browser."""
    browser = _detect_browser()
    cmd = _build_osascript_command(browser)
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return []
    return _parse_osascript_output(result.stdout)


# -- Request handling --


def _handle_message(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a native messaging request."""
    action = request.get("action")
    if not action:
        return {
            "success": False,
            "error": "Missing 'action' field in request",
        }
    if action == "get_window_names":
        try:
            windows = _get_window_names()
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }
        return {
            "success": True,
            "windows": windows,
        }
    return {
        "success": False,
        "error": f"Unknown action: {action}",
    }


# -- Main entry point --


def main() -> None:
    """Run the native messaging host."""
    raw = _read_stdin_message()
    if not raw:
        return
    request = _decode_message(raw)
    if request is None:
        _write_stdout_message({
            "success": False,
            "error": "Failed to decode message",
        })
        return
    response = _handle_message(request)
    _write_stdout_message(response)


if __name__ == "__main__":
    main()

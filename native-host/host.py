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
import logging
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

_HEADER_SIZE = 4
_LOG_DIR = Path.home() / ".local" / "lib" / "tab-groups-window-namer"
_LOG_FILE = _LOG_DIR / "debug.log"
_MAX_LOG_LINES = 1000


def _setup_debug_logging() -> logging.Logger:
    """Set up file-based debug logging with line truncation."""
    logger = logging.getLogger("tgwl-host")
    logger.setLevel(logging.DEBUG)

    # Don't add handlers if already configured
    if logger.handlers:
        return logger

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Truncate log file to last _MAX_LOG_LINES on startup
        if _LOG_FILE.exists():
            try:
                lines = _LOG_FILE.read_text().splitlines()
                if len(lines) > _MAX_LOG_LINES:
                    _LOG_FILE.write_text(
                        "\n".join(lines[-_MAX_LOG_LINES:]) + "\n",
                    )
            except OSError:
                pass

        handler = logging.FileHandler(str(_LOG_FILE))
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except OSError:
        # If we can't write logs, continue without them
        pass

    return logger


_logger = _setup_debug_logging()


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
    _logger.debug("Detecting browser...")
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
        _logger.debug("Detected: Brave Browser")
        return "Brave Browser"
    _logger.debug("Detected: Google Chrome")
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


def _get_window_names(browser: str | None = None) -> list[dict[str, Any]]:
    """Get window names for the specified or detected browser."""
    if not browser:
        browser = _detect_browser()
    else:
        _logger.debug("Using browser from request: %s", browser)
    cmd = _build_osascript_command(browser)
    _logger.debug("osascript command: %s", cmd[:200])
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    _logger.debug("osascript rc=%d stdout=%s stderr=%s",
                   result.returncode,
                   result.stdout[:500] if result.stdout else "",
                   result.stderr[:500] if result.stderr else "")
    if result.returncode != 0:
        _logger.warning("osascript failed with rc=%d", result.returncode)
        return []
    windows = _parse_osascript_output(result.stdout)
    _logger.debug("Parsed %d windows", len(windows))
    return windows


# -- Request handling --


def _handle_message(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a native messaging request."""
    _logger.debug("Request received: %s", json.dumps(request)[:500])
    action = request.get("action")
    if not action:
        _logger.warning("Missing 'action' field")
        return {
            "success": False,
            "error": "Missing 'action' field in request",
        }
    if action == "get_window_names":
        try:
            browser = request.get("browser")
            windows = _get_window_names(browser)
        except Exception as exc:
            _logger.exception("get_window_names failed")
            return {
                "success": False,
                "error": str(exc),
            }
        response = {
            "success": True,
            "windows": windows,
        }
        _logger.debug("Response: %s", json.dumps(response)[:500])
        return response
    if action == "ping":
        _logger.debug("Ping received")
        return {"success": True}
    if action == "get_debug_log":
        return _get_debug_log_tail()
    if action == "log_extension_data":
        return _log_extension_data(request)
    _logger.warning("Unknown action: %s", action)
    return {
        "success": False,
        "error": f"Unknown action: {action}",
    }


def _log_extension_data(request: dict[str, Any]) -> dict[str, Any]:
    """Log extension data to the debug log file."""
    data = request.get("data")
    if not data:
        return {"success": False, "error": "Missing 'data' field in request"}
    _logger.info("[EXT-DATA] %s", json.dumps(data)[:2000])
    return {"success": True}


def _get_debug_log_tail(lines: int = 20) -> dict[str, Any]:
    """Return the tail of the debug log file."""
    try:
        if _LOG_FILE.exists():
            all_lines = _LOG_FILE.read_text().splitlines()
            tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {"success": True, "log": "\n".join(tail)}
        return {"success": True, "log": "(no log file)"}
    except OSError as exc:
        return {"success": False, "error": str(exc)}


# -- Main entry point --


def main() -> None:
    """Run the native messaging host."""
    _logger.debug("--- host.py started ---")
    raw = _read_stdin_message()
    if not raw:
        _logger.debug("Empty stdin, exiting")
        return
    request = _decode_message(raw)
    if request is None:
        _logger.warning("Failed to decode message")
        _write_stdout_message({
            "success": False,
            "error": "Failed to decode message",
        })
        return
    response = _handle_message(request)
    _write_stdout_message(response)
    _logger.debug("--- host.py finished ---")


if __name__ == "__main__":
    main()

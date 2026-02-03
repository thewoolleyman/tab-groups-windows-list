"""Native messaging request handler.

Dispatches incoming JSON requests by action type and
returns JSON responses.
"""
from __future__ import annotations

from typing import Any

from adws.native_host.browser import get_window_names


def handle_message(
    request: dict[str, Any],
) -> dict[str, Any]:
    """Handle a native messaging request.

    Dispatches based on the 'action' field. Returns a
    response dict with 'success' and either 'windows'
    or 'error'.
    """
    action = request.get("action")
    if not action:
        return {
            "success": False,
            "error": "Missing 'action' field in request",
        }
    if action == "get_window_names":
        return _handle_get_window_names()
    return {
        "success": False,
        "error": f"Unknown action: {action}",
    }


def _handle_get_window_names() -> dict[str, Any]:
    """Handle the get_window_names action.

    Returns success response with windows list, or error
    response on exception.
    """
    try:
        windows = get_window_names()
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "error": str(exc),
        }
    return {
        "success": True,
        "windows": windows,
    }

"""Browser detection and window name reading via osascript.

Detects whether Brave Browser or Google Chrome is running,
then uses osascript -l JavaScript to query window names,
bounds, and active tab titles.
"""
from __future__ import annotations

import json
from typing import Any

from adws.native_host import io_ops

_DETECT_SCRIPT = (
    "osascript -e 'tell application \"System Events\" to "
    "get name of first process whose name contains \"Brave\"'"
)

_OSASCRIPT_TEMPLATE = """osascript -l JavaScript -e '
var app = Application("{browser}");
var wins = app.windows();
var result = [];
for (var i = 0; i < wins.length; i++) {{
    var w = wins[i];
    var tabs = w.tabs();
    var activeTab = w.activeTab();
    result.push({{
        name: w.name(),
        bounds: w.bounds(),
        activeTabTitle: activeTab ? activeTab.title() : ""
    }});
}}
JSON.stringify(result);
'"""


def detect_browser() -> str:
    """Detect which Chromium browser is running.

    Checks for Brave Browser first, falls back to Google
    Chrome.
    """
    result = io_ops.run_subprocess(
        ["osascript", "-e",
         'tell application "System Events" to '
         'get name of first process whose '
         'name contains "Brave"'],
        timeout=5,
    )
    if result.returncode == 0 and "Brave" in result.stdout:
        return "Brave Browser"
    return "Google Chrome"


def build_osascript_command(browser: str) -> str:
    """Build the osascript command for the given browser.

    Returns the full command string that queries window
    names, bounds, and active tab titles.
    """
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


def parse_osascript_output(
    raw: str,
) -> list[dict[str, Any]]:
    """Parse osascript JSON output and add hasCustomName.

    Returns list of window dicts. Each dict gets a
    hasCustomName field: true when name differs from
    activeTabTitle.
    """
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


def get_window_names() -> list[dict[str, Any]]:
    """Get window names for the detected browser.

    Detects the browser, builds and runs osascript command,
    parses output. Returns list of window dicts with
    hasCustomName field.
    """
    browser = detect_browser()
    cmd = build_osascript_command(browser)
    result = io_ops.run_subprocess(
        ["bash", "-c", cmd],
        timeout=10,
    )
    if result.returncode != 0:
        return []
    return parse_osascript_output(result.stdout)

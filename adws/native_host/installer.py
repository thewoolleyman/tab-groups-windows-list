"""Native messaging host installer for macOS.

Downloads host.py, makes it executable, detects installed
Chromium browsers, and places manifest JSON files in each
browser's NativeMessagingHosts directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from adws.native_host import io_ops

EXTENSION_ID = "gialhfelganamiclidkigjnjdkdbohcb"
HOST_NAME = "com.tabgroups.window_namer"
INSTALL_DIR = str(
    Path("~/.local/lib/tab-groups-window-namer").expanduser(),
)
HOST_PY_URL = (
    "https://raw.githubusercontent.com/"
    "thewoolleyman/tab-groups-windows-list/"
    "master/native-host/host.py"
)

BROWSERS_MACOS: list[dict[str, str]] = [
    {
        "name": "Google Chrome",
        "manifest_dir": str(
            Path(
                "~/Library/Application Support/"
                "Google/Chrome/NativeMessagingHosts",
            ).expanduser(),
        ),
    },
    {
        "name": "Brave Browser",
        "manifest_dir": str(
            Path(
                "~/Library/Application Support/"
                "BraveSoftware/Brave-Browser/"
                "NativeMessagingHosts",
            ).expanduser(),
        ),
    },
    {
        "name": "Microsoft Edge",
        "manifest_dir": str(
            Path(
                "~/Library/Application Support/"
                "Microsoft Edge/NativeMessagingHosts",
            ).expanduser(),
        ),
    },
    {
        "name": "Chromium",
        "manifest_dir": str(
            Path(
                "~/Library/Application Support/"
                "Chromium/NativeMessagingHosts",
            ).expanduser(),
        ),
    },
]


def is_macos() -> bool:
    """Check if current platform is macOS."""
    return sys.platform == "darwin"


def build_manifest(host_path: str) -> dict[str, Any]:
    """Build the native messaging host manifest dict.

    Returns a dict with name, description, path, type,
    and allowed_origins fields.
    """
    return {
        "name": HOST_NAME,
        "description": (
            "Native messaging host for Tab Groups "
            "Windows List window name reading"
        ),
        "path": host_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{EXTENSION_ID}/",
        ],
    }


def detect_installed_browsers() -> list[dict[str, str]]:
    """Detect which Chromium browsers are installed.

    Checks each browser's Application Support directory
    parent to determine if the browser is installed.
    Returns list of browser dicts for installed browsers.
    """
    installed: list[dict[str, str]] = []
    for browser in BROWSERS_MACOS:
        # Check if the parent of NativeMessagingHosts exists
        parent_dir = str(
            Path(browser["manifest_dir"]).parent,
        )
        if io_ops.path_exists(parent_dir):
            installed.append(browser)
    return installed


def make_executable(path: str) -> None:
    """Make a file executable."""
    io_ops.chmod_executable(path)


def install_manifest_for_browser(
    browser: dict[str, str],
    host_path: str,
) -> dict[str, Any]:
    """Install the manifest JSON for a single browser.

    Creates the NativeMessagingHosts directory and writes
    the manifest file. Returns a result dict with browser
    name, success status, and optional error.
    """
    try:
        io_ops.makedirs(browser["manifest_dir"])
        manifest = build_manifest(host_path)
        manifest_path = str(
            Path(browser["manifest_dir"])
            / f"{HOST_NAME}.json",
        )
        io_ops.write_file(
            manifest_path,
            json.dumps(manifest, indent=2) + "\n",
        )
        return {
            "browser": browser["name"],
            "success": True,
        }
    except OSError as e:
        return {
            "browser": browser["name"],
            "success": False,
            "error": str(e),
        }


def format_summary(
    results: list[dict[str, Any]],
) -> str:
    """Format installation results as a human-readable summary."""
    if not results:
        return (
            "No Chromium browsers detected. "
            "No manifests were installed."
        )
    lines = ["Installation summary:"]
    for result in results:
        name = result["browser"]
        if result["success"]:
            lines.append(f"  {name}: OK")
        else:
            error = result.get("error", "unknown error")
            lines.append(f"  {name}: FAIL ({error})")
    return "\n".join(lines)


def install_host() -> dict[str, Any]:
    """Main installer entry point.

    On non-macOS, prints a friendly message. On macOS,
    downloads host.py, makes it executable, detects
    browsers, installs manifests, and prints summary.
    """
    if not is_macos():
        msg = (
            "Window name sync is macOS only. "
            "This feature requires macOS to read "
            "browser window names via osascript."
        )
        io_ops.print_output(msg)
        return {"macos_only_message": True}

    # Create install directory
    io_ops.makedirs(INSTALL_DIR)

    # Download host.py
    host_path = str(Path(INSTALL_DIR) / "host.py")
    io_ops.download_file(HOST_PY_URL, host_path)

    # Make executable
    io_ops.chmod_executable(host_path)

    # Detect and install for each browser
    browsers = detect_installed_browsers()
    results: list[dict[str, Any]] = []
    for browser in browsers:
        result = install_manifest_for_browser(
            browser, host_path,
        )
        results.append(result)

    # Print summary
    summary = format_summary(results)
    io_ops.print_output(summary)

    return {"results": results, "summary": summary}

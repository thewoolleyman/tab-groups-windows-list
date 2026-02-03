"""Tests that native-host/host.py works as a standalone script.

Verifies host.py can be executed without the adws package
on sys.path, which is the condition when installed to
~/.local/lib/tab-groups-window-namer/.

The key trick: we COPY host.py to a temp directory before
running it, so the sys.path hack (parent.parent) no longer
points at the repo root.
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

_HOST_PY_SRC = (
    Path(__file__).resolve().parents[3] / "native-host" / "host.py"
)


@pytest.fixture
def isolated_host(tmp_path: Path) -> Path:
    """Copy host.py to an isolated temp directory.

    This simulates the install scenario where host.py lives
    in ~/.local/lib/tab-groups-window-namer/ with no adws
    package nearby.
    """
    dest = tmp_path / "host.py"
    shutil.copy2(_HOST_PY_SRC, dest)
    return dest


class TestHostStandalone:
    """Tests for host.py standalone execution."""

    def test_host_imports_without_adws_package(
        self, isolated_host: Path,
    ) -> None:
        """host.py should not raise ModuleNotFoundError.

        Runs the COPIED host.py with PYTHONPATH cleared so
        the adws package is not discoverable. Sends empty
        stdin so it exits immediately. The exit should be
        clean (rc 0), not a ModuleNotFoundError crash.
        """
        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0, (
            f"host.py crashed (rc={result.returncode}):\n"
            f"stderr: {result.stderr}"
        )
        assert "ModuleNotFoundError" not in result.stderr
        assert "ImportError" not in result.stderr

    def test_host_responds_to_get_window_names(
        self, isolated_host: Path,
    ) -> None:
        """host.py should respond to a valid native message.

        Sends a get_window_names request via native messaging
        protocol and checks for a JSON response with success
        field. osascript may fail in CI, so we accept either
        success:true or success:false with an error, as long
        as the script produces a valid framed response.
        """
        request = {"action": "get_window_names"}
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=15,
            check=False,
            cwd=str(isolated_host.parent),
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
            input=stdin_data,
        )
        assert result.returncode == 0, (
            f"host.py crashed (rc={result.returncode}):\n"
            f"stderr: {result.stderr.decode('utf-8', errors='replace')}"
        )
        stdout = result.stdout
        assert len(stdout) >= 4, "No response written to stdout"
        length = struct.unpack("<I", stdout[:4])[0]
        response_body = stdout[4 : 4 + length]
        response = json.loads(response_body)
        assert "success" in response

    def test_host_rejects_unknown_action(
        self, isolated_host: Path,
    ) -> None:
        """host.py returns error for unknown action."""
        request = {"action": "nonexistent_action"}
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is False
        assert "Unknown action" in response["error"]

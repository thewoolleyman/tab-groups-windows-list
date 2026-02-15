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
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

_HOST_PY_SRC = (
    Path(__file__).resolve().parents[2] / "native-host" / "host.py"
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

    def test_host_uses_browser_from_request(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should use the browser field from the request."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "browser_test_home"),
        }
        request = {"action": "get_window_names", "browser": "Google Chrome"}
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=15,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert "success" in response

        # Verify the debug log shows it used the browser from request
        log_dir = tmp_path / "browser_test_home" / ".local" / "lib" / "tab-groups-window-namer"
        log_file = log_dir / "debug.log"
        if log_file.exists():
            content = log_file.read_text()
            assert "Using browser from request: Google Chrome" in content

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


class TestHostDebugLogging:
    """Tests for host.py debug log file creation and truncation."""

    def test_creates_debug_log_file(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should create a debug.log file on execution."""
        log_dir = tmp_path / "log_home" / ".local" / "lib" / "tab-groups-window-namer"
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "log_home"),
        }

        # Send empty stdin so host exits quickly
        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0, (
            f"host.py crashed: {result.stderr}"
        )
        log_file = log_dir / "debug.log"
        assert log_file.exists(), "debug.log should be created"
        content = log_file.read_text()
        assert "host.py started" in content

    def test_debug_log_truncation(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should truncate debug.log to last 1000 lines."""
        log_dir = tmp_path / "trunc_home" / ".local" / "lib" / "tab-groups-window-namer"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "debug.log"

        # Write 1500 lines to simulate a large log
        lines = [f"line {i}" for i in range(1500)]
        log_file.write_text("\n".join(lines) + "\n")

        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "trunc_home"),
        }

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0

        # After truncation + new log entries, should be <= ~1002 lines
        remaining = log_file.read_text().splitlines()
        assert len(remaining) <= 1010, (
            f"Expected truncation to ~1000 lines, got {len(remaining)}"
        )
        # The first retained line should be from the tail end
        assert "line 500" in remaining[0]

    def test_get_debug_log_action(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should respond to get_debug_log action."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "log_action_home"),
        }

        # First run to create the log
        subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            stdin=subprocess.DEVNULL,
        )

        # Now request the log tail
        request = {"action": "get_debug_log"}
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is True
        assert "log" in response

    def test_log_extension_data_action(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should accept log_extension_data and write to debug log."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "ext_log_home"),
        }
        log_dir = tmp_path / "ext_log_home" / ".local" / "lib" / "tab-groups-window-namer"

        request = {
            "action": "log_extension_data",
            "data": {
                "source": "background.js",
                "event": "match_result",
                "matches": [
                    {"windowId": 123, "name": "Test Window", "score": 3},
                ],
                "totalMatches": 1,
            },
        }
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is True

        # Verify the data was written to the debug log
        log_file = log_dir / "debug.log"
        log_content = log_file.read_text()
        assert "EXT-DATA" in log_content
        assert "match_result" in log_content
        assert "Test Window" in log_content

    def test_log_extension_data_rejects_missing_data(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should reject log_extension_data without data field."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "ext_log_nodata"),
        }

        request = {"action": "log_extension_data"}
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is False
        assert "data" in response["error"].lower()


class TestHostMissingActionAndPing:
    """Tests for missing action field and ping action."""

    def test_host_rejects_missing_action_field(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should return error when action field is missing."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "no_action_home"),
        }
        request = {"key": "value"}  # No 'action' field
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is False
        assert "action" in response["error"].lower()

    def test_host_responds_to_ping(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should respond successfully to ping action."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "ping_home"),
        }
        request = {"action": "ping"}
        body = json.dumps(request).encode("utf-8")
        stdin_data = struct.pack("<I", len(body)) + body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is True


class TestHostMalformedInput:
    """Tests for malformed/corrupt native messaging input."""

    def test_host_handles_malformed_json(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should return error for invalid JSON in native message."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "bad_json_home"),
        }
        # Send a valid length header but invalid JSON body
        bad_body = b"not valid json{{"
        stdin_data = struct.pack("<I", len(bad_body)) + bad_body

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is False
        assert "decode" in response["error"].lower()

    def test_host_handles_truncated_message(
        self, isolated_host: Path, tmp_path: Path,
    ) -> None:
        """host.py should handle truncated stdin gracefully."""
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path / "trunc_home"),
        }
        # Send a length header claiming 100 bytes but only provide 5
        stdin_data = struct.pack("<I", 100) + b"short"

        result = subprocess.run(
            [sys.executable, str(isolated_host)],
            capture_output=True,
            timeout=10,
            check=False,
            cwd=str(isolated_host.parent),
            env=env,
            input=stdin_data,
        )
        assert result.returncode == 0
        stdout = result.stdout
        assert len(stdout) >= 4
        length = struct.unpack("<I", stdout[:4])[0]
        response = json.loads(stdout[4 : 4 + length])
        assert response["success"] is False

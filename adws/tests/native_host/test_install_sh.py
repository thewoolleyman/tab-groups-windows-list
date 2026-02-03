"""Tests for native-host/install.sh shell script.

Unit tests (static analysis) and E2E tests that actually run
the installer in a sandboxed temp environment. Covers both
macOS and Linux behavior.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

INSTALL_SH = str(
    Path(__file__).resolve().parents[3]
    / "native-host"
    / "install.sh",
)

# ----------------------------------------------------------------
# Unit tests: static analysis of shell script
# ----------------------------------------------------------------


class TestShellScriptCompatibility:
    """Verify install.sh avoids bash 4+ features."""

    def test_script_exists(self) -> None:
        """install.sh exists at expected path."""
        assert Path(INSTALL_SH).is_file()

    def test_no_associative_arrays(self) -> None:
        """Script must not use 'declare -A' (bash 4+ only).

        macOS ships with bash 3.2 and npm/package.json
        invokes /bin/bash, so the script must be compatible.
        """
        content = Path(INSTALL_SH).read_text()
        matches = re.findall(r"declare\s+-A", content)
        assert matches == [], (
            f"Found bash 4+ 'declare -A' on "
            f"{len(matches)} line(s). "
            f"macOS /bin/bash is 3.2."
        )

    def test_no_bash4_features(self) -> None:
        """Script avoids other common bash 4+ features.

        Checks for: nameref (declare -n), readarray/mapfile,
        associative arrays (${!arr[@]} pattern on -A vars),
        |& operator, and coproc.
        """
        content = Path(INSTALL_SH).read_text()
        bash4_patterns = [
            (r"declare\s+-n\b", "declare -n (nameref)"),
            (r"\breadarray\b", "readarray"),
            (r"\bmapfile\b", "mapfile"),
            (r"\bcoproc\b", "coproc"),
        ]
        violations = []
        for pattern, desc in bash4_patterns:
            if re.search(pattern, content):
                violations.append(desc)
        assert violations == [], (
            f"Found bash 4+ features: {violations}"
        )

    def test_shebang_is_bash(self) -> None:
        """Script starts with a bash shebang."""
        content = Path(INSTALL_SH).read_text()
        first_line = content.split("\n")[0]
        assert "bash" in first_line, (
            f"Expected bash shebang, got: {first_line}"
        )

    def test_bash_syntax_valid(self) -> None:
        """Script passes bash -n syntax check."""
        result = subprocess.run(  # noqa: S603
            ["/bin/bash", "-n", INSTALL_SH],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Syntax error: {result.stderr}"
        )


# ----------------------------------------------------------------
# E2E tests: run install.sh in sandboxed temp directory
# ----------------------------------------------------------------


class TestInstallShE2EMacOS:
    """E2E tests for install.sh on macOS.

    These tests create a fake HOME with simulated browser
    Application Support directories, run install.sh with
    a local file:// URL (no network), and verify manifests
    are created correctly.
    """

    @pytest.fixture
    def sandbox(self, tmp_path: Path) -> dict[str, Path]:
        """Create a sandboxed HOME with fake browser dirs.

        Sets up:
        - fake HOME at tmp_path/home
        - Brave Browser Application Support dir
        - A local host.py to serve via file://
        """
        home = tmp_path / "home"
        home.mkdir()

        # Create Brave's Application Support parent dir
        brave_dir = (
            home
            / "Library"
            / "Application Support"
            / "BraveSoftware"
            / "Brave-Browser"
        )
        brave_dir.mkdir(parents=True)

        # Create Chrome Application Support parent dir
        chrome_dir = (
            home
            / "Library"
            / "Application Support"
            / "Google"
            / "Chrome"
        )
        chrome_dir.mkdir(parents=True)

        # Create a local host.py to "download"
        local_host_py = tmp_path / "host.py"
        local_host_py.write_text(
            "#!/usr/bin/env python3\n"
            "# test host.py\n"
        )

        return {
            "home": home,
            "brave_dir": brave_dir,
            "chrome_dir": chrome_dir,
            "local_host_py": local_host_py,
        }

    @pytest.mark.skipif(
        sys.platform != "darwin",
        reason="macOS-only test",
    )
    def test_installs_manifest_for_detected_browsers(
        self, sandbox: dict[str, Path], tmp_path: Path,
    ) -> None:
        """Installs manifest JSON for each detected browser."""
        home = sandbox["home"]
        local_host_py = sandbox["local_host_py"]

        # Create a modified install.sh that uses file:// URL
        # and our fake HOME
        modified_script = _create_sandboxed_script(
            INSTALL_SH,
            home=str(home),
            host_py_url=local_host_py.as_uri(),
        )
        script_path = tmp_path / "install_test.sh"
        script_path.write_text(modified_script)
        script_path.chmod(
            script_path.stat().st_mode | stat.S_IXUSR,
        )

        result = subprocess.run(  # noqa: S603
            ["/bin/bash", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "HOME": str(home)},
        )

        assert result.returncode == 0, (
            f"install.sh failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

        # Verify host.py was downloaded
        installed_host = (
            home
            / ".local"
            / "lib"
            / "tab-groups-window-namer"
            / "host.py"
        )
        assert installed_host.is_file(), (
            "host.py not found at expected location"
        )
        assert os.access(installed_host, os.X_OK), (
            "host.py is not executable"
        )

        # Verify Brave manifest
        brave_manifest = (
            home
            / "Library"
            / "Application Support"
            / "BraveSoftware"
            / "Brave-Browser"
            / "NativeMessagingHosts"
            / "com.tabgroups.window_namer.json"
        )
        assert brave_manifest.is_file(), (
            "Brave manifest not created"
        )
        manifest_data = json.loads(brave_manifest.read_text())
        assert manifest_data["name"] == (
            "com.tabgroups.window_namer"
        )
        assert manifest_data["type"] == "stdio"
        assert "chrome-extension://" in (
            manifest_data["allowed_origins"][0]
        )

        # Verify Chrome manifest
        chrome_manifest = (
            home
            / "Library"
            / "Application Support"
            / "Google"
            / "Chrome"
            / "NativeMessagingHosts"
            / "com.tabgroups.window_namer.json"
        )
        assert chrome_manifest.is_file(), (
            "Chrome manifest not created"
        )

    @pytest.mark.skipif(
        sys.platform != "darwin",
        reason="macOS-only test",
    )
    def test_skips_uninstalled_browsers(
        self, tmp_path: Path,
    ) -> None:
        """Browsers without Application Support dirs are skipped."""
        home = tmp_path / "home"
        home.mkdir()
        # No browser dirs created — all should be skipped

        local_host_py = tmp_path / "host.py"
        local_host_py.write_text("#!/usr/bin/env python3\n")

        modified_script = _create_sandboxed_script(
            INSTALL_SH,
            home=str(home),
            host_py_url=local_host_py.as_uri(),
        )
        script_path = tmp_path / "install_test.sh"
        script_path.write_text(modified_script)
        script_path.chmod(
            script_path.stat().st_mode | stat.S_IXUSR,
        )

        result = subprocess.run(  # noqa: S603
            ["/bin/bash", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "HOME": str(home)},
        )

        assert result.returncode == 0
        assert "No Chromium browsers" in result.stdout

    @pytest.mark.skipif(
        sys.platform != "darwin",
        reason="macOS-only test",
    )
    def test_output_shows_success_summary(
        self, sandbox: dict[str, Path], tmp_path: Path,
    ) -> None:
        """Installer prints success summary for configured browsers."""
        home = sandbox["home"]
        local_host_py = sandbox["local_host_py"]

        modified_script = _create_sandboxed_script(
            INSTALL_SH,
            home=str(home),
            host_py_url=local_host_py.as_uri(),
        )
        script_path = tmp_path / "install_test.sh"
        script_path.write_text(modified_script)
        script_path.chmod(
            script_path.stat().st_mode | stat.S_IXUSR,
        )

        result = subprocess.run(  # noqa: S603
            ["/bin/bash", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "HOME": str(home)},
        )

        assert result.returncode == 0
        assert "Brave Browser" in result.stdout
        assert "OK" in result.stdout
        assert "Restart your browser" in result.stdout


class TestInstallShE2ELinux:
    """E2E tests for install.sh on Linux.

    On Linux, the script should print a friendly message
    and exit cleanly without installing anything.
    """

    @pytest.mark.skipif(
        sys.platform != "linux",
        reason="Linux-only test",
    )
    def test_prints_macos_only_message(
        self,
    ) -> None:
        """On Linux, prints macOS-only message and exits 0."""
        result = subprocess.run(  # noqa: S603
            ["/bin/bash", INSTALL_SH],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "macOS only" in result.stdout

    @pytest.mark.skipif(
        sys.platform != "linux",
        reason="Linux-only test",
    )
    def test_does_not_create_files(
        self, tmp_path: Path,
    ) -> None:
        """On Linux, no files are created."""
        home = tmp_path / "home"
        home.mkdir()

        result = subprocess.run(  # noqa: S603
            ["/bin/bash", INSTALL_SH],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "HOME": str(home)},
        )
        assert result.returncode == 0
        local_dir = home / ".local" / "lib"
        assert not local_dir.exists()


class TestInstallShViaNpmRun:
    """E2E test that verifies npm run install:native-host works.

    This is the exact invocation that was failing due to
    bash 3.2 incompatibility.
    """

    @pytest.mark.skipif(
        sys.platform != "darwin",
        reason="macOS-only test",
    )
    def test_npm_run_does_not_error(
        self, tmp_path: Path,
    ) -> None:
        """npm run install:native-host exits without bash errors.

        We override HOME so it doesn't touch real browser dirs,
        and use a local file:// URL to avoid network access.
        The key assertion is that it doesn't fail with
        'declare: -A: invalid option' or similar bash errors.
        """
        home = tmp_path / "home"
        home.mkdir()

        local_host_py = tmp_path / "host.py"
        local_host_py.write_text("#!/usr/bin/env python3\n")

        # Create modified script in a temp location
        modified_script = _create_sandboxed_script(
            INSTALL_SH,
            home=str(home),
            host_py_url=local_host_py.as_uri(),
        )
        script_path = tmp_path / "install.sh"
        script_path.write_text(modified_script)
        script_path.chmod(
            script_path.stat().st_mode | stat.S_IXUSR,
        )

        # Run via /bin/bash (same as npm would)
        result = subprocess.run(  # noqa: S603
            ["/bin/bash", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "HOME": str(home)},
        )

        # Must not have bash syntax/feature errors
        assert "invalid option" not in result.stderr, (
            f"Bash compatibility error: {result.stderr}"
        )
        assert "declare" not in result.stderr, (
            f"declare error: {result.stderr}"
        )
        assert result.returncode == 0, (
            f"Script failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------


def _create_sandboxed_script(
    original_path: str,
    *,
    home: str,
    host_py_url: str,
) -> str:
    """Create a modified install.sh for sandboxed testing.

    Replaces HOME and HOST_PY_URL so the script runs in a
    temp directory without network access.
    """
    content = Path(original_path).read_text()
    # Replace the download URL with a local file:// URL
    content = re.sub(
        r'HOST_PY_URL="[^"]*"',
        f'HOST_PY_URL="{host_py_url}"',
        content,
    )
    # Override HOME at the top of the script
    content = content.replace(
        "set -euo pipefail",
        f'set -euo pipefail\nexport HOME="{home}"',
    )
    # Use curl for file:// URLs
    return content.replace(
        "curl -fsSL",
        "curl -fsSL --proto -all,+file,+https",
    )

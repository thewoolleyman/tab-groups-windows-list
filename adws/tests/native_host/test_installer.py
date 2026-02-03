"""Tests for the native messaging host installer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from adws.native_host.installer import (
    BROWSERS_MACOS,
    EXTENSION_ID,
    HOST_NAME,
    HOST_PY_URL,
    INSTALL_DIR,
    build_manifest,
    detect_installed_browsers,
    format_summary,
    install_host,
    install_manifest_for_browser,
    is_macos,
    make_executable,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestConstants:
    """Tests for installer constants."""

    def test_extension_id(self) -> None:
        """Extension ID matches the published extension."""
        assert EXTENSION_ID == "gialhfelganamiclidkigjnjdkdbohcb"

    def test_host_name(self) -> None:
        """Host name matches the native messaging host name."""
        assert HOST_NAME == "com.tabgroups.window_namer"

    def test_install_dir(self) -> None:
        """Install directory uses ~/.local/lib path."""
        expected = str(
            Path(
                "~/.local/lib/tab-groups-window-namer",
            ).expanduser(),
        )
        assert expected == INSTALL_DIR

    def test_host_py_url(self) -> None:
        """Download URL points to the GitHub repo."""
        assert "github" in HOST_PY_URL.lower()
        assert "host.py" in HOST_PY_URL

    def test_browsers_macos_includes_chrome(self) -> None:
        """Browser list includes Google Chrome."""
        browser_names = [b["name"] for b in BROWSERS_MACOS]
        assert "Google Chrome" in browser_names

    def test_browsers_macos_includes_brave(self) -> None:
        """Browser list includes Brave Browser."""
        browser_names = [b["name"] for b in BROWSERS_MACOS]
        assert "Brave Browser" in browser_names

    def test_browsers_macos_includes_edge(self) -> None:
        """Browser list includes Microsoft Edge."""
        browser_names = [b["name"] for b in BROWSERS_MACOS]
        assert "Microsoft Edge" in browser_names

    def test_browsers_macos_includes_chromium(self) -> None:
        """Browser list includes Chromium."""
        browser_names = [b["name"] for b in BROWSERS_MACOS]
        assert "Chromium" in browser_names

    def test_browsers_macos_have_manifest_dirs(self) -> None:
        """Each browser entry has a manifest_dir path."""
        for browser in BROWSERS_MACOS:
            assert "manifest_dir" in browser
            assert "NativeMessagingHosts" in browser["manifest_dir"]


class TestIsMacos:
    """Tests for macOS platform detection."""

    def test_returns_true_on_darwin(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns True when sys.platform is 'darwin'."""
        mocker.patch(
            "adws.native_host.installer.sys.platform",
            "darwin",
        )
        assert is_macos() is True

    def test_returns_false_on_linux(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns False when sys.platform is 'linux'."""
        mocker.patch(
            "adws.native_host.installer.sys.platform",
            "linux",
        )
        assert is_macos() is False


class TestBuildManifest:
    """Tests for native messaging host manifest generation."""

    def test_manifest_has_name(self) -> None:
        """Manifest contains the host name."""
        manifest = build_manifest("/path/to/host.py")
        assert manifest["name"] == HOST_NAME

    def test_manifest_has_description(self) -> None:
        """Manifest contains a description."""
        manifest = build_manifest("/path/to/host.py")
        assert "description" in manifest
        assert len(manifest["description"]) > 0

    def test_manifest_has_path(self) -> None:
        """Manifest contains the path to host.py."""
        manifest = build_manifest("/path/to/host.py")
        assert manifest["path"] == "/path/to/host.py"

    def test_manifest_has_type_stdio(self) -> None:
        """Manifest type is 'stdio'."""
        manifest = build_manifest("/path/to/host.py")
        assert manifest["type"] == "stdio"

    def test_manifest_has_allowed_origins(self) -> None:
        """Manifest contains allowed_origins with extension ID."""
        manifest = build_manifest("/path/to/host.py")
        expected_origin = (
            f"chrome-extension://{EXTENSION_ID}/"
        )
        assert manifest["allowed_origins"] == [expected_origin]

    def test_manifest_is_valid_json(self) -> None:
        """Manifest can be serialized to valid JSON."""
        manifest = build_manifest("/path/to/host.py")
        json_str = json.dumps(manifest)
        parsed = json.loads(json_str)
        assert parsed == manifest


class TestDetectInstalledBrowsers:
    """Tests for detecting installed Chromium browsers."""

    def test_detects_chrome_when_dir_exists(
        self, mocker: MockerFixture,
    ) -> None:
        """Detects Chrome when its NativeMessagingHosts dir parent exists."""
        mock_exists = mocker.patch(
            "adws.native_host.installer.io_ops.path_exists",
        )

        def exists_side_effect(path: str) -> bool:
            return "Google/Chrome" in path

        mock_exists.side_effect = exists_side_effect
        browsers = detect_installed_browsers()
        names = [b["name"] for b in browsers]
        assert "Google Chrome" in names

    def test_detects_brave_when_dir_exists(
        self, mocker: MockerFixture,
    ) -> None:
        """Detects Brave when its support dir exists."""
        mock_exists = mocker.patch(
            "adws.native_host.installer.io_ops.path_exists",
        )

        def exists_side_effect(path: str) -> bool:
            return "BraveSoftware/Brave-Browser" in path

        mock_exists.side_effect = exists_side_effect
        browsers = detect_installed_browsers()
        names = [b["name"] for b in browsers]
        assert "Brave Browser" in names

    def test_detects_multiple_browsers(
        self, mocker: MockerFixture,
    ) -> None:
        """Detects multiple browsers when multiple dirs exist."""
        mock_exists = mocker.patch(
            "adws.native_host.installer.io_ops.path_exists",
        )
        mock_exists.return_value = True
        browsers = detect_installed_browsers()
        assert len(browsers) >= 2

    def test_returns_empty_when_none_installed(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns empty list when no browser dirs exist."""
        mock_exists = mocker.patch(
            "adws.native_host.installer.io_ops.path_exists",
        )
        mock_exists.return_value = False
        browsers = detect_installed_browsers()
        assert browsers == []


class TestMakeExecutable:
    """Tests for making host.py executable."""

    def test_calls_chmod(self, mocker: MockerFixture) -> None:
        """Calls io_ops.chmod_executable on the given path."""
        mock_chmod = mocker.patch(
            "adws.native_host.installer.io_ops.chmod_executable",
        )
        make_executable("/path/to/host.py")
        mock_chmod.assert_called_once_with("/path/to/host.py")


class TestInstallManifestForBrowser:
    """Tests for writing manifest JSON for a browser."""

    def test_creates_manifest_dir(
        self, mocker: MockerFixture,
    ) -> None:
        """Creates the NativeMessagingHosts directory."""
        mock_makedirs = mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.write_file",
        )
        browser = {
            "name": "Google Chrome",
            "manifest_dir": "/path/to/NativeMessagingHosts",
        }
        install_manifest_for_browser(
            browser, "/path/to/host.py",
        )
        mock_makedirs.assert_called_once_with(
            "/path/to/NativeMessagingHosts",
        )

    def test_writes_manifest_json(
        self, mocker: MockerFixture,
    ) -> None:
        """Writes the manifest JSON file."""
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mock_write = mocker.patch(
            "adws.native_host.installer.io_ops.write_file",
        )
        browser = {
            "name": "Google Chrome",
            "manifest_dir": "/path/to/NativeMessagingHosts",
        }
        install_manifest_for_browser(
            browser, "/path/to/host.py",
        )
        expected_path = (
            "/path/to/NativeMessagingHosts/"
            f"{HOST_NAME}.json"
        )
        mock_write.assert_called_once()
        actual_path = mock_write.call_args[0][0]
        actual_content = mock_write.call_args[0][1]
        assert actual_path == expected_path
        manifest = json.loads(actual_content)
        assert manifest["name"] == HOST_NAME
        assert manifest["path"] == "/path/to/host.py"
        assert manifest["type"] == "stdio"

    def test_returns_success_result(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns success result dict on success."""
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.write_file",
        )
        browser = {
            "name": "Google Chrome",
            "manifest_dir": "/path/to/NativeMessagingHosts",
        }
        result = install_manifest_for_browser(
            browser, "/path/to/host.py",
        )
        assert result["browser"] == "Google Chrome"
        assert result["success"] is True

    def test_returns_failure_on_error(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns failure result dict when write fails."""
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.write_file",
            side_effect=OSError("Permission denied"),
        )
        browser = {
            "name": "Google Chrome",
            "manifest_dir": "/path/to/NativeMessagingHosts",
        }
        result = install_manifest_for_browser(
            browser, "/path/to/host.py",
        )
        assert result["browser"] == "Google Chrome"
        assert result["success"] is False
        assert "Permission denied" in result["error"]


class TestFormatSummary:
    """Tests for formatting the install summary."""

    def test_shows_success_for_browser(self) -> None:
        """Formats success message for installed browser."""
        results = [
            {"browser": "Google Chrome", "success": True},
        ]
        summary = format_summary(results)
        assert "Google Chrome" in summary
        assert "OK" in summary or "success" in summary.lower()

    def test_shows_failure_for_browser(self) -> None:
        """Formats failure message for failed browser."""
        results = [
            {
                "browser": "Brave Browser",
                "success": False,
                "error": "Permission denied",
            },
        ]
        summary = format_summary(results)
        assert "Brave Browser" in summary
        assert "FAIL" in summary or "fail" in summary.lower()

    def test_shows_multiple_results(self) -> None:
        """Formats summary with multiple browser results."""
        results = [
            {"browser": "Google Chrome", "success": True},
            {
                "browser": "Brave Browser",
                "success": False,
                "error": "error",
            },
        ]
        summary = format_summary(results)
        assert "Google Chrome" in summary
        assert "Brave Browser" in summary

    def test_shows_no_browsers_message(self) -> None:
        """Shows message when no browsers were detected."""
        summary = format_summary([])
        assert "no" in summary.lower() or "none" in summary.lower()


class TestInstallHost:
    """Tests for the main install_host orchestrator."""

    def test_non_macos_prints_message(
        self, mocker: MockerFixture,
    ) -> None:
        """On non-macOS, returns message about macOS only."""
        mocker.patch(
            "adws.native_host.installer.is_macos",
            return_value=False,
        )
        mock_print = mocker.patch(
            "adws.native_host.installer.io_ops.print_output",
        )
        result = install_host()
        assert result["macos_only_message"] is True
        mock_print.assert_called()
        output = mock_print.call_args[0][0]
        assert "macos" in output.lower() or "macOS" in output

    def test_macos_downloads_host_py(
        self, mocker: MockerFixture,
    ) -> None:
        """On macOS, downloads host.py to install dir."""
        mocker.patch(
            "adws.native_host.installer.is_macos",
            return_value=True,
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mock_download = mocker.patch(
            "adws.native_host.installer.io_ops.download_file",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.chmod_executable",
        )
        mocker.patch(
            "adws.native_host.installer.detect_installed_browsers",
            return_value=[],
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.print_output",
        )
        install_host()
        mock_download.assert_called_once()
        dl_url = mock_download.call_args[0][0]
        dl_dest = mock_download.call_args[0][1]
        assert "host.py" in dl_url
        assert dl_dest.endswith("host.py")

    def test_macos_makes_executable(
        self, mocker: MockerFixture,
    ) -> None:
        """On macOS, makes host.py executable."""
        mocker.patch(
            "adws.native_host.installer.is_macos",
            return_value=True,
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.download_file",
        )
        mock_chmod = mocker.patch(
            "adws.native_host.installer.io_ops.chmod_executable",
        )
        mocker.patch(
            "adws.native_host.installer.detect_installed_browsers",
            return_value=[],
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.print_output",
        )
        install_host()
        mock_chmod.assert_called_once()

    def test_macos_installs_manifests(
        self, mocker: MockerFixture,
    ) -> None:
        """On macOS, installs manifest for each detected browser."""
        mocker.patch(
            "adws.native_host.installer.is_macos",
            return_value=True,
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.download_file",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.chmod_executable",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.write_file",
        )
        browsers = [
            {
                "name": "Google Chrome",
                "manifest_dir": "/ch/NativeMessagingHosts",
            },
            {
                "name": "Brave Browser",
                "manifest_dir": "/br/NativeMessagingHosts",
            },
        ]
        mocker.patch(
            "adws.native_host.installer.detect_installed_browsers",
            return_value=browsers,
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.print_output",
        )
        result = install_host()
        assert len(result["results"]) == 2

    def test_macos_prints_summary(
        self, mocker: MockerFixture,
    ) -> None:
        """On macOS, prints installation summary."""
        mocker.patch(
            "adws.native_host.installer.is_macos",
            return_value=True,
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.download_file",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.chmod_executable",
        )
        mocker.patch(
            "adws.native_host.installer.detect_installed_browsers",
            return_value=[],
        )
        mock_print = mocker.patch(
            "adws.native_host.installer.io_ops.print_output",
        )
        install_host()
        mock_print.assert_called()

    def test_creates_install_dir(
        self, mocker: MockerFixture,
    ) -> None:
        """On macOS, creates the install directory."""
        mocker.patch(
            "adws.native_host.installer.is_macos",
            return_value=True,
        )
        mock_makedirs = mocker.patch(
            "adws.native_host.installer.io_ops.makedirs",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.download_file",
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.chmod_executable",
        )
        mocker.patch(
            "adws.native_host.installer.detect_installed_browsers",
            return_value=[],
        )
        mocker.patch(
            "adws.native_host.installer.io_ops.print_output",
        )
        install_host()
        # First makedirs call creates the install dir
        first_call = mock_makedirs.call_args_list[0]
        assert "tab-groups-window-namer" in first_call[0][0]

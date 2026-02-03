"""Tests for browser detection and window name reading."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from adws.native_host.browser import (
    build_osascript_command,
    detect_browser,
    get_window_names,
    parse_osascript_output,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestDetectBrowser:
    """Tests for dynamic browser name detection."""

    def test_detects_brave(self, mocker: MockerFixture) -> None:
        """Returns 'Brave Browser' when Brave is running."""
        mock_run = mocker.patch(
            "adws.native_host.io_ops.run_subprocess",
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Brave Browser\n",
        )
        result = detect_browser()
        assert result == "Brave Browser"

    def test_detects_chrome(self, mocker: MockerFixture) -> None:
        """Returns 'Google Chrome' when Chrome is running."""
        mock_run = mocker.patch(
            "adws.native_host.io_ops.run_subprocess",
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Google Chrome\n",
        )
        result = detect_browser()
        assert result == "Google Chrome"

    def test_falls_back_to_chrome(
        self, mocker: MockerFixture,
    ) -> None:
        """Falls back to 'Google Chrome' when detection fails."""
        mock_run = mocker.patch(
            "adws.native_host.io_ops.run_subprocess",
        )
        mock_run.return_value = MagicMock(
            returncode=1, stdout="",
        )
        result = detect_browser()
        assert result == "Google Chrome"


class TestBuildOsascriptCommand:
    """Tests for osascript command construction."""

    def test_builds_command_for_brave(self) -> None:
        """Command targets Brave Browser application."""
        cmd = build_osascript_command("Brave Browser")
        assert "Brave Browser" in cmd
        assert "osascript" in cmd

    def test_builds_command_for_chrome(self) -> None:
        """Command targets Google Chrome application."""
        cmd = build_osascript_command("Google Chrome")
        assert "Google Chrome" in cmd


class TestParseOsascriptOutput:
    """Tests for parsing osascript JSON output."""

    def test_parses_valid_json_array(self) -> None:
        """Parses JSON array of window objects."""
        raw = (
            '[{"name":"W1",'
            '"bounds":{"x":0,"y":0,"width":800,"height":600},'
            '"activeTabTitle":"Tab1"}]'
        )
        result = parse_osascript_output(raw)
        assert len(result) == 1
        assert result[0]["name"] == "W1"
        assert result[0]["activeTabTitle"] == "Tab1"

    def test_adds_has_custom_name_true(self) -> None:
        """hasCustomName is true when name differs from activeTabTitle."""
        raw = '[{"name":"My Window","bounds":{},"activeTabTitle":"Tab1"}]'
        result = parse_osascript_output(raw)
        assert result[0]["hasCustomName"] is True

    def test_adds_has_custom_name_false(self) -> None:
        """hasCustomName is false when name equals activeTabTitle."""
        raw = '[{"name":"Tab1","bounds":{},"activeTabTitle":"Tab1"}]'
        result = parse_osascript_output(raw)
        assert result[0]["hasCustomName"] is False

    def test_handles_empty_output(self) -> None:
        """Empty string returns empty list."""
        result = parse_osascript_output("")
        assert result == []

    def test_handles_invalid_json(self) -> None:
        """Invalid JSON returns empty list."""
        result = parse_osascript_output("not json")
        assert result == []

    def test_multiple_windows(self) -> None:
        """Parses multiple window entries."""
        raw = (
            '[{"name":"T1","bounds":{},"activeTabTitle":"T1"},'
            '{"name":"Custom","bounds":{},"activeTabTitle":"T2"}]'
        )
        result = parse_osascript_output(raw)
        assert len(result) == 2
        assert result[0]["hasCustomName"] is False
        assert result[1]["hasCustomName"] is True


class TestGetWindowNames:
    """Tests for the full get_window_names flow."""

    def test_returns_window_list(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns list of window dicts with hasCustomName."""
        mocker.patch(
            "adws.native_host.browser.detect_browser",
            return_value="Brave Browser",
        )
        mock_run = mocker.patch(
            "adws.native_host.io_ops.run_subprocess",
        )
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name":"Win","bounds":{},"activeTabTitle":"Tab"}]',
            stderr="",
        )
        result = get_window_names()
        assert len(result) == 1
        assert result[0]["name"] == "Win"
        assert result[0]["hasCustomName"] is True

    def test_returns_empty_on_osascript_failure(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns empty list when osascript fails."""
        mocker.patch(
            "adws.native_host.browser.detect_browser",
            return_value="Google Chrome",
        )
        mock_run = mocker.patch(
            "adws.native_host.io_ops.run_subprocess",
        )
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error",
        )
        result = get_window_names()
        assert result == []

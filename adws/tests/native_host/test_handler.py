"""Tests for the native messaging request handler."""
from __future__ import annotations

from typing import TYPE_CHECKING

from adws.native_host.handler import handle_message

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestHandleMessage:
    """Tests for handle_message -- request dispatch."""

    def test_get_window_names_action(
        self, mocker: MockerFixture,
    ) -> None:
        """get_window_names action returns windows list."""
        mock_get = mocker.patch(
            "adws.native_host.handler.get_window_names",
            return_value=[
                {
                    "name": "Win1",
                    "bounds": {},
                    "activeTabTitle": "Tab1",
                    "hasCustomName": True,
                },
            ],
        )
        request = {"action": "get_window_names"}
        result = handle_message(request)
        assert result["success"] is True
        assert len(result["windows"]) == 1
        assert result["windows"][0]["name"] == "Win1"
        mock_get.assert_called_once()

    def test_unknown_action_returns_error(self) -> None:
        """Unknown action returns error response."""
        request = {"action": "unknown_action"}
        result = handle_message(request)
        assert result["success"] is False
        assert "error" in result

    def test_missing_action_returns_error(self) -> None:
        """Missing action key returns error response."""
        request: dict[str, object] = {}
        result = handle_message(request)
        assert result["success"] is False
        assert "error" in result

    def test_get_window_names_exception_returns_error(
        self, mocker: MockerFixture,
    ) -> None:
        """Exception during get_window_names returns error."""
        mocker.patch(
            "adws.native_host.handler.get_window_names",
            side_effect=RuntimeError("boom"),
        )
        request = {"action": "get_window_names"}
        result = handle_message(request)
        assert result["success"] is False
        assert "boom" in result["error"]

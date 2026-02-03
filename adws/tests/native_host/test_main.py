"""Tests for the native messaging host main entry point."""
from __future__ import annotations

import json
import struct
from typing import TYPE_CHECKING

from adws.native_host.main import main

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestMain:
    """Tests for the main() entry point."""

    def test_processes_valid_message(
        self, mocker: MockerFixture,
    ) -> None:
        """Reads message, handles it, writes response."""
        request = {"action": "get_window_names"}
        body = json.dumps(request).encode("utf-8")
        raw = struct.pack("<I", len(body)) + body

        mocker.patch(
            "adws.native_host.main.read_stdin_message",
            return_value=raw,
        )
        mock_write = mocker.patch(
            "adws.native_host.main.write_stdout_message",
        )
        mocker.patch(
            "adws.native_host.handler.get_window_names",
            return_value=[],
        )
        main()
        mock_write.assert_called_once()
        response = mock_write.call_args[0][0]
        assert response["success"] is True

    def test_empty_stdin_returns_early(
        self, mocker: MockerFixture,
    ) -> None:
        """Empty stdin causes early return with no output."""
        mocker.patch(
            "adws.native_host.main.read_stdin_message",
            return_value=b"",
        )
        mock_write = mocker.patch(
            "adws.native_host.main.write_stdout_message",
        )
        main()
        mock_write.assert_not_called()

    def test_invalid_message_writes_error(
        self, mocker: MockerFixture,
    ) -> None:
        """Undecipherable message writes error response."""
        # 4-byte header saying 100 bytes but only 3 body bytes
        raw = struct.pack("<I", 100) + b"abc"
        mocker.patch(
            "adws.native_host.main.read_stdin_message",
            return_value=raw,
        )
        mock_write = mocker.patch(
            "adws.native_host.main.write_stdout_message",
        )
        main()
        mock_write.assert_called_once()
        response = mock_write.call_args[0][0]
        assert response["success"] is False
        assert "error" in response

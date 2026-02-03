"""Tests for native host I/O operations boundary."""
from __future__ import annotations

import os
import struct
import sys
from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from adws.native_host.io_ops import (
    _get_stdin_buffer,
    _get_stdout_buffer,
    chmod_executable,
    download_file,
    makedirs,
    path_exists,
    print_output,
    read_stdin_message,
    run_subprocess,
    write_file,
    write_stdout_message,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


class TestBufferSeams:
    """Tests for stdin/stdout buffer accessor seams."""

    def test_get_stdin_buffer_returns_binary_buffer(
        self,
    ) -> None:
        """_get_stdin_buffer returns sys.stdin.buffer."""
        result = _get_stdin_buffer()
        assert result is sys.stdin.buffer

    def test_get_stdout_buffer_returns_binary_buffer(
        self,
    ) -> None:
        """_get_stdout_buffer returns sys.stdout.buffer."""
        result = _get_stdout_buffer()
        assert result is sys.stdout.buffer


class TestReadStdinMessage:
    """Tests for reading from stdin with length-prefix framing."""

    def test_reads_complete_message(
        self, mocker: MockerFixture,
    ) -> None:
        """Reads 4-byte header then body from stdin buffer."""
        body = b'{"action":"test"}'
        data = struct.pack("<I", len(body)) + body
        mock_stdin = BytesIO(data)
        mocker.patch(
            "adws.native_host.io_ops._get_stdin_buffer",
            return_value=mock_stdin,
        )
        result = read_stdin_message()
        assert result == data

    def test_returns_empty_on_eof(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns empty bytes on EOF (no data on stdin)."""
        mock_stdin = BytesIO(b"")
        mocker.patch(
            "adws.native_host.io_ops._get_stdin_buffer",
            return_value=mock_stdin,
        )
        result = read_stdin_message()
        assert result == b""

    def test_returns_partial_on_truncated_body(
        self, mocker: MockerFixture,
    ) -> None:
        """Returns whatever is available if body is truncated."""
        # Header says 100 bytes but only 5 available
        data = struct.pack("<I", 100) + b"short"
        mock_stdin = BytesIO(data)
        mocker.patch(
            "adws.native_host.io_ops._get_stdin_buffer",
            return_value=mock_stdin,
        )
        result = read_stdin_message()
        # Should return header + whatever body was read
        assert len(result) == 4 + 5


class TestWriteStdoutMessage:
    """Tests for writing to stdout with length-prefix framing."""

    def test_writes_encoded_message(
        self, mocker: MockerFixture,
    ) -> None:
        """Writes length-prefixed message to stdout buffer."""
        mock_stdout = BytesIO()
        mocker.patch(
            "adws.native_host.io_ops._get_stdout_buffer",
            return_value=mock_stdout,
        )
        msg = {"result": "ok"}
        write_stdout_message(msg)
        written = mock_stdout.getvalue()
        assert len(written) > 4
        length = struct.unpack("<I", written[:4])[0]
        assert length == len(written) - 4


class TestRunSubprocess:
    """Tests for subprocess execution wrapper."""

    def test_runs_command_and_returns_result(
        self, mocker: MockerFixture,
    ) -> None:
        """Executes command via subprocess.run."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="output", stderr="",
        )
        result = run_subprocess(["echo", "test"])
        assert result.returncode == 0
        mock_run.assert_called_once()

    def test_passes_timeout(
        self, mocker: MockerFixture,
    ) -> None:
        """Passes timeout parameter to subprocess.run."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr="",
        )
        run_subprocess(["cmd"], timeout=10)
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 10


class TestPathExists:
    """Tests for path existence checking."""

    def test_returns_true_for_existing_path(
        self, tmp_path: Path,
    ) -> None:
        """Returns True when the path exists."""
        test_dir = tmp_path / "existing"
        test_dir.mkdir()
        assert path_exists(str(test_dir)) is True

    def test_returns_false_for_missing_path(self) -> None:
        """Returns False when the path does not exist."""
        assert path_exists("/nonexistent/path/xyz") is False


class TestMakedirs:
    """Tests for directory creation."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Creates directory and parents."""
        target = str(tmp_path / "a" / "b" / "c")
        makedirs(target)
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_no_error_if_exists(self, tmp_path: Path) -> None:
        """Does not error if directory already exists."""
        target = tmp_path / "existing"
        target.mkdir(parents=True)
        makedirs(str(target))  # Should not raise
        assert target.is_dir()


class TestWriteFile:
    """Tests for file writing."""

    def test_writes_content(self, tmp_path: Path) -> None:
        """Writes string content to file."""
        target = tmp_path / "test.json"
        write_file(str(target), '{"key": "value"}')
        assert target.read_text() == '{"key": "value"}'


class TestChmodExecutable:
    """Tests for making files executable."""

    def test_makes_file_executable(
        self, tmp_path: Path,
    ) -> None:
        """Sets executable permission on file."""
        target = tmp_path / "script.py"
        target.write_text("#!/usr/bin/env python3\n")
        chmod_executable(str(target))
        assert os.access(str(target), os.X_OK)


class TestDownloadFile:
    """Tests for downloading files."""

    def test_downloads_to_destination(
        self, mocker: MockerFixture, tmp_path: Path,
    ) -> None:
        """Downloads URL content to destination file."""
        mock_urlretrieve = mocker.patch(
            "adws.native_host.io_ops.urlretrieve",
        )
        dest = str(tmp_path / "host.py")
        download_file("https://example.com/host.py", dest)
        mock_urlretrieve.assert_called_once_with(
            "https://example.com/host.py", dest,
        )


class TestPrintOutput:
    """Tests for print output function."""

    def test_prints_message(
        self, mocker: MockerFixture,
    ) -> None:
        """Prints message to stdout."""
        mock_print = mocker.patch("builtins.print")
        print_output("Hello, world!")
        mock_print.assert_called_once_with("Hello, world!")

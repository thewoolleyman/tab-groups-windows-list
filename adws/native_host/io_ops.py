"""I/O boundary for native messaging host.

All external I/O (stdin, stdout, subprocess) goes through
here. Tests mock these functions at this boundary.
"""
from __future__ import annotations

import json
import os
import stat
import struct
import subprocess
import sys
from typing import IO, Any
from urllib.request import urlretrieve

_HEADER_SIZE = 4


def _get_stdin_buffer() -> IO[bytes]:
    """Return stdin binary buffer. Mockable seam."""
    return sys.stdin.buffer


def _get_stdout_buffer() -> IO[bytes]:
    """Return stdout binary buffer. Mockable seam."""
    return sys.stdout.buffer


def read_stdin_message() -> bytes:
    """Read a length-prefixed message from stdin.

    Reads 4-byte little-endian header, then reads that many
    bytes of body. Returns the complete raw bytes (header +
    body). Returns empty bytes on EOF.
    """
    stdin_buf = _get_stdin_buffer()
    header: bytes = stdin_buf.read(_HEADER_SIZE)
    if len(header) < _HEADER_SIZE:
        return b""
    length = struct.unpack("<I", header)[0]
    body: bytes = stdin_buf.read(length)
    return header + body


def write_stdout_message(msg: dict[str, Any]) -> None:
    """Write a length-prefixed JSON message to stdout.

    Encodes the dict as JSON, prepends 4-byte LE length,
    and writes to stdout binary buffer.
    """
    body = json.dumps(msg).encode("utf-8")
    header = struct.pack("<I", len(body))
    stdout_buf = _get_stdout_buffer()
    stdout_buf.write(header + body)
    stdout_buf.flush()


def run_subprocess(
    cmd: list[str],
    *,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command. Mockable I/O boundary.

    Executes the given command list with captured output.
    Commands are passed as explicit argument lists (not
    shell strings) for safety.
    """
    return subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def path_exists(path: str) -> bool:
    """Check if a filesystem path exists. Mockable seam."""
    return os.path.exists(path)  # noqa: PTH110


def makedirs(path: str) -> None:
    """Create directory and parents. Mockable seam."""
    os.makedirs(path, exist_ok=True)  # noqa: PTH103


def write_file(path: str, content: str) -> None:
    """Write string content to a file. Mockable seam."""
    with open(path, "w") as f:  # noqa: PTH123
        f.write(content)


def chmod_executable(path: str) -> None:
    """Make a file executable. Mockable seam."""
    st = os.stat(path)  # noqa: PTH116
    os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)  # noqa: PTH101


def download_file(url: str, dest: str) -> None:
    """Download a file from a URL. Mockable seam."""
    urlretrieve(url, dest)  # noqa: S310


def print_output(message: str) -> None:
    """Print a message to stdout. Mockable seam."""
    print(message)  # noqa: T201

"""Main entry point for native messaging host.

Reads a single native message from stdin, dispatches it to
the handler, and writes the response to stdout. Designed to
be called by Chrome's native messaging system.
"""
from __future__ import annotations

from adws.native_host.handler import handle_message
from adws.native_host.io_ops import (
    read_stdin_message,
    write_stdout_message,
)
from adws.native_host.protocol import decode_message


def main() -> None:
    """Run the native messaging host.

    Reads one message from stdin, processes it, writes
    response to stdout. Chrome opens a new process for
    each message exchange.
    """
    raw = read_stdin_message()
    if not raw:
        return
    request = decode_message(raw)
    if request is None:
        write_stdout_message({
            "success": False,
            "error": "Failed to decode message",
        })
        return
    response = handle_message(request)
    write_stdout_message(response)

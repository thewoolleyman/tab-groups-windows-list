"""Chrome native messaging protocol framing.

Implements the 4-byte little-endian length-prefix protocol
used by Chrome native messaging hosts for stdin/stdout
communication.
"""
from __future__ import annotations

import json
import struct
from typing import Any

_HEADER_SIZE = 4


def encode_message(msg: dict[str, Any]) -> bytes:
    """Encode a dict as a length-prefixed native message.

    Returns 4-byte LE length prefix + UTF-8 JSON body.
    """
    body = json.dumps(msg).encode("utf-8")
    header = struct.pack("<I", len(body))
    return header + body


def decode_message(
    raw: bytes,
) -> dict[str, Any] | None:
    """Decode a length-prefixed native message.

    Returns the parsed dict, or None if input is empty or
    truncated. Raises ValueError if body is not valid JSON.
    """
    if len(raw) < _HEADER_SIZE:
        return None
    length = struct.unpack("<I", raw[:_HEADER_SIZE])[0]
    body = raw[_HEADER_SIZE:]
    if len(body) < length:
        return None
    try:
        result: dict[str, Any] = json.loads(body[:length])
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in native message: {exc}"
        raise ValueError(msg) from exc
    return result

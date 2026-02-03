"""Tests for Chrome native messaging protocol framing."""
from __future__ import annotations

import json
import struct

import pytest

from adws.native_host.protocol import (
    decode_message,
    encode_message,
)


class TestEncodeMessage:
    """Tests for encode_message -- 4-byte length-prefix framing."""

    def test_encode_simple_dict(self) -> None:
        """Encoded message has 4-byte LE length prefix + JSON body."""
        msg = {"action": "test"}
        result = encode_message(msg)
        body = json.dumps(msg).encode("utf-8")
        expected = struct.pack("<I", len(body)) + body
        assert result == expected

    def test_encode_empty_dict(self) -> None:
        """Empty dict encodes correctly with length prefix."""
        msg: dict[str, object] = {}
        result = encode_message(msg)
        body = json.dumps(msg).encode("utf-8")
        prefix = struct.pack("<I", len(body))
        assert result[:4] == prefix
        assert result[4:] == body

    def test_encode_complex_payload(self) -> None:
        """Complex nested payload encodes correctly."""
        msg = {"windows": [{"name": "w1", "bounds": {"x": 0}}]}
        result = encode_message(msg)
        body = json.dumps(msg).encode("utf-8")
        length = struct.unpack("<I", result[:4])[0]
        assert length == len(body)
        decoded = json.loads(result[4:])
        assert decoded == msg


class TestDecodeMessage:
    """Tests for decode_message -- read length-prefix then JSON body."""

    def test_decode_simple_message(self) -> None:
        """Decodes a properly framed message."""
        msg = {"action": "get_window_names"}
        body = json.dumps(msg).encode("utf-8")
        raw = struct.pack("<I", len(body)) + body
        result = decode_message(raw)
        assert result == msg

    def test_decode_empty_input_returns_none(self) -> None:
        """Empty input returns None (EOF)."""
        result = decode_message(b"")
        assert result is None

    def test_decode_truncated_header_returns_none(self) -> None:
        """Input shorter than 4 bytes returns None."""
        result = decode_message(b"\x01\x02")
        assert result is None

    def test_decode_truncated_body_returns_none(self) -> None:
        """Input with valid header but truncated body returns None."""
        # Header says 100 bytes but only 5 bytes of body
        raw = struct.pack("<I", 100) + b"short"
        result = decode_message(raw)
        assert result is None

    def test_decode_invalid_json_raises(self) -> None:
        """Non-JSON body raises ValueError."""
        body = b"not json"
        raw = struct.pack("<I", len(body)) + body
        with pytest.raises(ValueError, match="Invalid JSON"):
            decode_message(raw)

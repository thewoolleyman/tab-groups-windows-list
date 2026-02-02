"""Enemy Unit Tests for SDK proxy (io_ops.execute_sdk_call).

These tests make REAL API calls through the REAL SDK.
Nothing is mocked. Requires ANTHROPIC_API_KEY environment variable.
"""
from __future__ import annotations

import os

import pytest
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.io_ops import execute_sdk_call
from adws.adw_modules.types import AdwsRequest, AdwsResponse

_HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))
_SKIP_REASON = "ANTHROPIC_API_KEY not set"


@pytest.mark.enemy
@pytest.mark.skipif(not _HAS_API_KEY, reason=_SKIP_REASON)
def test_eut_execute_sdk_call_round_trip() -> None:
    """EUT: Full round-trip through real SDK and real API."""
    request = AdwsRequest(
        model="claude-haiku-3-5-20241022",
        system_prompt="Respond with exactly: PONG",
        prompt="PING",
        max_turns=1,
        permission_mode="bypassPermissions",
    )

    result = execute_sdk_call(request)

    assert isinstance(result, IOSuccess)
    response = unsafe_perform_io(result.unwrap())
    assert isinstance(response, AdwsResponse)
    assert response.result == "PONG"
    assert response.is_error is False
    assert response.session_id is not None
    assert response.duration_ms is not None
    assert response.duration_ms > 0
    assert response.cost_usd is not None
    assert response.cost_usd > 0.0
    assert response.num_turns is not None
    assert response.num_turns >= 1


@pytest.mark.enemy
@pytest.mark.skipif(not _HAS_API_KEY, reason=_SKIP_REASON)
def test_eut_execute_sdk_call_invalid_model() -> None:
    """EUT: Invalid model name produces error response."""
    request = AdwsRequest(
        model="nonexistent-model-xyz-999",
        system_prompt="test",
        prompt="test",
        max_turns=1,
        permission_mode="bypassPermissions",
    )

    result = execute_sdk_call(request)

    # SDK should return an error (either IOFailure or IOSuccess with is_error=True)
    if isinstance(result, IOFailure):
        error = unsafe_perform_io(result.failure())
        assert error.step_name == "io_ops.execute_sdk_call"
    else:
        response = unsafe_perform_io(result.unwrap())
        assert isinstance(response, AdwsResponse)
        assert response.is_error is True

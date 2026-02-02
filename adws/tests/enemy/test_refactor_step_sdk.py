"""Enemy Unit Tests for refactor_step SDK call.

These tests make REAL API calls through the REAL SDK.
Nothing is mocked. Requires ANTHROPIC_API_KEY environment
variable.

Uses a constrained prompt to avoid filesystem side effects.
The EUT validates the SDK round-trip with a REFACTOR phase
request format, NOT that the agent writes good code.
"""
from __future__ import annotations

import os

import pytest
from returns.io import IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.io_ops import execute_sdk_call
from adws.adw_modules.steps.refactor_step import (
    REFACTOR_PHASE_SYSTEM_PROMPT,
)
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsRequest,
    AdwsResponse,
)

_HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))
_SKIP_REASON = "ANTHROPIC_API_KEY not set"


@pytest.mark.enemy
@pytest.mark.skipif(
    not _HAS_API_KEY, reason=_SKIP_REASON,
)
def test_eut_refactor_step_sdk_round_trip() -> None:
    """EUT: REFACTOR phase SDK round-trip with real API.

    Uses a constrained prompt to test the SDK call format
    without causing filesystem side effects.
    """
    request = AdwsRequest(
        model=DEFAULT_CLAUDE_MODEL,
        system_prompt=REFACTOR_PHASE_SYSTEM_PROMPT,
        prompt=(
            "Respond with exactly this text and nothing"
            " else:\n"
            "I would modify the following files:\n"
            "adws/adw_modules/steps/example.py"
        ),
        max_turns=1,
        permission_mode="bypassPermissions",
    )

    result = execute_sdk_call(request)

    assert isinstance(result, IOSuccess)
    response = unsafe_perform_io(result.unwrap())
    assert isinstance(response, AdwsResponse)
    assert response.is_error is False
    assert response.result is not None
    assert len(response.result) > 0

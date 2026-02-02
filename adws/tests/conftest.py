"""Shared test fixtures for ADWS test suite."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def sample_workflow_context() -> WorkflowContext:
    """Return a WorkflowContext with sample test data."""
    return WorkflowContext(
        inputs={"issue_id": "beads-123", "workflow_name": "implement_close"},
        outputs={},
        feedback=[],
    )


@pytest.fixture
def mock_io_ops(mocker: MagicMock) -> MagicMock:
    """Return a mocked io_ops module for boundary testing."""
    return mocker.patch("adws.adw_modules.io_ops")  # type: ignore[no-any-return]

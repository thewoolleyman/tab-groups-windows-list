"""Tests for the adversarial review fixes for Story 2.1."""
import json

import pytest

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext


class NonSerializable:
    """A class that cannot be serialized to JSON."""
    def __repr__(self) -> str:
        return "<NonSerializable>"


def test_pipeline_error_to_dict_handles_non_serializable_objects() -> None:
    """Test that to_dict safely converts non-JSON-serializable objects to strings."""
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
        context={"obj": NonSerializable(), "set": {1, 2, 3}},
    )

    # This checks that we can serialize the result of to_dict()
    data = error.to_dict()
    json_str = json.dumps(data)

    # Verify the non-serializable items were converted safely
    loaded = json.loads(json_str)
    assert loaded["context"]["obj"] == "<NonSerializable>"
    # Sets are unordered, so just check it's a string representation
    assert str(1) in loaded["context"]["set"]


def test_pipeline_error_str_truncates_large_context() -> None:
    """Test that __str__ truncates context if it's too large."""
    # Create a massive context
    huge_context: dict[str, object] = {f"key_{i}": "x" * 100 for i in range(50)}
    error = PipelineError(
        step_name="step",
        error_type="Error",
        message="msg",
        context=huge_context,
    )

    error_str = str(error)
    # Arbitrary limit, but should be significantly smaller than the full dump
    # 50 keys * 100 chars = 5000+ chars. We want it shorter.
    assert len(error_str) < 1000
    assert "..." in error_str or "truncated" in error_str


def test_workflow_context_promote_outputs_raises_on_collision() -> None:
    """Test that promote_outputs_to_inputs raises ValueError on key collision."""
    ctx = WorkflowContext(
        inputs={"existing_key": "old_value"},
        outputs={"existing_key": "new_value"},
    )

    # Should raise error to prevent silent overwrite
    with pytest.raises(ValueError, match="Collision detected"):
        ctx.promote_outputs_to_inputs()

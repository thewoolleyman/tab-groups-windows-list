"""Tests for WorkflowContext and shared types."""
import dataclasses

import pytest
from pydantic import BaseModel

from adws.adw_modules.types import AdwsRequest, AdwsResponse, WorkflowContext


def test_workflow_context_construction() -> None:
    """Test WorkflowContext stores all fields correctly."""
    ctx = WorkflowContext(
        inputs={"key": "value"},
        outputs={"result": 42},
        feedback=["some feedback"],
    )
    assert ctx.inputs == {"key": "value"}
    assert ctx.outputs == {"result": 42}
    assert ctx.feedback == ["some feedback"]


def test_workflow_context_defaults() -> None:
    """Test WorkflowContext defaults to empty collections."""
    ctx = WorkflowContext()
    assert ctx.inputs == {}
    assert ctx.outputs == {}
    assert ctx.feedback == []


def test_workflow_context_is_frozen() -> None:
    """Test WorkflowContext is an immutable frozen dataclass."""
    ctx = WorkflowContext()
    assert dataclasses.is_dataclass(ctx)
    assert type(ctx).__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_workflow_context_with_updates() -> None:
    """Test with_updates returns new context with changed fields."""
    ctx = WorkflowContext(inputs={"a": 1})
    updated = ctx.with_updates(outputs={"b": 2})
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {"b": 2}
    assert updated is not ctx


def test_workflow_context_with_updates_preserves_unchanged() -> None:
    """Test with_updates preserves fields not being updated."""
    ctx = WorkflowContext(
        inputs={"a": 1},
        outputs={"b": 2},
        feedback=["f1"],
    )
    updated = ctx.with_updates(feedback=["f1", "f2"])
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {"b": 2}
    assert updated.feedback == ["f1", "f2"]


def test_workflow_context_with_updates_inputs() -> None:
    """Test with_updates can replace inputs field."""
    ctx = WorkflowContext(inputs={"old": 1})
    updated = ctx.with_updates(inputs={"new": 2})
    assert updated.inputs == {"new": 2}
    assert updated.outputs == {}
    assert updated.feedback == []


def test_workflow_context_add_feedback_appends_entry() -> None:
    """RED: Will fail with AttributeError because add_feedback does not exist yet."""
    ctx = WorkflowContext(feedback=["first"])
    updated = ctx.add_feedback("second")
    assert updated.feedback == ["first", "second"]
    assert updated is not ctx


def test_workflow_context_add_feedback_preserves_other_fields() -> None:
    """RED: Will fail with AttributeError because add_feedback does not exist yet."""
    ctx = WorkflowContext(
        inputs={"a": 1},
        outputs={"b": 2},
        feedback=["f1"],
    )
    updated = ctx.add_feedback("f2")
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {"b": 2}
    assert updated.feedback == ["f1", "f2"]


def test_workflow_context_add_feedback_on_empty() -> None:
    """RED: Will fail with AttributeError because add_feedback does not exist yet."""
    ctx = WorkflowContext()
    updated = ctx.add_feedback("first")
    assert updated.feedback == ["first"]


def test_workflow_context_promote_outputs_to_inputs() -> None:
    """RED: promote_outputs_to_inputs does not exist yet."""
    ctx = WorkflowContext(
        inputs={"existing": 1},
        outputs={"result": 42, "data": "hello"},
    )
    updated = ctx.promote_outputs_to_inputs()
    assert updated.inputs == {"existing": 1, "result": 42, "data": "hello"}
    assert updated.outputs == {}
    assert updated is not ctx


def test_workflow_context_promote_outputs_raises_on_conflicting_inputs() -> None:
    """Test promote_outputs_to_inputs raises ValueError on key collision."""
    ctx = WorkflowContext(
        inputs={"key": "old"},
        outputs={"key": "new"},
    )
    with pytest.raises(ValueError, match="Collision detected"):
        ctx.promote_outputs_to_inputs()


def test_workflow_context_promote_outputs_empty() -> None:
    """RED: promote_outputs_to_inputs does not exist yet."""
    ctx = WorkflowContext(inputs={"a": 1})
    updated = ctx.promote_outputs_to_inputs()
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {}


def test_workflow_context_merge_outputs_adds_new() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(outputs={"a": 1})
    updated = ctx.merge_outputs({"b": 2})
    assert updated.outputs == {"a": 1, "b": 2}
    assert updated is not ctx


def test_workflow_context_merge_outputs_overwrites_existing() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(outputs={"key": "old"})
    updated = ctx.merge_outputs({"key": "new"})
    assert updated.outputs == {"key": "new"}


def test_workflow_context_merge_outputs_preserves_other_fields() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(
        inputs={"i": 1},
        outputs={"o": 2},
        feedback=["f"],
    )
    updated = ctx.merge_outputs({"o2": 3})
    assert updated.inputs == {"i": 1}
    assert updated.outputs == {"o": 2, "o2": 3}
    assert updated.feedback == ["f"]


def test_workflow_context_merge_outputs_empty() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(outputs={"a": 1})
    updated = ctx.merge_outputs({})
    assert updated.outputs == {"a": 1}


# --- AdwsRequest Tests ---


def test_adws_request_construction_all_fields() -> None:
    """RED: AdwsRequest does not exist yet."""
    req = AdwsRequest(
        model="claude-sonnet-4-20250514",
        system_prompt="You are helpful.",
        prompt="Hello",
        allowed_tools=["bash"],
        disallowed_tools=["web"],
        max_turns=5,
        permission_mode="acceptEdits",
    )
    assert req.model == "claude-sonnet-4-20250514"
    assert req.system_prompt == "You are helpful."
    assert req.prompt == "Hello"
    assert req.allowed_tools == ["bash"]
    assert req.disallowed_tools == ["web"]
    assert req.max_turns == 5
    assert req.permission_mode == "acceptEdits"


def test_adws_request_defaults() -> None:
    """RED: AdwsRequest does not exist yet."""
    req = AdwsRequest(system_prompt="sys", prompt="hello")
    assert req.model == "claude-sonnet-4-20250514"
    assert req.allowed_tools is None
    assert req.disallowed_tools is None
    assert req.max_turns is None
    assert req.permission_mode is None


def test_adws_request_is_frozen() -> None:
    """RED: AdwsRequest does not exist yet."""
    req = AdwsRequest(system_prompt="sys", prompt="hello")
    with pytest.raises(Exception):  # noqa: B017, PT011
        req.model = "other"


def test_adws_request_validation_missing_required() -> None:
    """RED: AdwsRequest does not exist yet."""
    with pytest.raises(Exception):  # noqa: B017, PT011
        AdwsRequest()  # type: ignore[call-arg]


def test_adws_request_is_pydantic_model() -> None:
    """RED: AdwsRequest does not exist yet."""
    assert issubclass(AdwsRequest, BaseModel)


# --- AdwsResponse Tests ---


def test_adws_response_construction_all_fields() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse(
        result="Hello!",
        cost_usd=0.003,
        duration_ms=1500,
        session_id="sess-123",
        is_error=False,
        error_message=None,
        num_turns=2,
    )
    assert resp.result == "Hello!"
    assert resp.cost_usd == 0.003
    assert resp.duration_ms == 1500
    assert resp.session_id == "sess-123"
    assert resp.is_error is False
    assert resp.error_message is None
    assert resp.num_turns == 2


def test_adws_response_defaults() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse()
    assert resp.result is None
    assert resp.cost_usd is None
    assert resp.duration_ms is None
    assert resp.session_id is None
    assert resp.is_error is False
    assert resp.error_message is None
    assert resp.num_turns is None


def test_adws_response_error_state() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse(
        is_error=True,
        error_message="Model not found",
    )
    assert resp.is_error is True
    assert resp.error_message == "Model not found"
    assert resp.result is None


def test_adws_response_is_frozen() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse()
    with pytest.raises(Exception):  # noqa: B017, PT011
        resp.is_error = True


def test_adws_response_is_pydantic_model() -> None:
    """RED: AdwsResponse does not exist yet."""
    assert issubclass(AdwsResponse, BaseModel)

"""Tests for WorkflowContext and shared types."""
import dataclasses

from adws.adw_modules.types import WorkflowContext


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

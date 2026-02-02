"""Tests for engine public API types (Workflow, Step)."""
import dataclasses

from adws.adw_modules.engine.types import Step, Workflow


def test_step_construction() -> None:
    """Test Step dataclass construction with all fields."""
    step = Step(name="test_step", function="my_func")
    assert step.name == "test_step"
    assert step.function == "my_func"
    assert step.always_run is False
    assert step.max_attempts == 1


def test_step_with_options() -> None:
    """Test Step with non-default options."""
    step = Step(
        name="retry_step",
        function="retry_func",
        always_run=True,
        max_attempts=3,
    )
    assert step.always_run is True
    assert step.max_attempts == 3


def test_step_is_frozen() -> None:
    """Test Step is immutable."""
    step = Step(name="s", function="f")
    assert dataclasses.is_dataclass(step)
    assert type(step).__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_workflow_construction() -> None:
    """Test Workflow dataclass construction."""
    steps = [Step(name="s1", function="f1"), Step(name="s2", function="f2")]
    wf = Workflow(
        name="test_workflow",
        description="A test workflow",
        steps=steps,
    )
    assert wf.name == "test_workflow"
    assert wf.description == "A test workflow"
    assert len(wf.steps) == 2
    assert wf.dispatchable is True


def test_workflow_not_dispatchable() -> None:
    """Test Workflow with dispatchable=False."""
    wf = Workflow(
        name="manual_only",
        description="Manual workflow",
        dispatchable=False,
    )
    assert wf.dispatchable is False
    assert wf.steps == []


def test_workflow_is_frozen() -> None:
    """Test Workflow is immutable."""
    wf = Workflow(name="w", description="d")
    assert dataclasses.is_dataclass(wf)
    assert type(wf).__dataclass_params__.frozen  # type: ignore[attr-defined]

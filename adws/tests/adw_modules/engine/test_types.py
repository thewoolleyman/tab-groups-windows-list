"""Tests for engine public API types (Workflow, Step, StepFunction)."""
import dataclasses
from collections.abc import Callable
from typing import get_args, get_origin

from adws.adw_modules.engine.types import Step, StepFunction, Workflow


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


# --- StepFunction Type Alias Tests ---


def test_step_function_type_is_callable() -> None:
    """Verify StepFunction is Callable[[WorkflowContext], IOResult[...]]."""
    origin = get_origin(StepFunction)
    assert origin is Callable
    args = get_args(StepFunction)
    assert len(args) == 2
    # First arg is param list containing WorkflowContext (string via TYPE_CHECKING)
    assert "WorkflowContext" in str(args[0])
    # Second arg is return type IOResult[WorkflowContext, PipelineError]
    assert "IOResult" in str(args[1])


# --- Step shell field tests ---


def test_step_shell_defaults() -> None:
    """RED: Step does not have shell/command fields yet."""
    step = Step(name="s", function="f")
    assert step.shell is False
    assert step.command == ""


def test_step_shell_command() -> None:
    """RED: Step does not have shell/command fields yet."""
    step = Step(  # noqa: S604
        name="run_tests",
        function="execute_shell_step",
        shell=True,
        command="npm test",
    )
    assert step.shell is True
    assert step.command == "npm test"
    assert step.name == "run_tests"


def test_step_backward_compatible() -> None:
    """Existing Step construction still works without new fields."""
    step = Step(
        name="old_step",
        function="old_func",
        always_run=True,
        max_attempts=2,
    )
    assert step.name == "old_step"
    assert step.function == "old_func"
    assert step.always_run is True
    assert step.max_attempts == 2
    assert step.shell is False
    assert step.command == ""


# --- Step retry_delay_seconds field tests (Story 2.5) ---


def test_step_retry_delay_default() -> None:
    """Step retry_delay_seconds defaults to 0.0."""
    step = Step(name="s", function="f")
    assert step.retry_delay_seconds == 0.0


def test_step_retry_delay_configured() -> None:
    """Step retry_delay_seconds can be set to custom value."""
    step = Step(
        name="retry_step",
        function="retry_func",
        max_attempts=3,
        retry_delay_seconds=1.5,
    )
    assert step.retry_delay_seconds == 1.5

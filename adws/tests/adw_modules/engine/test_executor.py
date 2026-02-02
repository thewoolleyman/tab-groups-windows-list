"""Tests for engine executor (run_step, run_workflow, registry)."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import (
    _resolve_step_function,
    run_step,
    run_workflow,
)
from adws.adw_modules.engine.types import Step, Workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import check_sdk_available, execute_shell_step
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Type alias for step function used by test helpers
_StepFn = Callable[
    [WorkflowContext],
    IOResult[WorkflowContext, PipelineError],
]


# --- Test helpers ---


def _make_success_step(
    output_key: str,
    output_value: object,
) -> _StepFn:
    """Create a step function that succeeds."""

    def step(
        ctx: WorkflowContext,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs({output_key: output_value}),
        )

    return step


def _make_failure_step(error_msg: str) -> _StepFn:
    """Create a step function that fails."""

    def step(
        ctx: WorkflowContext,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="test_step",
                error_type="TestError",
                message=error_msg,
                context={},
            ),
        )

    return step


# --- Task 4: Step function registry tests ---


class TestResolveStepFunction:
    """Tests for _resolve_step_function."""

    def test_resolve_known_function(self) -> None:
        """Known function name returns IOSuccess with callable."""
        result = _resolve_step_function("check_sdk_available")
        assert isinstance(result, IOSuccess)
        resolved_fn = unsafe_perform_io(result.unwrap())
        assert resolved_fn is check_sdk_available

    def test_resolve_unknown_function(self) -> None:
        """Unknown function returns IOFailure with PipelineError."""
        result = _resolve_step_function("nonexistent_function")
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert isinstance(error, PipelineError)
        assert error.error_type == "UnknownStepFunction"
        assert "nonexistent_function" in error.message
        assert "available" in error.message.lower()

    def test_resolve_execute_shell_step(self) -> None:
        """execute_shell_step is in the registry."""
        result = _resolve_step_function("execute_shell_step")
        assert isinstance(result, IOSuccess)
        resolved_fn = unsafe_perform_io(result.unwrap())
        assert resolved_fn is execute_shell_step


# --- Task 1: run_step tests ---


class TestRunStep:
    """Tests for run_step function."""

    def test_run_step_sdk_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK step success: resolves function, calls it."""
        ctx = WorkflowContext(inputs={"key": "val"})
        step = Step(
            name="test_step",
            function="check_sdk_available",
        )

        success_fn = _make_success_step("result", "ok")
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"check_sdk_available": success_fn},
        )

        result = run_step(step, ctx)
        assert isinstance(result, IOSuccess)
        updated_ctx = unsafe_perform_io(result.unwrap())
        assert updated_ctx.outputs["result"] == "ok"

    def test_run_step_sdk_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK step failure: propagates PipelineError."""
        ctx = WorkflowContext()
        step = Step(
            name="fail_step",
            function="check_sdk_available",
        )

        fail_fn = _make_failure_step("step failed")
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"check_sdk_available": fail_fn},
        )

        result = run_step(step, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert isinstance(error, PipelineError)
        assert "step failed" in error.message
        # Step function's original step_name is preserved
        assert error.step_name == "test_step"

    def test_run_step_shell_dispatch(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Shell step: injects shell_command and delegates."""
        ctx = WorkflowContext(inputs={"existing": "data"})
        step = Step(  # noqa: S604
            name="shell_step",
            function="execute_shell_step",
            shell=True,
            command="echo hello",
        )

        mock_shell_step = mocker.patch(
            "adws.adw_modules.engine.executor.execute_shell_step",
        )
        expected_ctx = ctx.merge_outputs(
            {"shell_stdout": "hello\n"},
        )
        mock_shell_step.return_value = IOSuccess(expected_ctx)

        result = run_step(step, ctx)
        assert isinstance(result, IOSuccess)

        # Verify shell_command was injected into inputs
        call_args = mock_shell_step.call_args
        called_ctx = call_args[0][0]
        assert called_ctx.inputs["shell_command"] == "echo hello"
        assert called_ctx.inputs["existing"] == "data"

    def test_run_step_sdk_dispatch(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK step: resolves from registry and calls."""
        ctx = WorkflowContext()
        step = Step(
            name="sdk_step",
            function="check_sdk_available",
        )

        sdk_ok = True
        success_fn = _make_success_step("sdk_ok", sdk_ok)
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"check_sdk_available": success_fn},
        )

        result = run_step(step, ctx)
        assert isinstance(result, IOSuccess)
        updated_ctx = unsafe_perform_io(result.unwrap())
        assert updated_ctx.outputs["sdk_ok"] is True

    def test_run_step_unknown_function(self) -> None:
        """Unknown function returns PipelineError with step name."""
        ctx = WorkflowContext()
        step = Step(
            name="bad_step",
            function="nonexistent_function",
        )

        result = run_step(step, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert isinstance(error, PipelineError)
        assert error.step_name == "bad_step"
        assert error.error_type == "UnknownStepFunction"


# --- Task 2: Context propagation tests ---


class TestContextPropagation:
    """Tests for context propagation between steps."""

    def test_outputs_become_inputs(
        self,
        mocker: MockerFixture,
    ) -> None:
        """After step N, outputs promoted to inputs for N+1."""
        step1 = Step(name="step1", function="fn1")
        step2 = Step(name="step2", function="fn2")
        workflow = Workflow(
            name="test_wf",
            description="test",
            steps=[step1, step2],
        )

        call_contexts: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            call_contexts.append(ctx)
            return IOSuccess(
                ctx.merge_outputs({"from_step": ctx.inputs}),
            )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("key1", "val1"),
                "fn2": capture_step,
            },
        )

        ctx = WorkflowContext(inputs={"initial": "data"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)

        # Step 2 received step 1's outputs as inputs
        step2_ctx = call_contexts[0]
        assert step2_ctx.inputs["key1"] == "val1"
        assert step2_ctx.inputs["initial"] == "data"
        assert step2_ctx.outputs == {}

    def test_empty_outputs_propagation(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Empty outputs still propagate (no-op promotion)."""

        def noop_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            return IOSuccess(ctx)

        step1 = Step(name="step1", function="fn1")
        step2 = Step(name="step2", function="fn2")
        workflow = Workflow(
            name="test_wf",
            description="test",
            steps=[step1, step2],
        )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": noop_step, "fn2": noop_step},
        )

        ctx = WorkflowContext(inputs={"k": "v"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)

    def test_collision_produces_pipeline_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Collision between outputs and inputs gives PipelineError."""

        def collision_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            return IOSuccess(
                ctx.merge_outputs({"existing": "new_val"}),
            )

        step1 = Step(name="collision_step", function="fn1")
        step2 = Step(name="step2", function="fn2")
        workflow = Workflow(
            name="test_wf",
            description="test",
            steps=[step1, step2],
        )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": collision_step,
                "fn2": _make_success_step("x", "y"),
            },
        )

        ctx = WorkflowContext(inputs={"existing": "orig"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert isinstance(error, PipelineError)
        assert error.error_type == "ContextCollisionError"
        assert error.step_name == "collision_step"
        # Verify context contains debugging info
        assert error.context["step_index"] == 0
        assert error.context["step_name"] == "collision_step"


# --- Task 3: run_workflow tests ---


class TestRunWorkflow:
    """Tests for run_workflow function."""

    def test_single_step_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Single step succeeds, returns final context."""
        step = Step(name="only_step", function="fn1")
        workflow = Workflow(
            name="wf",
            description="test",
            steps=[step],
        )

        done_flag = True
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": _make_success_step("done", done_flag)},
        )

        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        final = unsafe_perform_io(result.unwrap())
        assert final.outputs["done"] is True

    def test_multi_step_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Three steps succeed, context accumulates."""
        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
            Step(name="s3", function="fn3"),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("out1", "a"),
                "fn2": _make_success_step("out2", "b"),
                "fn3": _make_success_step("out3", "c"),
            },
        )

        ctx = WorkflowContext(inputs={"start": "x"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        final = unsafe_perform_io(result.unwrap())
        # Last step outputs in outputs dict
        assert final.outputs["out3"] == "c"
        # Previous outputs promoted to inputs
        assert final.inputs["out1"] == "a"
        assert final.inputs["out2"] == "b"
        assert final.inputs["start"] == "x"

    def test_mid_pipeline_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step 2 of 3 fails, halts, step 3 never called."""
        step3_mock = mocker.Mock()

        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
            Step(name="s3", function="fn3"),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("out1", "a"),
                "fn2": _make_failure_step("s2 exploded"),
                "fn3": step3_mock,
            },
        )

        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert "s2 exploded" in error.message
        step3_mock.assert_not_called()

    def test_first_step_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step 1 fails, no further steps execute."""
        step2_mock = mocker.Mock()

        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("s1 failed"),
                "fn2": step2_mock,
            },
        )

        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        step2_mock.assert_not_called()

    def test_empty_workflow(self) -> None:
        """Workflow with no steps returns initial context."""
        workflow = Workflow(
            name="empty",
            description="empty",
            steps=[],
        )
        ctx = WorkflowContext(inputs={"init": "val"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        final = unsafe_perform_io(result.unwrap())
        assert final.inputs["init"] == "val"

    def test_context_flows_through_steps(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Outputs from step 1 available as inputs to step 2."""
        received_inputs: list[dict[str, object]] = []

        def capturing_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received_inputs.append(dict(ctx.inputs))
            return IOSuccess(
                ctx.merge_outputs({"captured": "yes"}),
            )

        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )

        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("from_s1", "hello"),
                "fn2": capturing_step,
            },
        )

        ctx = WorkflowContext(inputs={"original": "data"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)

        # Step 2 received step 1's output as input
        assert received_inputs[0]["from_s1"] == "hello"
        assert received_inputs[0]["original"] == "data"

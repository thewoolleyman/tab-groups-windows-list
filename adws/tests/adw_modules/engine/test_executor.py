"""Tests for engine executor (run_step, run_workflow, registry)."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import (
    _resolve_input_from,
    _resolve_step_function,
    _run_step_with_retry,
    _should_skip_step,
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


# --- Test helper for flaky steps (Story 2.5) ---


def _make_flaky_step(
    fail_count: int,
    output_key: str,
    output_value: object,
) -> _StepFn:
    """Create a step that fails fail_count times then succeeds."""
    attempts: dict[str, int] = {"count": 0}

    def step(
        ctx: WorkflowContext,
    ) -> IOResult[WorkflowContext, PipelineError]:
        attempts["count"] += 1
        if attempts["count"] <= fail_count:
            return IOFailure(
                PipelineError(
                    step_name="flaky_step",
                    error_type="TransientError",
                    message=(
                        f"Attempt {attempts['count']} failed"
                    ),
                    context={"attempt": attempts["count"]},
                ),
            )
        return IOSuccess(
            ctx.merge_outputs({output_key: output_value}),
        )

    return step


# --- Task 3: _run_step_with_retry tests (Story 2.5) ---


class TestRunStepWithRetry:
    """Tests for _run_step_with_retry function."""

    def test_retry_success_first_attempt(
        self,
        mocker: MockerFixture,
    ) -> None:
        """max_attempts=3, succeeds first try, no retries."""
        step = Step(
            name="ok_step",
            function="fn1",
            max_attempts=3,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": _make_success_step("result", "ok")},
        )
        ctx = WorkflowContext()
        result = _run_step_with_retry(step, ctx)
        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["result"] == "ok"

    def test_retry_success_second_attempt(
        self,
        mocker: MockerFixture,
    ) -> None:
        """max_attempts=3, fails once then succeeds."""
        flaky = _make_flaky_step(1, "result", "recovered")
        step = Step(
            name="flaky_step",
            function="fn1",
            max_attempts=3,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": flaky},
        )
        mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = _run_step_with_retry(step, ctx)
        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["result"] == "recovered"

    def test_retry_exhaustion(
        self,
        mocker: MockerFixture,
    ) -> None:
        """max_attempts=2, fails both times, PipelineError returned."""
        step = Step(
            name="always_fail",
            function="fn1",
            max_attempts=2,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": _make_failure_step("permanent error")},
        )
        mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = _run_step_with_retry(step, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert "permanent error" in error.message

    def test_retry_delay_called(
        self,
        mocker: MockerFixture,
    ) -> None:
        """sleep_seconds called between retries with correct delay."""
        flaky = _make_flaky_step(1, "result", "ok")
        step = Step(
            name="delay_step",
            function="fn1",
            max_attempts=3,
            retry_delay_seconds=2.0,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": flaky},
        )
        mock_sleep = mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = _run_step_with_retry(step, ctx)
        assert isinstance(result, IOSuccess)
        mock_sleep.assert_called_once_with(2.0)

    def test_retry_no_delay_when_zero(
        self,
        mocker: MockerFixture,
    ) -> None:
        """retry_delay_seconds=0.0 means sleep not called."""
        flaky = _make_flaky_step(1, "result", "ok")
        step = Step(
            name="no_delay",
            function="fn1",
            max_attempts=2,
            retry_delay_seconds=0.0,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": flaky},
        )
        mock_sleep = mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = _run_step_with_retry(step, ctx)
        assert isinstance(result, IOSuccess)
        mock_sleep.assert_not_called()

    def test_retry_feedback_accumulation(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Each retry receives feedback from prior failure."""
        received_ctxs: list[WorkflowContext] = []

        def capturing_flaky(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received_ctxs.append(ctx)
            if len(received_ctxs) <= 1:
                return IOFailure(
                    PipelineError(
                        step_name="flaky",
                        error_type="TransientError",
                        message="first attempt failed",
                        context={},
                    ),
                )
            return IOSuccess(
                ctx.merge_outputs({"done": True}),
            )

        step = Step(
            name="feedback_step",
            function="fn1",
            max_attempts=3,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": capturing_flaky},
        )
        mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = _run_step_with_retry(step, ctx)
        assert isinstance(result, IOSuccess)
        # Second call should have feedback from first failure
        assert len(received_ctxs) == 2
        assert len(received_ctxs[1].feedback) == 1
        assert "Retry 1/3" in received_ctxs[1].feedback[0]
        assert "first attempt failed" in received_ctxs[1].feedback[0]


# --- Task 4: always_run tests (Story 2.5) ---


class TestAlwaysRun:
    """Tests for always_run step behavior in run_workflow."""

    def test_always_run_after_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Normal step fails, always_run step still executes."""
        cleanup_called: list[bool] = []

        def cleanup_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            cleanup_called.append(True)
            return IOSuccess(
                ctx.merge_outputs({"cleaned": True}),
            )

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("s1 exploded"),
                "fn2": cleanup_step,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        # Original error preserved
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert "s1 exploded" in error.message
        # Cleanup ran
        assert cleanup_called == [True]

    def test_always_run_after_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """All steps succeed, always_run runs normally."""
        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
            ),
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
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        final = unsafe_perform_io(result.unwrap())
        assert final.outputs["out2"] == "b"
        assert final.inputs["out1"] == "a"

    def test_always_run_step_itself_fails(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Original error preserved when always_run also fails."""
        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("original error"),
                "fn2": _make_failure_step("cleanup failed"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        # Original pipeline error is preserved
        assert "original error" in error.message
        # AC5: always_run failure included in context
        ar_failures = error.context["always_run_failures"]
        assert isinstance(ar_failures, list)
        assert len(ar_failures) == 1
        assert "cleanup failed" in str(ar_failures[0])

    def test_multiple_always_run_steps(
        self,
        mocker: MockerFixture,
    ) -> None:
        """All always_run steps execute even if one fails."""
        calls: list[str] = []

        def track_step(
            name: str,
        ) -> _StepFn:
            def step(
                ctx: WorkflowContext,
            ) -> IOResult[WorkflowContext, PipelineError]:
                calls.append(name)
                return IOSuccess(
                    ctx.merge_outputs({name: True}),
                )

            return step

        def track_and_fail(
            name: str,
            msg: str,
        ) -> _StepFn:
            def step(
                ctx: WorkflowContext,
            ) -> IOResult[WorkflowContext, PipelineError]:
                calls.append(name)
                return IOFailure(
                    PipelineError(
                        step_name=name,
                        error_type="CleanupError",
                        message=msg,
                        context={},
                    ),
                )

            return step

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup1",
                function="fn2",
                always_run=True,
            ),
            Step(
                name="cleanup2",
                function="fn3",
                always_run=True,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": track_and_fail(
                    "cleanup1", "cleanup1 broke"
                ),
                "fn3": track_step("cleanup2"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        # Both always_run steps ran despite cleanup1 failing
        assert calls == ["cleanup1", "cleanup2"]
        error = unsafe_perform_io(result.failure())
        # Original error preserved
        assert "boom" in error.message
        # cleanup1 failure tracked in context
        ar_failures = error.context["always_run_failures"]
        assert isinstance(ar_failures, list)
        assert len(ar_failures) == 1
        assert "cleanup1 broke" in str(ar_failures[0])

    def test_always_run_with_retry(
        self,
        mocker: MockerFixture,
    ) -> None:
        """always_run step with max_attempts retries."""
        cleaned = True
        flaky = _make_flaky_step(1, "cleaned", cleaned)
        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
                max_attempts=3,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": flaky,
            },
        )
        mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        # Original error preserved
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert "boom" in error.message

    def test_always_run_receives_failure_context(
        self,
        mocker: MockerFixture,
    ) -> None:
        """always_run step gets context at point of failure."""
        received: list[WorkflowContext] = []

        def capture_ctx(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(ctx)

        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
            Step(
                name="cleanup",
                function="fn3",
                always_run=True,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("data", "val"),
                "fn2": _make_failure_step("s2 failed"),
                "fn3": capture_ctx,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        # Cleanup step received context with s1 outputs
        # promoted to inputs
        assert len(received) == 1
        assert received[0].inputs["data"] == "val"

    def test_normal_steps_skipped_after_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step 2 fails, step 3 (normal) skipped, step 4 runs."""
        step3_mock = mocker.Mock()
        cleanup_called: list[bool] = []

        def cleanup(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            cleanup_called.append(True)
            return IOSuccess(ctx)

        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
            Step(name="s3", function="fn3"),
            Step(
                name="s4",
                function="fn4",
                always_run=True,
            ),
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
                "fn2": _make_failure_step("s2 failed"),
                "fn3": step3_mock,
                "fn4": cleanup,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        step3_mock.assert_not_called()
        assert cleanup_called == [True]

    def test_always_run_collision_preserves_original(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Collision in always_run step keeps original error."""

        def collision_cleanup(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            return IOSuccess(
                ctx.merge_outputs({"data": "collision"}),
            )

        steps = [
            Step(name="s1", function="fn1"),
            Step(name="s2", function="fn2"),
            Step(
                name="cleanup",
                function="fn3",
                always_run=True,
            ),
            Step(
                name="cleanup2",
                function="fn4",
                always_run=True,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("data", "val"),
                "fn2": _make_failure_step("s2 failed"),
                "fn3": collision_cleanup,
                "fn4": _make_success_step("final", "ok"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        # Original error preserved, not the collision
        assert "s2 failed" in error.message


# --- Task 5: Retry + workflow integration tests ---


class TestRetryWorkflowIntegration:
    """Tests for retry wired into run_workflow."""

    def test_workflow_retryable_step_recovers(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step with max_attempts=3 fails twice, succeeds third."""
        flaky = _make_flaky_step(2, "result", "recovered")
        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="flaky",
                function="fn2",
                max_attempts=3,
            ),
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
                "fn2": flaky,
                "fn3": _make_success_step("out3", "c"),
            },
        )
        mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        final = unsafe_perform_io(result.unwrap())
        assert final.outputs["out3"] == "c"
        assert final.inputs["result"] == "recovered"

    def test_workflow_retry_exhaustion_to_always_run(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Retryable step exhausts, always_run still runs."""
        cleanup_called: list[bool] = []

        def cleanup(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            cleanup_called.append(True)
            return IOSuccess(ctx)

        steps = [
            Step(
                name="failing",
                function="fn1",
                max_attempts=2,
            ),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("always fails"),
                "fn2": cleanup,
            },
        )
        mocker.patch(
            "adws.adw_modules.engine.executor.sleep_seconds",
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert "always fails" in error.message
        assert cleanup_called == [True]


# --- Story 2.6: Output data flow tests ---


class TestOutputDataFlow:
    """Tests for output data flow registry in run_workflow."""

    def test_output_registered_in_data_flow(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step with output set registers in data flow."""
        # Step 1 outputs data with output="s1_data"
        # Step 2 uses input_from to pull from s1_data
        received: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(
                ctx.merge_outputs({"result": "done"}),
            )

        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_data",
            ),
            Step(
                name="s2",
                function="fn2",
                input_from={"s1_data": "source"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("key1", "val1"),
                "fn2": capture_step,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        # Step 2 received s1's outputs via input_from
        assert received[0].inputs["source"] == {
            "key1": "val1",
        }

    def test_output_empty_outputs_registered(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step with output set but no outputs: registered empty."""

        def noop_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            return IOSuccess(ctx)

        received: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(ctx)

        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_data",
            ),
            Step(
                name="s2",
                function="fn2",
                input_from={"s1_data": "source"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": noop_step, "fn2": capture_step},
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        # Empty dict registered
        assert received[0].inputs["source"] == {}

    def test_output_not_set_no_registration(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Step without output field does not register."""
        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="s2",
                function="fn2",
                input_from={"s1_data": "source"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("k", "v"),
                "fn2": _make_success_step("k2", "v2"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputFromError"
        assert "s1_data" in error.message


# --- Story 2.6: input_from data flow tests ---


class TestInputFromDataFlow:
    """Tests for input_from resolution in run_workflow."""

    def test_input_from_resolves_single_source(
        self,
        mocker: MockerFixture,
    ) -> None:
        """input_from maps data from one upstream step."""
        received: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(
                ctx.merge_outputs({"done": True}),
            )

        steps = [
            Step(
                name="producer",
                function="fn1",
                output="prod_out",
            ),
            Step(
                name="consumer",
                function="fn2",
                input_from={"prod_out": "my_data"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("x", 42),
                "fn2": capture_step,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        assert received[0].inputs["my_data"] == {"x": 42}

    def test_input_from_resolves_multiple_sources(
        self,
        mocker: MockerFixture,
    ) -> None:
        """input_from maps data from multiple upstream steps."""
        received: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(ctx)

        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_out",
            ),
            Step(
                name="s2",
                function="fn2",
                output="s2_out",
            ),
            Step(
                name="s3",
                function="fn3",
                input_from={
                    "s1_out": "from_s1",
                    "s2_out": "from_s2",
                },
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("a", 1),
                "fn2": _make_success_step("b", 2),
                "fn3": capture_step,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        assert received[0].inputs["from_s1"] == {"a": 1}
        assert received[0].inputs["from_s2"] == {"b": 2}

    def test_input_from_missing_source_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Missing input_from source produces PipelineError."""
        steps = [
            Step(
                name="s1",
                function="fn1",
                output="actual_name",
            ),
            Step(
                name="s2",
                function="fn2",
                input_from={"wrong_name": "data"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("k", "v"),
                "fn2": _make_success_step("k2", "v2"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputFromError"
        assert "wrong_name" in error.message
        assert "actual_name" in error.message
        assert error.step_name == "s2"

    def test_input_from_collision_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """input_from collision with existing input key."""
        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_out",
            ),
            Step(
                name="s2",
                function="fn2",
                input_from={"s1_out": "existing_key"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("k", "v"),
                "fn2": _make_success_step("k2", "v2"),
            },
        )
        ctx = WorkflowContext(
            inputs={"existing_key": "original"},
        )
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "InputFromCollisionError"
        assert "existing_key" in error.message
        assert error.step_name == "s2"

    def test_input_from_and_promote_coexist(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Both implicit and explicit flow in same workflow."""
        received: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(
                ctx.merge_outputs({"final": "done"}),
            )

        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_out",
            ),
            Step(
                name="s2",
                function="fn2",
                input_from={"s1_out": "explicit_data"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("imp_key", "imp_v"),
                "fn2": capture_step,
            },
        )
        ctx = WorkflowContext(inputs={"init": "data"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        # Both implicit (promoted) and explicit (input_from)
        assert received[0].inputs["init"] == "data"
        # Promoted from s1
        assert received[0].inputs["imp_key"] == "imp_v"
        # Explicit via input_from
        assert received[0].inputs["explicit_data"] == {
            "imp_key": "imp_v",
        }


# --- Story 2.6: Condition predicate tests ---


class TestConditionPredicate:
    """Tests for condition predicate in run_workflow."""

    def test_condition_true_executes(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Condition returns True, step runs normally."""
        executed: list[bool] = []

        def track_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            executed.append(True)
            return IOSuccess(
                ctx.merge_outputs({"ran": True}),
            )

        def always_true(ctx: WorkflowContext) -> bool:
            return True

        steps = [
            Step(
                name="s1",
                function="fn1",
                condition=always_true,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": track_step},
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        assert executed == [True]

    def test_condition_false_skips(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Condition returns False, step skipped, no error."""
        step_mock = mocker.Mock()

        def always_false(ctx: WorkflowContext) -> bool:
            return False

        steps = [
            Step(
                name="s1",
                function="fn1",
                condition=always_false,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": step_mock},
        )
        ctx = WorkflowContext(inputs={"init": "val"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        step_mock.assert_not_called()

    def test_condition_false_no_output_registered(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Skipped step's output NOT in data flow registry."""

        def always_false(ctx: WorkflowContext) -> bool:
            return False

        steps = [
            Step(
                name="skipped",
                function="fn1",
                condition=always_false,
                output="skipped_data",
            ),
            Step(
                name="consumer",
                function="fn2",
                input_from={"skipped_data": "data"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("k", "v"),
                "fn2": _make_success_step("k2", "v2"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputFromError"
        assert "skipped_data" in error.message

    def test_condition_false_subsequent_steps_run(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Steps after skipped step still execute."""
        executed: list[str] = []

        def track(
            name: str,
        ) -> _StepFn:
            def step(
                ctx: WorkflowContext,
            ) -> IOResult[WorkflowContext, PipelineError]:
                executed.append(name)
                return IOSuccess(
                    ctx.merge_outputs({name: True}),
                )

            return step

        def always_false(ctx: WorkflowContext) -> bool:
            return False

        steps = [
            Step(
                name="s1",
                function="fn1",
                condition=always_false,
            ),
            Step(name="s2", function="fn2"),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": track("s1"), "fn2": track("s2")},
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        assert executed == ["s2"]

    def test_condition_none_always_executes(
        self,
        mocker: MockerFixture,
    ) -> None:
        """No condition set, step always runs (backward compat)."""
        executed: list[bool] = []

        def track_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            executed.append(True)
            return IOSuccess(ctx)

        steps = [
            Step(name="s1", function="fn1"),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": track_step},
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        assert executed == [True]

    def test_condition_always_run_failure_path(
        self,
        mocker: MockerFixture,
    ) -> None:
        """always_run + condition=True in failure path: executes."""
        cleanup_ran: list[bool] = []

        def cleanup(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            cleanup_ran.append(True)
            return IOSuccess(ctx)

        def always_true(ctx: WorkflowContext) -> bool:
            return True

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
                condition=always_true,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": cleanup,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        assert cleanup_ran == [True]

    def test_condition_always_run_false_skipped(
        self,
        mocker: MockerFixture,
    ) -> None:
        """always_run + condition=False in failure: skipped."""
        cleanup_mock = mocker.Mock()

        def always_false(ctx: WorkflowContext) -> bool:
            return False

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
                condition=always_false,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": cleanup_mock,
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        cleanup_mock.assert_not_called()

    def test_condition_receives_current_context(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Condition callable receives current (not initial) ctx."""
        condition_ctxs: list[WorkflowContext] = []

        def tracking_condition(
            ctx: WorkflowContext,
        ) -> bool:
            condition_ctxs.append(ctx)
            return True

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="s2",
                function="fn2",
                condition=tracking_condition,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("from_s1", "v"),
                "fn2": _make_success_step("from_s2", "w"),
            },
        )
        ctx = WorkflowContext(inputs={"init": "data"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        # Condition received context after s1 promotion
        assert len(condition_ctxs) == 1
        assert condition_ctxs[0].inputs["from_s1"] == "v"
        assert condition_ctxs[0].inputs["init"] == "data"

    def test_condition_after_failure_normal_skip(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Non-always_run + condition after failure: skipped."""
        condition_mock = mocker.Mock(return_value=True)

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="s2",
                function="fn2",
                condition=condition_mock,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": _make_success_step("k", "v"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        # Condition was NOT evaluated for skipped step
        condition_mock.assert_not_called()

    def test_input_from_error_always_run_failure_path(
        self,
        mocker: MockerFixture,
    ) -> None:
        """input_from error on always_run step in failure path."""
        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
                input_from={"missing": "data"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": _make_success_step("k", "v"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        # Original error preserved
        assert "boom" in error.message
        # input_from error tracked in always_run_failures
        ar_failures = error.context["always_run_failures"]
        assert isinstance(ar_failures, list)
        assert len(ar_failures) == 1
        assert "MissingInputFromError" in str(
            ar_failures[0],
        )

    def test_condition_exception_produces_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Condition predicate that raises gives PipelineError."""

        def exploding(ctx: WorkflowContext) -> bool:
            msg = "predicate exploded"
            raise RuntimeError(msg)

        steps = [
            Step(
                name="s1",
                function="fn1",
                condition=exploding,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {"fn1": _make_success_step("k", "v")},
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ConditionEvaluationError"
        assert "predicate exploded" in error.message
        assert error.step_name == "s1"
        assert (
            error.context["exception_type"] == "RuntimeError"
        )

    def test_condition_exception_always_run_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Condition exception on always_run in failure path."""

        def exploding(ctx: WorkflowContext) -> bool:
            msg = "cleanup condition failed"
            raise ValueError(msg)

        steps = [
            Step(name="s1", function="fn1"),
            Step(
                name="cleanup",
                function="fn2",
                always_run=True,
                condition=exploding,
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_failure_step("boom"),
                "fn2": _make_success_step("k", "v"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        # Original error preserved
        assert "boom" in error.message
        # Condition error tracked in always_run_failures
        ar_failures = error.context["always_run_failures"]
        assert isinstance(ar_failures, list)
        assert len(ar_failures) == 1
        assert "ConditionEvaluationError" in str(
            ar_failures[0],
        )


# --- Story 2.6: _should_skip_step tests ---


class TestShouldSkipStep:
    """Tests for _should_skip_step helper function."""

    def test_skip_non_always_run_after_failure(self) -> None:
        """Non-always_run step skipped after pipeline failure."""
        step = Step(name="s", function="f")
        ctx = WorkflowContext()
        err = PipelineError(
            step_name="x",
            error_type="E",
            message="boom",
            context={},
        )
        result = _should_skip_step(step, ctx, err)
        assert isinstance(result, IOSuccess)
        assert unsafe_perform_io(result.unwrap()) is True

    def test_no_skip_always_run_after_failure(self) -> None:
        """always_run step NOT skipped after pipeline failure."""
        step = Step(
            name="s", function="f", always_run=True,
        )
        ctx = WorkflowContext()
        err = PipelineError(
            step_name="x",
            error_type="E",
            message="boom",
            context={},
        )
        result = _should_skip_step(step, ctx, err)
        assert isinstance(result, IOSuccess)
        assert unsafe_perform_io(result.unwrap()) is False

    def test_skip_false_condition(self) -> None:
        """Step with false condition is skipped."""

        def nope(ctx: WorkflowContext) -> bool:
            return False

        step = Step(
            name="s", function="f", condition=nope,
        )
        ctx = WorkflowContext()
        result = _should_skip_step(step, ctx, None)
        assert isinstance(result, IOSuccess)
        assert unsafe_perform_io(result.unwrap()) is True

    def test_no_skip_true_condition(self) -> None:
        """Step with true condition runs."""

        def yes(ctx: WorkflowContext) -> bool:
            return True

        step = Step(
            name="s", function="f", condition=yes,
        )
        ctx = WorkflowContext()
        result = _should_skip_step(step, ctx, None)
        assert isinstance(result, IOSuccess)
        assert unsafe_perform_io(result.unwrap()) is False

    def test_no_skip_no_condition(self) -> None:
        """Step without condition runs normally."""
        step = Step(name="s", function="f")
        ctx = WorkflowContext()
        result = _should_skip_step(step, ctx, None)
        assert isinstance(result, IOSuccess)
        assert unsafe_perform_io(result.unwrap()) is False

    def test_condition_exception_returns_failure(self) -> None:
        """Condition that raises returns IOFailure."""

        def boom(ctx: WorkflowContext) -> bool:
            msg = "broken"
            raise RuntimeError(msg)

        step = Step(
            name="bad", function="f", condition=boom,
        )
        ctx = WorkflowContext()
        result = _should_skip_step(step, ctx, None)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "ConditionEvaluationError"
        assert "broken" in error.message
        assert error.step_name == "bad"


# --- Story 2.6: Integration tests ---


class TestDataFlowIntegration:
    """Integration tests for data flow + condition + always_run."""

    def test_full_data_flow_pipeline(
        self,
        mocker: MockerFixture,
    ) -> None:
        """3 steps with output/input_from, data flows."""
        received: list[WorkflowContext] = []

        def capture_step(
            ctx: WorkflowContext,
        ) -> IOResult[WorkflowContext, PipelineError]:
            received.append(ctx)
            return IOSuccess(
                ctx.merge_outputs({"s3_out": "final"}),
            )

        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_out",
            ),
            Step(
                name="s2",
                function="fn2",
                output="s2_out",
            ),
            Step(
                name="s3",
                function="fn3",
                input_from={
                    "s1_out": "from_s1",
                    "s2_out": "from_s2",
                },
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": _make_success_step("a", 1),
                "fn2": _make_success_step("b", 2),
                "fn3": capture_step,
            },
        )
        ctx = WorkflowContext(inputs={"init": "x"})
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        # s3 got both s1 and s2 data via input_from
        assert received[0].inputs["from_s1"] == {"a": 1}
        assert received[0].inputs["from_s2"] == {"b": 2}
        # Also got implicit promoted data
        assert received[0].inputs["init"] == "x"
        assert received[0].inputs["a"] == 1
        assert received[0].inputs["b"] == 2

    def test_condition_plus_data_flow_plus_always_run(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Conditional skip, always_run, data flow combined."""
        executed: list[str] = []

        def track(
            name: str,
        ) -> _StepFn:
            def step(
                ctx: WorkflowContext,
            ) -> IOResult[WorkflowContext, PipelineError]:
                executed.append(name)
                return IOSuccess(
                    ctx.merge_outputs({name: True}),
                )

            return step

        def always_false(ctx: WorkflowContext) -> bool:
            return False

        steps = [
            Step(
                name="s1",
                function="fn1",
                output="s1_out",
            ),
            Step(
                name="skip_me",
                function="fn2",
                condition=always_false,
                output="skip_out",
            ),
            Step(
                name="s3",
                function="fn3",
                input_from={"s1_out": "data"},
            ),
        ]
        workflow = Workflow(
            name="wf",
            description="test",
            steps=steps,
        )
        mocker.patch(
            "adws.adw_modules.engine.executor._STEP_REGISTRY",
            {
                "fn1": track("s1"),
                "fn2": track("skip_me"),
                "fn3": track("s3"),
            },
        )
        ctx = WorkflowContext()
        result = run_workflow(workflow, ctx)
        assert isinstance(result, IOSuccess)
        # skip_me was skipped, others executed
        assert executed == ["s1", "s3"]


# --- Story 2.6: _resolve_input_from tests ---


class TestResolveInputFrom:
    """Tests for _resolve_input_from helper function."""

    def test_resolve_input_from_none(self) -> None:
        """No input_from returns context unchanged."""
        step = Step(name="s", function="f")
        ctx = WorkflowContext(inputs={"k": "v"})
        registry: dict[str, dict[str, object]] = {}
        result = _resolve_input_from(step, ctx, registry)
        assert isinstance(result, IOSuccess)
        resolved = unsafe_perform_io(result.unwrap())
        assert resolved.inputs == {"k": "v"}

    def test_resolve_input_from_success(self) -> None:
        """Successful resolution merges data."""
        step = Step(
            name="s",
            function="f",
            input_from={"src": "dest"},
        )
        ctx = WorkflowContext(inputs={"k": "v"})
        registry: dict[str, dict[str, object]] = {
            "src": {"data": 42},
        }
        result = _resolve_input_from(step, ctx, registry)
        assert isinstance(result, IOSuccess)
        resolved = unsafe_perform_io(result.unwrap())
        assert resolved.inputs["dest"] == {"data": 42}
        assert resolved.inputs["k"] == "v"

    def test_resolve_input_from_missing(self) -> None:
        """Missing source produces IOFailure."""
        step = Step(
            name="s",
            function="f",
            input_from={"missing": "dest"},
        )
        ctx = WorkflowContext()
        registry: dict[str, dict[str, object]] = {
            "other": {},
        }
        result = _resolve_input_from(step, ctx, registry)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "MissingInputFromError"
        assert "missing" in error.message
        assert "other" in error.message

    def test_resolve_input_from_collision(self) -> None:
        """Collision with existing input key."""
        step = Step(
            name="s",
            function="f",
            input_from={"src": "existing"},
        )
        ctx = WorkflowContext(
            inputs={"existing": "original"},
        )
        registry: dict[str, dict[str, object]] = {
            "src": {"data": 42},
        }
        result = _resolve_input_from(step, ctx, registry)
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error.error_type == "InputFromCollisionError"
        assert "existing" in error.message

"""Integration tests for feedback accumulation across retry cycles.

Simulates verify-implement retry cycles to verify feedback flows
correctly from verify failure -> accumulation -> retry context.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import run_workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.add_verify_feedback import (
    add_verify_feedback_to_context,
)
from adws.adw_modules.steps.build_feedback_context import (
    build_feedback_context,
)
from adws.adw_modules.types import WorkflowContext
from adws.workflows import WorkflowName, load_workflow

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _make_pass_step(
    output_key: str,
) -> object:
    """Create a mock step that always passes."""

    def step(
        ctx: WorkflowContext,
    ) -> IOSuccess[WorkflowContext]:
        return IOSuccess(
            ctx.merge_outputs({output_key: True}),
        )

    return step


def _make_fail_step(
    step_name: str,
    tool_name: str,
    errors: list[str],
    raw_output: str,
) -> object:
    """Create a mock step that always fails."""

    def step(
        ctx: WorkflowContext,
    ) -> IOFailure[PipelineError]:
        return IOFailure(
            PipelineError(
                step_name=step_name,
                error_type="VerifyFailed",
                message=(
                    f"{tool_name} check failed:"
                    f" {len(errors)} error(s)"
                ),
                context={
                    "tool_name": tool_name,
                    "errors": errors,
                    "raw_output": raw_output,
                },
            ),
        )

    return step


def test_feedback_cycle_single_failure_integration(
    mocker: MockerFixture,
) -> None:
    """Single verify failure flows through accumulation.

    1. Run verify workflow (mocked jest failure)
    2. Accumulate feedback from the PipelineError
    3. Build feedback context string
    4. Verify it contains tool name, errors, attempt
    """
    mocker.patch(
        "adws.adw_modules.engine.executor._STEP_REGISTRY",
        {
            "run_jest_step": _make_fail_step(
                "run_jest_step",
                "jest",
                ["FAIL src/popup.test.ts"],
                "FAIL src/popup.test.ts\n1 failed",
            ),
            "run_playwright_step": _make_pass_step(
                "verify_playwright",
            ),
            "run_mypy_step": _make_pass_step(
                "verify_mypy",
            ),
            "run_ruff_step": _make_pass_step(
                "verify_ruff",
            ),
        },
    )

    # Step 1: Run verify workflow
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    ctx = WorkflowContext()
    result = run_workflow(wf, ctx)

    # Verify workflow fails (jest failed)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "VerifyFailed"

    # Step 2: Accumulate feedback
    updated_ctx = add_verify_feedback_to_context(
        ctx, error, attempt=1,
    )
    assert len(updated_ctx.feedback) == 1

    # Step 3: Build feedback context
    feedback_str = build_feedback_context(updated_ctx)

    # Step 4: Verify content
    assert "jest" in feedback_str
    assert "FAIL src/popup.test.ts" in feedback_str
    assert "Attempt 1" in feedback_str


def test_feedback_cycle_multi_attempt_integration(
    mocker: MockerFixture,
) -> None:
    """Multi-cycle: jest failure then ruff failure.

    1. Verify fails (jest), add feedback attempt 1
    2. Verify fails (ruff), add feedback attempt 2
    3. build_feedback_context includes BOTH failures
    4. No duplication
    """
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    ctx = WorkflowContext()

    # --- Cycle 1: jest fails ---
    mocker.patch(
        "adws.adw_modules.engine.executor._STEP_REGISTRY",
        {
            "run_jest_step": _make_fail_step(
                "run_jest_step",
                "jest",
                ["FAIL src/popup.test.ts"],
                "jest output cycle 1",
            ),
            "run_playwright_step": _make_pass_step(
                "verify_playwright",
            ),
            "run_mypy_step": _make_pass_step(
                "verify_mypy",
            ),
            "run_ruff_step": _make_pass_step(
                "verify_ruff",
            ),
        },
    )
    result1 = run_workflow(wf, ctx)
    assert isinstance(result1, IOFailure)
    error1 = unsafe_perform_io(result1.failure())
    ctx = add_verify_feedback_to_context(
        ctx, error1, attempt=1,
    )

    # --- Cycle 2: ruff fails ---
    mocker.patch(
        "adws.adw_modules.engine.executor._STEP_REGISTRY",
        {
            "run_jest_step": _make_pass_step(
                "verify_jest",
            ),
            "run_playwright_step": _make_pass_step(
                "verify_playwright",
            ),
            "run_mypy_step": _make_pass_step(
                "verify_mypy",
            ),
            "run_ruff_step": _make_fail_step(
                "run_ruff_step",
                "ruff",
                ["E501 line too long", "F401 unused"],
                "ruff output cycle 2",
            ),
        },
    )
    result2 = run_workflow(wf, ctx)
    assert isinstance(result2, IOFailure)
    error2 = unsafe_perform_io(result2.failure())
    ctx = add_verify_feedback_to_context(
        ctx, error2, attempt=2,
    )

    # Verify accumulation
    assert len(ctx.feedback) == 2

    # Build feedback context
    feedback_str = build_feedback_context(ctx)

    # Verify BOTH attempts present
    assert "Attempt 1" in feedback_str
    assert "Attempt 2" in feedback_str
    assert "jest" in feedback_str
    assert "ruff" in feedback_str
    assert "FAIL src/popup.test.ts" in feedback_str
    assert "E501 line too long" in feedback_str
    assert "F401 unused" in feedback_str

    # Verify chronological order
    idx1 = feedback_str.index("Attempt 1")
    idx2 = feedback_str.index("Attempt 2")
    assert idx1 < idx2

    # Verify no duplication (each attempt appears once)
    assert feedback_str.count("### Attempt 1") == 1
    assert feedback_str.count("### Attempt 2") == 1

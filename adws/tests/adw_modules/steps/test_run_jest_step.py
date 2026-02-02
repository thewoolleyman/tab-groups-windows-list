"""Tests for run_jest_step step module."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import run_jest_step as pkg_run_jest_step
from adws.adw_modules.steps.run_jest_step import run_jest_step
from adws.adw_modules.types import VerifyResult, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_jest_step_importable_from_steps_package() -> None:
    """run_jest_step is importable from steps package."""
    assert pkg_run_jest_step is run_jest_step


def test_run_jest_step_success(
    mocker: MockerFixture,
) -> None:
    """Jest passes: VerifyResult in context outputs."""
    verify_result = VerifyResult(
        tool_name="jest",
        passed=True,
        errors=[],
        raw_output="all tests passed",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_jest_step.run_jest_tests",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_jest_step(ctx)
    assert isinstance(result, IOSuccess)
    updated_ctx = unsafe_perform_io(result.unwrap())
    assert "verify_jest" in updated_ctx.outputs
    assert updated_ctx.outputs["verify_jest"] is verify_result


def test_run_jest_step_tool_failure(
    mocker: MockerFixture,
) -> None:
    """Jest fails: IOFailure with PipelineError."""
    verify_result = VerifyResult(
        tool_name="jest",
        passed=False,
        errors=["FAIL src/test.ts"],
        raw_output="FAIL src/test.ts\n1 test failed",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_jest_step.run_jest_tests",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_jest_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "run_jest_step"
    assert error.error_type == "VerifyFailed"
    assert "jest check failed" in error.message
    assert "1 error(s)" in error.message
    assert error.context["tool_name"] == "jest"
    assert error.context["errors"] == ["FAIL src/test.ts"]
    assert error.context["raw_output"] == (
        "FAIL src/test.ts\n1 test failed"
    )
    # Original context unchanged on failure
    assert ctx.outputs == {}


def test_run_jest_step_io_failure(
    mocker: MockerFixture,
) -> None:
    """io_ops IOFailure propagates through bind."""
    io_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="TimeoutError",
        message="Command timed out",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_jest_step.run_jest_tests",
        return_value=IOFailure(io_error),
    )
    ctx = WorkflowContext()
    result = run_jest_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is io_error
    assert error.error_type == "TimeoutError"

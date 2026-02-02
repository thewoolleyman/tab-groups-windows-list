"""Tests for run_mypy_step step module."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    run_mypy_step as pkg_run_mypy_step,
)
from adws.adw_modules.steps.run_mypy_step import run_mypy_step
from adws.adw_modules.types import VerifyResult, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_mypy_step_importable_from_steps_package() -> None:
    """run_mypy_step is importable from steps package."""
    assert pkg_run_mypy_step is run_mypy_step


def test_run_mypy_step_success(
    mocker: MockerFixture,
) -> None:
    """mypy passes: VerifyResult in context outputs."""
    verify_result = VerifyResult(
        tool_name="mypy",
        passed=True,
        errors=[],
        raw_output="Success: no issues found",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_mypy_step.run_mypy_check",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_mypy_step(ctx)
    assert isinstance(result, IOSuccess)
    updated_ctx = unsafe_perform_io(result.unwrap())
    assert "verify_mypy" in updated_ctx.outputs
    assert updated_ctx.outputs["verify_mypy"] is verify_result


def test_run_mypy_step_tool_failure(
    mocker: MockerFixture,
) -> None:
    """mypy fails: IOFailure with PipelineError."""
    verify_result = VerifyResult(
        tool_name="mypy",
        passed=False,
        errors=["adws/io_ops.py:10: error: Missing type"],
        raw_output="adws/io_ops.py:10: error: Missing type",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_mypy_step.run_mypy_check",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_mypy_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "run_mypy_step"
    assert error.error_type == "VerifyFailed"
    assert "mypy check failed" in error.message
    assert "1 error(s)" in error.message
    assert error.context["tool_name"] == "mypy"
    assert error.context["errors"] == [
        "adws/io_ops.py:10: error: Missing type",
    ]
    assert error.context["raw_output"] == (
        "adws/io_ops.py:10: error: Missing type"
    )
    # Original context unchanged on failure
    assert ctx.outputs == {}


def test_run_mypy_step_io_failure(
    mocker: MockerFixture,
) -> None:
    """io_ops IOFailure propagates through bind."""
    io_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="TimeoutError",
        message="Command timed out",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_mypy_step.run_mypy_check",
        return_value=IOFailure(io_error),
    )
    ctx = WorkflowContext()
    result = run_mypy_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is io_error
    assert error.error_type == "TimeoutError"

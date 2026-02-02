"""Tests for run_ruff_step step module."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    run_ruff_step as pkg_run_ruff_step,
)
from adws.adw_modules.steps.run_ruff_step import run_ruff_step
from adws.adw_modules.types import VerifyResult, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_ruff_step_importable_from_steps_package() -> None:
    """run_ruff_step is importable from steps package."""
    assert pkg_run_ruff_step is run_ruff_step


def test_run_ruff_step_success(
    mocker: MockerFixture,
) -> None:
    """ruff passes: VerifyResult in context outputs."""
    verify_result = VerifyResult(
        tool_name="ruff",
        passed=True,
        errors=[],
        raw_output="All checks passed!",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_ruff_step.run_ruff_check",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_ruff_step(ctx)
    assert isinstance(result, IOSuccess)
    updated_ctx = unsafe_perform_io(result.unwrap())
    assert "verify_ruff" in updated_ctx.outputs
    assert updated_ctx.outputs["verify_ruff"] is verify_result


def test_run_ruff_step_tool_failure(
    mocker: MockerFixture,
) -> None:
    """ruff fails: IOFailure with PipelineError."""
    verify_result = VerifyResult(
        tool_name="ruff",
        passed=False,
        errors=["adws/io_ops.py:5:1: E302 expected 2 blank"],
        raw_output="adws/io_ops.py:5:1: E302 expected 2 blank",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_ruff_step.run_ruff_check",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_ruff_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "run_ruff_step"
    assert error.error_type == "VerifyFailed"
    assert "ruff check failed" in error.message
    assert "1 error(s)" in error.message
    assert error.context["tool_name"] == "ruff"
    assert error.context["errors"] == [
        "adws/io_ops.py:5:1: E302 expected 2 blank",
    ]
    assert error.context["raw_output"] == (
        "adws/io_ops.py:5:1: E302 expected 2 blank"
    )
    # Original context unchanged on failure
    assert ctx.outputs == {}


def test_run_ruff_step_io_failure(
    mocker: MockerFixture,
) -> None:
    """io_ops IOFailure propagates through bind."""
    io_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="Command not found",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_ruff_step.run_ruff_check",
        return_value=IOFailure(io_error),
    )
    ctx = WorkflowContext()
    result = run_ruff_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is io_error
    assert error.error_type == "FileNotFoundError"

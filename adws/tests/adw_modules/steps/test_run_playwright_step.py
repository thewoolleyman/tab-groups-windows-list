"""Tests for run_playwright_step step module."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    run_playwright_step as pkg_run_playwright_step,
)
from adws.adw_modules.steps.run_playwright_step import (
    run_playwright_step,
)
from adws.adw_modules.types import VerifyResult, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_playwright_step_importable_from_steps_package() -> None:
    """run_playwright_step is importable from steps package."""
    assert pkg_run_playwright_step is run_playwright_step


def test_run_playwright_step_success(
    mocker: MockerFixture,
) -> None:
    """Playwright passes: VerifyResult in context outputs."""
    verify_result = VerifyResult(
        tool_name="playwright",
        passed=True,
        errors=[],
        raw_output="all e2e tests passed",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_playwright_step"
        ".run_playwright_tests",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_playwright_step(ctx)
    assert isinstance(result, IOSuccess)
    updated_ctx = unsafe_perform_io(result.unwrap())
    assert "verify_playwright" in updated_ctx.outputs
    assert (
        updated_ctx.outputs["verify_playwright"]
        is verify_result
    )


def test_run_playwright_step_tool_failure(
    mocker: MockerFixture,
) -> None:
    """Playwright fails: IOFailure with PipelineError."""
    verify_result = VerifyResult(
        tool_name="playwright",
        passed=False,
        errors=["Error: test failed"],
        raw_output="Error: test failed\n1 test failed",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_playwright_step"
        ".run_playwright_tests",
        return_value=IOSuccess(verify_result),
    )
    ctx = WorkflowContext()
    result = run_playwright_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.step_name == "run_playwright_step"
    assert error.error_type == "VerifyFailed"
    assert "playwright check failed" in error.message
    assert "1 error(s)" in error.message
    assert error.context["tool_name"] == "playwright"
    assert error.context["errors"] == [
        "Error: test failed",
    ]
    assert error.context["raw_output"] == (
        "Error: test failed\n1 test failed"
    )
    # Original context unchanged on failure
    assert ctx.outputs == {}


def test_run_playwright_step_io_failure(
    mocker: MockerFixture,
) -> None:
    """io_ops IOFailure propagates through bind."""
    io_error = PipelineError(
        step_name="io_ops.run_shell_command",
        error_type="FileNotFoundError",
        message="Command not found",
    )
    mocker.patch(
        "adws.adw_modules.steps.run_playwright_step"
        ".run_playwright_tests",
        return_value=IOFailure(io_error),
    )
    ctx = WorkflowContext()
    result = run_playwright_step(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error is io_error
    assert error.error_type == "FileNotFoundError"

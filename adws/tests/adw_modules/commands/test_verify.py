"""Tests for /verify command entry point (Story 4.2)."""
from __future__ import annotations

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.types import Workflow
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import VerifyResult, WorkflowContext

# --- Task 1: VerifyCommandResult ---


def test_verify_command_result_construction() -> None:
    """VerifyCommandResult can be constructed with all fields."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
    )

    result = VerifyCommandResult(
        success=True,
        tool_results={"jest": True, "ruff": True},
        summary="All checks passed",
    )
    assert result.success is True
    assert result.tool_results == {"jest": True, "ruff": True}
    assert result.summary == "All checks passed"
    assert result.failure_details == []


def test_verify_command_result_with_failure_details() -> None:
    """VerifyCommandResult stores failure_details."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
    )

    result = VerifyCommandResult(
        success=False,
        tool_results={"jest": False},
        summary="1 check failed",
        failure_details=["jest: 2 error(s)"],
    )
    assert result.success is False
    assert result.failure_details == ["jest: 2 error(s)"]


def test_verify_command_result_immutable() -> None:
    """VerifyCommandResult is frozen (immutable)."""
    import pytest  # noqa: PLC0415

    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
    )

    result = VerifyCommandResult(
        success=True,
        tool_results={},
        summary="ok",
    )
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


# --- Task 2: format_verify_success ---


def test_format_verify_success_all_tools_pass() -> None:
    """format_verify_success with all 4 tools passing."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_success,
    )

    ctx = WorkflowContext(
        outputs={
            "verify_jest": VerifyResult(
                tool_name="jest", passed=True,
            ),
            "verify_playwright": VerifyResult(
                tool_name="playwright", passed=True,
            ),
            "verify_mypy": VerifyResult(
                tool_name="mypy", passed=True,
            ),
            "verify_ruff": VerifyResult(
                tool_name="ruff", passed=True,
            ),
        },
    )
    result = format_verify_success(ctx)
    assert result.success is True
    assert len(result.tool_results) == 4
    assert all(result.tool_results.values())
    assert "jest" in result.tool_results
    assert "playwright" in result.tool_results
    assert "mypy" in result.tool_results
    assert "ruff" in result.tool_results
    assert "passed" in result.summary.lower()
    assert result.failure_details == []


def test_format_verify_success_partial_outputs() -> None:
    """format_verify_success with only some tools in outputs."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_success,
    )

    ctx = WorkflowContext(
        outputs={
            "verify_jest": VerifyResult(
                tool_name="jest", passed=True,
            ),
            "other_key": "not a VerifyResult",
        },
    )
    result = format_verify_success(ctx)
    assert result.success is True
    assert len(result.tool_results) == 1
    assert result.tool_results["jest"] is True
    assert result.failure_details == []


# --- Task 3: format_verify_failure ---


def test_format_verify_failure_multiple_tools() -> None:
    """format_verify_failure with multiple tool failures."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_failure,
    )

    error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 2 error(s)",
        context={
            "tool_name": "jest",
            "errors": ["FAIL src/a.test.ts"],
            "raw_output": "jest output",
            "always_run_failures": [
                {
                    "step_name": "run_ruff_step",
                    "error_type": "VerifyFailed",
                    "message": "ruff check failed: 1 error(s)",
                    "context": {
                        "tool_name": "ruff",
                        "errors": ["file.py:1:1: E501"],
                        "raw_output": "ruff output",
                    },
                },
            ],
        },
    )
    result = format_verify_failure(error)
    assert result.success is False
    assert result.tool_results["jest"] is False
    assert result.tool_results["ruff"] is False
    assert len(result.failure_details) >= 2
    assert any("jest" in d for d in result.failure_details)
    assert any("ruff" in d for d in result.failure_details)


def test_format_verify_failure_single_tool() -> None:
    """format_verify_failure with only one tool failing."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_failure,
    )

    error = PipelineError(
        step_name="run_ruff_step",
        error_type="VerifyFailed",
        message="ruff check failed: 1 error(s)",
        context={
            "tool_name": "ruff",
            "errors": ["file.py:1:1: E501"],
            "raw_output": "ruff output",
        },
    )
    result = format_verify_failure(error)
    assert result.success is False
    assert result.tool_results == {"ruff": False}
    assert len(result.failure_details) == 1
    assert "ruff" in result.failure_details[0]


def test_format_verify_failure_no_always_run() -> None:
    """format_verify_failure with simple error, no aggregated failures."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_failure,
    )

    error = PipelineError(
        step_name="verify_engine",
        error_type="EngineError",
        message="Unexpected engine error",
        context={},
    )
    result = format_verify_failure(error)
    assert result.success is False
    assert result.tool_results == {}
    assert len(result.failure_details) == 1
    assert "Unexpected engine error" in result.failure_details[0]


def test_format_verify_failure_malformed_arf_entries() -> None:
    """format_verify_failure handles malformed always_run_failures."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_failure,
    )

    error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed",
        context={
            "tool_name": "jest",
            "errors": ["FAIL test"],
            "always_run_failures": [
                "not a dict",
                {"context": "not a dict either"},
                {"context": {"no_tool_name": True}},
                {
                    "context": {
                        "tool_name": "ruff",
                        "errors": ["err"],
                    },
                },
            ],
        },
    )
    result = format_verify_failure(error)
    assert result.success is False
    # Only jest (primary) and ruff (valid arf) are in results
    assert result.tool_results == {
        "jest": False,
        "ruff": False,
    }
    assert len(result.failure_details) == 2


def test_format_verify_failure_compatible_with_feedback() -> None:
    """Failure report is compatible with feedback accumulation."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        format_verify_failure,
    )

    error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 2 error(s)",
        context={
            "tool_name": "jest",
            "errors": [
                "FAIL src/a.test.ts",
                "FAIL src/b.test.ts",
            ],
            "raw_output": "jest output",
        },
    )
    result = format_verify_failure(error)
    # Failure details include tool name and error list
    detail = result.failure_details[0]
    assert "jest" in detail
    assert "FAIL" in detail


# --- Task 4: run_verify_command ---


def test_run_verify_command_success(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_verify_command returns IOSuccess with success result."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
        run_verify_command,
    )

    fake_wf = Workflow(
        name="verify", description="test", steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={
            "verify_jest": VerifyResult(
                tool_name="jest", passed=True,
            ),
            "verify_ruff": VerifyResult(
                tool_name="ruff", passed=True,
            ),
        },
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    ctx = WorkflowContext()
    result = run_verify_command(ctx)
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyCommandResult)
    assert vr.success is True
    assert vr.tool_results["jest"] is True
    assert vr.tool_results["ruff"] is True


def test_run_verify_command_tool_failure(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_verify_command returns IOSuccess with failure result on tool failure."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
        run_verify_command,
    )

    fake_wf = Workflow(
        name="verify", description="test", steps=[],
    )
    tool_error = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 1 error(s)",
        context={
            "tool_name": "jest",
            "errors": ["FAIL src/a.test.ts"],
            "raw_output": "jest output",
        },
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(tool_error),
    )
    ctx = WorkflowContext()
    result = run_verify_command(ctx)
    # Tool failure -> IOSuccess with success=False
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyCommandResult)
    assert vr.success is False
    assert vr.tool_results["jest"] is False


def test_run_verify_command_workflow_load_failure(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """run_verify_command propagates IOFailure on load failure."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        run_verify_command,
    )

    load_err = PipelineError(
        step_name="io_ops.load_command_workflow",
        error_type="WorkflowNotFoundError",
        message="Workflow 'verify' is not registered",
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOFailure(load_err),
    )
    ctx = WorkflowContext()
    result = run_verify_command(ctx)
    assert isinstance(result, IOFailure)
    err = unsafe_perform_io(result.failure())
    assert err is load_err


# --- Task 8: Integration tests ---


def test_integration_verify_all_tools_pass(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """Integration: run_verify_command with all 4 tools passing."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
        run_verify_command,
    )

    fake_wf = Workflow(
        name="verify", description="test", steps=[],
    )
    result_ctx = WorkflowContext(
        outputs={
            "verify_jest": VerifyResult(
                tool_name="jest", passed=True,
            ),
            "verify_playwright": VerifyResult(
                tool_name="playwright", passed=True,
            ),
            "verify_mypy": VerifyResult(
                tool_name="mypy", passed=True,
            ),
            "verify_ruff": VerifyResult(
                tool_name="ruff", passed=True,
            ),
        },
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOSuccess(result_ctx),
    )
    ctx = WorkflowContext()
    result = run_verify_command(ctx)
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyCommandResult)
    assert vr.success is True
    assert len(vr.tool_results) == 4
    assert all(vr.tool_results.values())
    assert "passed" in vr.summary.lower()
    assert vr.failure_details == []


def test_integration_verify_mixed_failures(  # type: ignore[no-untyped-def]
    mocker,
) -> None:
    """Integration: jest+ruff fail, playwright+mypy pass."""
    from adws.adw_modules.commands.verify import (  # noqa: PLC0415
        VerifyCommandResult,
        run_verify_command,
    )

    fake_wf = Workflow(
        name="verify", description="test", steps=[],
    )
    # The engine would return this when jest fails first
    # and ruff fails as an always_run step
    tool_err = PipelineError(
        step_name="run_jest_step",
        error_type="VerifyFailed",
        message="jest check failed: 1 error(s)",
        context={
            "tool_name": "jest",
            "errors": ["FAIL src/a.test.ts"],
            "raw_output": "jest output",
            "always_run_failures": [
                {
                    "step_name": "run_ruff_step",
                    "error_type": "VerifyFailed",
                    "message": (
                        "ruff check failed: 1 error(s)"
                    ),
                    "context": {
                        "tool_name": "ruff",
                        "errors": ["file.py:1:1: E501"],
                        "raw_output": "ruff output",
                    },
                },
            ],
        },
    )
    mocker.patch(
        "adws.adw_modules.io_ops.load_command_workflow",
        return_value=IOSuccess(fake_wf),
    )
    mocker.patch(
        "adws.adw_modules.io_ops.execute_command_workflow",
        return_value=IOFailure(tool_err),
    )
    ctx = WorkflowContext()
    result = run_verify_command(ctx)
    assert isinstance(result, IOSuccess)
    vr = unsafe_perform_io(result.unwrap())
    assert isinstance(vr, VerifyCommandResult)
    assert vr.success is False
    assert vr.tool_results["jest"] is False
    assert vr.tool_results["ruff"] is False
    assert len(vr.failure_details) == 2
    assert any("jest" in d for d in vr.failure_details)
    assert any("ruff" in d for d in vr.failure_details)

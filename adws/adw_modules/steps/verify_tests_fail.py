"""Verify tests fail step -- RED gate for TDD workflow."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from adws.adw_modules.types import (
        ShellResult,
        WorkflowContext,
    )

VALID_RED_FAILURES: frozenset[str] = frozenset({
    "ImportError",
    "AssertionError",
    "NotImplementedError",
    "AttributeError",
})

INVALID_RED_FAILURES: frozenset[str] = frozenset({
    "SyntaxError",
    "IndentationError",
    "NameError",
})

RED_GATE_PYTEST_COMMAND: str = (
    "uv run pytest adws/tests/"
    " -m 'not enemy' --no-header -q"
)

_ERROR_TYPE_PATTERN = re.compile(
    r"^E\s+(\w+Error)\b", re.MULTILINE,
)
_FAILED_COUNT_PATTERN = re.compile(r"(\d+) failed")
_NO_TESTS_RAN_PATTERN = re.compile(r"no tests ran")
_PASSED_PATTERN = re.compile(r"(\d+) passed")
_ERROR_COUNT_PATTERN = re.compile(r"(\d+) errors? in ")


@dataclass(frozen=True)
class ParsedTestResult:
    """Parsed result from pytest output analysis."""

    tests_ran: bool
    all_passed: bool
    failure_types: frozenset[str]
    failure_count: int
    raw_output: str


@dataclass(frozen=True)
class FailureClassification:
    """Classification of test failure types."""

    is_valid_red: bool
    valid_types: frozenset[str]
    invalid_types: frozenset[str]


def _parse_pytest_output(
    stdout: str,
    stderr: str,
) -> ParsedTestResult:
    """Parse pytest output to extract failure information.

    Pure function: extracts failure types, counts, and
    pass/fail status from pytest stdout and stderr.
    """
    combined = stdout + "\n" + stderr
    raw_output = combined.strip()

    if not stdout.strip() and not stderr.strip():
        return ParsedTestResult(
            tests_ran=False,
            all_passed=False,
            failure_types=frozenset(),
            failure_count=0,
            raw_output=raw_output,
        )

    # Check for "no tests ran"
    if _NO_TESTS_RAN_PATTERN.search(combined):
        return ParsedTestResult(
            tests_ran=False,
            all_passed=False,
            failure_types=frozenset(),
            failure_count=0,
            raw_output=raw_output,
        )

    # Extract error types from E lines
    error_types = frozenset(
        _ERROR_TYPE_PATTERN.findall(combined),
    )

    # Extract failure count from summary
    failed_match = _FAILED_COUNT_PATTERN.search(combined)
    failure_count = (
        int(failed_match.group(1))
        if failed_match
        else 0
    )

    # Check if errors occurred (collection errors count)
    error_count_match = _ERROR_COUNT_PATTERN.search(
        combined,
    )
    if not failed_match and error_count_match:
        failure_count = int(error_count_match.group(1))

    # Determine if all passed
    passed_match = _PASSED_PATTERN.search(combined)
    all_passed = (
        passed_match is not None
        and not failed_match
        and not error_types
        and not error_count_match
    )

    # tests_ran is True if we have passed/failed/error
    tests_ran = bool(
        passed_match
        or failed_match
        or error_types
        or error_count_match,
    )

    return ParsedTestResult(
        tests_ran=tests_ran,
        all_passed=all_passed,
        failure_types=error_types,
        failure_count=failure_count,
        raw_output=raw_output,
    )


def _classify_failures(
    parsed: ParsedTestResult,
) -> FailureClassification:
    """Classify failure types as valid or invalid RED.

    Pure function: any invalid type makes the entire
    classification invalid. Unknown types are treated
    as valid (conservative).
    """
    invalid_types = parsed.failure_types & INVALID_RED_FAILURES
    valid_types = parsed.failure_types - INVALID_RED_FAILURES
    is_valid_red = len(invalid_types) == 0

    return FailureClassification(
        is_valid_red=is_valid_red,
        valid_types=frozenset(valid_types),
        invalid_types=frozenset(invalid_types),
    )


def _interpret_shell_result(
    shell_result: ShellResult,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Interpret shell result for the RED gate.

    Parses pytest output, classifies failures, and
    returns IOSuccess or IOFailure based on classification.
    """
    parsed = _parse_pytest_output(
        shell_result.stdout, shell_result.stderr,
    )

    if not parsed.tests_ran:
        return IOFailure(
            PipelineError(
                step_name="verify_tests_fail",
                error_type="NoTestsRan",
                message=(
                    "No tests were discovered or ran."
                    " Ensure test files exist and are"
                    " collected by pytest."
                ),
                context={
                    "return_code": (
                        shell_result.return_code
                    ),
                    "raw_output": parsed.raw_output,
                },
            ),
        )

    if parsed.all_passed:
        return IOFailure(
            PipelineError(
                step_name="verify_tests_fail",
                error_type="TestsPassedInRedPhase",
                message=(
                    "Tests passed unexpectedly in RED"
                    " phase. Tests should fail with"
                    " expected errors (ImportError,"
                    " AssertionError, etc.) before"
                    " proceeding to GREEN."
                ),
                context={
                    "return_code": (
                        shell_result.return_code
                    ),
                    "raw_output": parsed.raw_output,
                },
            ),
        )

    classification = _classify_failures(parsed)

    if not classification.is_valid_red:
        invalid_list = sorted(classification.invalid_types)
        return IOFailure(
            PipelineError(
                step_name="verify_tests_fail",
                error_type="InvalidRedFailure",
                message=(
                    "Tests failed with invalid failure"
                    f" types: {invalid_list}. These"
                    " indicate broken test code, not"
                    " valid RED failures. Fix the"
                    " tests before proceeding."
                ),
                context={
                    "invalid_types": invalid_list,
                    "valid_types": sorted(
                        classification.valid_types,
                    ),
                    "raw_output": parsed.raw_output,
                },
            ),
        )

    failure_types_list = sorted(parsed.failure_types)
    return IOSuccess(
        ctx.with_updates(
            outputs={
                "red_gate_passed": True,
                "failure_types": failure_types_list,
                "failure_count": parsed.failure_count,
            },
        ),
    )


def verify_tests_fail(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute RED gate: verify tests fail for expected reasons.

    Runs the test suite via io_ops.run_shell_command,
    parses pytest output, classifies failure types,
    and returns IOSuccess only if failures are valid RED.
    """
    shell_result = io_ops.run_shell_command(
        RED_GATE_PYTEST_COMMAND,
    )

    def _on_failure(
        error: PipelineError,
    ) -> IOResult[ShellResult, PipelineError]:
        return IOFailure(
            PipelineError(
                step_name="verify_tests_fail",
                error_type=error.error_type,
                message=error.message,
                context=error.context,
            ),
        )

    return (
        shell_result
        .lash(_on_failure)
        .bind(
            lambda sr: _interpret_shell_result(sr, ctx),
        )
    )

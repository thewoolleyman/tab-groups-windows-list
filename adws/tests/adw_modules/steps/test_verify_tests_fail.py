"""Tests for verify_tests_fail step (RED gate)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import _STEP_REGISTRY
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    verify_tests_fail as vtf_from_init,
)
from adws.adw_modules.steps.verify_tests_fail import (
    INVALID_RED_FAILURES,
    RED_GATE_PYTEST_COMMAND,
    VALID_RED_FAILURES,
    FailureClassification,
    ParsedTestResult,
    _classify_failures,
    _parse_pytest_output,
    verify_tests_fail,
)
from adws.adw_modules.types import (
    ShellResult,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Pytest output fixtures ---

_IMPORT_ERROR_OUTPUT = (
    "adws/tests/steps/test_new_step.py:3:"
    " in <module>\n"
    "    from adws.adw_modules.steps.new_step"
    " import new_step\n"
    "E   ImportError: No module named"
    " 'adws.adw_modules.steps.new_step'\n"
    "ERRORS\n"
    "1 error in 0.05s\n"
)

_ASSERTION_ERROR_OUTPUT = (
    "FAILED adws/tests/steps/test_new_step.py"
    "::test_new_step_returns_success\n"
    "adws/tests/steps/test_new_step.py:15:"
    " in test_new_step_returns_success\n"
    "    assert result == expected\n"
    "E   AssertionError: assert None =="
    " 'expected'\n"
    "1 failed in 0.10s\n"
)

_MULTI_FAILURE_OUTPUT = (
    "adws/tests/steps/test_new_step.py:3:"
    " in <module>\n"
    "E   ImportError: No module named"
    " 'adws.adw_modules.steps.new_step'\n"
    "FAILED adws/tests/steps/test_other.py"
    "::test_other\n"
    "E   AssertionError: assert False\n"
    "2 failed in 0.20s\n"
)

_SYNTAX_ERROR_OUTPUT = (
    "ERRORS\n"
    "_ ERROR collecting"
    " adws/tests/steps/test_broken.py _\n"
    "adws/tests/steps/test_broken.py:5:"
    " in <module>\n"
    "E     SyntaxError: invalid syntax\n"
    "1 error in 0.02s\n"
)

_ALL_PASSED_OUTPUT = (
    "450 passed, 3 deselected in 2.50s\n"
)

_NO_TESTS_RAN_OUTPUT = (
    "no tests ran in 0.01s\n"
)

_NOT_IMPLEMENTED_OUTPUT = (
    "FAILED adws/tests/steps/test_stub.py"
    "::test_stub_raises\n"
    "E   NotImplementedError\n"
    "1 failed in 0.10s\n"
)

_MIXED_VALID_INVALID_OUTPUT = (
    "adws/tests/steps/test_new_step.py:3:"
    " in <module>\n"
    "E   ImportError: No module named 'foo'\n"
    "ERRORS\n"
    "E     SyntaxError: invalid syntax\n"
    "2 failed in 0.10s\n"
)


# --- Task 1: Constant tests ---


class TestValidRedFailures:
    """Tests for VALID_RED_FAILURES constant."""

    def test_valid_red_failures_is_frozenset(self) -> None:
        """VALID_RED_FAILURES is a frozenset of strings."""
        assert isinstance(VALID_RED_FAILURES, frozenset)

    def test_valid_red_failures_contains_import_error(
        self,
    ) -> None:
        """VALID_RED_FAILURES contains ImportError."""
        assert "ImportError" in VALID_RED_FAILURES

    def test_valid_red_failures_contains_assertion_error(
        self,
    ) -> None:
        """VALID_RED_FAILURES contains AssertionError."""
        assert "AssertionError" in VALID_RED_FAILURES

    def test_valid_red_failures_contains_not_implemented(
        self,
    ) -> None:
        """VALID_RED_FAILURES contains NotImplementedError."""
        assert "NotImplementedError" in VALID_RED_FAILURES

    def test_valid_red_failures_contains_attribute_error(
        self,
    ) -> None:
        """VALID_RED_FAILURES contains AttributeError."""
        assert "AttributeError" in VALID_RED_FAILURES


class TestInvalidRedFailures:
    """Tests for INVALID_RED_FAILURES constant."""

    def test_invalid_red_failures_is_frozenset(self) -> None:
        """INVALID_RED_FAILURES is a frozenset of strings."""
        assert isinstance(INVALID_RED_FAILURES, frozenset)

    def test_invalid_red_failures_contains_syntax_error(
        self,
    ) -> None:
        """INVALID_RED_FAILURES contains SyntaxError."""
        assert "SyntaxError" in INVALID_RED_FAILURES

    def test_invalid_red_failures_contains_indentation_error(
        self,
    ) -> None:
        """INVALID_RED_FAILURES contains IndentationError."""
        assert "IndentationError" in INVALID_RED_FAILURES

    def test_invalid_red_failures_contains_name_error(
        self,
    ) -> None:
        """INVALID_RED_FAILURES contains NameError."""
        assert "NameError" in INVALID_RED_FAILURES


# --- Task 2: _parse_pytest_output tests ---


class TestParsedTestResult:
    """Tests for ParsedTestResult frozen dataclass."""

    def test_parsed_test_result_is_frozen(self) -> None:
        """ParsedTestResult is a frozen dataclass."""
        result = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset({"ImportError"}),
            failure_count=1,
            raw_output="test output",
        )
        assert result.tests_ran is True
        assert result.all_passed is False
        assert result.failure_types == frozenset(
            {"ImportError"},
        )
        assert result.failure_count == 1
        assert result.raw_output == "test output"


class TestParsePytestOutput:
    """Tests for _parse_pytest_output helper."""

    def test_parse_pytest_output_import_error(
        self,
    ) -> None:
        """Parses ImportError from pytest output."""
        result = _parse_pytest_output(
            _IMPORT_ERROR_OUTPUT, "",
        )
        assert result.tests_ran is True
        assert result.all_passed is False
        assert "ImportError" in result.failure_types
        assert result.failure_count >= 1

    def test_parse_pytest_output_multiple_failure_types(
        self,
    ) -> None:
        """Parses multiple failure types."""
        result = _parse_pytest_output(
            _MULTI_FAILURE_OUTPUT, "",
        )
        assert result.tests_ran is True
        assert result.all_passed is False
        assert "ImportError" in result.failure_types
        assert "AssertionError" in result.failure_types

    def test_parse_pytest_output_all_passed(self) -> None:
        """Detects all tests passed."""
        result = _parse_pytest_output(
            _ALL_PASSED_OUTPUT, "",
        )
        assert result.tests_ran is True
        assert result.all_passed is True
        assert result.failure_types == frozenset()
        assert result.failure_count == 0

    def test_parse_pytest_output_syntax_error(
        self,
    ) -> None:
        """Detects SyntaxError from collection error."""
        result = _parse_pytest_output(
            _SYNTAX_ERROR_OUTPUT, "",
        )
        assert "SyntaxError" in result.failure_types

    def test_parse_pytest_output_no_tests_ran(
        self,
    ) -> None:
        """Detects no tests ran."""
        result = _parse_pytest_output(
            _NO_TESTS_RAN_OUTPUT, "",
        )
        assert result.tests_ran is False

    def test_parse_pytest_output_empty(self) -> None:
        """Handles empty stdout and stderr."""
        result = _parse_pytest_output("", "")
        assert result.tests_ran is False
        assert result.all_passed is False
        assert result.failure_types == frozenset()
        assert result.failure_count == 0

    def test_parse_pytest_output_not_implemented_error(
        self,
    ) -> None:
        """Detects NotImplementedError in traceback."""
        result = _parse_pytest_output(
            _NOT_IMPLEMENTED_OUTPUT, "",
        )
        assert "NotImplementedError" in result.failure_types

    def test_parse_pytest_output_raw_output_captured(
        self,
    ) -> None:
        """raw_output captures combined stdout+stderr."""
        result = _parse_pytest_output(
            "some stdout", "some stderr",
        )
        assert "some stdout" in result.raw_output
        assert "some stderr" in result.raw_output
        assert result.tests_ran is False
        assert result.all_passed is False


# --- FailureClassification dataclass tests ---


class TestFailureClassification:
    """Tests for FailureClassification frozen dataclass."""

    def test_failure_classification_is_frozen(
        self,
    ) -> None:
        """FailureClassification is a frozen dataclass."""
        result = FailureClassification(
            is_valid_red=True,
            valid_types=frozenset({"ImportError"}),
            invalid_types=frozenset(),
        )
        assert result.is_valid_red is True
        assert result.valid_types == frozenset(
            {"ImportError"},
        )
        assert result.invalid_types == frozenset()


# --- Task 3: _classify_failures tests ---


class TestClassifyFailures:
    """Tests for _classify_failures helper."""

    def test_classify_failures_valid_import_error(
        self,
    ) -> None:
        """ImportError is classified as valid RED."""
        parsed = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset({"ImportError"}),
            failure_count=1,
            raw_output="",
        )
        result = _classify_failures(parsed)
        assert isinstance(result, FailureClassification)
        assert result.is_valid_red is True
        assert result.invalid_types == frozenset()
        assert "ImportError" in result.valid_types

    def test_classify_failures_invalid_syntax_error(
        self,
    ) -> None:
        """SyntaxError is classified as invalid RED."""
        parsed = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset({"SyntaxError"}),
            failure_count=1,
            raw_output="",
        )
        result = _classify_failures(parsed)
        assert result.is_valid_red is False
        assert "SyntaxError" in result.invalid_types
        assert result.valid_types == frozenset()

    def test_classify_failures_mixed_types(self) -> None:
        """Mixed valid+invalid is classified as invalid."""
        parsed = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset(
                {"ImportError", "SyntaxError"},
            ),
            failure_count=2,
            raw_output="",
        )
        result = _classify_failures(parsed)
        assert result.is_valid_red is False
        assert "SyntaxError" in result.invalid_types
        assert "ImportError" in result.valid_types

    def test_classify_failures_multiple_valid(
        self,
    ) -> None:
        """Multiple valid types is valid RED."""
        parsed = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset(
                {"AssertionError", "NotImplementedError"},
            ),
            failure_count=2,
            raw_output="",
        )
        result = _classify_failures(parsed)
        assert result.is_valid_red is True
        assert "AssertionError" in result.valid_types
        assert "NotImplementedError" in result.valid_types
        assert result.invalid_types == frozenset()

    def test_classify_failures_unknown_type(self) -> None:
        """Unknown type (RuntimeError) treated as valid."""
        parsed = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset({"RuntimeError"}),
            failure_count=1,
            raw_output="",
        )
        result = _classify_failures(parsed)
        assert result.is_valid_red is True
        assert "RuntimeError" in result.valid_types
        assert result.invalid_types == frozenset()

    def test_classify_failures_empty(self) -> None:
        """Empty failure_types is valid (no invalid)."""
        parsed = ParsedTestResult(
            tests_ran=True,
            all_passed=False,
            failure_types=frozenset(),
            failure_count=0,
            raw_output="",
        )
        result = _classify_failures(parsed)
        assert result.is_valid_red is True
        assert result.valid_types == frozenset()
        assert result.invalid_types == frozenset()


# --- Task 4: verify_tests_fail step tests ---


class TestVerifyTestsFail:
    """Tests for verify_tests_fail step function."""

    def test_verify_tests_fail_valid_red(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Valid RED: ImportError -> IOSuccess."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_IMPORT_ERROR_OUTPUT,
                    stderr="",
                    command="pytest",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["red_gate_passed"] is True
        assert "ImportError" in updated.outputs[
            "failure_types"
        ]

    def test_verify_tests_fail_tests_passed(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Tests pass -> IOFailure(TestsPassedInRedPhase)."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout=_ALL_PASSED_OUTPUT,
                    stderr="",
                    command="pytest",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "verify_tests_fail"
        assert err.error_type == "TestsPassedInRedPhase"

    def test_verify_tests_fail_invalid_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SyntaxError -> IOFailure(InvalidRedFailure)."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_SYNTAX_ERROR_OUTPUT,
                    stderr="",
                    command="pytest",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "verify_tests_fail"
        assert err.error_type == "InvalidRedFailure"
        assert "SyntaxError" in err.message

    def test_verify_tests_fail_shell_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Shell failure -> IOFailure propagated."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_shell_command",
                    error_type="ShellExecutionError",
                    message="pytest not found",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "verify_tests_fail"

    def test_verify_tests_fail_mixed_types(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Mixed valid+invalid -> IOFailure."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_MIXED_VALID_INVALID_OUTPUT,
                    stderr="",
                    command="pytest",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "InvalidRedFailure"

    def test_verify_tests_fail_no_tests_ran(
        self,
        mocker: MockerFixture,
    ) -> None:
        """No tests ran -> IOFailure(NoTestsRan)."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=5,
                    stdout=_NO_TESTS_RAN_OUTPUT,
                    stderr="",
                    command="pytest",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "verify_tests_fail"
        assert err.error_type == "NoTestsRan"

    def test_verify_tests_fail_assertion_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """AssertionError -> IOSuccess."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_ASSERTION_ERROR_OUTPUT,
                    stderr="",
                    command="pytest",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["red_gate_passed"] is True
        assert "AssertionError" in updated.outputs[
            "failure_types"
        ]


# --- Task 5: RED_GATE_PYTEST_COMMAND tests ---


class TestRedGatePytestCommand:
    """Tests for RED_GATE_PYTEST_COMMAND constant."""

    def test_red_gate_pytest_command_constant(
        self,
    ) -> None:
        """Command contains uv run pytest and not enemy."""
        assert "uv run pytest" in RED_GATE_PYTEST_COMMAND
        assert (
            "-m 'not enemy'" in RED_GATE_PYTEST_COMMAND
        )

    def test_verify_tests_fail_command_used(
        self,
        mocker: MockerFixture,
    ) -> None:
        """verify_tests_fail calls run_shell_command."""
        mock_shell = mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_IMPORT_ERROR_OUTPUT,
                    stderr="",
                    command=RED_GATE_PYTEST_COMMAND,
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        verify_tests_fail(ctx)

        mock_shell.assert_called_once_with(
            RED_GATE_PYTEST_COMMAND,
        )


# --- Task 6: Registration tests ---


class TestVerifyTestsFailRegistration:
    """Tests for step registration and importability."""

    def test_verify_tests_fail_importable(self) -> None:
        """verify_tests_fail importable from steps."""
        assert callable(vtf_from_init)

    def test_verify_tests_fail_step_registry(
        self,
    ) -> None:
        """verify_tests_fail is in _STEP_REGISTRY."""
        assert "verify_tests_fail" in _STEP_REGISTRY
        assert (
            _STEP_REGISTRY["verify_tests_fail"]
            is verify_tests_fail
        )


# --- Task 7: Integration tests ---


class TestVerifyTestsFailIntegration:
    """Integration tests for the full step flow."""

    def test_integration_valid_red(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: ImportError -> IOSuccess."""
        mock_shell = mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_IMPORT_ERROR_OUTPUT,
                    stderr="",
                    command=RED_GATE_PYTEST_COMMAND,
                ),
            ),
        )
        ctx = WorkflowContext(
            inputs={
                "issue_id": "BEADS-123",
                "test_files": [
                    "adws/tests/steps/test_new.py",
                ],
                "red_phase_complete": True,
            },
        )
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["red_gate_passed"] is True
        assert "ImportError" in updated.outputs[
            "failure_types"
        ]
        mock_shell.assert_called_once_with(
            RED_GATE_PYTEST_COMMAND,
        )

    def test_integration_tests_passed(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: all passed -> IOFailure."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout=_ALL_PASSED_OUTPUT,
                    stderr="",
                    command=RED_GATE_PYTEST_COMMAND,
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "TestsPassedInRedPhase"

    def test_integration_syntax_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: SyntaxError -> IOFailure."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=1,
                    stdout=_SYNTAX_ERROR_OUTPUT,
                    stderr="",
                    command=RED_GATE_PYTEST_COMMAND,
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "InvalidRedFailure"
        assert "SyntaxError" in err.message

    def test_integration_shell_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: shell failure -> IOFailure."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_shell_command",
                    error_type="ShellExecutionError",
                    message="Command not found",
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "verify_tests_fail"

    def test_integration_no_tests_ran(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: no tests ran -> IOFailure."""
        mocker.patch(
            "adws.adw_modules.steps.verify_tests_fail"
            ".io_ops.run_shell_command",
            return_value=IOSuccess(
                ShellResult(
                    return_code=5,
                    stdout=_NO_TESTS_RAN_OUTPUT,
                    stderr="",
                    command=RED_GATE_PYTEST_COMMAND,
                ),
            ),
        )
        ctx = WorkflowContext(inputs={})
        result = verify_tests_fail(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "NoTestsRan"

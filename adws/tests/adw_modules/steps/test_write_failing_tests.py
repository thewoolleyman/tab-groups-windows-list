"""Tests for write_failing_tests step (RED phase TDD agent)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import _STEP_REGISTRY
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    write_failing_tests as write_failing_tests_from_init,
)
from adws.adw_modules.steps.write_failing_tests import (
    RED_PHASE_SYSTEM_PROMPT,
    _build_red_phase_request,
    _extract_test_files,
    write_failing_tests,
)
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsRequest,
    AdwsResponse,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 1: RED_PHASE_SYSTEM_PROMPT tests ---


class TestRedPhaseSystemPrompt:
    """Tests for the RED_PHASE_SYSTEM_PROMPT constant."""

    def test_red_phase_system_prompt_not_empty(self) -> None:
        """Prompt constant is a non-empty string."""
        assert isinstance(RED_PHASE_SYSTEM_PROMPT, str)
        assert len(RED_PHASE_SYSTEM_PROMPT) > 0

    def test_red_phase_system_prompt_contains_write_tests_only(
        self,
    ) -> None:
        """Prompt instructs agent to write tests only."""
        assert (
            "write tests"
            in RED_PHASE_SYSTEM_PROMPT.lower()
        )
        assert (
            "do not implement"
            in RED_PHASE_SYSTEM_PROMPT.lower()
        )

    def test_red_phase_system_prompt_contains_red_annotation(
        self,
    ) -> None:
        """Prompt requires RED: annotation on each test."""
        assert "RED:" in RED_PHASE_SYSTEM_PROMPT

    def test_red_phase_system_prompt_contains_expected_failures(
        self,
    ) -> None:
        """Prompt lists expected failure types."""
        assert "ImportError" in RED_PHASE_SYSTEM_PROMPT
        assert "AssertionError" in RED_PHASE_SYSTEM_PROMPT
        assert "NotImplementedError" in RED_PHASE_SYSTEM_PROMPT

    def test_red_phase_system_prompt_contains_test_dir(
        self,
    ) -> None:
        """Prompt mentions the adws/tests/ directory."""
        assert "adws/tests/" in RED_PHASE_SYSTEM_PROMPT

    def test_red_phase_system_prompt_contains_mock_io_ops(
        self,
    ) -> None:
        """Prompt instructs mocking at io_ops boundary."""
        assert "io_ops" in RED_PHASE_SYSTEM_PROMPT


# --- Task 2: _build_red_phase_request tests ---


class TestBuildRedPhaseRequest:
    """Tests for _build_red_phase_request helper."""

    def test_build_red_phase_request_with_description(
        self,
    ) -> None:
        """Returns AdwsRequest with prompt from description."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": "Story content here...",
            },
        )
        request = _build_red_phase_request(ctx)

        assert isinstance(request, AdwsRequest)
        assert request.system_prompt == RED_PHASE_SYSTEM_PROMPT
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert "Story content here..." in request.prompt
        assert (
            request.permission_mode == "bypassPermissions"
        )

    def test_build_red_phase_request_no_description(
        self,
    ) -> None:
        """Graceful degradation when description is missing."""
        ctx = WorkflowContext(inputs={})
        request = _build_red_phase_request(ctx)

        assert isinstance(request, AdwsRequest)
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert request.system_prompt == RED_PHASE_SYSTEM_PROMPT
        assert (
            request.permission_mode == "bypassPermissions"
        )
        assert "no issue description" in request.prompt.lower()

    def test_build_red_phase_request_with_feedback(
        self,
    ) -> None:
        """Feedback entries are included in the prompt."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": "Some story",
            },
            feedback=[
                "Previous test had SyntaxError",
                "Another feedback entry",
            ],
        )
        request = _build_red_phase_request(ctx)

        assert request.system_prompt == RED_PHASE_SYSTEM_PROMPT
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert (
            request.permission_mode == "bypassPermissions"
        )
        assert "Previous test had SyntaxError" in request.prompt
        assert "Another feedback entry" in request.prompt


# --- Task 3: _extract_test_files tests ---


class TestExtractTestFiles:
    """Tests for _extract_test_files helper."""

    def test_extract_test_files_single_file(self) -> None:
        """Extracts a single test file path from response."""
        response = AdwsResponse(
            result=(
                "Created test file:"
                " adws/tests/adw_modules/steps"
                "/test_new_step.py"
            ),
            is_error=False,
        )
        files = _extract_test_files(response)

        assert files == [
            "adws/tests/adw_modules/steps"
            "/test_new_step.py",
        ]

    def test_extract_test_files_multiple_files(
        self,
    ) -> None:
        """Extracts multiple test file paths."""
        response = AdwsResponse(
            result=(
                "Created:\n"
                "adws/tests/steps/test_a.py\n"
                "adws/tests/steps/test_b.py"
            ),
            is_error=False,
        )
        files = _extract_test_files(response)

        assert len(files) == 2
        assert "adws/tests/steps/test_a.py" in files
        assert "adws/tests/steps/test_b.py" in files

    def test_extract_test_files_no_matches(self) -> None:
        """Returns empty list when no test paths found."""
        response = AdwsResponse(
            result="No files created",
            is_error=False,
        )
        files = _extract_test_files(response)

        assert files == []

    def test_extract_test_files_none_result(self) -> None:
        """Returns empty list when result is None."""
        response = AdwsResponse(
            result=None,
            is_error=True,
            error_message="Something went wrong",
        )
        files = _extract_test_files(response)

        assert files == []

    def test_extract_test_files_deduplication(self) -> None:
        """Duplicate paths are removed, insertion order preserved."""
        response = AdwsResponse(
            result=(
                "adws/tests/test_foo.py\n"
                "adws/tests/test_foo.py\n"
                "adws/tests/test_bar.py"
            ),
            is_error=False,
        )
        files = _extract_test_files(response)

        assert files == [
            "adws/tests/test_foo.py",
            "adws/tests/test_bar.py",
        ]


# --- Task 4: write_failing_tests step function tests ---


class TestWriteFailingTests:
    """Tests for the write_failing_tests step function."""

    def test_write_failing_tests_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Success: SDK returns valid response with test files."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=(
                        "Created test files:\n"
                        "adws/tests/steps/test_x.py"
                    ),
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Test story",
            },
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["test_files"] == [
            "adws/tests/steps/test_x.py",
        ]
        assert updated.outputs["red_phase_complete"] is True
        mock_sdk.assert_called_once()

    def test_write_failing_tests_sdk_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK call returns IOFailure -- propagated."""
        mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.execute_sdk_call",
                    error_type="ClaudeSDKError",
                    message="SDK unavailable",
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Test story",
            },
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "write_failing_tests"
        assert err.error_type == "ClaudeSDKError"

    def test_write_failing_tests_sdk_error_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK returns success IOResult but is_error=True."""
        mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=None,
                    is_error=True,
                    error_message="Rate limited",
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Test story",
            },
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "write_failing_tests"
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message

    def test_write_failing_tests_empty_test_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Success even when no test files extracted."""
        mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result="Done but no paths listed",
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Test story",
            },
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["test_files"] == []
        assert updated.outputs["red_phase_complete"] is True


# --- Task 5: Registration tests ---


class TestWriteFailingTestsRegistration:
    """Tests for step registration and importability."""

    def test_write_failing_tests_importable(self) -> None:
        """write_failing_tests is importable from steps."""
        assert callable(write_failing_tests_from_init)

    def test_write_failing_tests_step_registry(
        self,
    ) -> None:
        """write_failing_tests is in _STEP_REGISTRY."""
        assert "write_failing_tests" in _STEP_REGISTRY
        assert (
            _STEP_REGISTRY["write_failing_tests"]
            is write_failing_tests
        )


# --- Task 7: Integration tests ---


class TestWriteFailingTestsIntegration:
    """Integration tests for the full step flow."""

    def test_integration_success_with_feedback(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: description + feedback -> success."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=(
                        "Created test files:\n"
                        "adws/tests/steps/test_email.py"
                    ),
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Implement a function that validates"
                    " email addresses"
                ),
            },
            feedback=[
                "Previous test had SyntaxError",
            ],
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs["test_files"] == [
            "adws/tests/steps/test_email.py",
        ]
        assert updated.outputs["red_phase_complete"] is True

        # Verify the SDK request included both
        call_args = mock_sdk.call_args
        request_sent = call_args[0][0]
        assert (
            "validates email" in request_sent.prompt
        )
        assert (
            "SyntaxError" in request_sent.prompt
        )

    def test_integration_sdk_unavailable(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK failure propagates with correct step_name."""
        mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.execute_sdk_call",
                    error_type="ClaudeSDKError",
                    message="SDK unavailable",
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "A story",
            },
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "write_failing_tests"

    def test_integration_sdk_error_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK error response (is_error=True) propagates."""
        mocker.patch(
            "adws.adw_modules.steps.write_failing_tests"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=None,
                    is_error=True,
                    error_message="Rate limited",
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "A story",
            },
        )
        result = write_failing_tests(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message

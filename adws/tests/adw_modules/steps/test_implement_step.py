"""Tests for implement_step (GREEN phase TDD agent)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import _STEP_REGISTRY
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    implement_step as implement_step_from_init,
)
from adws.adw_modules.steps.implement_step import (
    GREEN_PHASE_SYSTEM_PROMPT,
    _build_green_phase_request,
    _extract_implementation_files,
    _process_implement_response,
    implement_step,
)
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsRequest,
    AdwsResponse,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 1: GREEN_PHASE_SYSTEM_PROMPT tests ---


class TestGreenPhaseSystemPrompt:
    """Tests for the GREEN_PHASE_SYSTEM_PROMPT constant."""

    def test_green_phase_system_prompt_not_empty(
        self,
    ) -> None:
        """Prompt constant is a non-empty string."""
        assert isinstance(GREEN_PHASE_SYSTEM_PROMPT, str)
        assert len(GREEN_PHASE_SYSTEM_PROMPT) > 0

    def test_green_phase_system_prompt_contains_minimum_code(
        self,
    ) -> None:
        """Prompt instructs to implement minimum code."""
        lower = GREEN_PHASE_SYSTEM_PROMPT.lower()
        assert "minimum" in lower
        assert (
            "implementation" in lower
            or "implement" in lower
        )

    def test_green_phase_system_prompt_contains_no_refactor(
        self,
    ) -> None:
        """Prompt instructs not to refactor."""
        lower = GREEN_PHASE_SYSTEM_PROMPT.lower()
        assert "do not refactor" in lower

    def test_green_phase_system_prompt_contains_no_extra_features(
        self,
    ) -> None:
        """Prompt says not to add features beyond tests."""
        lower = GREEN_PHASE_SYSTEM_PROMPT.lower()
        assert "do not add features" in lower

    def test_green_phase_system_prompt_contains_tests_must_pass(
        self,
    ) -> None:
        """Prompt says all tests must pass."""
        lower = GREEN_PHASE_SYSTEM_PROMPT.lower()
        assert "all tests must pass" in lower

    def test_green_phase_system_prompt_contains_coverage(
        self,
    ) -> None:
        """Prompt mentions 100% coverage."""
        assert "100%" in GREEN_PHASE_SYSTEM_PROMPT

    def test_green_phase_system_prompt_contains_io_ops_boundary(
        self,
    ) -> None:
        """Prompt mentions the io_ops boundary."""
        assert "io_ops" in GREEN_PHASE_SYSTEM_PROMPT

    def test_green_phase_system_prompt_contains_bypass_permissions(
        self,
    ) -> None:
        """Prompt mentions bypassPermissions mode."""
        assert (
            "bypassPermissions"
            in GREEN_PHASE_SYSTEM_PROMPT
        )

    def test_green_phase_system_prompt_contains_file_ref(
        self,
    ) -> None:
        """Prompt mentions files for write context."""
        lower = GREEN_PHASE_SYSTEM_PROMPT.lower()
        assert "file" in lower


# --- Task 2: _build_green_phase_request tests ---


class TestBuildGreenPhaseRequest:
    """Tests for _build_green_phase_request helper."""

    def test_build_green_phase_request_with_description(
        self,
    ) -> None:
        """Returns AdwsRequest with prompt from description."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Story content here..."
                ),
                "test_files": [
                    "adws/tests/test_foo.py",
                ],
                "red_gate_passed": True,
            },
        )
        request = _build_green_phase_request(ctx)

        assert isinstance(request, AdwsRequest)
        assert (
            request.system_prompt
            == GREEN_PHASE_SYSTEM_PROMPT
        )
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert "Story content here..." in request.prompt
        assert (
            request.permission_mode
            == "bypassPermissions"
        )

    def test_build_green_phase_request_no_description(
        self,
    ) -> None:
        """Graceful degradation when description missing."""
        ctx = WorkflowContext(inputs={})
        request = _build_green_phase_request(ctx)

        assert isinstance(request, AdwsRequest)
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert (
            request.system_prompt
            == GREEN_PHASE_SYSTEM_PROMPT
        )
        assert (
            request.permission_mode
            == "bypassPermissions"
        )
        assert (
            "no issue description"
            in request.prompt.lower()
        )

    def test_build_green_phase_request_with_feedback(
        self,
    ) -> None:
        """Feedback entries are included in the prompt."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": "Some story",
            },
            feedback=[
                "Previous attempt: AssertionError",
                "Another feedback entry",
            ],
        )
        request = _build_green_phase_request(ctx)

        assert (
            "Previous attempt: AssertionError"
            in request.prompt
        )
        assert "Another feedback entry" in request.prompt

    def test_build_green_phase_request_with_test_files(
        self,
    ) -> None:
        """Test file paths are included in the prompt."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": "Some story",
                "test_files": [
                    "adws/tests/test_foo.py",
                    "adws/tests/test_bar.py",
                ],
            },
        )
        request = _build_green_phase_request(ctx)

        assert "adws/tests/test_foo.py" in request.prompt
        assert "adws/tests/test_bar.py" in request.prompt


# --- Task 3: _extract_implementation_files tests ---


class TestExtractImplementationFiles:
    """Tests for _extract_implementation_files helper."""

    def test_extract_implementation_files_single_file(
        self,
    ) -> None:
        """Extracts a single source file path."""
        response = AdwsResponse(
            result=(
                "Modified files:\n"
                "adws/adw_modules/steps/new_step.py"
            ),
            is_error=False,
        )
        files = _extract_implementation_files(response)

        assert files == [
            "adws/adw_modules/steps/new_step.py",
        ]

    def test_extract_implementation_files_multiple_files(
        self,
    ) -> None:
        """Extracts multiple source file paths."""
        response = AdwsResponse(
            result=(
                "Created:\n"
                "adws/adw_modules/steps/step_a.py\n"
                "adws/adw_modules/steps/step_b.py"
            ),
            is_error=False,
        )
        files = _extract_implementation_files(response)

        assert len(files) == 2
        assert (
            "adws/adw_modules/steps/step_a.py" in files
        )
        assert (
            "adws/adw_modules/steps/step_b.py" in files
        )

    def test_extract_implementation_files_no_matches(
        self,
    ) -> None:
        """Returns empty list when no source paths found."""
        response = AdwsResponse(
            result="No files created",
            is_error=False,
        )
        files = _extract_implementation_files(response)

        assert files == []

    def test_extract_implementation_files_none_result(
        self,
    ) -> None:
        """Returns empty list when result is None."""
        response = AdwsResponse(
            result=None,
            is_error=True,
            error_message="Something went wrong",
        )
        files = _extract_implementation_files(response)

        assert files == []

    def test_extract_implementation_files_deduplication(
        self,
    ) -> None:
        """Duplicates removed, insertion order preserved."""
        response = AdwsResponse(
            result=(
                "adws/adw_modules/steps/foo.py\n"
                "adws/adw_modules/steps/foo.py\n"
                "adws/adw_modules/steps/bar.py"
            ),
            is_error=False,
        )
        files = _extract_implementation_files(response)

        assert files == [
            "adws/adw_modules/steps/foo.py",
            "adws/adw_modules/steps/bar.py",
        ]

    def test_extract_implementation_files_excludes_test(
        self,
    ) -> None:
        """Only extracts adws/adw_modules/ paths, not tests."""
        response = AdwsResponse(
            result=(
                "adws/adw_modules/steps/new_step.py\n"
                "adws/tests/steps/test_new_step.py"
            ),
            is_error=False,
        )
        files = _extract_implementation_files(response)

        assert files == [
            "adws/adw_modules/steps/new_step.py",
        ]


# --- Task 4: _process_implement_response and
#     implement_step tests ---


class TestProcessImplementResponse:
    """Tests for _process_implement_response helper."""

    def test_process_implement_response_success(
        self,
    ) -> None:
        """Success: extracts files and sets outputs."""
        response = AdwsResponse(
            result=(
                "Modified files:\n"
                "adws/adw_modules/steps/new_step.py"
            ),
            is_error=False,
        )
        ctx = WorkflowContext(
            inputs={"issue_description": "Story"},
        )
        result = _process_implement_response(
            response, ctx,
        )

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs[
            "implementation_files"
        ] == [
            "adws/adw_modules/steps/new_step.py",
        ]
        assert (
            updated.outputs["green_phase_complete"]
            is True
        )

    def test_process_implement_response_is_error(
        self,
    ) -> None:
        """SDK error response returns IOFailure."""
        response = AdwsResponse(
            result=None,
            is_error=True,
            error_message="Rate limited",
        )
        ctx = WorkflowContext(
            inputs={"issue_description": "Story"},
        )
        result = _process_implement_response(
            response, ctx,
        )

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "implement_step"
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message


class TestImplementStep:
    """Tests for the implement_step step function."""

    def test_implement_step_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Success: SDK returns valid response."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.implement_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=(
                        "Modified files:\n"
                        "adws/adw_modules/steps/x.py"
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
        result = implement_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs[
            "implementation_files"
        ] == [
            "adws/adw_modules/steps/x.py",
        ]
        assert (
            updated.outputs["green_phase_complete"]
            is True
        )
        mock_sdk.assert_called_once()

    def test_implement_step_sdk_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK call returns IOFailure -- propagated."""
        mocker.patch(
            "adws.adw_modules.steps.implement_step"
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
        result = implement_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "implement_step"
        assert err.error_type == "ClaudeSDKError"

    def test_implement_step_sdk_error_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK returns success IOResult but is_error=True."""
        mocker.patch(
            "adws.adw_modules.steps.implement_step"
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
        result = implement_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "implement_step"
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message

    def test_implement_step_empty_implementation_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Success even when no impl files extracted."""
        mocker.patch(
            "adws.adw_modules.steps.implement_step"
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
        result = implement_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert (
            updated.outputs["implementation_files"] == []
        )
        assert (
            updated.outputs["green_phase_complete"]
            is True
        )


# --- Task 9: Registration tests ---


class TestImplementStepRegistration:
    """Tests for step registration and importability."""

    def test_implement_step_importable(self) -> None:
        """implement_step is importable from steps."""
        assert callable(implement_step_from_init)

    def test_implement_step_step_registry(
        self,
    ) -> None:
        """implement_step is in _STEP_REGISTRY."""
        assert "implement_step" in _STEP_REGISTRY
        assert (
            _STEP_REGISTRY["implement_step"]
            is implement_step
        )


# --- Task 11: Integration tests ---


class TestImplementStepIntegration:
    """Integration tests for the full implement_step flow."""

    def test_integration_success_with_feedback(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: description + feedback -> success."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.implement_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=(
                        "Created implementation:\n"
                        "adws/adw_modules/steps"
                        "/email_validator.py"
                    ),
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Implement email validation"
                ),
                "test_files": [
                    "adws/tests/test_email.py",
                ],
                "red_gate_passed": True,
            },
            feedback=[
                "Previous attempt:"
                " AssertionError in test_email",
            ],
        )
        result = implement_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs[
            "implementation_files"
        ] == [
            "adws/adw_modules/steps"
            "/email_validator.py",
        ]
        assert (
            updated.outputs["green_phase_complete"]
            is True
        )

        # Verify request included all context
        call_args = mock_sdk.call_args
        request_sent = call_args[0][0]
        assert (
            "email validation" in request_sent.prompt
        )
        assert (
            "adws/tests/test_email.py"
            in request_sent.prompt
        )
        assert (
            "AssertionError" in request_sent.prompt
        )

    def test_integration_sdk_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK failure propagates with correct step_name."""
        mocker.patch(
            "adws.adw_modules.steps.implement_step"
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
        result = implement_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "implement_step"

    def test_integration_sdk_error_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK error response (is_error=True) propagates."""
        mocker.patch(
            "adws.adw_modules.steps.implement_step"
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
        result = implement_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message

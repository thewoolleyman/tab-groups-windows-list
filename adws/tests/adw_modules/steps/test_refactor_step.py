"""Tests for refactor_step (REFACTOR phase TDD agent)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import _STEP_REGISTRY
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    refactor_step as refactor_step_from_init,
)
from adws.adw_modules.steps.refactor_step import (
    REFACTOR_PHASE_SYSTEM_PROMPT,
    _build_refactor_phase_request,
    _extract_refactored_files,
    _process_refactor_response,
    refactor_step,
)
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsRequest,
    AdwsResponse,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 5: REFACTOR_PHASE_SYSTEM_PROMPT tests ---


class TestRefactorPhaseSystemPrompt:
    """Tests for the REFACTOR_PHASE_SYSTEM_PROMPT constant."""

    def test_refactor_phase_system_prompt_not_empty(
        self,
    ) -> None:
        """Prompt constant is a non-empty string."""
        assert isinstance(
            REFACTOR_PHASE_SYSTEM_PROMPT, str,
        )
        assert len(REFACTOR_PHASE_SYSTEM_PROMPT) > 0

    def test_refactor_phase_system_prompt_contains_refactor_only(
        self,
    ) -> None:
        """Prompt instructs refactor only."""
        lower = REFACTOR_PHASE_SYSTEM_PROMPT.lower()
        assert "refactor only" in lower

    def test_refactor_phase_system_prompt_contains_no_behavior_change(
        self,
    ) -> None:
        """Prompt instructs not to change behavior."""
        lower = REFACTOR_PHASE_SYSTEM_PROMPT.lower()
        assert "do not change behavior" in lower

    def test_refactor_phase_system_prompt_contains_tests_still_pass(
        self,
    ) -> None:
        """Prompt says all tests must still pass."""
        lower = REFACTOR_PHASE_SYSTEM_PROMPT.lower()
        assert "all tests must still pass" in lower

    def test_refactor_phase_system_prompt_contains_improve_quality(
        self,
    ) -> None:
        """Prompt mentions improving code quality."""
        lower = REFACTOR_PHASE_SYSTEM_PROMPT.lower()
        assert "improve" in lower

    def test_refactor_phase_system_prompt_contains_follow_patterns(
        self,
    ) -> None:
        """Prompt says to follow established patterns."""
        lower = REFACTOR_PHASE_SYSTEM_PROMPT.lower()
        assert "established" in lower
        assert "pattern" in lower

    def test_refactor_phase_system_prompt_contains_coverage(
        self,
    ) -> None:
        """Prompt mentions 100% coverage."""
        assert "100%" in REFACTOR_PHASE_SYSTEM_PROMPT

    def test_refactor_phase_system_prompt_contains_io_ops(
        self,
    ) -> None:
        """Prompt mentions io_ops boundary."""
        assert "io_ops" in REFACTOR_PHASE_SYSTEM_PROMPT

    def test_refactor_phase_system_prompt_contains_bypass_permissions(
        self,
    ) -> None:
        """Prompt mentions bypassPermissions mode."""
        assert (
            "bypassPermissions"
            in REFACTOR_PHASE_SYSTEM_PROMPT
        )

    def test_refactor_phase_system_prompt_contains_file_ref(
        self,
    ) -> None:
        """Prompt mentions files (bypassPermissions context)."""
        lower = REFACTOR_PHASE_SYSTEM_PROMPT.lower()
        assert "file" in lower


# --- Task 6: _build_refactor_phase_request tests ---


class TestBuildRefactorPhaseRequest:
    """Tests for _build_refactor_phase_request helper."""

    def test_build_refactor_phase_request_with_description(
        self,
    ) -> None:
        """Returns AdwsRequest with prompt from description."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Story content..."
                ),
                "implementation_files": [
                    "adws/adw_modules/steps/new_step.py",
                ],
                "green_phase_complete": True,
            },
        )
        request = _build_refactor_phase_request(ctx)

        assert isinstance(request, AdwsRequest)
        assert (
            request.system_prompt
            == REFACTOR_PHASE_SYSTEM_PROMPT
        )
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert "Story content..." in request.prompt
        assert (
            request.permission_mode
            == "bypassPermissions"
        )

    def test_build_refactor_phase_request_no_description(
        self,
    ) -> None:
        """Graceful degradation when description missing."""
        ctx = WorkflowContext(inputs={})
        request = _build_refactor_phase_request(ctx)

        assert isinstance(request, AdwsRequest)
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert (
            request.system_prompt
            == REFACTOR_PHASE_SYSTEM_PROMPT
        )
        assert (
            request.permission_mode
            == "bypassPermissions"
        )
        assert (
            "no issue description"
            in request.prompt.lower()
        )

    def test_build_refactor_phase_request_with_implementation_files(
        self,
    ) -> None:
        """Implementation file paths included in prompt."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": "Some story",
                "implementation_files": [
                    "adws/adw_modules/steps/foo.py",
                    "adws/adw_modules/steps/bar.py",
                ],
            },
        )
        request = _build_refactor_phase_request(ctx)

        assert (
            "adws/adw_modules/steps/foo.py"
            in request.prompt
        )
        assert (
            "adws/adw_modules/steps/bar.py"
            in request.prompt
        )

    def test_build_refactor_phase_request_with_feedback(
        self,
    ) -> None:
        """Feedback entries are included in the prompt."""
        ctx = WorkflowContext(
            inputs={
                "issue_description": "Some story",
            },
            feedback=[
                "Previous refactor broke a test",
                "Another feedback entry",
            ],
        )
        request = _build_refactor_phase_request(ctx)

        assert (
            "Previous refactor broke a test"
            in request.prompt
        )
        assert "Another feedback entry" in request.prompt


# --- Task 7: _extract_refactored_files tests ---


class TestExtractRefactoredFiles:
    """Tests for _extract_refactored_files helper."""

    def test_extract_refactored_files_single_file(
        self,
    ) -> None:
        """Extracts a single project file path."""
        response = AdwsResponse(
            result=(
                "Modified files:\n"
                "adws/adw_modules/steps/new_step.py"
            ),
            is_error=False,
        )
        files = _extract_refactored_files(response)

        assert files == [
            "adws/adw_modules/steps/new_step.py",
        ]

    def test_extract_refactored_files_includes_tests(
        self,
    ) -> None:
        """Extracts both source and test file paths."""
        response = AdwsResponse(
            result=(
                "Refactored:\n"
                "adws/adw_modules/steps/new_step.py\n"
                "adws/tests/steps/test_new_step.py"
            ),
            is_error=False,
        )
        files = _extract_refactored_files(response)

        assert len(files) == 2
        assert (
            "adws/adw_modules/steps/new_step.py"
            in files
        )
        assert (
            "adws/tests/steps/test_new_step.py"
            in files
        )

    def test_extract_refactored_files_no_matches(
        self,
    ) -> None:
        """Returns empty list when no paths found."""
        response = AdwsResponse(
            result="No files modified",
            is_error=False,
        )
        files = _extract_refactored_files(response)

        assert files == []

    def test_extract_refactored_files_none_result(
        self,
    ) -> None:
        """Returns empty list when result is None."""
        response = AdwsResponse(
            result=None,
            is_error=True,
            error_message="Something went wrong",
        )
        files = _extract_refactored_files(response)

        assert files == []

    def test_extract_refactored_files_deduplication(
        self,
    ) -> None:
        """Duplicates removed, insertion order preserved."""
        response = AdwsResponse(
            result=(
                "adws/adw_modules/steps/foo.py\n"
                "adws/adw_modules/steps/foo.py\n"
                "adws/tests/steps/test_foo.py"
            ),
            is_error=False,
        )
        files = _extract_refactored_files(response)

        assert files == [
            "adws/adw_modules/steps/foo.py",
            "adws/tests/steps/test_foo.py",
        ]


# --- Task 8: _process_refactor_response and
#     refactor_step tests ---


class TestProcessRefactorResponse:
    """Tests for _process_refactor_response helper."""

    def test_process_refactor_response_success(
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
        result = _process_refactor_response(
            response, ctx,
        )

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs[
            "refactored_files"
        ] == [
            "adws/adw_modules/steps/new_step.py",
        ]
        assert (
            updated.outputs["refactor_phase_complete"]
            is True
        )

    def test_process_refactor_response_is_error(
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
        result = _process_refactor_response(
            response, ctx,
        )

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "refactor_step"
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message


class TestRefactorStep:
    """Tests for the refactor_step step function."""

    def test_refactor_step_success(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Success: SDK returns valid response."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.refactor_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=(
                        "Refactored files:\n"
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
        result = refactor_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs[
            "refactored_files"
        ] == [
            "adws/adw_modules/steps/x.py",
        ]
        assert (
            updated.outputs["refactor_phase_complete"]
            is True
        )
        mock_sdk.assert_called_once()

    def test_refactor_step_sdk_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK call returns IOFailure -- propagated."""
        mocker.patch(
            "adws.adw_modules.steps.refactor_step"
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
        result = refactor_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "refactor_step"
        assert err.error_type == "ClaudeSDKError"

    def test_refactor_step_sdk_error_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK returns success IOResult but is_error=True."""
        mocker.patch(
            "adws.adw_modules.steps.refactor_step"
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
        result = refactor_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "refactor_step"
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message

    def test_refactor_step_empty_refactored_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Success even when no refactored files extracted."""
        mocker.patch(
            "adws.adw_modules.steps.refactor_step"
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
        result = refactor_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert (
            updated.outputs["refactored_files"] == []
        )
        assert (
            updated.outputs["refactor_phase_complete"]
            is True
        )


# --- Task 9: Registration tests ---


class TestRefactorStepRegistration:
    """Tests for step registration and importability."""

    def test_refactor_step_importable(self) -> None:
        """refactor_step is importable from steps."""
        assert callable(refactor_step_from_init)

    def test_refactor_step_step_registry(
        self,
    ) -> None:
        """refactor_step is in _STEP_REGISTRY."""
        assert "refactor_step" in _STEP_REGISTRY
        assert (
            _STEP_REGISTRY["refactor_step"]
            is refactor_step
        )


# --- Task 11: Integration tests ---


class TestRefactorStepIntegration:
    """Integration tests for the full refactor_step flow."""

    def test_integration_success_with_feedback(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full flow: description + feedback -> success."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.refactor_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result=(
                        "Refactored:\n"
                        "adws/adw_modules/steps"
                        "/new_step.py"
                    ),
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Story about refactoring"
                ),
                "implementation_files": [
                    "adws/adw_modules/steps"
                    "/new_step.py",
                ],
                "green_phase_complete": True,
            },
            feedback=[
                "Previous refactor broke tests",
            ],
        )
        result = refactor_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert updated.outputs[
            "refactored_files"
        ] == [
            "adws/adw_modules/steps/new_step.py",
        ]
        assert (
            updated.outputs["refactor_phase_complete"]
            is True
        )

        # Verify request included all context
        call_args = mock_sdk.call_args
        request_sent = call_args[0][0]
        assert "refactoring" in request_sent.prompt
        assert (
            "adws/adw_modules/steps/new_step.py"
            in request_sent.prompt
        )
        assert (
            "Previous refactor broke tests"
            in request_sent.prompt
        )

    def test_integration_sdk_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK failure propagates with correct step_name."""
        mocker.patch(
            "adws.adw_modules.steps.refactor_step"
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
        result = refactor_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.step_name == "refactor_step"

    def test_integration_sdk_error_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK error response (is_error=True) propagates."""
        mocker.patch(
            "adws.adw_modules.steps.refactor_step"
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
        result = refactor_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message

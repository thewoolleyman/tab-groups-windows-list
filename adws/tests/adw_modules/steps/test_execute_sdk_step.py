"""Tests for execute_sdk_step (generic SDK wrapper)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.engine.executor import _STEP_REGISTRY
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps import (
    execute_sdk_step as execute_sdk_step_from_init,
)
from adws.adw_modules.steps.execute_sdk_step import (
    GENERIC_SYSTEM_PROMPT,
    execute_sdk_step,
)
from adws.adw_modules.types import (
    DEFAULT_CLAUDE_MODEL,
    AdwsResponse,
    WorkflowContext,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- GENERIC_SYSTEM_PROMPT tests ---


class TestGenericSystemPrompt:
    """Tests for the GENERIC_SYSTEM_PROMPT constant."""

    def test_generic_system_prompt_not_empty(
        self,
    ) -> None:
        """Prompt constant is a non-empty string."""
        assert isinstance(GENERIC_SYSTEM_PROMPT, str)
        assert len(GENERIC_SYSTEM_PROMPT) > 0

    def test_generic_system_prompt_mentions_io_ops(
        self,
    ) -> None:
        """Prompt mentions the io_ops boundary."""
        assert "io_ops" in GENERIC_SYSTEM_PROMPT


# --- execute_sdk_step success path ---


class TestExecuteSdkStepSuccess:
    """Tests for execute_sdk_step success path."""

    def test_success_returns_sdk_response_in_outputs(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK call succeeds: outputs contain sdk_response."""
        mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result="Implementation complete.",
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Update README",
            },
        )
        result = execute_sdk_step(ctx)

        assert isinstance(result, IOSuccess)
        updated = unsafe_perform_io(result.unwrap())
        assert (
            updated.outputs["sdk_response"]
            == "Implementation complete."
        )

    def test_success_passes_description_as_prompt(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK request prompt is the issue description."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result="Done",
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": (
                    "Implement feature X"
                ),
            },
        )
        execute_sdk_step(ctx)

        mock_sdk.assert_called_once()
        request = mock_sdk.call_args[0][0]
        assert request.prompt == "Implement feature X"
        assert (
            request.system_prompt
            == GENERIC_SYSTEM_PROMPT
        )
        assert request.model == DEFAULT_CLAUDE_MODEL
        assert (
            request.permission_mode
            == "bypassPermissions"
        )


# --- execute_sdk_step is_error path ---


class TestExecuteSdkStepSdkError:
    """Tests for execute_sdk_step SDK error response path."""

    def test_sdk_is_error_returns_iofailure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK returns is_error=True: returns IOFailure."""
        mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
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
        result = execute_sdk_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert isinstance(err, PipelineError)
        assert err.step_name == "execute_sdk_step"
        assert err.error_type == "SdkResponseError"
        assert "Rate limited" in err.message


# --- execute_sdk_step IOFailure path ---


class TestExecuteSdkStepIOFailure:
    """Tests for execute_sdk_step SDK call IOFailure path."""

    def test_sdk_call_iofailure_propagates(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK call IOFailure propagates with correct step_name."""
        mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
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
        result = execute_sdk_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert isinstance(err, PipelineError)
        assert err.step_name == "execute_sdk_step"
        assert err.error_type == "ClaudeSDKError"
        assert "SDK unavailable" in err.message

    def test_sdk_call_iofailure_preserves_context(
        self,
        mocker: MockerFixture,
    ) -> None:
        """SDK call IOFailure preserves error context dict."""
        mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
            ".io_ops.execute_sdk_call",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.execute_sdk_call",
                    error_type="TimeoutError",
                    message="Request timed out",
                    context={"timeout_ms": 30000},
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={
                "issue_description": "Test story",
            },
        )
        result = execute_sdk_step(ctx)

        assert isinstance(result, IOFailure)
        err = unsafe_perform_io(result.failure())
        assert err.context == {"timeout_ms": 30000}


# --- Missing/non-string description fallback ---


class TestExecuteSdkStepDescriptionFallback:
    """Tests for description fallback behavior."""

    def test_missing_description_uses_default(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Missing issue_description falls back to default prompt."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result="Done",
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(inputs={})
        execute_sdk_step(ctx)

        request = mock_sdk.call_args[0][0]
        assert (
            request.prompt == "No description provided."
        )

    def test_non_string_description_uses_default(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Non-string issue_description falls back to default."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result="Done",
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={"issue_description": 42},
        )
        execute_sdk_step(ctx)

        request = mock_sdk.call_args[0][0]
        assert (
            request.prompt == "No description provided."
        )

    def test_empty_string_description_uses_default(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Empty string issue_description falls back to default."""
        mock_sdk = mocker.patch(
            "adws.adw_modules.steps.execute_sdk_step"
            ".io_ops.execute_sdk_call",
            return_value=IOSuccess(
                AdwsResponse(
                    result="Done",
                    is_error=False,
                ),
            ),
        )

        ctx = WorkflowContext(
            inputs={"issue_description": "   "},
        )
        execute_sdk_step(ctx)

        request = mock_sdk.call_args[0][0]
        assert (
            request.prompt == "No description provided."
        )


# --- Registration tests ---


class TestExecuteSdkStepRegistration:
    """Tests for step registration and importability."""

    def test_execute_sdk_step_importable_from_init(
        self,
    ) -> None:
        """execute_sdk_step importable from steps __init__."""
        assert callable(execute_sdk_step_from_init)

    def test_execute_sdk_step_in_step_registry(
        self,
    ) -> None:
        """execute_sdk_step is in _STEP_REGISTRY."""
        assert "execute_sdk_step" in _STEP_REGISTRY
        assert (
            _STEP_REGISTRY["execute_sdk_step"]
            is execute_sdk_step
        )

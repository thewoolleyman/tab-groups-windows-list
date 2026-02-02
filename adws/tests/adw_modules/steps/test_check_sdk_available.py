"""Tests for check_sdk_available step."""
from returns.io import IOFailure, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.steps.check_sdk_available import check_sdk_available


def test_check_sdk_available_success(mocker, sample_workflow_context) -> None:  # type: ignore[no-untyped-def]
    """Test returns IOSuccess when SDK is importable."""
    mocker.patch(
        "adws.adw_modules.steps.check_sdk_available.check_sdk_import",
        return_value=IOSuccess(True),  # noqa: FBT003
    )
    result = check_sdk_available(sample_workflow_context)
    assert isinstance(result, IOSuccess)


def test_check_sdk_available_failure(mocker, sample_workflow_context) -> None:  # type: ignore[no-untyped-def]
    """Test returns IOFailure when SDK is not importable."""
    mocker.patch(
        "adws.adw_modules.steps.check_sdk_available.check_sdk_import",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.check_sdk_import",
                error_type="ImportError",
                message="SDK not available",
            ),
        ),
    )
    result = check_sdk_available(sample_workflow_context)
    assert isinstance(result, IOFailure)

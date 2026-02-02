"""Tests for shared finalize helpers (_finalize.py)."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- _build_failure_metadata tests ---


def test_shared_build_failure_metadata_format() -> None:
    """_build_failure_metadata returns pipe-delimited string."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        build_failure_metadata,
    )

    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="Model timeout",
    )
    result = build_failure_metadata(error, 1)
    assert result.startswith("ADWS_FAILED|")
    assert "attempt=1" in result
    assert "error_class=SdkCallError" in result
    assert "step=implement" in result
    assert "summary=Model timeout" in result
    ts_match = re.search(
        r"last_failure=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)",
        result,
    )
    assert ts_match is not None


def test_shared_build_failure_metadata_pipe_escaping() -> None:
    """Pipe chars in message are escaped in metadata."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        build_failure_metadata,
    )

    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="fail|with|pipes",
    )
    result = build_failure_metadata(error, 2)
    assert "summary=fail\\|with\\|pipes" in result


def test_shared_build_failure_metadata_attempt_1_indexed() -> None:
    """attempt_count=0 produces attempt=1 (1-indexed)."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        build_failure_metadata,
    )

    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="first try",
    )
    result = build_failure_metadata(error, 0)
    assert "attempt=1" in result


# --- finalize_on_success tests ---


def test_shared_finalize_on_success_close(
    mocker: MockerFixture,
) -> None:
    """finalize_on_success returns IOSuccess('closed')."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_success,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOSuccess(
            WorkflowContext(),
        ),
    )
    result = finalize_on_success("TEST-1")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "closed"


def test_shared_finalize_on_success_bd_failure(
    mocker: MockerFixture,
) -> None:
    """finalize_on_success returns 'close_failed' on bd error."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_success,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_close",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.run_beads_close",
                error_type="BeadsCloseError",
                message="bd close failed",
            ),
        ),
    )
    result = finalize_on_success("TEST-1")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "close_failed"


def test_shared_finalize_on_success_no_issue() -> None:
    """finalize_on_success returns 'skipped' when no issue."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_success,
    )

    result = finalize_on_success(None)
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "skipped"


def test_shared_finalize_on_success_empty_issue() -> None:
    """finalize_on_success returns 'skipped' for empty str."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_success,
    )

    result = finalize_on_success("")
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "skipped"


# --- finalize_on_failure tests ---


def test_shared_finalize_on_failure_tag(
    mocker: MockerFixture,
) -> None:
    """finalize_on_failure returns 'tagged_failure'."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_failure,
    )

    mock_update = mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOSuccess(
            WorkflowContext(),
        ),
    )
    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="Model timeout",
    )
    result = finalize_on_failure("TEST-2", error, 1)
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "tagged_failure"
    call_args = mock_update.call_args
    notes = call_args[0][1]
    assert notes.startswith("ADWS_FAILED|")
    assert "SdkCallError" in notes
    assert "implement" in notes


def test_shared_finalize_on_failure_no_issue(
    mocker: MockerFixture,
) -> None:
    """finalize_on_failure returns 'skipped' when no issue."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_failure,
    )

    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="fail",
    )
    result = finalize_on_failure(None, error, 1)
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "skipped"


def test_shared_finalize_on_failure_empty_issue(
    mocker: MockerFixture,
) -> None:
    """finalize_on_failure returns 'skipped' for empty str."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_failure,
    )

    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="fail",
    )
    result = finalize_on_failure("", error, 1)
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "skipped"


def test_shared_finalize_on_failure_bd_failure(
    mocker: MockerFixture,
) -> None:
    """finalize_on_failure returns 'tag_failed' on bd error."""
    from adws.adw_modules.commands._finalize import (  # noqa: PLC0415
        finalize_on_failure,
    )

    mocker.patch(
        "adws.adw_modules.io_ops.run_beads_update_notes",
        return_value=IOFailure(
            PipelineError(
                step_name="io_ops.run_beads_update_notes",
                error_type="BeadsUpdateError",
                message="bd update failed",
            ),
        ),
    )
    error = PipelineError(
        step_name="implement",
        error_type="SdkCallError",
        message="fail",
    )
    result = finalize_on_failure("TEST-3", error, 1)
    assert isinstance(result, IOSuccess)
    val = unsafe_perform_io(result.unwrap())
    assert val == "tag_failed"

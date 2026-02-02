"""Integration tests for cron trigger flow (Story 7.3).

Tests the full cron trigger path: poll -> filter -> dispatch -> execute.
Mocks at the io_ops boundary to let the full chain run.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import ShellResult, WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestCronTriggerSuccessFlow:
    """Integration tests for successful poll-dispatch-execute cycle."""

    def test_full_success_cycle(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Full success: poll 2 issues -> dispatch -> execute -> close."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess('[{"id": "ISSUE-1"}, {"id": "ISSUE-2"}]'),
        )
        # read_issue_description is called during poll
        # (via _is_dispatchable_issue) and during dispatch
        # (via dispatch_workflow). Both go through io_ops
        # so we use a single return_value for all calls.
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(
                WorkflowContext(
                    inputs={
                        "issue_id": "X",
                        "workflow_tag": "implement_close",
                    },
                ),
            ),
        )
        mock_close = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="closed",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        result = run_poll_cycle()
        assert result.issues_found == 2
        assert result.issues_succeeded == 2
        assert result.issues_failed == 0
        assert mock_close.call_count == 2


class TestCronTriggerDispatchGuardFlow:
    """Integration tests for dispatch guard filtering."""

    def test_guard_filters_failed_and_needs_human(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Issues with ADWS_FAILED and needs_human are excluded."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(
                '[{"id": "ISSUE-1"}, {"id": "ISSUE-2"}, {"id": "ISSUE-3"}]',
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            side_effect=[
                IOSuccess("ADWS_FAILED|attempt=1|..."),
                IOSuccess("needs_human: review"),
                IOSuccess(""),
            ],
        )
        # Only ISSUE-3 should be dispatched
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(
                WorkflowContext(
                    inputs={
                        "issue_id": "ISSUE-3",
                        "workflow_tag": "implement_close",
                    },
                ),
            ),
        )
        mock_close = mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="closed",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        result = run_poll_cycle()
        assert result.issues_found == 1
        assert result.issues_succeeded == 1
        mock_close.assert_called_once()


class TestCronTriggerMixedFlow:
    """Integration tests for mixed success/failure cycles."""

    def test_mixed_success_failure_skip(
        self,
        mocker: MockerFixture,
    ) -> None:
        """3 issues: 1 succeeds, 1 fails, 1 dispatch-skipped."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(
                '[{"id": "ISSUE-1"}, {"id": "ISSUE-2"}, {"id": "ISSUE-3"}]',
            ),
        )
        # During poll, all 3 issues get read_issue_description
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        # For mixed test, mock at the dispatch_and_execute
        # level to avoid complex io_ops mock ordering.
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
        )

        mocker.patch(
            "adws.adw_trigger_cron.dispatch_and_execute",
            side_effect=[
                # ISSUE-1: success
                IOSuccess(
                    DispatchExecutionResult(
                        success=True,
                        workflow_executed="implement_close",
                        issue_id="ISSUE-1",
                        finalize_action="closed",
                        summary="OK",
                    ),
                ),
                # ISSUE-2: workflow failure
                IOSuccess(
                    DispatchExecutionResult(
                        success=False,
                        workflow_executed="implement_close",
                        issue_id="ISSUE-2",
                        finalize_action="tagged_failure",
                        summary="Failed: timeout",
                    ),
                ),
                # ISSUE-3: infrastructure failure
                IOFailure(
                    PipelineError(
                        step_name="adw_dispatch",
                        error_type="ValueError",
                        message="dispatch infra error",
                    ),
                ),
            ],
        )
        result = run_poll_cycle()
        assert result.issues_found == 3
        assert result.issues_dispatched == 3
        assert result.issues_succeeded == 1
        assert result.issues_failed == 1
        assert result.issues_skipped == 1


class TestCronTriggerPollErrorFlow:
    """Integration tests for poll error recovery."""

    def test_poll_error_recovery(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Poll failure produces error CronCycleResult, no dispatches."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_beads_list",
                    error_type="BeadsListError",
                    message="bd list timeout",
                ),
            ),
        )
        mock_dispatch = mocker.patch(
            "adws.adw_trigger_cron.dispatch_and_execute",
        )
        result = run_poll_cycle()
        assert result.issues_found == 0
        assert len(result.errors) == 1
        assert "bd list timeout" in result.errors[0]
        mock_dispatch.assert_not_called()


class TestCronTriggerMultiCycleFlow:
    """Integration tests for multi-cycle trigger loop."""

    def test_multi_cycle_with_sleep(
        self,
        mocker: MockerFixture,
    ) -> None:
        """2 cycles: first has 1 issue, second has 0."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_trigger_loop,
        )

        # Cycle 1: 1 ready issue
        # Cycle 2: 0 ready issues
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            side_effect=[
                IOSuccess('[{"id": "ISSUE-1"}]'),
                IOSuccess("[]"),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(
                WorkflowContext(
                    inputs={
                        "issue_id": "ISSUE-1",
                        "workflow_tag": "implement_close",
                    },
                ),
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="closed",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        mock_sleep = mocker.patch(
            "adws.adw_trigger_cron.io_ops.sleep_seconds",
            return_value=IOSuccess(None),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.write_stderr",
            return_value=IOSuccess(None),
        )
        results = run_trigger_loop(
            poll_interval_seconds=10.0,
            max_cycles=2,
        )
        assert len(results) == 2
        assert results[0].issues_found == 1
        assert results[0].issues_succeeded == 1
        assert results[1].issues_found == 0
        mock_sleep.assert_called_once_with(10.0)


class TestCronTriggerNFR19Flow:
    """Integration tests for NFR19 compliance."""

    def test_full_cron_flow_never_reads_bmad(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Cron trigger never reads BMAD files (NFR19)."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess("ISSUE-1\n"),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.read_issue_description",
            return_value=IOSuccess(
                "Content\n\n{implement_close}",
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.execute_command_workflow",
            return_value=IOSuccess(
                WorkflowContext(
                    inputs={
                        "issue_id": "ISSUE-1",
                        "workflow_tag": "implement_close",
                    },
                ),
            ),
        )
        mocker.patch(
            "adws.adw_dispatch.io_ops.run_beads_close",
            return_value=IOSuccess(
                ShellResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                    command="bd close",
                ),
            ),
        )
        mock_bmad_trigger = mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_bmad_file",
        )
        mock_bmad_dispatch = mocker.patch(
            "adws.adw_dispatch.io_ops.read_bmad_file",
        )
        run_poll_cycle()
        mock_bmad_trigger.assert_not_called()
        mock_bmad_dispatch.assert_not_called()

"""Tests for cron trigger module (Story 7.3)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestPollReadyIssues:
    """Tests for poll_ready_issues function."""

    def test_filters_to_dispatchable_tags(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given open issues, filters to those with dispatchable workflow tags."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(
                "ISSUE-1\nISSUE-2\nISSUE-3\n",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            side_effect=[
                IOSuccess(
                    "Content\n\n{implement_verify_close}",
                ),
                IOSuccess("Content\n\n{implement_close}"),
                IOSuccess("No workflow tag here"),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-1", "ISSUE-2"]

    def test_dispatch_guard_filters_failed(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given ADWS_FAILED metadata, issue is excluded."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess("ISSUE-1\nISSUE-2\n"),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            side_effect=[
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            side_effect=[
                IOSuccess("ADWS_FAILED|attempt=1|..."),
                IOSuccess(""),
            ],
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-2"]

    def test_dispatch_guard_filters_needs_human(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given needs_human metadata, issue is excluded."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess("ISSUE-1\nISSUE-2\n"),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            side_effect=[
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            side_effect=[
                IOSuccess("needs_human: review required"),
                IOSuccess(""),
            ],
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-2"]

    def test_beads_list_failure_propagates(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given run_beads_list failure, propagates IOFailure."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        err = PipelineError(
            step_name="io_ops.run_beads_list",
            error_type="BeadsListError",
            message="bd list failed",
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOFailure(err),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOFailure)
        error = unsafe_perform_io(result.failure())
        assert error is err

    def test_no_open_issues(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given no open issues, returns IOSuccess([])."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(""),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == []

    def test_description_read_failure_skips_issue(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given description read fails for one issue, skips it."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(
                "ISSUE-1\nISSUE-2\nISSUE-3\n",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            side_effect=[
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
                IOFailure(
                    PipelineError(
                        step_name="io_ops",
                        error_type="BeadsShowError",
                        message="bd show failed",
                    ),
                ),
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-1", "ISSUE-3"]

    def test_non_dispatchable_workflow_excluded(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given non-dispatchable workflow tag, issue is excluded."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(
                "ISSUE-1\nISSUE-2\n",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            side_effect=[
                IOSuccess(
                    "Content\n\n{convert_stories_to_beads}",
                ),
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-2"]

    def test_unknown_workflow_tag_excluded(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given unknown workflow tag (no registered workflow), issue excluded."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
        )

        mocker.patch(
            "adws.adw_trigger_cron.io_ops.run_beads_list",
            return_value=IOSuccess(
                "ISSUE-1\nISSUE-2\n",
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_description",
            side_effect=[
                IOSuccess(
                    "Content\n\n{totally_unknown}",
                ),
                IOSuccess(
                    "Content\n\n{implement_close}",
                ),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOSuccess(""),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-2"]

    def test_guard_io_failure_allows_dispatch(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given read_issue_notes IOFailure, issue dispatched (fail-open)."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
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
        # Mock read_issue_notes to return IOFailure -- the
        # check_dispatch_guard .lash() fail-open should convert
        # this to IOSuccess(True), allowing dispatch.
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_issue_notes",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.read_issue_notes",
                    error_type="BeadsShowNotesError",
                    message="bd show --notes failed",
                ),
            ),
        )
        result = poll_ready_issues()
        assert isinstance(result, IOSuccess)
        ids = unsafe_perform_io(result.unwrap())
        assert ids == ["ISSUE-1"]

    def test_never_reads_bmad_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """poll_ready_issues never calls read_bmad_file (NFR19)."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            poll_ready_issues,
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
        mock_bmad = mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_bmad_file",
        )
        poll_ready_issues()
        mock_bmad.assert_not_called()


class TestRunPollCycle:
    """Tests for run_poll_cycle function."""

    def test_success_dispatches_all(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given ready issues, dispatches and succeeds all."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
        )
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.poll_ready_issues",
            return_value=IOSuccess(
                ["ISSUE-1", "ISSUE-2"],
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.dispatch_and_execute",
            return_value=IOSuccess(
                DispatchExecutionResult(
                    success=True,
                    workflow_executed="implement_close",
                    issue_id="X",
                    finalize_action="closed",
                    summary="OK",
                ),
            ),
        )
        result = run_poll_cycle()
        assert result.issues_found == 2
        assert result.issues_dispatched == 2
        assert result.issues_succeeded == 2
        assert result.issues_failed == 0
        assert result.issues_skipped == 0
        assert result.errors == []

    def test_mixed_success_and_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given one success and one failure, both processed."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
        )
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.poll_ready_issues",
            return_value=IOSuccess(
                ["ISSUE-1", "ISSUE-2"],
            ),
        )
        mocker.patch(
            "adws.adw_trigger_cron.dispatch_and_execute",
            side_effect=[
                IOSuccess(
                    DispatchExecutionResult(
                        success=True,
                        workflow_executed="implement_close",
                        issue_id="ISSUE-1",
                        finalize_action="closed",
                        summary="OK",
                    ),
                ),
                IOSuccess(
                    DispatchExecutionResult(
                        success=False,
                        workflow_executed="implement_close",
                        issue_id="ISSUE-2",
                        finalize_action="tagged_failure",
                        summary="Failed: timeout",
                    ),
                ),
            ],
        )
        result = run_poll_cycle()
        assert result.issues_succeeded == 1
        assert result.issues_failed == 1
        assert result.issues_dispatched == 2

    def test_dispatch_io_failure_skips_issue(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given dispatch_and_execute returns IOFailure, issue is skipped."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.poll_ready_issues",
            return_value=IOSuccess(["ISSUE-1"]),
        )
        mocker.patch(
            "adws.adw_trigger_cron.dispatch_and_execute",
            return_value=IOFailure(
                PipelineError(
                    step_name="adw_dispatch",
                    error_type="ValueError",
                    message="infrastructure error",
                ),
            ),
        )
        result = run_poll_cycle()
        assert result.issues_skipped == 1
        assert len(result.errors) == 1
        assert "infrastructure error" in result.errors[0]

    def test_poll_failure_handled_gracefully(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given poll_ready_issues returns IOFailure, cycle doesn't crash."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.poll_ready_issues",
            return_value=IOFailure(
                PipelineError(
                    step_name="io_ops.run_beads_list",
                    error_type="BeadsListError",
                    message="poll failed",
                ),
            ),
        )
        result = run_poll_cycle()
        assert result.issues_found == 0
        assert result.issues_dispatched == 0
        assert len(result.errors) == 1
        assert "poll failed" in result.errors[0]

    def test_empty_poll_result(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given no ready issues, returns empty CronCycleResult."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.poll_ready_issues",
            return_value=IOSuccess([]),
        )
        result = run_poll_cycle()
        assert result.issues_found == 0
        assert result.issues_dispatched == 0
        assert result.issues_succeeded == 0
        assert result.issues_failed == 0
        assert result.errors == []

    def test_never_reads_bmad_files(
        self,
        mocker: MockerFixture,
    ) -> None:
        """run_poll_cycle never calls read_bmad_file (NFR19)."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            run_poll_cycle,
        )

        mocker.patch(
            "adws.adw_trigger_cron.poll_ready_issues",
            return_value=IOSuccess([]),
        )
        mock_bmad = mocker.patch(
            "adws.adw_trigger_cron.io_ops.read_bmad_file",
        )
        run_poll_cycle()
        mock_bmad.assert_not_called()


class TestRunTriggerLoop:
    """Tests for run_trigger_loop function."""

    def test_max_cycles_two(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given max_cycles=2, runs exactly 2 cycles with sleep between."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            run_trigger_loop,
        )

        mocker.patch(
            "adws.adw_trigger_cron.run_poll_cycle",
            return_value=CronCycleResult(
                issues_found=0,
                issues_dispatched=0,
                issues_succeeded=0,
                issues_failed=0,
                issues_skipped=0,
                errors=[],
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
            poll_interval_seconds=5.0,
            max_cycles=2,
        )
        assert len(results) == 2
        mock_sleep.assert_called_once_with(5.0)

    def test_varying_results_across_cycles(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given 3 cycles with varying results, all captured."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            run_trigger_loop,
        )

        mocker.patch(
            "adws.adw_trigger_cron.run_poll_cycle",
            side_effect=[
                CronCycleResult(
                    issues_found=2,
                    issues_dispatched=2,
                    issues_succeeded=2,
                    issues_failed=0,
                    issues_skipped=0,
                    errors=[],
                ),
                CronCycleResult(
                    issues_found=1,
                    issues_dispatched=1,
                    issues_succeeded=0,
                    issues_failed=1,
                    issues_skipped=0,
                    errors=[],
                ),
                CronCycleResult(
                    issues_found=0,
                    issues_dispatched=0,
                    issues_succeeded=0,
                    issues_failed=0,
                    issues_skipped=0,
                    errors=[],
                ),
            ],
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
            poll_interval_seconds=1.0,
            max_cycles=3,
        )
        assert len(results) == 3
        assert results[0].issues_found == 2
        assert results[1].issues_failed == 1
        assert results[2].issues_found == 0
        assert mock_sleep.call_count == 2

    def test_single_cycle_no_sleep(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given max_cycles=1, no sleep is called."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            run_trigger_loop,
        )

        mocker.patch(
            "adws.adw_trigger_cron.run_poll_cycle",
            return_value=CronCycleResult(
                issues_found=0,
                issues_dispatched=0,
                issues_succeeded=0,
                issues_failed=0,
                issues_skipped=0,
                errors=[],
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
            poll_interval_seconds=5.0,
            max_cycles=1,
        )
        assert len(results) == 1
        mock_sleep.assert_not_called()

    def test_unexpected_exception_caught(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given run_poll_cycle raises exception, loop catches and continues."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            run_trigger_loop,
        )

        mocker.patch(
            "adws.adw_trigger_cron.run_poll_cycle",
            side_effect=[
                RuntimeError("unexpected error"),
                CronCycleResult(
                    issues_found=0,
                    issues_dispatched=0,
                    issues_succeeded=0,
                    issues_failed=0,
                    issues_skipped=0,
                    errors=[],
                ),
            ],
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.sleep_seconds",
            return_value=IOSuccess(None),
        )
        mocker.patch(
            "adws.adw_trigger_cron.io_ops.write_stderr",
            return_value=IOSuccess(None),
        )
        results = run_trigger_loop(
            poll_interval_seconds=0.0,
            max_cycles=2,
        )
        assert len(results) == 2
        assert len(results[0].errors) == 1
        assert "unexpected error" in results[0].errors[0]
        assert results[1].errors == []


class TestFormatCycleSummary:
    """Tests for format_cycle_summary pure function."""

    def test_formats_key_metrics(self) -> None:
        """Given a CronCycleResult, formats key metrics including skipped."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            format_cycle_summary,
        )

        result = CronCycleResult(
            issues_found=3,
            issues_dispatched=2,
            issues_succeeded=1,
            issues_failed=1,
            issues_skipped=0,
            errors=[],
        )
        summary = format_cycle_summary(result)
        assert "3 found" in summary
        assert "2 dispatched" in summary
        assert "1 succeeded" in summary
        assert "1 failed" in summary
        assert "0 skipped" in summary

    def test_formats_with_skipped(self) -> None:
        """Given issues_skipped > 0, includes skipped count."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            format_cycle_summary,
        )

        result = CronCycleResult(
            issues_found=3,
            issues_dispatched=3,
            issues_succeeded=1,
            issues_failed=0,
            issues_skipped=2,
            errors=["err1", "err2"],
        )
        summary = format_cycle_summary(result)
        assert "2 skipped" in summary
        assert "2 errors" in summary

    def test_formats_with_errors(self) -> None:
        """Given a CronCycleResult with errors, includes error count."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            format_cycle_summary,
        )

        result = CronCycleResult(
            issues_found=0,
            issues_dispatched=0,
            issues_succeeded=0,
            issues_failed=0,
            issues_skipped=0,
            errors=["Poll failed: timeout"],
        )
        summary = format_cycle_summary(result)
        assert "1 error" in summary


class TestLogCycleResult:
    """Tests for log_cycle_result function."""

    def test_writes_to_stderr(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Given a CronCycleResult, writes formatted summary to stderr."""
        from adws.adw_trigger_cron import (  # noqa: PLC0415
            CronCycleResult,
            log_cycle_result,
        )

        mock_stderr = mocker.patch(
            "adws.adw_trigger_cron.io_ops.write_stderr",
            return_value=IOSuccess(None),
        )
        result = CronCycleResult(
            issues_found=2,
            issues_dispatched=2,
            issues_succeeded=2,
            issues_failed=0,
            issues_skipped=0,
            errors=[],
        )
        log_cycle_result(result)
        mock_stderr.assert_called_once()
        call_arg = mock_stderr.call_args[0][0]
        assert "2 found" in call_arg

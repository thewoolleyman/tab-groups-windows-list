"""Tests for CLI entry points in ADWS executable scripts.

Covers the Click command functions in adw_dispatch.py,
adw_trigger_cron.py, and adw_triage.py. Uses Click's
CliRunner for in-process testing (counts toward coverage).
"""
from __future__ import annotations

from unittest.mock import patch

import click.testing
from returns.io import IOFailure, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_trigger_cron import CronCycleResult


class TestTriggerCronCLI:
    """Tests for adw_trigger_cron.py CLI."""

    def test_dry_run_no_issues(self) -> None:
        """--dry-run with no ready issues prints message."""
        from adws.adw_trigger_cron import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_trigger_cron.poll_ready_issues",
        ) as mock_poll:
            mock_poll.return_value = IOSuccess([])
            result = runner.invoke(main, ["--dry-run"])
        assert result.exit_code == 0
        assert "No ready issues" in result.output

    def test_dry_run_with_ready_issues(self) -> None:
        """--dry-run lists ready issue IDs."""
        from adws.adw_trigger_cron import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_trigger_cron.poll_ready_issues",
        ) as mock_poll:
            mock_poll.return_value = IOSuccess(
                ["beads-abc", "beads-def"],
            )
            result = runner.invoke(main, ["--dry-run"])
        assert result.exit_code == 0
        assert "beads-abc" in result.output
        assert "beads-def" in result.output

    def test_dry_run_poll_failure(self) -> None:
        """--dry-run exits 1 on poll failure."""
        from adws.adw_trigger_cron import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_trigger_cron.poll_ready_issues",
        ) as mock_poll:
            mock_poll.return_value = IOFailure(
                PipelineError(
                    step_name="test",
                    error_type="TestError",
                    message="poll failed",
                    context={},
                ),
            )
            result = runner.invoke(main, ["--dry-run"])
        assert result.exit_code != 0

    def test_single_cycle_default(self) -> None:
        """Default (no --poll) runs one cycle via run_trigger_loop."""
        from adws.adw_trigger_cron import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_trigger_cron.run_trigger_loop",
        ) as mock_loop:
            mock_loop.return_value = [
                CronCycleResult(
                    issues_found=0,
                    issues_dispatched=0,
                    issues_succeeded=0,
                    issues_failed=0,
                    issues_skipped=0,
                    errors=[],
                ),
            ]
            result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_loop.assert_called_once_with(
            poll_interval_seconds=60.0,
            max_cycles=1,
        )

    def test_poll_mode_unlimited_cycles(self) -> None:
        """--poll passes max_cycles=None to run_trigger_loop."""
        from adws.adw_trigger_cron import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_trigger_cron.run_trigger_loop",
        ) as mock_loop:
            mock_loop.return_value = []
            result = runner.invoke(main, ["--poll", "--max-cycles=1"])
        assert result.exit_code == 0
        mock_loop.assert_called_once_with(
            poll_interval_seconds=60.0,
            max_cycles=1,
        )

    def test_errors_cause_nonzero_exit(self) -> None:
        """Cycle with errors causes exit code 1."""
        from adws.adw_trigger_cron import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_trigger_cron.run_trigger_loop",
        ) as mock_loop:
            mock_loop.return_value = [
                CronCycleResult(
                    issues_found=1,
                    issues_dispatched=1,
                    issues_succeeded=0,
                    issues_failed=0,
                    issues_skipped=1,
                    errors=["some error"],
                ),
            ]
            result = runner.invoke(main, [])
        assert result.exit_code != 0


class TestTriageCLI:
    """Tests for adw_triage.py CLI."""

    def test_dry_run_no_failed_issues(self) -> None:
        """--dry-run with no failed issues prints message."""
        from adws.adw_triage import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_triage.poll_failed_issues",
        ) as mock_poll:
            mock_poll.return_value = IOSuccess([])
            result = runner.invoke(main, ["--dry-run"])
        assert result.exit_code == 0
        assert "No failed issues" in result.output

    def test_dry_run_with_candidates(self) -> None:
        """--dry-run lists failed issue details."""
        from adws.adw_triage import (  # noqa: PLC0415
            TriageCandidate,
            main,
        )
        from adws.adw_modules.steps.triage import (  # noqa: PLC0415
            FailureMetadata,
        )

        runner = click.testing.CliRunner()
        candidate = TriageCandidate(
            issue_id="beads-xyz",
            metadata=FailureMetadata(
                attempt=2,
                error_class="SdkError",
                step="execute_sdk_call",
                summary="SDK timeout",
                last_failure="2025-01-01T00:00:00Z",
            ),
        )
        with patch(
            "adws.adw_triage.poll_failed_issues",
        ) as mock_poll:
            mock_poll.return_value = IOSuccess([candidate])
            result = runner.invoke(main, ["--dry-run"])
        assert result.exit_code == 0
        assert "beads-xyz" in result.output
        assert "attempt 2" in result.output

    def test_dry_run_poll_failure(self) -> None:
        """--dry-run exits 1 on poll failure."""
        from adws.adw_triage import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_triage.poll_failed_issues",
        ) as mock_poll:
            mock_poll.return_value = IOFailure(
                PipelineError(
                    step_name="test",
                    error_type="TestError",
                    message="poll failed",
                    context={},
                ),
            )
            result = runner.invoke(main, ["--dry-run"])
        assert result.exit_code != 0

    def test_single_cycle_default(self) -> None:
        """Default (no --poll) runs one triage cycle."""
        from adws.adw_triage import (  # noqa: PLC0415
            TriageCycleResult,
            main,
        )

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_triage.run_triage_loop",
        ) as mock_loop:
            mock_loop.return_value = [
                TriageCycleResult(
                    issues_found=0,
                    tier1_cleared=0,
                    tier1_pending=0,
                    tier2_adjusted=0,
                    tier2_split=0,
                    tier3_escalated=0,
                    triage_errors=0,
                    errors=[],
                ),
            ]
            result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_loop.assert_called_once_with(
            poll_interval_seconds=300.0,
            max_cycles=1,
        )

    def test_errors_cause_nonzero_exit(self) -> None:
        """Triage cycle with errors causes exit code 1."""
        from adws.adw_triage import (  # noqa: PLC0415
            TriageCycleResult,
            main,
        )

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_triage.run_triage_loop",
        ) as mock_loop:
            mock_loop.return_value = [
                TriageCycleResult(
                    issues_found=1,
                    tier1_cleared=0,
                    tier1_pending=0,
                    tier2_adjusted=0,
                    tier2_split=0,
                    tier3_escalated=0,
                    triage_errors=1,
                    errors=["triage error"],
                ),
            ]
            result = runner.invoke(main, [])
        assert result.exit_code != 0


class TestDispatchCLI:
    """Tests for adw_dispatch.py CLI."""

    def test_list_flag_shows_workflows(self) -> None:
        """--list shows dispatchable workflow names."""
        from adws.adw_dispatch import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.workflows.list_dispatchable_workflows",
        ) as mock_list:
            mock_list.return_value = [
                "implement_close",
                "implement_verify_close",
            ]
            result = runner.invoke(main, ["--list"])
        assert result.exit_code == 0
        assert "implement_close" in result.output

    def test_list_flag_no_workflows(self) -> None:
        """--list with no workflows prints message."""
        from adws.adw_dispatch import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.workflows.list_dispatchable_workflows",
        ) as mock_list:
            mock_list.return_value = []
            result = runner.invoke(main, ["--list"])
        assert result.exit_code == 0
        assert "No dispatchable workflows" in result.output

    def test_no_args_shows_error(self) -> None:
        """No arguments shows usage error."""
        from adws.adw_dispatch import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code != 0
        assert "specify --issue" in result.output or "Error" in result.output

    def test_issue_dispatch_success(self) -> None:
        """--issue with successful dispatch exits 0."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
            main,
        )

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_dispatch.dispatch_and_execute",
        ) as mock_exec:
            mock_exec.return_value = IOSuccess(
                DispatchExecutionResult(
                    success=True,
                    workflow_executed="implement_close",
                    issue_id="beads-abc",
                    finalize_action="closed",
                    summary="Completed successfully",
                ),
            )
            result = runner.invoke(main, ["--issue=beads-abc"])
        assert result.exit_code == 0
        assert "Success" in result.output

    def test_issue_dispatch_failure(self) -> None:
        """--issue with IOFailure exits 1."""
        from adws.adw_dispatch import main  # noqa: PLC0415

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_dispatch.dispatch_and_execute",
        ) as mock_exec:
            mock_exec.return_value = IOFailure(
                PipelineError(
                    step_name="test",
                    error_type="TestError",
                    message="dispatch failed",
                    context={},
                ),
            )
            result = runner.invoke(main, ["--issue=beads-abc"])
        assert result.exit_code != 0
        assert "dispatch failed" in result.output

    def test_issue_workflow_failure(self) -> None:
        """--issue with workflow failure (success=False) exits 1."""
        from adws.adw_dispatch import (  # noqa: PLC0415
            DispatchExecutionResult,
            main,
        )

        runner = click.testing.CliRunner()
        with patch(
            "adws.adw_dispatch.dispatch_and_execute",
        ) as mock_exec:
            mock_exec.return_value = IOSuccess(
                DispatchExecutionResult(
                    success=False,
                    workflow_executed="implement_close",
                    issue_id="beads-abc",
                    finalize_action="tagged_failure",
                    summary="Failed: step X error",
                ),
            )
            result = runner.invoke(main, ["--issue=beads-abc"])
        assert result.exit_code != 0
        assert "Failed" in result.output

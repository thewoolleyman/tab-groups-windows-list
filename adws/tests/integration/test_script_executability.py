"""Smoke tests: ADWS scripts must be directly executable with uv run.

These scripts are meant to be invoked as:
    uv run adws/adw_trigger_cron.py --dry-run
    uv run adws/adw_dispatch.py --list

These tests verify the scripts have working CLI entry points
(Click commands, __main__ blocks) and that imports resolve
when run as scripts. They exercise --help as the cheapest
possible invocation that proves the CLI is wired up.
"""
from __future__ import annotations

import subprocess
import sys


def _run_script(script_path: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run an adws script as a subprocess and return the result."""
    return subprocess.run(  # noqa: S603
        [sys.executable, script_path, *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


class TestAdwTriggerCronExecutable:
    """adw_trigger_cron.py must be directly executable."""

    def test_help_flag_works(self) -> None:
        """'python adws/adw_trigger_cron.py --help' should print usage and exit 0."""
        result = _run_script("adws/adw_trigger_cron.py", "--help")
        assert result.returncode == 0, (
            f"adw_trigger_cron.py --help failed (rc={result.returncode}):\n"
            f"stderr: {result.stderr}"
        )
        assert "Usage" in result.stdout or "usage" in result.stdout

    def test_no_import_errors(self) -> None:
        """Running the script should not crash with ModuleNotFoundError."""
        result = _run_script("adws/adw_trigger_cron.py", "--help")
        assert "ModuleNotFoundError" not in result.stderr
        assert "ImportError" not in result.stderr

    def test_dry_run_flag_exists(self) -> None:
        """--dry-run should be a recognized option."""
        result = _run_script("adws/adw_trigger_cron.py", "--help")
        assert result.returncode == 0
        assert "dry-run" in result.stdout or "dry_run" in result.stdout


class TestAdwTriageExecutable:
    """adw_triage.py must be directly executable."""

    def test_help_flag_works(self) -> None:
        """'python adws/adw_triage.py --help' should print usage and exit 0."""
        result = _run_script("adws/adw_triage.py", "--help")
        assert result.returncode == 0, (
            f"adw_triage.py --help failed (rc={result.returncode}):\n"
            f"stderr: {result.stderr}"
        )
        assert "Usage" in result.stdout or "usage" in result.stdout

    def test_no_import_errors(self) -> None:
        """Running the script should not crash with ModuleNotFoundError."""
        result = _run_script("adws/adw_triage.py", "--help")
        assert "ModuleNotFoundError" not in result.stderr
        assert "ImportError" not in result.stderr


class TestAdwDispatchExecutable:
    """adw_dispatch.py must be directly executable."""

    def test_help_flag_works(self) -> None:
        """'python adws/adw_dispatch.py --help' should print usage and exit 0."""
        result = _run_script("adws/adw_dispatch.py", "--help")
        assert result.returncode == 0, (
            f"adw_dispatch.py --help failed (rc={result.returncode}):\n"
            f"stderr: {result.stderr}"
        )
        assert "Usage" in result.stdout or "usage" in result.stdout

    def test_no_import_errors(self) -> None:
        """Running the script should not crash with ModuleNotFoundError."""
        result = _run_script("adws/adw_dispatch.py", "--help")
        assert "ModuleNotFoundError" not in result.stderr
        assert "ImportError" not in result.stderr

    def test_list_flag_exists(self) -> None:
        """--list should be a recognized option."""
        result = _run_script("adws/adw_dispatch.py", "--help")
        assert result.returncode == 0
        assert "--list" in result.stdout

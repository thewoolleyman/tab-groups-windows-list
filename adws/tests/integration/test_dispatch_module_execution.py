"""Integration test for dispatch module execution without RuntimeWarning."""
from __future__ import annotations

import subprocess
import sys


def test_dispatch_module_runs_without_runtime_warning() -> None:
    """Running dispatch as module should not produce RuntimeWarning.

    When running 'python -m adws.adw_modules.commands.dispatch --help',
    there should be no RuntimeWarning about the module being found in
    sys.modules before execution.

    This is RED phase - test should FAIL until we fix __init__.py
    """
    # Run dispatch as a module
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "adws.adw_modules.commands.dispatch",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Check stderr for RuntimeWarning
    assert "RuntimeWarning" not in result.stderr, (
        f"Expected no RuntimeWarning, but got:\n{result.stderr}"
    )

    # Verify the command at least tried to run (may fail for other reasons)
    # We're just checking there's no import-related RuntimeWarning

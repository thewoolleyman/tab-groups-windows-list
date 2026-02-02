"""Wiring verification tests for command pattern (AC #3).

These tests verify the structural integrity of the command
pattern: module imports, workflow mappings, and .md file
existence. No mocks -- these test real wiring.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from adws.adw_modules.commands.registry import COMMAND_REGISTRY
from adws.workflows import load_workflow

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


# --- Package export wiring tests ---


def test_import_command_spec_from_package() -> None:
    """CommandSpec is importable from adws.adw_modules.commands."""
    from adws.adw_modules.commands import CommandSpec  # noqa: PLC0415

    assert CommandSpec is not None


def test_import_get_command_from_package() -> None:
    """get_command is importable from adws.adw_modules.commands."""
    from adws.adw_modules.commands import get_command  # noqa: PLC0415

    assert callable(get_command)


def test_import_list_commands_from_package() -> None:
    """list_commands is importable from adws.adw_modules.commands."""
    from adws.adw_modules.commands import list_commands  # noqa: PLC0415

    assert callable(list_commands)


def test_import_run_command_from_package() -> None:
    """run_command is importable from adws.adw_modules.commands."""
    from adws.adw_modules.commands import run_command  # noqa: PLC0415

    assert callable(run_command)


def test_import_verify_command_result_from_package() -> None:
    """VerifyCommandResult importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        VerifyCommandResult,
    )

    assert VerifyCommandResult is not None


def test_import_run_verify_command_from_package() -> None:
    """run_verify_command importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        run_verify_command,
    )

    assert callable(run_verify_command)


# --- Module import wiring tests ---


def test_wiring_all_commands_have_importable_modules() -> None:
    """Every command's python_module is importable."""
    for name, spec in COMMAND_REGISTRY.items():
        mod = importlib.import_module(spec.python_module)
        assert mod is not None, (
            f"Command '{name}' module"
            f" '{spec.python_module}' not importable"
        )


# --- Workflow mapping wiring tests ---


def test_wiring_workflow_commands_map_to_registered() -> None:
    """Every command with a workflow_name maps to a real workflow."""
    for name, spec in COMMAND_REGISTRY.items():
        if spec.workflow_name is not None:
            wf = load_workflow(spec.workflow_name)
            assert wf is not None, (
                f"Command '{name}' references workflow"
                f" '{spec.workflow_name}' which is not"
                f" registered"
            )
            assert wf.name == spec.workflow_name


# --- .md file existence wiring tests ---


def test_wiring_verify_md_exists() -> None:
    """adws-verify.md exists with delegation instructions."""
    md_path = _PROJECT_ROOT / ".claude" / "commands" / "adws-verify.md"
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "adws.adw_modules.commands.dispatch" in content
    assert "verify" in content


def test_wiring_verify_md_references_verify_module() -> None:
    """adws-verify.md references the verify-specific module."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands" / "adws-verify.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "run_verify_command" in content


def test_wiring_build_md_exists() -> None:
    """adws-build.md exists in .claude/commands/."""
    md_path = _PROJECT_ROOT / ".claude" / "commands" / "adws-build.md"
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "adws.adw_modules.commands.dispatch" in content
    assert "build" in content


def test_wiring_prime_md_exists() -> None:
    """adws-prime.md exists in .claude/commands/."""
    md_path = _PROJECT_ROOT / ".claude" / "commands" / "adws-prime.md"
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "adws.adw_modules.commands.dispatch" in content
    assert "prime" in content


def test_wiring_implement_md_exists() -> None:
    """adws-implement.md exists in .claude/commands/."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands" / "adws-implement.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "adws.adw_modules.commands.dispatch" in content
    assert "implement" in content


def test_import_prime_context_result_from_package() -> None:
    """PrimeContextResult importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        PrimeContextResult,
    )

    assert PrimeContextResult is not None


def test_import_prime_file_spec_from_package() -> None:
    """PrimeFileSpec importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        PrimeFileSpec,
    )

    assert PrimeFileSpec is not None


def test_import_run_prime_command_from_package() -> None:
    """run_prime_command importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        run_prime_command,
    )

    assert callable(run_prime_command)


def test_wiring_prime_md_references_prime_module() -> None:
    """adws-prime.md references the prime-specific module."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands" / "adws-prime.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "run_prime_command" in content
    assert "adws.adw_modules.commands.prime" in content


def test_wiring_prime_md_not_stub() -> None:
    """adws-prime.md is no longer marked as stub."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands" / "adws-prime.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "stub" not in content.lower()
    assert "Story 4.3" not in content


def test_wiring_all_md_files_follow_template() -> None:
    """All command .md files have consistent structure."""
    md_dir = _PROJECT_ROOT / ".claude" / "commands"
    expected_files = [
        "adws-verify.md",
        "adws-build.md",
        "adws-prime.md",
        "adws-implement.md",
        "adws-load-bundle.md",
    ]
    for filename in expected_files:
        md_path = md_dir / filename
        assert md_path.exists(), f"Missing: {md_path}"
        content = md_path.read_text()
        assert "# /adws-" in content, (
            f"{filename} missing title"
        )
        assert "## Usage" in content, (
            f"{filename} missing Usage section"
        )
        assert "## What it does" in content, (
            f"{filename} missing What it does section"
        )
        assert "## Implementation" in content, (
            f"{filename} missing Implementation section"
        )
        assert "FR28" in content, (
            f"{filename} missing FR28 reference"
        )


# --- Build command wiring tests (Story 4.4) ---


def test_import_build_command_result_from_package() -> None:
    """BuildCommandResult importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        BuildCommandResult,
    )

    assert BuildCommandResult is not None


def test_import_run_build_command_from_package() -> None:
    """run_build_command importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        run_build_command,
    )

    assert callable(run_build_command)


def test_wiring_build_md_references_build_module() -> None:
    """adws-build.md references the build-specific module."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands"
        / "adws-build.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "run_build_command" in content
    assert "adws.adw_modules.commands.build" in content


def test_wiring_build_md_not_stub() -> None:
    """adws-build.md is no longer marked as stub."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands"
        / "adws-build.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "stub" not in content.lower()
    assert "Story 4.4" not in content


# --- Load bundle command wiring tests (Story 5.3) ---


def test_import_load_bundle_result_from_package() -> None:
    """LoadBundleResult importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        LoadBundleResult,
    )

    assert LoadBundleResult is not None


def test_import_run_load_bundle_command_from_package() -> None:
    """run_load_bundle_command importable from commands package."""
    from adws.adw_modules.commands import (  # noqa: PLC0415
        run_load_bundle_command,
    )

    assert callable(run_load_bundle_command)


def test_wiring_load_bundle_md_exists() -> None:
    """adws-load-bundle.md exists in .claude/commands/."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands"
        / "adws-load-bundle.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "adws.adw_modules.commands.dispatch" in content
    assert "load_bundle" in content


def test_wiring_load_bundle_md_references_module() -> None:
    """adws-load-bundle.md references the load_bundle module."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands"
        / "adws-load-bundle.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "run_load_bundle_command" in content
    assert (
        "adws.adw_modules.commands.load_bundle"
        in content
    )


def test_wiring_load_bundle_md_not_stub() -> None:
    """adws-load-bundle.md is not marked as stub."""
    md_path = (
        _PROJECT_ROOT / ".claude" / "commands"
        / "adws-load-bundle.md"
    )
    assert md_path.exists(), f"Missing: {md_path}"
    content = md_path.read_text()
    assert "stub" not in content.lower()

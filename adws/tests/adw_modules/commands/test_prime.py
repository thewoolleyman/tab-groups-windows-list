"""Tests for /prime command -- context loading (Story 4.3).

Tests cover PrimeContextResult, PrimeFileSpec, PRIME_FILE_SPECS,
_load_file_context, _load_directory_context, run_prime_command.
All io_ops calls are mocked per NFR10.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.commands.prime import (
    PRIME_FILE_SPECS,
    PrimeContextResult,
    PrimeFileSpec,
    _load_directory_context,
    _load_file_context,
    run_prime_command,
)
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- Task 1: PrimeContextResult tests ---


def test_prime_context_result_construction() -> None:
    """PrimeContextResult can be constructed with all fields."""
    result = PrimeContextResult(
        success=True,
        files_loaded=["CLAUDE.md"],
        summary="Loaded 1 file",
        context_sections={"claude_md": "content"},
    )
    assert result.success is True
    assert result.files_loaded == ["CLAUDE.md"]
    assert result.summary == "Loaded 1 file"
    assert result.context_sections == {"claude_md": "content"}


def test_prime_context_result_immutable() -> None:
    """PrimeContextResult is frozen -- no attribute reassignment."""
    result = PrimeContextResult(
        success=True,
        files_loaded=[],
        summary="test",
        context_sections={},
    )
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


def test_prime_context_result_default_context_sections() -> None:
    """PrimeContextResult defaults context_sections to empty dict."""
    result = PrimeContextResult(
        success=True,
        files_loaded=[],
        summary="test",
    )
    assert result.context_sections == {}


# --- Task 2: PrimeFileSpec and PRIME_FILE_SPECS tests ---


def test_prime_file_spec_construction() -> None:
    """PrimeFileSpec can be constructed with all fields."""
    spec = PrimeFileSpec(
        key="test_key",
        path="test/path.md",
        description="Test file",
        required=True,
    )
    assert spec.key == "test_key"
    assert spec.path == "test/path.md"
    assert spec.description == "Test file"
    assert spec.required is True


def test_prime_file_spec_immutable() -> None:
    """PrimeFileSpec is frozen -- no attribute reassignment."""
    spec = PrimeFileSpec(
        key="k",
        path="p",
        description="d",
        required=False,
    )
    with pytest.raises(AttributeError):
        spec.key = "new"  # type: ignore[misc]


def test_prime_file_specs_is_tuple() -> None:
    """PRIME_FILE_SPECS is a tuple (immutable container)."""
    assert isinstance(PRIME_FILE_SPECS, tuple)


def test_prime_file_specs_contain_claude_md() -> None:
    """PRIME_FILE_SPECS includes CLAUDE.md as required."""
    keys = {s.key for s in PRIME_FILE_SPECS}
    assert "claude_md" in keys
    claude_spec = next(
        s for s in PRIME_FILE_SPECS if s.key == "claude_md"
    )
    assert claude_spec.path == "CLAUDE.md"
    assert claude_spec.required is True


def test_prime_file_specs_contain_architecture() -> None:
    """PRIME_FILE_SPECS includes architecture.md as optional."""
    keys = {s.key for s in PRIME_FILE_SPECS}
    assert "architecture" in keys
    arch_spec = next(
        s for s in PRIME_FILE_SPECS if s.key == "architecture"
    )
    assert arch_spec.required is False


def test_prime_file_specs_contain_epics() -> None:
    """PRIME_FILE_SPECS includes epics.md as optional."""
    keys = {s.key for s in PRIME_FILE_SPECS}
    assert "epics" in keys
    epics_spec = next(
        s for s in PRIME_FILE_SPECS if s.key == "epics"
    )
    assert epics_spec.required is False


def test_prime_file_specs_no_secret_paths() -> None:
    """PRIME_FILE_SPECS does not reference secret-bearing paths."""
    secret_segments = [
        ".env",
        "credentials",
        "secrets",
        "api_key",
        ".env.sample",
    ]
    for spec in PRIME_FILE_SPECS:
        path_lower = spec.path.lower()
        for segment in secret_segments:
            assert segment not in path_lower, (
                f"PRIME_FILE_SPECS path '{spec.path}'"
                f" contains secret segment '{segment}'"
            )


def test_prime_file_specs_all_have_descriptions() -> None:
    """Every PrimeFileSpec has a non-empty description."""
    for spec in PRIME_FILE_SPECS:
        assert spec.description, (
            f"PrimeFileSpec '{spec.key}' has empty description"
        )


# --- Task 4: _load_file_context tests ---


def test_load_file_context_all_files_exist(
    mocker: MockerFixture,
) -> None:
    """_load_file_context returns IOSuccess when all files exist."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("claude content"),
            IOSuccess("arch content"),
            IOSuccess("epics content"),
        ],
    )
    result = _load_file_context(PRIME_FILE_SPECS)
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    assert isinstance(pcr, PrimeContextResult)
    assert pcr.success is True
    assert len(pcr.files_loaded) == 3
    assert pcr.context_sections["claude_md"] == "claude content"
    assert pcr.context_sections["architecture"] == "arch content"
    assert pcr.context_sections["epics"] == "epics content"
    assert "3" in pcr.summary


def test_load_file_context_optional_file_missing(
    mocker: MockerFixture,
) -> None:
    """_load_file_context skips optional files gracefully."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("claude content"),
            IOFailure(
                PipelineError(
                    step_name="io_ops.read_prime_file",
                    error_type="FileNotFoundError",
                    message="Not found: architecture.md",
                ),
            ),
            IOSuccess("epics content"),
        ],
    )
    result = _load_file_context(PRIME_FILE_SPECS)
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    assert pcr.success is True
    assert "architecture.md" not in " ".join(pcr.files_loaded)
    assert "architecture" not in pcr.context_sections
    assert "CLAUDE.md" in " ".join(pcr.files_loaded)
    assert "skipped" in pcr.summary.lower()


def test_load_file_context_required_file_missing(
    mocker: MockerFixture,
) -> None:
    """_load_file_context fails when a required file is missing."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOFailure(
                PipelineError(
                    step_name="io_ops.read_prime_file",
                    error_type="FileNotFoundError",
                    message="Not found: CLAUDE.md",
                ),
            ),
        ],
    )
    result = _load_file_context(PRIME_FILE_SPECS)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "RequiredFileError"
    assert "CLAUDE.md" in error.message


def test_load_file_context_empty_specs() -> None:
    """_load_file_context handles empty specs tuple."""
    result = _load_file_context(())
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    assert pcr.success is True
    assert pcr.files_loaded == []
    assert pcr.context_sections == {}


# --- Task 5: _load_directory_context tests ---


def test_load_directory_context_success(
    mocker: MockerFixture,
) -> None:
    """_load_directory_context returns dict with tree strings."""
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws/\n  __init__.py"),
            IOSuccess("project/\n  README.md"),
        ],
    )
    result = _load_directory_context()
    assert isinstance(result, IOSuccess)
    trees = unsafe_perform_io(result.unwrap())
    assert isinstance(trees, dict)
    assert "adws_tree" in trees
    assert "project_tree" in trees
    assert "adws/" in trees["adws_tree"]
    assert "project/" in trees["project_tree"]


def test_load_directory_context_tree_failure(
    mocker: MockerFixture,
) -> None:
    """_load_directory_context returns empty entry on failure."""
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOFailure(
                PipelineError(
                    step_name="io_ops.get_directory_tree",
                    error_type="OSError",
                    message="Cannot list directory",
                ),
            ),
            IOSuccess("project/\n  README.md"),
        ],
    )
    result = _load_directory_context()
    assert isinstance(result, IOSuccess)
    trees = unsafe_perform_io(result.unwrap())
    assert trees["adws_tree"] == ""
    assert trees["project_tree"] == "project/\n  README.md"


def test_load_directory_context_both_fail(
    mocker: MockerFixture,
) -> None:
    """_load_directory_context handles both trees failing."""
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOFailure(
                PipelineError(
                    step_name="io_ops.get_directory_tree",
                    error_type="OSError",
                    message="Cannot list adws",
                ),
            ),
            IOFailure(
                PipelineError(
                    step_name="io_ops.get_directory_tree",
                    error_type="OSError",
                    message="Cannot list project",
                ),
            ),
        ],
    )
    result = _load_directory_context()
    assert isinstance(result, IOSuccess)
    trees = unsafe_perform_io(result.unwrap())
    assert trees["adws_tree"] == ""
    assert trees["project_tree"] == ""


# --- Task 6: run_prime_command tests ---


def test_run_prime_command_success(
    mocker: MockerFixture,
) -> None:
    """run_prime_command returns IOSuccess with full context."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("claude content"),
            IOSuccess("arch content"),
            IOSuccess("epics content"),
        ],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws tree"),
            IOSuccess("project tree"),
        ],
    )
    ctx = WorkflowContext()
    result = run_prime_command(ctx)
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    assert isinstance(pcr, PrimeContextResult)
    assert pcr.success is True
    assert "claude_md" in pcr.context_sections
    assert "adws_tree" in pcr.context_sections
    assert "project_tree" in pcr.context_sections


def test_run_prime_command_required_file_failure(
    mocker: MockerFixture,
) -> None:
    """run_prime_command propagates required file failure."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOFailure(
                PipelineError(
                    step_name="io_ops.read_prime_file",
                    error_type="FileNotFoundError",
                    message="Not found: CLAUDE.md",
                ),
            ),
        ],
    )
    ctx = WorkflowContext()
    result = run_prime_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "RequiredFileError"


def test_run_prime_command_no_secrets(
    mocker: MockerFixture,
) -> None:
    """run_prime_command output does NOT contain secret keys."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("claude content"),
            IOSuccess("arch content"),
            IOSuccess("epics content"),
        ],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws tree"),
            IOSuccess("project tree"),
        ],
    )
    ctx = WorkflowContext()
    result = run_prime_command(ctx)
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    secret_keys = [".env", "credentials", "secrets", "api_key"]
    for key in pcr.context_sections:
        for secret in secret_keys:
            assert secret not in key.lower(), (
                f"Secret key '{secret}' found in"
                f" context_sections key '{key}'"
            )


# --- Task 10: Integration tests ---


def test_integration_full_prime_flow(
    mocker: MockerFixture,
) -> None:
    """Full /prime flow: all files exist, trees succeed."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("# TDD mandate\nAll code..."),
            IOSuccess("# Architecture\nDecisions..."),
            IOSuccess("# Epics\nEpic 1..."),
        ],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws/\n  __init__.py\n  adw_modules/"),
            IOSuccess("project/\n  package.json\n  adws/"),
        ],
    )
    ctx = WorkflowContext()
    result = run_prime_command(ctx)
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    assert pcr.success is True
    assert len(pcr.files_loaded) == 3
    expected_keys = {
        "claude_md",
        "architecture",
        "epics",
        "adws_tree",
        "project_tree",
    }
    assert set(pcr.context_sections.keys()) == expected_keys
    assert "3" in pcr.summary


def test_integration_optional_file_missing(
    mocker: MockerFixture,
) -> None:
    """Integration: optional file missing still succeeds."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOSuccess("# TDD mandate"),
            IOFailure(
                PipelineError(
                    step_name="io_ops.read_prime_file",
                    error_type="FileNotFoundError",
                    message="Not found",
                ),
            ),
            IOSuccess("# Epics"),
        ],
    )
    mocker.patch(
        "adws.adw_modules.io_ops.get_directory_tree",
        side_effect=[
            IOSuccess("adws tree"),
            IOSuccess("project tree"),
        ],
    )
    ctx = WorkflowContext()
    result = run_prime_command(ctx)
    assert isinstance(result, IOSuccess)
    pcr = unsafe_perform_io(result.unwrap())
    assert pcr.success is True
    assert "architecture" not in pcr.context_sections
    assert "claude_md" in pcr.context_sections
    assert "epics" in pcr.context_sections
    assert "skipped" in pcr.summary.lower()


def test_integration_required_file_missing(
    mocker: MockerFixture,
) -> None:
    """Integration: required file missing propagates failure."""
    mocker.patch(
        "adws.adw_modules.io_ops.read_prime_file",
        side_effect=[
            IOFailure(
                PipelineError(
                    step_name="io_ops.read_prime_file",
                    error_type="FileNotFoundError",
                    message="Not found: CLAUDE.md",
                ),
            ),
        ],
    )
    ctx = WorkflowContext()
    result = run_prime_command(ctx)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert error.error_type == "RequiredFileError"
    assert "CLAUDE.md" in error.message

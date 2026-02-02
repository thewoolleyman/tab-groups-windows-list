"""Tests for I/O boundary module."""
import importlib
from pathlib import Path

from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import check_sdk_import, read_file


def test_read_file_success(tmp_path: Path) -> None:
    """Test read_file returns IOSuccess with file contents."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    result = read_file(test_file)
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) == "hello world"


def test_read_file_not_found(tmp_path: Path) -> None:
    """Test read_file returns IOFailure when file does not exist."""
    result = read_file(tmp_path / "nonexistent.txt")
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "FileNotFoundError"
    assert "nonexistent.txt" in error.message


def test_read_file_permission_error(tmp_path: Path) -> None:
    """Test read_file returns IOFailure on permission error."""
    test_file = tmp_path / "noperm.txt"
    test_file.write_text("secret")
    test_file.chmod(0o000)
    result = read_file(test_file)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "PermissionError"
    test_file.chmod(0o644)


def test_check_sdk_import_success() -> None:
    """Test check_sdk_import returns IOSuccess when SDK is installed."""
    result = check_sdk_import()
    assert isinstance(result, IOSuccess)
    assert unsafe_perform_io(result.unwrap()) is True


def test_check_sdk_import_failure(mocker) -> None:  # type: ignore[no-untyped-def]
    """Test check_sdk_import returns IOFailure when SDK import fails."""
    mocker.patch.dict("sys.modules", {"claude_agent_sdk": None})

    import adws.adw_modules.io_ops  # noqa: PLC0415

    importlib.reload(adws.adw_modules.io_ops)
    from adws.adw_modules.io_ops import (  # noqa: PLC0415
        check_sdk_import as reloaded_check,
    )

    result = reloaded_check()
    # Restore module
    importlib.reload(adws.adw_modules.io_ops)
    assert isinstance(result, IOFailure)
    error = unsafe_perform_io(result.failure())
    assert isinstance(error, PipelineError)
    assert error.error_type == "ImportError"

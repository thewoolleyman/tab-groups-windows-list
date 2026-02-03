"""Tests for commands package __init__ lazy import mechanism."""
from __future__ import annotations

import pytest


def test_lazy_import_run_command_works() -> None:
    """__getattr__ successfully imports run_command on demand."""
    from adws.adw_modules import commands  # noqa: PLC0415

    # Access run_command through the package
    run_command = commands.run_command
    assert callable(run_command)
    assert run_command.__name__ == "run_command"


def test_lazy_import_raises_for_unknown_attr() -> None:
    """__getattr__ raises AttributeError for unknown attributes."""
    from adws.adw_modules import commands  # noqa: PLC0415

    with pytest.raises(AttributeError, match="nonexistent"):
        _ = commands.nonexistent


def test_direct_import_still_works() -> None:
    """Direct import from dispatch module still works."""
    from adws.adw_modules.commands.dispatch import (  # noqa: PLC0415
        run_command,
    )

    assert callable(run_command)

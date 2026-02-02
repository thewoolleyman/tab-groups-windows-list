"""Tests for command types module."""
from __future__ import annotations

import pytest

from adws.adw_modules.commands.types import CommandSpec


def test_command_spec_construction() -> None:
    """CommandSpec can be constructed with all fields."""
    spec = CommandSpec(
        name="verify",
        description="Run quality gate",
        python_module="adws.adw_modules.commands.dispatch",
        workflow_name="verify",
    )
    assert spec.name == "verify"
    assert spec.description == "Run quality gate"
    assert spec.python_module == "adws.adw_modules.commands.dispatch"
    assert spec.workflow_name == "verify"


def test_command_spec_workflow_name_defaults_to_none() -> None:
    """CommandSpec workflow_name defaults to None."""
    spec = CommandSpec(
        name="prime",
        description="Load context",
        python_module="adws.adw_modules.commands.dispatch",
    )
    assert spec.workflow_name is None


def test_command_spec_immutable() -> None:
    """CommandSpec is frozen -- attribute assignment raises."""
    spec = CommandSpec(
        name="verify",
        description="Run quality gate",
        python_module="adws.adw_modules.commands.dispatch",
    )
    with pytest.raises(AttributeError):
        spec.name = "changed"  # type: ignore[misc]

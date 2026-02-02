"""Tests for command registry module."""
from __future__ import annotations

from types import MappingProxyType

import pytest

from adws.adw_modules.commands.registry import (
    COMMAND_REGISTRY,
    get_command,
    list_commands,
)
from adws.adw_modules.commands.types import CommandSpec

# --- COMMAND_REGISTRY tests ---

EXPECTED_COMMANDS = [
    "verify",
    "prime",
    "build",
    "implement",
    "load_bundle",
    "convert_stories_to_beads",
]


def test_command_registry_contains_all_commands() -> None:
    """Registry has entries for all 6 planned commands."""
    for name in EXPECTED_COMMANDS:
        assert name in COMMAND_REGISTRY, (
            f"Missing command: {name}"
        )
    assert len(COMMAND_REGISTRY) == 6


def test_command_registry_values_are_command_specs() -> None:
    """Every registry value is a CommandSpec instance."""
    for name, spec in COMMAND_REGISTRY.items():
        assert isinstance(spec, CommandSpec), (
            f"{name} is not a CommandSpec"
        )


def test_command_registry_specs_have_required_fields() -> None:
    """Every CommandSpec has name, description, python_module."""
    for name, spec in COMMAND_REGISTRY.items():
        assert spec.name == name
        assert spec.description, f"{name} has empty description"
        assert spec.python_module, f"{name} has empty module"


def test_command_registry_verify_has_workflow() -> None:
    """Verify command maps to 'verify' workflow."""
    spec = COMMAND_REGISTRY["verify"]
    assert spec.workflow_name == "verify"


def test_command_registry_build_has_workflow() -> None:
    """Build command maps to 'implement_close' workflow."""
    spec = COMMAND_REGISTRY["build"]
    assert spec.workflow_name == "implement_close"


def test_command_registry_implement_has_workflow() -> None:
    """Implement maps to 'implement_verify_close' workflow."""
    spec = COMMAND_REGISTRY["implement"]
    assert spec.workflow_name == "implement_verify_close"


def test_command_registry_convert_has_workflow() -> None:
    """Convert stories maps to 'convert_stories_to_beads'."""
    spec = COMMAND_REGISTRY["convert_stories_to_beads"]
    assert spec.workflow_name == "convert_stories_to_beads"


def test_command_registry_prime_has_no_workflow() -> None:
    """Prime command has no workflow (custom logic)."""
    spec = COMMAND_REGISTRY["prime"]
    assert spec.workflow_name is None


def test_command_registry_load_bundle_has_no_workflow() -> None:
    """Load bundle has no workflow (custom logic)."""
    spec = COMMAND_REGISTRY["load_bundle"]
    assert spec.workflow_name is None


def test_command_registry_is_immutable() -> None:
    """COMMAND_REGISTRY is a MappingProxyType -- mutation blocked."""
    assert isinstance(COMMAND_REGISTRY, MappingProxyType)
    with pytest.raises(TypeError):
        COMMAND_REGISTRY["evil"] = CommandSpec(  # type: ignore[index]
            name="evil",
            description="bad",
            python_module="bad.module",
        )


# --- get_command tests ---


def test_get_command_verify_returns_spec() -> None:
    """get_command('verify') returns the verify CommandSpec."""
    spec = get_command("verify")
    assert spec is not None
    assert spec.name == "verify"
    assert spec.workflow_name == "verify"


def test_get_command_all_expected() -> None:
    """get_command returns a spec for every expected name."""
    for name in EXPECTED_COMMANDS:
        spec = get_command(name)
        assert spec is not None, f"get_command({name!r}) None"
        assert spec.name == name


def test_get_command_unknown_returns_none() -> None:
    """get_command returns None for unregistered commands."""
    assert get_command("nonexistent") is None


# --- list_commands tests ---


def test_list_commands_returns_all() -> None:
    """list_commands returns all 6 registered commands."""
    commands = list_commands()
    assert len(commands) == 6
    names = {spec.name for spec in commands}
    assert names == set(EXPECTED_COMMANDS)


def test_list_commands_returns_command_specs() -> None:
    """list_commands returns CommandSpec instances."""
    for spec in list_commands():
        assert isinstance(spec, CommandSpec)

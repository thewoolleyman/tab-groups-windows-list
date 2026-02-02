"""Command registry and lookup functions (FR28)."""
from __future__ import annotations

from types import MappingProxyType

from adws.adw_modules.commands.types import CommandSpec

COMMAND_REGISTRY: MappingProxyType[str, CommandSpec] = (
    MappingProxyType(
        {
            "verify": CommandSpec(
                name="verify",
                description="Run full local quality gate",
                python_module=(
                    "adws.adw_modules.commands.dispatch"
                ),
                workflow_name="verify",
            ),
            "build": CommandSpec(
                name="build",
                description="Fast-track trivial changes",
                python_module=(
                    "adws.adw_modules.commands.dispatch"
                ),
                workflow_name="implement_close",
            ),
            "implement": CommandSpec(
                name="implement",
                description=(
                    "Execute full TDD-enforced"
                    " implementation workflow"
                ),
                python_module=(
                    "adws.adw_modules.commands.dispatch"
                ),
                workflow_name="implement_verify_close",
            ),
            "prime": CommandSpec(
                name="prime",
                description=(
                    "Load codebase context into session"
                ),
                python_module=(
                    "adws.adw_modules.commands.dispatch"
                ),
                workflow_name=None,
            ),
            "load_bundle": CommandSpec(
                name="load_bundle",
                description=(
                    "Reload previous session context"
                ),
                python_module=(
                    "adws.adw_modules.commands.dispatch"
                ),
                workflow_name=None,
            ),
            "convert_stories_to_beads": CommandSpec(
                name="convert_stories_to_beads",
                description=(
                    "Convert BMAD stories to Beads issues"
                ),
                python_module=(
                    "adws.adw_modules.commands.dispatch"
                ),
                workflow_name="convert_stories_to_beads",
            ),
        }
    )
)


def get_command(name: str) -> CommandSpec | None:
    """Look up a command by name. Returns None if not found."""
    return COMMAND_REGISTRY.get(name)


def list_commands() -> list[CommandSpec]:
    """Return all registered commands."""
    return list(COMMAND_REGISTRY.values())

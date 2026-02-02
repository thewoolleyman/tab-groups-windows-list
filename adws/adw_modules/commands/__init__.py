"""Commands package -- dual-layer command pattern (FR28).

Public API for command infrastructure: types, registry,
and dispatch.
"""
from adws.adw_modules.commands.dispatch import run_command
from adws.adw_modules.commands.registry import (
    get_command,
    list_commands,
)
from adws.adw_modules.commands.types import CommandSpec

__all__ = [
    "CommandSpec",
    "get_command",
    "list_commands",
    "run_command",
]

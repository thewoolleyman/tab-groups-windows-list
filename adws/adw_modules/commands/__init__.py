"""Commands package -- dual-layer command pattern (FR28).

Public API for command infrastructure: types, registry,
dispatch, verify command (FR30), and prime command (FR31).
"""
from adws.adw_modules.commands.dispatch import run_command
from adws.adw_modules.commands.prime import (
    PrimeContextResult,
    PrimeFileSpec,
    run_prime_command,
)
from adws.adw_modules.commands.registry import (
    get_command,
    list_commands,
)
from adws.adw_modules.commands.types import CommandSpec
from adws.adw_modules.commands.verify import (
    VerifyCommandResult,
    run_verify_command,
)

__all__ = [
    "CommandSpec",
    "PrimeContextResult",
    "PrimeFileSpec",
    "VerifyCommandResult",
    "get_command",
    "list_commands",
    "run_command",
    "run_prime_command",
    "run_verify_command",
]

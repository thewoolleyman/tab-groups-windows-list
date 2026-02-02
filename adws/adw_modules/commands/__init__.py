"""Commands package -- dual-layer command pattern (FR28).

Public API for command infrastructure: types, registry,
dispatch, verify (FR30), prime (FR31), build (FR32),
and implement (FR28).
"""
from adws.adw_modules.commands.build import (
    BuildCommandResult,
    run_build_command,
)
from adws.adw_modules.commands.dispatch import run_command
from adws.adw_modules.commands.implement import (
    ImplementCommandResult,
    run_implement_command,
)
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
    "BuildCommandResult",
    "CommandSpec",
    "ImplementCommandResult",
    "PrimeContextResult",
    "PrimeFileSpec",
    "VerifyCommandResult",
    "get_command",
    "list_commands",
    "run_build_command",
    "run_command",
    "run_implement_command",
    "run_prime_command",
    "run_verify_command",
]

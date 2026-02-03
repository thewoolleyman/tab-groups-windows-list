"""Commands package -- dual-layer command pattern (FR28).

Public API for command infrastructure: types, registry,
dispatch, verify (FR30), prime (FR31), build (FR32),
implement (FR28), load_bundle (FR35), and
convert_stories (FR23).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from adws.adw_modules.commands.build import (
    BuildCommandResult,
    run_build_command,
)
from adws.adw_modules.commands.convert_stories import (
    run_convert_stories_command,
)
from adws.adw_modules.commands.implement import (
    ImplementCommandResult,
    run_implement_command,
)
from adws.adw_modules.commands.load_bundle import (
    LoadBundleResult,
    run_load_bundle_command,
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

# Avoid importing dispatch at package load time to prevent
# RuntimeWarning when dispatch is run as a module with -m flag
if TYPE_CHECKING:
    from adws.adw_modules.commands.dispatch import (
        run_command,
    )


def __getattr__(name: str) -> object:
    """Lazy import run_command to avoid dispatch in sys.modules.

    When dispatch.py is run with 'python -m', importing it at
    package level causes RuntimeWarning. This lazy loader defers
    the import until actually needed.
    """
    if name == "run_command":
        from adws.adw_modules.commands.dispatch import (  # noqa: PLC0415
            run_command,
        )

        return run_command
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "BuildCommandResult",
    "CommandSpec",
    "ImplementCommandResult",
    "LoadBundleResult",
    "PrimeContextResult",
    "PrimeFileSpec",
    "VerifyCommandResult",
    "get_command",
    "list_commands",
    "run_build_command",
    "run_command",
    "run_convert_stories_command",
    "run_implement_command",
    "run_load_bundle_command",
    "run_prime_command",
    "run_verify_command",
]

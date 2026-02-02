"""Command type definitions for ADWS command pattern (FR28)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    """Metadata for a registered command.

    Each command has a name, description, the Python module
    that implements it, and optionally a workflow name for
    workflow-backed commands.
    """

    name: str
    description: str
    python_module: str
    workflow_name: str | None = None

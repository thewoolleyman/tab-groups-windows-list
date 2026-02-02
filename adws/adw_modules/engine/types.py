"""Public API types for workflow definitions (Tier 1).

Workflow authors use these types to define pipelines declaratively.
ROP internals (IOResult, flow, bind) are hidden in Tier 2 (executor).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    """A single step in a workflow pipeline."""

    name: str
    function: str
    always_run: bool = False
    max_attempts: int = 1


@dataclass(frozen=True)
class Workflow:
    """Declarative workflow definition.

    Workflows are data, not code. They define WHAT steps run
    in WHAT order. The engine handles HOW.
    """

    name: str
    description: str
    steps: list[Step] = field(default_factory=list)
    dispatchable: bool = True

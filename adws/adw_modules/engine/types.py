"""Public API types for workflow definitions (Tier 1).

Workflow authors use these types to define pipelines declaratively.
ROP internals (IOResult, flow, bind) are hidden in Tier 2 (executor).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from returns.io import IOResult

    from adws.adw_modules.errors import PipelineError
    from adws.adw_modules.types import WorkflowContext

StepFunction = Callable[
    ["WorkflowContext"],
    "IOResult[WorkflowContext, PipelineError]",
]


@dataclass(frozen=True)
class Step:
    """A single step in a workflow pipeline.

    When shell=True, the engine uses execute_shell_step instead of an
    SDK call. The command string is placed into ctx.inputs["shell_command"]
    before step execution. The function field is ignored for shell steps.
    """

    name: str
    function: str
    always_run: bool = False
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0
    shell: bool = False
    command: str = ""


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

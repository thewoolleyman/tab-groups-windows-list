"""Workflow registry and discovery (Tier 1 API)."""
from __future__ import annotations

from adws.adw_modules.engine.types import Step, Workflow


class WorkflowName:
    """Registry of valid workflow names (constants for downstream epics)."""

    IMPLEMENT_CLOSE = "implement_close"
    IMPLEMENT_VERIFY_CLOSE = "implement_verify_close"
    CONVERT_STORIES_TO_BEADS = "convert_stories_to_beads"


# --- Registered workflows ---

_IMPLEMENT_CLOSE = Workflow(
    name=WorkflowName.IMPLEMENT_CLOSE,
    description="Fast-track for trivial changes: implement then close",
    dispatchable=True,
    steps=[
        Step(name="implement", function="execute_sdk_call"),
        Step(name="close", function="bd_close", always_run=True),
    ],
)

_IMPLEMENT_VERIFY_CLOSE = Workflow(
    name=WorkflowName.IMPLEMENT_VERIFY_CLOSE,
    description="Full TDD workflow: RED -> GREEN -> REFACTOR with verification",
    dispatchable=True,
    steps=[],  # Steps populated in Epic 4
)

_CONVERT_STORIES_TO_BEADS = Workflow(
    name=WorkflowName.CONVERT_STORIES_TO_BEADS,
    description="Convert BMAD stories to Beads issues with workflow tags",
    dispatchable=False,
    steps=[],  # Steps populated in Epic 6
)

_REGISTRY: dict[str, Workflow] = {
    _IMPLEMENT_CLOSE.name: _IMPLEMENT_CLOSE,
    _IMPLEMENT_VERIFY_CLOSE.name: _IMPLEMENT_VERIFY_CLOSE,
    _CONVERT_STORIES_TO_BEADS.name: _CONVERT_STORIES_TO_BEADS,
}


def load_workflow(name: str) -> Workflow | None:
    """Pure lookup -- find workflow by name. No policy enforcement."""
    return _REGISTRY.get(name)


def list_workflows(*, dispatchable_only: bool = False) -> list[Workflow]:
    """Return registered workflows, optionally filtered to dispatchable."""
    workflows = list(_REGISTRY.values())
    if dispatchable_only:
        return [w for w in workflows if w.dispatchable]
    return workflows

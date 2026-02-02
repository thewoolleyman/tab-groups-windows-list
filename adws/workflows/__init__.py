"""Workflow registry and discovery (Tier 1 API)."""
from __future__ import annotations

from adws.adw_modules.engine.types import Step, Workflow


class WorkflowName:
    """Registry of valid workflow names (constants for downstream epics)."""

    IMPLEMENT_CLOSE = "implement_close"
    IMPLEMENT_VERIFY_CLOSE = "implement_verify_close"
    CONVERT_STORIES_TO_BEADS = "convert_stories_to_beads"
    SAMPLE = "sample"
    TRIAGE = "triage"
    VERIFY = "verify"


# --- Registered workflows ---

_IMPLEMENT_CLOSE = Workflow(
    name=WorkflowName.IMPLEMENT_CLOSE,
    description=(
        "Fast-track for trivial changes:"
        " implement then verify"
    ),
    dispatchable=True,
    steps=[
        Step(
            name="implement",
            function="execute_sdk_call",
        ),
        Step(  # noqa: S604
            name="verify_tests_pass",
            function="execute_shell_step",
            shell=True,
            command=(
                "uv run pytest adws/tests/"
                " -m 'not enemy'"
            ),
        ),
    ],
)

_IMPLEMENT_VERIFY_CLOSE = Workflow(
    name=WorkflowName.IMPLEMENT_VERIFY_CLOSE,
    description="Full TDD workflow: RED -> GREEN -> REFACTOR with verification",
    dispatchable=True,
    steps=[
        Step(
            name="write_failing_tests",
            function="write_failing_tests",
        ),
        Step(
            name="verify_tests_fail",
            function="verify_tests_fail",
        ),
        Step(
            name="implement",
            function="implement_step",
        ),
        Step(  # noqa: S604
            name="verify_tests_pass",
            function="execute_shell_step",
            shell=True,
            command=(
                "uv run pytest adws/tests/"
                " -m 'not enemy'"
            ),
        ),
        Step(
            name="refactor",
            function="refactor_step",
        ),
        Step(  # noqa: S604
            name="verify_tests_pass_refactor",
            function="execute_shell_step",
            shell=True,
            command=(
                "uv run pytest adws/tests/"
                " -m 'not enemy'"
            ),
        ),
        Step(  # noqa: S604
            name="finalize",
            function="execute_shell_step",
            shell=True,
            command="echo 'finalize'",
            always_run=True,
        ),
    ],
)

_CONVERT_STORIES_TO_BEADS = Workflow(
    name=WorkflowName.CONVERT_STORIES_TO_BEADS,
    description="Convert BMAD stories to Beads issues with workflow tags",
    dispatchable=False,
    steps=[
        Step(
            name="parse_bmad_story",
            function="parse_bmad_story",
        ),
        Step(
            name="convert_stories_orchestrator",
            function="convert_stories_orchestrator",
        ),
    ],
)

_VERIFY = Workflow(
    name=WorkflowName.VERIFY,
    description=(
        "Full local quality gate:"
        " Jest, Playwright, mypy, ruff"
    ),
    dispatchable=False,
    steps=[
        Step(
            name="jest",
            function="run_jest_step",
            always_run=True,
            output="jest_results",
        ),
        Step(
            name="playwright",
            function="run_playwright_step",
            always_run=True,
            output="playwright_results",
        ),
        Step(
            name="mypy",
            function="run_mypy_step",
            always_run=True,
            output="mypy_results",
        ),
        Step(
            name="ruff",
            function="run_ruff_step",
            always_run=True,
            output="ruff_results",
        ),
    ],
)

_SAMPLE = Workflow(
    name=WorkflowName.SAMPLE,
    description=(
        "Sample workflow demonstrating full Epic 2 pipeline"
    ),
    dispatchable=False,
    steps=[
        Step(
            name="setup",
            function="check_sdk_available",
            output="setup_data",
        ),
        Step(  # noqa: S604
            name="process",
            function="execute_shell_step",
            shell=True,
            command="echo 'processing'",
            max_attempts=2,
            retry_delay_seconds=0.0,
            input_from={"setup_data": "setup_result"},
        ),
        Step(
            name="cleanup",
            function="check_sdk_available",
            always_run=True,
        ),
    ],
)

_TRIAGE = Workflow(
    name=WorkflowName.TRIAGE,
    description=(
        "Self-healing failure recovery: triage"
        " failed issues with tiered escalation"
    ),
    dispatchable=False,
    steps=[],
)

_REGISTRY: dict[str, Workflow] = {
    _IMPLEMENT_CLOSE.name: _IMPLEMENT_CLOSE,
    _IMPLEMENT_VERIFY_CLOSE.name: _IMPLEMENT_VERIFY_CLOSE,
    _CONVERT_STORIES_TO_BEADS.name: _CONVERT_STORIES_TO_BEADS,
    _VERIFY.name: _VERIFY,
    _SAMPLE.name: _SAMPLE,
    _TRIAGE.name: _TRIAGE,
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


def list_dispatchable_workflows() -> list[str]:
    """Return sorted names of dispatchable workflows.

    Convenience helper for error messages and dispatch UI.
    """
    return sorted(
        w.name
        for w in list_workflows(dispatchable_only=True)
    )

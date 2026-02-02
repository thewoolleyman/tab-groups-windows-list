"""Tests for workflow registry and discovery."""
from adws.adw_modules.engine.types import Workflow
from adws.workflows import WorkflowName, list_workflows, load_workflow


def test_workflow_name_constants() -> None:
    """Test workflow name registry has expected constants."""
    assert WorkflowName.IMPLEMENT_CLOSE == "implement_close"
    assert WorkflowName.IMPLEMENT_VERIFY_CLOSE == "implement_verify_close"
    assert WorkflowName.CONVERT_STORIES_TO_BEADS == "convert_stories_to_beads"


def test_load_workflow_found() -> None:
    """Test load_workflow returns Workflow for known name."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    assert isinstance(wf, Workflow)
    assert wf.name == WorkflowName.IMPLEMENT_CLOSE


def test_load_workflow_not_found() -> None:
    """Test load_workflow returns None for unknown name."""
    assert load_workflow("nonexistent_workflow") is None


def test_list_workflows_all() -> None:
    """Test list_workflows returns all registered workflows."""
    workflows = list_workflows()
    assert len(workflows) >= 1
    names = [w.name for w in workflows]
    assert WorkflowName.IMPLEMENT_CLOSE in names


def test_list_workflows_dispatchable_only() -> None:
    """Test list_workflows filters to dispatchable workflows."""
    all_wfs = list_workflows()
    dispatchable = list_workflows(dispatchable_only=True)
    assert all(w.dispatchable for w in dispatchable)
    assert len(dispatchable) <= len(all_wfs)


def test_implement_close_workflow_structure() -> None:
    """Test implement_close workflow has expected properties."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    assert wf.dispatchable is True
    assert len(wf.steps) >= 1

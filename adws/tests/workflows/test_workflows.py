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


# --- Story 2.6: Dispatchable filter tests ---


def test_list_workflows_dispatchable_includes_expected() -> None:
    """dispatchable_only=True includes dispatchable workflows."""
    dispatchable = list_workflows(dispatchable_only=True)
    names = [w.name for w in dispatchable]
    assert WorkflowName.IMPLEMENT_CLOSE in names
    assert WorkflowName.IMPLEMENT_VERIFY_CLOSE in names
    # Non-dispatchable excluded
    assert WorkflowName.CONVERT_STORIES_TO_BEADS not in names


def test_list_workflows_all_includes_non_dispatchable() -> None:
    """dispatchable_only=False returns all including non-disp."""
    all_wfs = list_workflows(dispatchable_only=False)
    names = [w.name for w in all_wfs]
    assert WorkflowName.IMPLEMENT_CLOSE in names
    assert WorkflowName.IMPLEMENT_VERIFY_CLOSE in names
    assert WorkflowName.CONVERT_STORIES_TO_BEADS in names


def test_workflows_are_declarative_data() -> None:
    """Workflow definitions are testable data (NFR13)."""
    all_wfs = list_workflows()
    for wf in all_wfs:
        assert isinstance(wf, Workflow)
        assert isinstance(wf.name, str)
        assert isinstance(wf.description, str)
        assert isinstance(wf.steps, list)
        assert isinstance(wf.dispatchable, bool)

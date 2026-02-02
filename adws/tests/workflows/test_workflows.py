"""Tests for workflow registry and discovery."""
from adws.adw_modules.engine.types import Step, Workflow
from adws.workflows import (
    WorkflowName,
    list_dispatchable_workflows,
    list_workflows,
    load_workflow,
)


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
    assert len(wf.steps) == 2


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


# --- Story 2.7: Sample workflow registry tests ---


def test_sample_workflow_registered() -> None:
    """load_workflow("sample") returns sample workflow."""
    wf = load_workflow(WorkflowName.SAMPLE)
    assert wf is not None
    assert isinstance(wf, Workflow)
    assert wf.name == WorkflowName.SAMPLE


def test_sample_workflow_not_dispatchable() -> None:
    """Sample workflow has dispatchable=False."""
    wf = load_workflow(WorkflowName.SAMPLE)
    assert wf is not None
    assert wf.dispatchable is False


def test_sample_workflow_has_steps() -> None:
    """Sample workflow has 3 steps with expected names."""
    wf = load_workflow(WorkflowName.SAMPLE)
    assert wf is not None
    assert len(wf.steps) == 3
    names = [s.name for s in wf.steps]
    assert names == ["setup", "process", "cleanup"]
    # Verify step types
    for step in wf.steps:
        assert isinstance(step, Step)


def test_sample_workflow_not_in_dispatchable_list() -> None:
    """Sample workflow excluded from dispatchable listing."""
    dispatchable = list_workflows(dispatchable_only=True)
    names = [w.name for w in dispatchable]
    assert WorkflowName.SAMPLE not in names


def test_sample_workflow_in_all_list() -> None:
    """Sample workflow appears in all-workflows listing."""
    all_wfs = list_workflows()
    names = [w.name for w in all_wfs]
    assert WorkflowName.SAMPLE in names


def test_sample_workflow_name_constant() -> None:
    """WorkflowName.SAMPLE equals 'sample'."""
    assert WorkflowName.SAMPLE == "sample"


# --- Story 3.2: Verify workflow registry tests ---


def test_verify_workflow_name_constant() -> None:
    """WorkflowName.VERIFY equals 'verify'."""
    assert WorkflowName.VERIFY == "verify"


def test_verify_workflow_registered() -> None:
    """load_workflow("verify") returns verify workflow."""
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    assert isinstance(wf, Workflow)
    assert wf.name == WorkflowName.VERIFY


def test_verify_workflow_not_dispatchable() -> None:
    """Verify workflow has dispatchable=False."""
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    assert wf.dispatchable is False


def test_verify_workflow_has_four_steps() -> None:
    """Verify workflow has 4 steps with expected names."""
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    assert len(wf.steps) == 4
    names = [s.name for s in wf.steps]
    assert names == ["jest", "playwright", "mypy", "ruff"]
    for step in wf.steps:
        assert isinstance(step, Step)


def test_verify_workflow_all_steps_always_run() -> None:
    """All verify steps have always_run=True."""
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    for step in wf.steps:
        assert step.always_run is True


def test_verify_workflow_steps_have_output_names() -> None:
    """Each verify step has a unique output name."""
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    outputs = [s.output for s in wf.steps]
    assert outputs == [
        "jest_results",
        "playwright_results",
        "mypy_results",
        "ruff_results",
    ]
    # All unique
    assert len(set(outputs)) == len(outputs)


def test_verify_workflow_step_functions() -> None:
    """Each verify step references correct function name."""
    wf = load_workflow(WorkflowName.VERIFY)
    assert wf is not None
    functions = [s.function for s in wf.steps]
    assert functions == [
        "run_jest_step",
        "run_playwright_step",
        "run_mypy_step",
        "run_ruff_step",
    ]


def test_verify_workflow_not_in_dispatchable_list() -> None:
    """Verify workflow excluded from dispatchable listing."""
    dispatchable = list_workflows(dispatchable_only=True)
    names = [w.name for w in dispatchable]
    assert WorkflowName.VERIFY not in names


def test_verify_workflow_in_all_list() -> None:
    """Verify workflow appears in all-workflows listing."""
    all_wfs = list_workflows()
    names = [w.name for w in all_wfs]
    assert WorkflowName.VERIFY in names


# --- Story 4.4: implement_close workflow step composition ---


def test_implement_close_step_names() -> None:
    """implement_close has implement and verify_tests_pass."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    names = [s.name for s in wf.steps]
    assert names == ["implement", "verify_tests_pass"]


def test_implement_close_no_tdd_steps() -> None:
    """implement_close has no write_failing_tests or verify_tests_fail."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    names = [s.name for s in wf.steps]
    assert "write_failing_tests" not in names
    assert "verify_tests_fail" not in names


def test_implement_close_implement_step() -> None:
    """implement step uses execute_sdk_call function."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    impl = wf.steps[0]
    assert impl.name == "implement"
    assert impl.function == "execute_sdk_step"
    assert impl.shell is False


def test_implement_close_verify_step() -> None:
    """verify_tests_pass step is a shell step."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    verify = wf.steps[1]
    assert verify.name == "verify_tests_pass"
    assert verify.shell is True
    assert "pytest" in verify.command
    assert "not enemy" in verify.command


def test_implement_close_no_finalize_step() -> None:
    """implement_close has no finalize step (handled by cmd)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_CLOSE)
    assert wf is not None
    names = [s.name for s in wf.steps]
    assert "close" not in names
    assert "finalize" not in names


# --- Story 4.8: implement_verify_close workflow composition ---


def test_implement_verify_close_step_names() -> None:
    """implement_verify_close has 7 steps in correct order."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    names = [s.name for s in wf.steps]
    assert names == [
        "write_failing_tests",
        "verify_tests_fail",
        "implement",
        "verify_tests_pass",
        "refactor",
        "verify_tests_pass_refactor",
        "finalize",
    ]


def test_implement_verify_close_finalize_always_run() -> None:
    """finalize step has always_run=True, others False."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    for step in wf.steps:
        if step.name == "finalize":
            assert step.always_run is True
        else:
            assert step.always_run is False


def test_implement_verify_close_dispatchable() -> None:
    """implement_verify_close has dispatchable=True."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    assert wf.dispatchable is True


def test_implement_verify_close_verify_shell_commands() -> None:
    """verify_tests_pass shell steps contain pytest and not enemy."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    for step in wf.steps:
        if step.name in (
            "verify_tests_pass",
            "verify_tests_pass_refactor",
        ):
            assert "pytest" in step.command
            assert "not enemy" in step.command


def test_implement_verify_close_write_failing_tests_is_sdk() -> None:
    """write_failing_tests is an SDK step (not shell)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step = wf.steps[0]
    assert step.name == "write_failing_tests"
    assert step.shell is False


def test_implement_verify_close_implement_is_sdk() -> None:
    """implement step is an SDK step (not shell)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step = wf.steps[2]
    assert step.name == "implement"
    assert step.shell is False


def test_implement_verify_close_refactor_is_sdk() -> None:
    """refactor step is an SDK step (not shell)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step = wf.steps[4]
    assert step.name == "refactor"
    assert step.shell is False


# --- Story 4.8: Workflow composition -- phase tests (Task 7) ---


def test_ivc_red_phase_composition() -> None:
    """RED phase: write_failing_tests (SDK) then verify_tests_fail (SDK)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step1 = wf.steps[0]
    step2 = wf.steps[1]
    assert step1.name == "write_failing_tests"
    assert step1.function == "write_failing_tests"
    assert step1.shell is False
    assert step2.name == "verify_tests_fail"
    assert step2.function == "verify_tests_fail"
    assert step2.shell is False


def test_ivc_green_phase_composition() -> None:
    """GREEN phase: implement (SDK) then verify_tests_pass (shell)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step3 = wf.steps[2]
    step4 = wf.steps[3]
    assert step3.name == "implement"
    assert step3.function == "implement_step"
    assert step3.shell is False
    assert step4.name == "verify_tests_pass"
    assert step4.shell is True
    assert "pytest" in step4.command
    assert "not enemy" in step4.command


def test_ivc_refactor_phase_composition() -> None:
    """REFACTOR phase: refactor (SDK) then verify_tests_pass_refactor (shell)."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step5 = wf.steps[4]
    step6 = wf.steps[5]
    assert step5.name == "refactor"
    assert step5.function == "refactor_step"
    assert step5.shell is False
    assert step6.name == "verify_tests_pass_refactor"
    assert step6.shell is True
    assert "pytest" in step6.command
    assert "not enemy" in step6.command


def test_ivc_finalize_step_properties() -> None:
    """Finalize step: always_run=True, shell step placeholder."""
    wf = load_workflow(WorkflowName.IMPLEMENT_VERIFY_CLOSE)
    assert wf is not None
    step7 = wf.steps[6]
    assert step7.name == "finalize"
    assert step7.always_run is True
    assert step7.shell is True


# --- Story 6.2: convert_stories_to_beads workflow composition ---


def test_convert_stories_to_beads_registered() -> None:
    """convert_stories_to_beads workflow is registered."""
    wf = load_workflow(WorkflowName.CONVERT_STORIES_TO_BEADS)
    assert wf is not None
    assert isinstance(wf, Workflow)
    assert wf.name == WorkflowName.CONVERT_STORIES_TO_BEADS


def test_convert_stories_to_beads_not_dispatchable() -> None:
    """convert_stories_to_beads has dispatchable=False."""
    wf = load_workflow(WorkflowName.CONVERT_STORIES_TO_BEADS)
    assert wf is not None
    assert wf.dispatchable is False


def test_convert_stories_to_beads_has_steps() -> None:
    """convert_stories_to_beads has 2 steps."""
    wf = load_workflow(WorkflowName.CONVERT_STORIES_TO_BEADS)
    assert wf is not None
    assert len(wf.steps) == 2
    for step in wf.steps:
        assert isinstance(step, Step)


def test_convert_stories_to_beads_step_names() -> None:
    """convert_stories_to_beads steps are in correct order."""
    wf = load_workflow(WorkflowName.CONVERT_STORIES_TO_BEADS)
    assert wf is not None
    names = [s.name for s in wf.steps]
    assert names == [
        "parse_bmad_story",
        "convert_stories_orchestrator",
    ]


def test_convert_stories_to_beads_step_functions() -> None:
    """convert_stories_to_beads step functions match names."""
    wf = load_workflow(WorkflowName.CONVERT_STORIES_TO_BEADS)
    assert wf is not None
    functions = [s.function for s in wf.steps]
    assert functions == [
        "parse_bmad_story",
        "convert_stories_orchestrator",
    ]


def test_convert_stories_to_beads_orchestrator_is_step_two() -> None:
    """convert_stories_orchestrator is the second step."""
    wf = load_workflow(WorkflowName.CONVERT_STORIES_TO_BEADS)
    assert wf is not None
    step2 = wf.steps[1]
    assert step2.name == "convert_stories_orchestrator"
    assert step2.function == "convert_stories_orchestrator"


# --- Story 6.3: Steps init exports ---


def test_write_beads_id_in_steps_init() -> None:
    """write_beads_id is importable from steps and in __all__."""
    from adws.adw_modules import steps  # noqa: PLC0415

    assert hasattr(steps, "write_beads_id")
    assert "write_beads_id" in steps.__all__


def test_convert_stories_orchestrator_in_steps_init() -> None:
    """convert_stories_orchestrator importable from steps and in __all__."""
    from adws.adw_modules import steps  # noqa: PLC0415

    assert hasattr(steps, "convert_stories_orchestrator")
    assert "convert_stories_orchestrator" in steps.__all__


def test_step_registry_has_write_beads_id() -> None:
    """_STEP_REGISTRY contains write_beads_id entry."""
    from adws.adw_modules.engine.executor import (  # noqa: PLC0415
        _STEP_REGISTRY,
    )

    assert "write_beads_id" in _STEP_REGISTRY


def test_step_registry_has_convert_stories_orchestrator() -> None:
    """_STEP_REGISTRY contains convert_stories_orchestrator entry."""
    from adws.adw_modules.engine.executor import (  # noqa: PLC0415
        _STEP_REGISTRY,
    )

    assert "convert_stories_orchestrator" in _STEP_REGISTRY


def test_ivc_registry_entry() -> None:
    """implement command in COMMAND_REGISTRY has correct workflow."""
    from adws.adw_modules.commands.registry import (  # noqa: PLC0415
        COMMAND_REGISTRY,
    )

    spec = COMMAND_REGISTRY.get("implement")
    assert spec is not None
    assert spec.workflow_name == "implement_verify_close"


# --- Story 7.1: list_dispatchable_workflows helper tests ---


def test_list_dispatchable_workflows_returns_sorted() -> None:
    """list_dispatchable_workflows returns sorted dispatchable names."""
    names = list_dispatchable_workflows()
    assert isinstance(names, list)
    assert names == sorted(names)


def test_list_dispatchable_workflows_includes_expected() -> None:
    """Includes implement_close and implement_verify_close."""
    names = list_dispatchable_workflows()
    assert WorkflowName.IMPLEMENT_CLOSE in names
    assert WorkflowName.IMPLEMENT_VERIFY_CLOSE in names


def test_list_dispatchable_workflows_excludes_non_dispatchable() -> None:
    """list_dispatchable_workflows excludes non-dispatchable workflows."""
    names = list_dispatchable_workflows()
    assert WorkflowName.CONVERT_STORIES_TO_BEADS not in names
    assert WorkflowName.SAMPLE not in names
    assert WorkflowName.VERIFY not in names
    assert WorkflowName.TRIAGE not in names


# --- Story 7.4: Triage workflow registry tests ---


def test_triage_workflow_name_constant() -> None:
    """WorkflowName.TRIAGE equals 'triage'."""
    assert WorkflowName.TRIAGE == "triage"


def test_triage_workflow_registered() -> None:
    """load_workflow("triage") returns triage workflow."""
    wf = load_workflow(WorkflowName.TRIAGE)
    assert wf is not None
    assert isinstance(wf, Workflow)
    assert wf.name == WorkflowName.TRIAGE


def test_triage_workflow_not_dispatchable() -> None:
    """Triage workflow has dispatchable=False."""
    wf = load_workflow(WorkflowName.TRIAGE)
    assert wf is not None
    assert wf.dispatchable is False


def test_triage_workflow_not_in_dispatchable_list() -> None:
    """Triage workflow excluded from dispatchable listing."""
    dispatchable = list_workflows(dispatchable_only=True)
    names = [w.name for w in dispatchable]
    assert WorkflowName.TRIAGE not in names


def test_triage_workflow_in_all_list() -> None:
    """Triage workflow appears in all-workflows listing."""
    all_wfs = list_workflows()
    names = [w.name for w in all_wfs]
    assert WorkflowName.TRIAGE in names


def test_triage_workflow_not_in_dispatchable_names() -> None:
    """list_dispatchable_workflows excludes triage."""
    names = list_dispatchable_workflows()
    assert WorkflowName.TRIAGE not in names

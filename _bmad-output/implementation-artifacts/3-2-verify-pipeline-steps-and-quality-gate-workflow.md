# Story 3.2: Verify Pipeline Steps & Quality Gate Workflow

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want pipeline steps and a workflow definition for the full local quality gate,
so that `/verify` can execute all quality checks as a composable pipeline.

## Acceptance Criteria

1. **Given** io_ops verify functions from Story 3.1, **When** I inspect verify pipeline steps, **Then** each step wraps its io_ops function with the standard step signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` **And** step output includes structured `VerifyResult` in `WorkflowContext.outputs`.

2. **Given** all verify steps exist, **When** I inspect the `verify` workflow definition, **Then** it composes all verify steps (Jest, Playwright, mypy, ruff) into a single quality gate workflow (FR12) **And** the workflow is declarative data, not imperative code **And** the workflow runs all checks even if earlier checks fail (each is independent).

3. **Given** the verify workflow is executed by the engine, **When** all checks pass, **Then** the workflow succeeds with all VerifyResults in context outputs.

4. **Given** the verify workflow is executed, **When** one or more checks fail, **Then** the workflow completes all checks before reporting aggregate failure **And** all individual failures are captured in the result.

5. **Given** all verify pipeline code, **When** I run tests, **Then** tests cover: all-pass, single-failure, multiple-failures scenarios **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create verify step functions wrapping io_ops (AC: #1)
  - [x] 1.1 RED: Write test for `run_jest_step(ctx)` -- mock `io_ops.run_jest_tests` returning `IOSuccess(VerifyResult(tool_name="jest", passed=True, ...))`. Verify returns `IOResult[WorkflowContext, PipelineError]` with `VerifyResult` in `ctx.outputs["verify_jest"]`.
  - [x] 1.2 GREEN: Implement `run_jest_step` in `adws/adw_modules/steps/run_jest_step.py`. Calls `io_ops.run_jest_tests()`, wraps result into WorkflowContext outputs.
  - [x] 1.3 RED: Write test for `run_jest_step` failure path -- mock `io_ops.run_jest_tests` returning `IOSuccess(VerifyResult(passed=False, errors=[...]))`. Verify step returns `IOFailure(PipelineError(...))` with tool name and error details in context.
  - [x] 1.4 GREEN: Implement failure handling -- nonzero `VerifyResult.passed=False` produces a PipelineError.
  - [x] 1.5 RED: Write test for `run_jest_step` when `io_ops.run_jest_tests` returns `IOFailure`. Verify IOFailure propagates as-is.
  - [x] 1.6 GREEN: Implement IOFailure propagation via bind pattern.
  - [x] 1.7 RED: Write tests for `run_playwright_step`, `run_mypy_step`, `run_ruff_step` -- same 3 paths (success, tool failure, IOFailure propagation) for each.
  - [x] 1.8 GREEN: Implement `run_playwright_step.py`, `run_mypy_step.py`, `run_ruff_step.py` following same pattern as `run_jest_step`.
  - [x] 1.9 REFACTOR: Extract shared verify step pattern if duplication exists. Verify all 4 steps follow identical structure. Verify mypy/ruff clean.

- [x] Task 2: Export verify steps from steps/__init__.py (AC: #1)
  - [x] 2.1 RED: Write tests for importing all 4 verify steps from `adws.adw_modules.steps`.
  - [x] 2.2 GREEN: Add exports to `adws/adw_modules/steps/__init__.py` in a new "Verify pipeline steps" conceptual group.
  - [x] 2.3 REFACTOR: Verify import paths, mypy, ruff.

- [x] Task 3: Register verify step functions in engine step registry (AC: #1, #2)
  - [x] 3.1 RED: Write tests that `_STEP_REGISTRY` in executor.py contains entries for all 4 verify step functions.
  - [x] 3.2 GREEN: Add verify step functions to `_STEP_REGISTRY` in `adws/adw_modules/engine/executor.py`.
  - [x] 3.3 REFACTOR: Verify registry is consistent, mypy/ruff clean.

- [x] Task 4: Create verify workflow definition with always_run steps (AC: #2, #3, #4)
  - [x] 4.1 RED: Write test for verify workflow structure -- load `WorkflowName.VERIFY` (new constant) via `load_workflow()`. Verify: 4 steps (jest, playwright, mypy, ruff), all marked `always_run=True`, workflow is not dispatchable, each step has correct function name and output name.
  - [x] 4.2 GREEN: Add `WorkflowName.VERIFY = "verify"` to workflow registry. Create `_VERIFY` workflow in `workflows/__init__.py` with 4 steps, each `always_run=True`, with distinct `output` names for data flow.
  - [x] 4.3 RED: Write test for verify workflow all-pass scenario -- execute `run_workflow(verify_wf, ctx)` with all 4 step functions mocked to succeed. Verify IOSuccess, all 4 VerifyResults accessible in context via data flow registry.
  - [x] 4.4 GREEN: Ensure workflow definition works with engine execution (existing run_workflow handles always_run steps).
  - [x] 4.5 RED: Write test for verify workflow single-failure scenario -- mock jest step to fail, others succeed. Verify all 4 steps execute (always_run), final result is IOFailure with jest's PipelineError, other 3 steps' VerifyResults are tracked.
  - [x] 4.6 GREEN: Verify always_run behavior works correctly for independent quality checks.
  - [x] 4.7 RED: Write test for verify workflow multiple-failures scenario -- mock jest and ruff to fail, playwright and mypy succeed. Verify all 4 execute, final result is IOFailure with first failure (jest) as primary error, ruff failure in always_run_failures context.
  - [x] 4.8 GREEN: Verify multiple-failure aggregation works via existing always_run failure tracking.
  - [x] 4.9 REFACTOR: Clean up workflow definition, verify all scenarios covered, mypy/ruff clean.

- [x] Task 5: Verify full integration and quality gates (AC: #6)
  - [x] 5.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 5.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 5.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 3.1)

**io_ops.py** has 10 public functions + 1 shared helper + 1 async helper + 1 internal exception:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_shell_command(command: str, *, timeout: int | None = None, cwd: str | None = None) -> IOResult[ShellResult, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[None, PipelineError]: ...
def _build_verify_result(shell_result: ShellResult, tool_name: str, error_filter: Callable[[str], bool]) -> VerifyResult: ...
def run_jest_tests() -> IOResult[VerifyResult, PipelineError]: ...
def run_playwright_tests() -> IOResult[VerifyResult, PipelineError]: ...
def run_mypy_check() -> IOResult[VerifyResult, PipelineError]: ...
def run_ruff_check() -> IOResult[VerifyResult, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError exception
```

**types.py** has: `VerifyResult`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`.

**engine/executor.py** has 8 functions: `_resolve_step_function`, `run_step`, `_run_step_with_retry`, `_resolve_input_from`, `_should_skip_step`, `_record_failure`, `_finalize_workflow`, `run_workflow`. `_STEP_REGISTRY` has 2 entries: `check_sdk_available`, `execute_shell_step`.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (4 constants), `load_workflow()`, `list_workflows()`, 4 registered workflows (implement_close, implement_verify_close, convert_stories_to_beads, sample). `_REGISTRY` dict maps names to workflows.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 219 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: Verify Pipeline Steps

Each verify step follows the established step pattern from `execute_shell_step.py` and `check_sdk_available.py`:

```python
"""Execute <tool> quality gate and capture result in workflow context."""
from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import run_<tool>
from adws.adw_modules.types import VerifyResult, WorkflowContext


def run_<tool>_step(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute <tool> and capture VerifyResult in context outputs."""
    result = run_<tool>()

    def _handle_result(
        verify_result: VerifyResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        if not verify_result.passed:
            return IOFailure(
                PipelineError(
                    step_name="run_<tool>_step",
                    error_type="VerifyFailed",
                    message=f"<tool> check failed: {len(verify_result.errors)} error(s)",
                    context={
                        "tool_name": verify_result.tool_name,
                        "errors": verify_result.errors,
                        "raw_output": verify_result.raw_output,
                    },
                ),
            )
        return IOSuccess(
            ctx.merge_outputs({"verify_<tool>": verify_result}),
        )

    return result.bind(_handle_result)
```

**Key design decisions:**

1. **Four separate step files** -- one per tool, following the architecture rule "one public function per step matching filename": `run_jest_step.py`, `run_playwright_step.py`, `run_mypy_step.py`, `run_ruff_step.py`.

2. **VerifyResult in outputs** -- each step puts its `VerifyResult` in `ctx.outputs` under a unique key (e.g., `"verify_jest"`, `"verify_playwright"`, `"verify_mypy"`, `"verify_ruff"`). This enables Story 3.3 to accumulate feedback from all results.

3. **Failed VerifyResult = IOFailure** -- unlike the io_ops layer (Story 3.1) where `VerifyResult(passed=False)` is a valid success result, the STEP layer treats failed checks as pipeline failures (IOFailure with PipelineError). This is the policy boundary: io_ops reports facts, steps enforce policy.

4. **bind pattern for IOFailure propagation** -- if `run_<tool>()` itself returns IOFailure (timeout, command not found), it propagates automatically through bind. The `_handle_result` inner function only handles the IOSuccess case.

### Design: Verify Workflow (always_run Pattern)

The verify workflow marks ALL steps as `always_run=True` so the engine executes all quality checks even when earlier ones fail. This directly satisfies AC #2: "the workflow runs all checks even if earlier checks fail (each is independent)."

```python
_VERIFY = Workflow(
    name=WorkflowName.VERIFY,
    description="Full local quality gate: Jest, Playwright, mypy, ruff",
    dispatchable=False,  # Invoked via /verify command, not Beads dispatch
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
```

**Why `always_run=True` on all steps?**

The existing engine executor already supports the `always_run` behavior (Story 2.5). When the first step fails:
- Normal steps would be skipped (halt-on-failure)
- `always_run` steps continue executing regardless
- The original failure is preserved in `pipeline_failure`
- Subsequent always_run failures are tracked in `always_run_failures`
- `_finalize_workflow()` returns the original error enriched with `always_run_failures` context

This perfectly matches the requirement: "the workflow completes all checks before reporting aggregate failure."

**Why `dispatchable=False`?**

The verify workflow is invoked by the `/verify` command (Story 4.2) and used inline by `implement_verify_close` (Story 4.8). It is not triggered by Beads issue tags, so it should not be dispatchable.

**Why `output` on each step?**

Each step has a named `output` key so the data flow registry can track individual VerifyResults. This enables Story 3.3 to access individual tool results for feedback accumulation.

### Design: Failure Aggregation Through always_run

When the verify workflow executes with failures, the engine's existing always_run failure tracking provides the aggregate behavior:

**Single failure (jest fails, others pass):**
1. jest step executes, returns IOFailure -> `pipeline_failure = jest_error`
2. playwright step executes (always_run), succeeds -> outputs recorded
3. mypy step executes (always_run), succeeds -> outputs recorded
4. ruff step executes (always_run), succeeds -> outputs recorded
5. `_finalize_workflow` returns IOFailure with jest_error

**Multiple failures (jest and ruff fail):**
1. jest step executes, returns IOFailure -> `pipeline_failure = jest_error`
2. playwright step executes (always_run), succeeds -> outputs recorded
3. mypy step executes (always_run), succeeds -> outputs recorded
4. ruff step executes (always_run), returns IOFailure -> ruff_error added to `always_run_failures`
5. `_finalize_workflow` returns IOFailure with jest_error, context includes `always_run_failures: [ruff_error.to_dict()]`

This leverages the existing `_record_failure()` and `_finalize_workflow()` functions from Story 2.5 without any engine changes.

### Test Strategy

**New test files** (one per step module):
- `adws/tests/adw_modules/steps/test_run_jest_step.py`
- `adws/tests/adw_modules/steps/test_run_playwright_step.py`
- `adws/tests/adw_modules/steps/test_run_mypy_step.py`
- `adws/tests/adw_modules/steps/test_run_ruff_step.py`

Per architecture: "Every test file tests exactly one module. No multi-module test files."

**Modified test files**:
- `adws/tests/workflows/test_workflows.py` -- add verify workflow registry and structure tests
- `adws/tests/adw_modules/engine/test_executor.py` -- add verify workflow integration tests (all-pass, single-failure, multi-failure)

**Mock targets for step tests**:
- `adws.adw_modules.io_ops.run_jest_tests` (mock within the step's import of io_ops)
- `adws.adw_modules.io_ops.run_playwright_tests`
- `adws.adw_modules.io_ops.run_mypy_check`
- `adws.adw_modules.io_ops.run_ruff_check`

The step tests mock at the io_ops boundary (NFR10), NOT at subprocess/shell level.

**Mock targets for workflow integration tests**:
- `adws.adw_modules.engine.executor._STEP_REGISTRY` -- inject controllable step functions

**For each verify step, test 3 paths:**
1. **Success**: io_ops returns `IOSuccess(VerifyResult(passed=True))` -> step returns `IOSuccess(ctx_with_verify_result_in_outputs)`
2. **Tool failure**: io_ops returns `IOSuccess(VerifyResult(passed=False, errors=[...]))` -> step returns `IOFailure(PipelineError(...))` with tool name, errors, raw_output in context
3. **IO failure**: io_ops returns `IOFailure(PipelineError(...))` -> step returns `IOFailure(same_error)` via bind propagation

**For verify workflow integration tests (in test_executor.py):**
- `test_verify_workflow_all_pass` -- all 4 steps succeed, IOSuccess with all VerifyResults
- `test_verify_workflow_single_failure` -- 1 step fails, others succeed (always_run), IOFailure with single error
- `test_verify_workflow_multiple_failures` -- 2+ steps fail, all execute, IOFailure with first failure + always_run_failures

**For verify workflow registry tests (in test_workflows.py):**
- `test_verify_workflow_registered` -- `load_workflow("verify")` returns verify workflow
- `test_verify_workflow_not_dispatchable` -- `dispatchable=False`
- `test_verify_workflow_has_four_steps` -- 4 steps with expected names
- `test_verify_workflow_all_steps_always_run` -- all steps have `always_run=True`
- `test_verify_workflow_steps_have_output_names` -- each step has a unique `output` name

### Ruff Considerations

- `FBT001`/`FBT002` (boolean positional): `VerifyResult(passed=True)` is a keyword arg in frozen dataclass. No issue.
- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files.
- `E501` (line too long): Keep all lines under 88 characters.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations, following existing step patterns.
- `ARG001` (unused function argument): Step functions receive `ctx` but verify functions don't need inputs from context. The ctx parameter is still required for the step signature. If ruff flags it, suppress with `# noqa: ARG001` -- BUT actually `ctx` IS used (to produce the output context via `ctx.merge_outputs()`), so this should not arise.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- steps use IOResult/bind pattern, never raise.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Steps call io_ops verify functions, never subprocess/shell directly.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR13**: Workflow definitions (Tier 1) testable without mocking ROP internals. Verify workflow is declarative data tested as plain structure.
- **FR12**: `/verify` quality gate execution -- the verify workflow composes all checks.
- **FR13**: Jest via `run_jest_step` -> `io_ops.run_jest_tests()`.
- **FR14**: Playwright via `run_playwright_step` -> `io_ops.run_playwright_tests()`.
- **FR15**: mypy + ruff via `run_mypy_step`/`run_ruff_step` -> `io_ops.run_mypy_check()`/`io_ops.run_ruff_check()`.

### What NOT to Do

- Do NOT implement feedback accumulation -- that is Story 3.3. This story is steps + workflow only.
- Do NOT create the `/verify` command entry point -- that is Story 4.2.
- Do NOT change any io_ops verify functions from Story 3.1 -- build ON TOP of them.
- Do NOT change the engine executor -- the existing always_run + data flow + failure aggregation handles everything.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `merge_outputs()` or `with_updates()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe`.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT create step files with wrong names -- use imperative form matching function name: `run_jest_step.py`, not `jest_step.py` or `verify_jest.py`.
- Do NOT make the verify workflow dispatchable -- it is invoked via command, not Beads dispatch.
- Do NOT create a separate workflow file for the verify workflow -- keep it in `workflows/__init__.py` following the established pattern (all workflow definitions live there).
- Do NOT use separate step directories or subdirectories -- all steps are flat in `adws/adw_modules/steps/` per architecture.
- Do NOT skip `output` names on verify steps -- data flow tracking is needed for Story 3.3 feedback accumulation.
- Do NOT change the `always_run` behavior pattern -- it is tested and working from Story 2.5.

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/run_jest_step.py` -- verify step wrapping io_ops.run_jest_tests
- `adws/adw_modules/steps/run_playwright_step.py` -- verify step wrapping io_ops.run_playwright_tests
- `adws/adw_modules/steps/run_mypy_step.py` -- verify step wrapping io_ops.run_mypy_check
- `adws/adw_modules/steps/run_ruff_step.py` -- verify step wrapping io_ops.run_ruff_check
- `adws/tests/adw_modules/steps/test_run_jest_step.py` -- jest step tests (3 paths)
- `adws/tests/adw_modules/steps/test_run_playwright_step.py` -- playwright step tests (3 paths)
- `adws/tests/adw_modules/steps/test_run_mypy_step.py` -- mypy step tests (3 paths)
- `adws/tests/adw_modules/steps/test_run_ruff_step.py` -- ruff step tests (3 paths)

Files to modify:
- `adws/adw_modules/steps/__init__.py` -- add exports for 4 verify steps
- `adws/adw_modules/engine/executor.py` -- add 4 verify step functions to `_STEP_REGISTRY`
- `adws/workflows/__init__.py` -- add `WorkflowName.VERIFY`, `_VERIFY` workflow, register in `_REGISTRY`
- `adws/tests/workflows/test_workflows.py` -- add verify workflow registry/structure tests
- `adws/tests/adw_modules/engine/test_executor.py` -- add verify workflow integration tests (all-pass, single-failure, multi-failure)

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] -- AC and story definition (FR12, FR13, FR14, FR15)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] -- Epic summary: "Story ordering critical: verify steps wrap shell execution from Epic 2 (FR11). Each verify sub-step is an io_ops shell function before it becomes a pipeline step."
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, dispatchable flag, load_workflow() pure lookup
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, verify workflow as part of implement_verify_close
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist, step internal structure, io_ops function pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Quality Verification (FR12-17)] -- "Inline shell steps in implement_verify_close.py", verify steps
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Composition Notes] -- "Verification logic (FR12-FR17) is composed from inline shell Step definitions"
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- Steps flat in adws/adw_modules/steps/, workflows in workflows/__init__.py
- [Source: adws/adw_modules/io_ops.py] -- io_ops with 4 verify functions (run_jest_tests, run_playwright_tests, run_mypy_check, run_ruff_check)
- [Source: adws/adw_modules/types.py] -- VerifyResult frozen dataclass, WorkflowContext with merge_outputs()
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/executor.py] -- Engine with always_run, _record_failure, _finalize_workflow, _STEP_REGISTRY
- [Source: adws/adw_modules/engine/types.py] -- Step (always_run, output), Workflow, StepFunction
- [Source: adws/adw_modules/steps/execute_shell_step.py] -- Established step pattern using bind for IOFailure propagation
- [Source: adws/adw_modules/steps/check_sdk_available.py] -- Established step pattern for non-shell steps
- [Source: adws/adw_modules/steps/__init__.py] -- Current exports (check_sdk_available, execute_shell_step)
- [Source: adws/workflows/__init__.py] -- Workflow registry with WorkflowName, _REGISTRY, load_workflow(), list_workflows()
- [Source: adws/tests/conftest.py] -- Shared fixtures (sample_workflow_context, mock_io_ops)
- [Source: adws/tests/adw_modules/steps/test_execute_shell_step.py] -- Existing step test patterns
- [Source: adws/tests/adw_modules/engine/test_executor.py] -- Existing executor tests with _STEP_REGISTRY mocking pattern
- [Source: adws/tests/workflows/test_workflows.py] -- Existing workflow registry tests
- [Source: _bmad-output/implementation-artifacts/3-1-verify-io-ops-shell-functions.md] -- Previous story: io_ops verify functions, VerifyResult, _build_verify_result, bind pattern, IOFailure propagation design
- [Source: _bmad-output/implementation-artifacts/2-7-workflow-combinators-and-sample-workflow.md] -- Combinator design, sample workflow, IOResult type order, _STEP_REGISTRY mocking pattern

### Git Intelligence (Recent Commits)

```
9df410d fix: Code review fixes for Story 2.2 (4 issues resolved)
0a0e276 chore: Bump version to 1.2.20 [skip ci]
009fe43 feat: Implement io_ops SDK Client & Enemy Unit Tests (Story 2.2)
4d5fcd1 chore: Bump version to 1.2.19 [skip ci]
b085c46 feat: Create Story 2.2 - io_ops SDK Client & Enemy Unit Tests (ready-for-dev)
```

Pattern: RED commits use prefix `test(RED):`, feature commits use `feat:`, review fixes use `fix:`.

### Previous Story Intelligence

From Story 3.1 learnings:
- **VerifyResult**: Frozen dataclass with `tool_name`, `passed`, `errors` (default_factory=list), `raw_output` (default=""). Lives in types.py.
- **_build_verify_result shared helper**: Extracted during refactoring. Each verify function passes a tool-specific filter predicate. DRY across all 4 verify functions.
- **bind pattern**: All 4 verify functions use `result.bind(_handle_result)`. IOFailure propagation is automatic via bind.
- **Nonzero exit is NOT IOFailure in io_ops**: The io_ops layer returns `IOSuccess(VerifyResult(passed=False))` for tool failures. Policy enforcement (treating failed checks as pipeline errors) belongs at the STEP layer.
- **io_ops.py size**: 10 public functions, 91 statements. Still within single-file threshold.
- **Test count**: 219 tests (excluding 2 enemy), 100% line+branch coverage.
- **Ruff noise filter**: `_ruff_filter` uses structural `file:line:col:` check, not naive string matching.
- **Command assertions**: Tests verify the exact command passed to `run_shell_command` via `assert_called_once_with`.

From Story 2.7 learnings:
- **_STEP_REGISTRY mocking**: Tests mock `adws.adw_modules.engine.executor._STEP_REGISTRY` directly via `mocker.patch("adws.adw_modules.engine.executor._STEP_REGISTRY", {...})`.
- **Sample workflow integration tests**: Use mock step functions that return controlled IOSuccess/IOFailure. Helper functions `_make_success_step`, `_make_failure_step`, `_make_flaky_step` exist in test_executor.py.
- **always_run tracking**: `always_run_failures` accumulator in `run_workflow` tracks always_run step failures without losing the original pipeline error.

From Story 2.5 learnings:
- **unsafe_perform_io()**: Use `from returns.unsafe import unsafe_perform_io` to unwrap IOResult containers.
- **pipeline_failure tracking**: `run_workflow` tracks via `pipeline_failure: PipelineError | None`.
- **sleep_seconds mock**: Tests mock `adws.adw_modules.engine.executor.sleep_seconds`.

From Story 2.4 learnings:
- **TYPE_CHECKING guard**: Used in executor.py for Step, StepFunction, Workflow, WorkflowContext.
- **Registry mocking**: `mocker.patch("adws.adw_modules.engine.executor._STEP_REGISTRY", {...})`.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Architecture Note on Step vs Inline Shell Steps

The architecture says "Verification logic (FR12-FR17) is NOT a dedicated step module. It is composed from inline shell Step definitions within the implement_verify_close workflow." However, the EPICS file for Story 3.2 explicitly defines steps wrapping io_ops functions with the standard step signature. The EPICS definition takes precedence for story-level scope.

The architecture's "inline shell Step definitions" refers to the overall workflow composition approach. Our implementation creates proper step modules that follow the established step creation checklist, which is architecturally consistent -- each step wraps its io_ops function and produces a typed result. The `implement_verify_close` workflow (Story 4.8) can then compose these steps or define inline variants as needed.

The key architectural constraint that IS respected: the verify workflow is declarative data (not imperative code), and each step goes through the io_ops boundary.

### Step Registry Growth Note

After this story, `_STEP_REGISTRY` in executor.py will have 6 entries (up from 2). This is well within manageable limits. The registry pattern remains simple: string name -> step function callable.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 4 verify step modules follow identical structure: call io_ops function, bind _handle_result inner function, IOFailure propagation automatic via bind.
- No shared extraction needed (REFACTOR phase confirmed 4 identical patterns, but each is a single small function -- extraction would add complexity without reducing duplication meaningfully).
- The verify workflow leverages existing always_run engine behavior from Story 2.5 with zero engine changes.
- Test count: 251 tests (up from 219, +32 new tests), 100% line+branch coverage maintained.
- _STEP_REGISTRY now has 6 entries (up from 2): check_sdk_available, execute_shell_step, run_jest_step, run_playwright_step, run_mypy_step, run_ruff_step.
- WorkflowName has 5 constants (up from 4): added VERIFY.
- _REGISTRY has 5 workflows (up from 4): added _VERIFY.

### File List

Files created:
- `adws/adw_modules/steps/run_jest_step.py` -- verify step wrapping io_ops.run_jest_tests
- `adws/adw_modules/steps/run_playwright_step.py` -- verify step wrapping io_ops.run_playwright_tests
- `adws/adw_modules/steps/run_mypy_step.py` -- verify step wrapping io_ops.run_mypy_check
- `adws/adw_modules/steps/run_ruff_step.py` -- verify step wrapping io_ops.run_ruff_check
- `adws/tests/adw_modules/steps/test_run_jest_step.py` -- jest step tests (4 tests: 3 paths + import)
- `adws/tests/adw_modules/steps/test_run_playwright_step.py` -- playwright step tests (4 tests)
- `adws/tests/adw_modules/steps/test_run_mypy_step.py` -- mypy step tests (4 tests)
- `adws/tests/adw_modules/steps/test_run_ruff_step.py` -- ruff step tests (4 tests)

Files modified:
- `adws/adw_modules/steps/__init__.py` -- added exports for 4 verify steps
- `adws/adw_modules/engine/executor.py` -- added 4 verify step functions to _STEP_REGISTRY
- `adws/workflows/__init__.py` -- added WorkflowName.VERIFY, _VERIFY workflow, registered in _REGISTRY
- `adws/tests/workflows/test_workflows.py` -- added 8 verify workflow registry/structure tests
- `adws/tests/adw_modules/engine/test_executor.py` -- added 4 registry tests + 3 verify workflow integration tests

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (Adversarial Code Review)
**Date**: 2026-02-02
**Verdict**: APPROVED with 5 issues found, all fixed

### Issues Found

| # | Severity | Description | Resolution |
|---|----------|-------------|------------|
| 1 | MEDIUM | **Failure message assertion missing tool name check** -- All 4 step tool_failure tests only asserted `"1 error(s)" in error.message` without verifying the tool name was present. A refactoring could silently drop the tool name from the message format. | Added `assert "<tool> check failed" in error.message` to all 4 step failure tests. |
| 2 | MEDIUM | **No assertion that failure path leaves ctx.outputs empty** -- Failure tests did not verify that the original context was not polluted with outputs. While `WorkflowContext` is frozen, this assertion guards against refactoring that could merge outputs before returning IOFailure. | Added `assert ctx.outputs == {}` to all 4 step tool_failure tests. |
| 3 | LOW | **Single-failure integration test did not assert absence of always_run_failures** -- `test_verify_workflow_single_failure` verified jest was the primary error and all 4 steps ran, but did not assert that `always_run_failures` was absent from the error context. | Added `assert "always_run_failures" not in error.context`. |
| 4 | LOW | **All-pass integration test only checked 2 of 4 VerifyResults** -- `test_verify_workflow_all_pass` only verified jest in inputs and ruff in outputs, leaving playwright and mypy unchecked. | Replaced single jest assertion with a loop verifying all 3 promoted tools (jest, playwright, mypy) in inputs. |
| 5 | LOW | **Story dev notes reference to _make_flaky_step** -- Story notes mention this helper from existing test patterns; it exists from prior stories but was not relevant to 3.2. No code fix needed. | Noted, no fix required. |

### AC Verification

| AC | Status | Evidence |
|----|--------|----------|
| AC1 | PASS | 4 step modules each follow `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` signature, placing `VerifyResult` in `ctx.outputs["verify_<tool>"]` on success. Tests verify all 3 paths per step. |
| AC2 | PASS | `_VERIFY` workflow in `workflows/__init__.py` is declarative data with 4 steps, all `always_run=True`, `dispatchable=False`. Tests verify structure, step names, output names, function names. |
| AC3 | PASS | `test_verify_workflow_all_pass` demonstrates all 4 steps succeed, final context has all VerifyResults accessible (ruff in outputs, jest/playwright/mypy promoted to inputs). |
| AC4 | PASS | `test_verify_workflow_single_failure` and `test_verify_workflow_multiple_failures` demonstrate all steps execute despite failures, aggregate failure captured with `always_run_failures` for multi-failure case. |
| AC5 | PASS | All-pass, single-failure, and multiple-failure scenarios covered in integration tests. 100% branch coverage. |
| AC6 | PASS | 251 tests pass, 100% line+branch coverage, mypy strict clean, ruff zero violations. |

### Quality Gates (Post-Fix)

- pytest: 251 passed, 2 deselected (enemy) -- PASS
- coverage: 100.00% line+branch -- PASS
- mypy: strict mode, 0 issues in 39 files -- PASS
- ruff: All checks passed -- PASS

### Implementation Quality Notes

- The 4 verify step modules are clean, consistent, and follow the established step pattern from `execute_shell_step.py`.
- The `bind` pattern for IOFailure propagation is correct and elegant.
- The workflow definition correctly leverages the existing `always_run` engine behavior from Story 2.5 with zero engine changes.
- Step registry in `executor.py` is cleanly extended from 2 to 6 entries.
- Test count increased from 219 to 251 (+32 new tests).
- No architectural violations detected.

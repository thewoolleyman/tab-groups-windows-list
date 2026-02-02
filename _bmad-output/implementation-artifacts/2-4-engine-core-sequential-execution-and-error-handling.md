# Story 2.4: Engine Core - Sequential Execution & Error Handling

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want the engine to execute workflows as a sequence of steps with ROP-based error handling,
so that step failures are handled gracefully without uncaught exceptions or partial state corruption.

## Acceptance Criteria

1. **Given** a workflow with multiple steps, **When** the engine executes the workflow, **Then** steps run in sequence with ROP-based error handling (FR1) **And** each SDK step is executed as a fresh SDK call via `ClaudeSDKClient` (FR2) **And** context (outputs/inputs) propagates between sequential steps (FR3).

2. **Given** a step fails during execution, **When** the engine processes the failure, **Then** execution halts and `PipelineError` propagates with structured details (FR4) **And** no uncaught exceptions occur (NFR1) **And** no partial state corruption -- context is consistent up to the failed step.

3. **Given** all engine code, **When** I run tests, **Then** tests cover: successful multi-step execution, mid-pipeline failure, context propagation across steps **And** tests validate PipelineError contains correct step_name, error_type, and message **And** 100% coverage is maintained (NFR9).

4. **Given** all code, **When** I run `uv run pytest adws/tests/`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Implement `run_step` function in executor.py (AC: #1, #2)
  - [x] 1.1 RED: Write tests for `run_step` success path -- given a step and WorkflowContext, calls the step function and returns the updated context
  - [x] 1.2 GREEN: Implement `run_step` in `adws/adw_modules/engine/executor.py` -- resolves step function by name, dispatches shell vs SDK steps, returns `IOResult[WorkflowContext, PipelineError]`
  - [x] 1.3 RED: Write tests for `run_step` failure path -- step function returns IOFailure, run_step propagates PipelineError with correct step_name
  - [x] 1.4 GREEN: Implement error propagation -- wrap PipelineError with step name context if not already set
  - [x] 1.5 RED: Write tests for `run_step` shell step dispatch -- when `step.shell=True`, run_step injects `shell_command` into context inputs and delegates to `execute_shell_step`
  - [x] 1.6 GREEN: Implement shell step dispatch in `run_step`
  - [x] 1.7 RED: Write tests for `run_step` SDK step dispatch -- when `step.shell=False`, run_step resolves function from step registry and calls it
  - [x] 1.8 GREEN: Implement SDK step dispatch using step function registry
  - [x] 1.9 REFACTOR: Clean up, verify 100% coverage, mypy/ruff clean

- [x] Task 2: Implement context propagation via `promote_outputs_to_inputs` (AC: #1)
  - [x] 2.1 RED: Write tests for context propagation between steps -- after step N succeeds, outputs are promoted to inputs for step N+1
  - [x] 2.2 GREEN: Implement context propagation in executor using `WorkflowContext.promote_outputs_to_inputs()`
  - [x] 2.3 RED: Write tests for context propagation edge cases -- empty outputs, collision detection (outputs key already in inputs)
  - [x] 2.4 GREEN: Handle collision edge case -- convert ValueError from `promote_outputs_to_inputs` into PipelineError
  - [x] 2.5 REFACTOR: Clean up, verify coverage

- [x] Task 3: Implement `run_workflow` function in executor.py (AC: #1, #2)
  - [x] 3.1 RED: Write tests for `run_workflow` with single step -- executes step, returns final context
  - [x] 3.2 GREEN: Implement `run_workflow` that iterates through workflow.steps, calling `run_step` for each
  - [x] 3.3 RED: Write tests for `run_workflow` with multiple steps -- all succeed, final context has accumulated state
  - [x] 3.4 GREEN: Wire sequential step execution with context propagation between steps
  - [x] 3.5 RED: Write tests for `run_workflow` mid-pipeline failure -- step 2 of 3 fails, execution halts, PipelineError propagated, context is consistent up to the failed step
  - [x] 3.6 GREEN: Implement failure halt -- on IOFailure from any step, stop execution and return the PipelineError
  - [x] 3.7 RED: Write tests for `run_workflow` first step failure -- step 1 fails, no further steps execute
  - [x] 3.8 GREEN: Ensure first-step failure is handled correctly
  - [x] 3.9 REFACTOR: Clean up, verify full coverage

- [x] Task 4: Implement step function registry (AC: #1)
  - [x] 4.1 RED: Write tests for step function lookup -- given a function name string, returns the corresponding StepFunction callable
  - [x] 4.2 GREEN: Implement `_resolve_step_function` in executor.py that maps function name strings to actual step callables
  - [x] 4.3 RED: Write tests for unknown function name -- returns PipelineError with available function names
  - [x] 4.4 GREEN: Implement unknown function error with helpful message listing registered functions
  - [x] 4.5 REFACTOR: Clean up, export from engine/__init__.py, verify coverage

- [x] Task 5: Verify full integration and quality gates (AC: #3, #4)
  - [x] 5.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all unit tests pass, 100% coverage
  - [x] 5.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 5.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 2.3)

**engine/types.py** has the full Tier 1 public API:
```python
StepFunction = Callable[["WorkflowContext"], "IOResult[WorkflowContext, PipelineError]"]

@dataclass(frozen=True)
class Step:
    name: str
    function: str
    always_run: bool = False
    max_attempts: int = 1
    shell: bool = False
    command: str = ""

@dataclass(frozen=True)
class Workflow:
    name: str
    description: str
    steps: list[Step] = field(default_factory=list)
    dispatchable: bool = True
```

**engine/__init__.py** is empty (just the package marker). The executor module does NOT exist yet -- that is the primary deliverable of this story.

**io_ops.py** has 4 functions + 1 async helper:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_shell_command(command: str, *, timeout: int | None = None, cwd: str | None = None) -> IOResult[ShellResult, PipelineError]: ...
```

**types.py** has: `WorkflowContext` (frozen dataclass with `inputs`, `outputs`, `feedback` and methods: `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `ShellResult`, `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`.

**steps/check_sdk_available.py** -- step with correct signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.

**steps/execute_shell_step.py** -- shell command step that reads `shell_command` from `ctx.inputs`, calls `run_shell_command`, merges output into `ctx.outputs`.

**workflows/__init__.py** -- Has `WorkflowName`, `load_workflow()`, `list_workflows()`, and 3 registered workflows (implement_close has steps, others empty).

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 88 tests (excluding 2 enemy tests), 100% coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[str, PipelineError]` -- success is `str`, error is `PipelineError`
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`
- `IOResult[AdwsResponse, PipelineError]` -- success is `AdwsResponse`

### Engine Executor Design

The executor is the Tier 2 ROP execution logic. It is the ONLY module that chains `IOResult` operations and manages the step execution loop. Workflow definitions (Tier 1) never see ROP internals.

**File**: `adws/adw_modules/engine/executor.py`

**Two public functions:**

1. `run_step(step: Step, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`
   - Resolves step function from the function name string
   - Dispatches: shell steps go to `execute_shell_step` (after injecting `shell_command` into context inputs), SDK steps go through the step function registry
   - Returns updated `WorkflowContext` on success, `PipelineError` on failure

2. `run_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`
   - Iterates through `workflow.steps` sequentially
   - Calls `run_step` for each step
   - On success: promotes outputs to inputs between steps (via `promote_outputs_to_inputs()`)
   - On failure: halts execution, returns the `PipelineError`
   - **IMPORTANT**: This story implements ONLY sequential execution and halt-on-failure. `always_run` steps and retry logic are deferred to Story 2.5.

**One private function:**

3. `_resolve_step_function(function_name: str) -> IOResult[StepFunction, PipelineError]`
   - Maps function name strings (e.g., `"check_sdk_available"`) to actual callables
   - Uses a registry dict mapping names to imported step functions
   - Returns `IOFailure` with helpful error for unknown function names

### Step Function Registry Pattern

The executor needs to map the `Step.function` string field to actual callable step functions. This is a simple dict-based registry:

```python
from adws.adw_modules.steps import check_sdk_available, execute_shell_step

_STEP_REGISTRY: dict[str, StepFunction] = {
    "check_sdk_available": check_sdk_available,
    "execute_shell_step": execute_shell_step,
}
```

For Story 2.4, only existing step functions need to be registered. Future stories add new steps to this registry. The registry is intentionally simple -- a dict lookup, not a plugin system.

### Shell Step Dispatch Pattern

When `step.shell` is `True`, the executor:
1. Takes `step.command` and injects it into `ctx.inputs` as `"shell_command"`
2. Calls `execute_shell_step(updated_ctx)` directly (bypasses the step function registry)
3. Returns the result

This is consistent with how `execute_shell_step` already works -- it reads `shell_command` from `ctx.inputs`.

```python
if step.shell:
    shell_ctx = ctx.with_updates(
        inputs={**ctx.inputs, "shell_command": step.command},
    )
    return execute_shell_step(shell_ctx)
```

### Context Propagation Pattern

Between sequential steps, outputs from step N become inputs for step N+1:

```python
# After step N succeeds with updated_ctx:
propagated_ctx = updated_ctx.promote_outputs_to_inputs()
# propagated_ctx.inputs now contains step N's outputs
# propagated_ctx.outputs is empty (ready for step N+1)
```

**Collision handling**: `promote_outputs_to_inputs()` raises `ValueError` if any output key already exists in inputs. The executor MUST catch this and convert to a `PipelineError` rather than letting the exception propagate uncaught (NFR1).

### Halt-on-Failure Pattern

When a step returns `IOFailure`, the executor:
1. Stops iterating through remaining steps
2. Returns the `IOFailure` immediately
3. Does NOT call any further steps

**IMPORTANT**: This story does NOT implement `always_run` step handling. Steps marked `always_run=True` are still skipped on failure in this story. Story 2.5 adds the `always_run` behavior. The executor should be designed to make this extension straightforward (e.g., by separating the step iteration from the always_run logic).

### What `run_workflow` Does NOT Do (deferred to later stories)

- **always_run steps** (Story 2.5): Steps with `always_run=True` should execute even after failures
- **Retry logic** (Story 2.5): Steps with `max_attempts > 1` should be retried on failure
- **Data flow via output/input_from** (Story 2.6): Explicit data flow mapping between steps
- **Conditional steps** (Story 2.6): Steps with condition predicates
- **Combinators** (Story 2.7): `with_verification`, `sequence`

Design the executor so these features can be added incrementally without rewriting the core loop.

### Test Strategy

**Test file**: `adws/tests/adw_modules/engine/test_executor.py` (new file)

**Mock targets**: Step functions are mocked directly (not via io_ops). The executor tests verify orchestration logic, not step internals. Use `mocker.patch` to replace step functions in the registry.

**Test helper**: Create simple step functions for testing:
```python
def _make_success_step(output_key: str, output_value: object) -> StepFunction:
    """Create a step function that succeeds and adds to outputs."""
    def step(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(ctx.merge_outputs({output_key: output_value}))
    return step

def _make_failure_step(error_msg: str) -> StepFunction:
    """Create a step function that fails with a PipelineError."""
    def step(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]:
        return IOFailure(PipelineError(
            step_name="test_step",
            error_type="TestError",
            message=error_msg,
            context={},
        ))
    return step
```

**Tests needed for `run_step`:**
- `test_run_step_success` -- step function returns IOSuccess, run_step returns updated context
- `test_run_step_failure` -- step function returns IOFailure, run_step propagates PipelineError
- `test_run_step_shell_dispatch` -- step.shell=True, injects shell_command and delegates to execute_shell_step
- `test_run_step_sdk_dispatch` -- step.shell=False, resolves function from registry
- `test_run_step_unknown_function` -- function name not in registry, returns PipelineError with available names

**Tests needed for context propagation:**
- `test_context_propagation_outputs_become_inputs` -- step outputs are promoted to inputs for next step
- `test_context_propagation_empty_outputs` -- empty outputs still work (no-op promotion)
- `test_context_propagation_collision_error` -- collision between outputs and existing inputs produces PipelineError

**Tests needed for `run_workflow`:**
- `test_run_workflow_single_step_success` -- one step succeeds, returns final context
- `test_run_workflow_multi_step_success` -- three steps succeed, context accumulates across all
- `test_run_workflow_mid_pipeline_failure` -- step 2 of 3 fails, execution halts, PipelineError returned, step 3 never called
- `test_run_workflow_first_step_failure` -- step 1 fails, no further steps execute
- `test_run_workflow_empty_workflow` -- workflow with no steps returns initial context unchanged
- `test_run_workflow_context_flows_through_steps` -- verify outputs from step 1 are available as inputs to step 2

### Ruff Considerations

- `PLR0911` (too many return statements): If `run_step` has too many returns, consolidate branches
- `S108` (hardcoded temp directory): Avoid `/tmp/` in test data
- `E501` (line too long): Keep all lines under 88 characters
- `ARG001` (unused function argument): Already suppressed for test files in pyproject.toml
- `FBT001`/`FBT002` (boolean): The `shell` field on Step is a dataclass field, not a function parameter

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- all errors wrapped in IOResult/PipelineError. The ValueError from `promote_outputs_to_inputs()` MUST be caught.
- **NFR9**: 100% line + branch coverage on all adws/ code
- **NFR10**: The executor does NOT import `subprocess` or `claude_agent_sdk` -- it calls step functions which call io_ops
- **NFR11**: mypy strict mode -- all function signatures fully typed
- **NFR12**: ruff ALL rules -- zero lint violations
- **NFR13**: Workflow definitions (Tier 1) remain testable without mocking ROP internals. The executor (Tier 2) uses ROP internally but Tier 1 tests should not need to know about it.
- **FR1**: Workflow execution with ROP error handling
- **FR2**: Each SDK step as fresh SDK call (via step functions that call io_ops.execute_sdk_call)
- **FR3**: Context propagation between sequential steps
- **FR4**: Halt on failure, propagate PipelineError

### What NOT to Do

- Do NOT import `subprocess` or `claude_agent_sdk` in executor.py -- the executor orchestrates steps, steps call io_ops
- Do NOT implement `always_run` logic in this story -- that is Story 2.5
- Do NOT implement retry logic in this story -- that is Story 2.5
- Do NOT implement `input_from`/`output` data flow mapping -- that is Story 2.6
- Do NOT implement conditional step execution -- that is Story 2.6
- Do NOT implement combinators (`with_verification`, `sequence`) -- that is Story 2.7
- Do NOT catch bare `Exception` in the executor -- catch specific errors, let others propagate as IOFailure
- Do NOT mutate `WorkflowContext` -- always return new instances
- Do NOT change existing test assertions or existing function signatures
- Do NOT put executor logic in steps -- the executor orchestrates, steps execute
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`
- Do NOT add new io_ops functions -- the executor uses existing step functions which already call io_ops
- Do NOT use `flow()` or `bind()` for the main execution loop -- use a simple for-loop with early return on failure. ROP combinators are better for within-step logic, not for the executor's sequential iteration. Keep the executor loop readable.

### Project Structure Notes

Files to create:
- `adws/adw_modules/engine/executor.py` -- engine executor with `run_step`, `run_workflow`, `_resolve_step_function`
- `adws/tests/adw_modules/engine/test_executor.py` -- comprehensive tests for executor

Files to modify:
- `adws/adw_modules/engine/__init__.py` -- export `run_step`, `run_workflow` from executor

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist, io_ops function pattern, step internal structure, Four-Layer Pipeline Boundary
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, load_workflow() pure lookup
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries] -- Tier 2 engine executor, ROP internals hidden from Tier 1
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5] -- Next story (always_run + retry) depends on executor from this story
- [Source: _bmad-output/implementation-artifacts/2-3-step-function-type-and-shell-command-execution.md] -- Previous story learnings, current code state
- [Source: _bmad-output/implementation-artifacts/2-2-io-ops-sdk-client-and-enemy-unit-tests.md] -- SDK client pattern, IOResult conventions
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction types
- [Source: adws/adw_modules/types.py] -- WorkflowContext with promote_outputs_to_inputs(), merge_outputs()
- [Source: adws/adw_modules/errors.py] -- PipelineError
- [Source: adws/adw_modules/io_ops.py] -- I/O boundary (4 functions)
- [Source: adws/adw_modules/steps/execute_shell_step.py] -- Shell step pattern
- [Source: adws/adw_modules/steps/check_sdk_available.py] -- SDK step pattern
- [Source: adws/adw_modules/steps/__init__.py] -- Step exports (check_sdk_available, execute_shell_step)
- [Source: adws/workflows/__init__.py] -- Workflow registry, load_workflow(), list_workflows()
- [Source: adws/tests/conftest.py] -- Shared test fixtures
- [Source: adws/tests/adw_modules/engine/test_types.py] -- Existing engine type tests (reference for test patterns)

### Git Intelligence (Recent Commits)

```
b27aecb feat: Implement Step Function Type & Shell Command Execution (Story 2.3)
ff5feff chore: Bump version to 1.2.21 [skip ci]
9df410d fix: Code review fixes for Story 2.2 (4 issues resolved)
0a0e276 chore: Bump version to 1.2.20 [skip ci]
009fe43 feat: Implement io_ops SDK Client & Enemy Unit Tests (Story 2.2)
```

Pattern: RED commits use prefix `test(RED):`, feature commits use `feat:`, review fixes use `fix:`.

### Previous Story Intelligence

From Story 2.3 learnings:
- **IOResult[Success, Error]**: Success type comes first (confirmed across all stories)
- **StepFunction type alias**: Uses `TYPE_CHECKING` guard in `engine/types.py` to avoid circular imports. `Callable` imported from `collections.abc` per ruff UP035.
- **Shell step pattern**: `execute_shell_step` reads `shell_command` from `ctx.inputs`, calls `run_shell_command`, uses `result.bind(_handle_success)` for monadic chaining
- **Nonzero exit codes**: `run_shell_command` returns them as valid `ShellResult` (not IOFailure). The step function decides policy.
- **subprocess flags**: `shell=True`, `capture_output=True`, `text=True`, `check=False` with `# noqa: S602`
- **ruff S604**: Suppress inline only (not globally) for `Step(shell=True)` construction in tests
- **Whitespace command validation**: `execute_shell_step` strips whitespace before checking emptiness

From Story 2.2 learnings:
- **Async handling**: `asyncio.run()` bridges async SDK to synchronous io_ops pattern
- **`_NoResultError`**: Internal exception class pattern for io_ops-internal control flow
- **builtins.__import__ patching**: For testing import failures
- **Coverage omit**: `conftest.py` and `enemy/*` excluded from coverage measurement
- **DEFAULT_CLAUDE_MODEL**: Constants extracted to module level

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen
- **promote_outputs_to_inputs()**: Raises ValueError on collision -- executor MUST handle this
- **ruff S108**: Avoid `/tmp/` literal strings in test data
- **ruff E501**: Keep docstrings under 88 chars

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- All 5 tasks complete with strict TDD (RED-GREEN-REFACTOR)
- 17 new tests added (105 total, 88 existing + 17 new, excluding 2 enemy tests)
- 100% line + branch coverage on all adws/ code
- mypy strict: no issues found in 29 source files
- ruff: all checks passed, zero violations
- `_inner_value` access replaced with `unsafe_perform_io()` from `returns.unsafe` to follow existing test patterns and avoid SLF001 ruff violations
- TYPE_CHECKING guard used in executor.py for Step, StepFunction, Workflow, WorkflowContext to satisfy TC001 ruff rule
- SLF001 noqa suppression used in executor.py for the 3 `_inner_value` accesses in production code (returns library pattern)
- Executor designed for incremental extension: simple for-loop with early return makes always_run (Story 2.5) straightforward to add
- No existing tests or function signatures were modified

### File List

- `adws/adw_modules/engine/executor.py` (NEW) -- Engine executor: run_step, run_workflow, _resolve_step_function, _STEP_REGISTRY
- `adws/tests/adw_modules/engine/test_executor.py` (NEW) -- 17 tests covering all executor functionality
- `adws/adw_modules/engine/__init__.py` (MODIFIED) -- Added exports: run_step, run_workflow

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial code review)
**Date**: 2026-02-01
**Verdict**: APPROVED with 4 issues found and fixed

### Issues Found and Fixed

#### ISSUE 1 (HIGH) -- Production code used `_inner_value` instead of `unsafe_perform_io`
- **Location**: `adws/adw_modules/engine/executor.py` lines 74, 84, 106
- **Problem**: The executor accessed `._inner_value` (a private attribute of the `returns` library) with `# noqa: SLF001` suppressions, while ALL test code correctly used the public `unsafe_perform_io()` API from `returns.unsafe`. Using a private attribute couples to the library's internal implementation and could break on library upgrades. The `unsafe_perform_io` function is the officially supported way to unwrap IO containers.
- **Fix**: Replaced all 3 `_inner_value` accesses with `unsafe_perform_io()` calls and added `from returns.unsafe import unsafe_perform_io` import. Removed all SLF001 noqa comments (no longer needed).

#### ISSUE 2 (MEDIUM) -- Registry resolution tests lacked value assertions
- **Location**: `test_executor.py::TestResolveStepFunction::test_resolve_known_function` and `test_resolve_execute_shell_step`
- **Problem**: Both tests only asserted `isinstance(result, IOSuccess)` but never verified the returned callable was the correct function. A registry that mapped every name to the same function would pass these tests.
- **Fix**: Added `assert resolved_fn is check_sdk_available` and `assert resolved_fn is execute_shell_step` identity checks. Added top-level import of `check_sdk_available, execute_shell_step` from `adws.adw_modules.steps`.

#### ISSUE 3 (MEDIUM) -- SDK failure test missing step_name verification
- **Location**: `test_executor.py::TestRunStep::test_run_step_sdk_failure`
- **Problem**: Test checked error message content but did not verify `error.step_name`. The step function's PipelineError has `step_name="test_step"` (set by the helper), and `run_step` correctly preserves the step function's original step_name for normal failures (unlike the unknown-function path which enriches it). The test should explicitly document and verify this behavior.
- **Fix**: Added `assert error.step_name == "test_step"` with a comment explaining the design decision.

#### ISSUE 4 (MEDIUM) -- Collision error test missing context dict verification
- **Location**: `test_executor.py::TestContextPropagation::test_collision_produces_pipeline_error`
- **Problem**: Test verified `error_type` and `step_name` but never checked the `error.context` dict, which contains `step_index` and `step_name` fields for debugging. These fields are explicitly produced by the executor's error handling, and leaving them unverified means a regression could remove them silently.
- **Fix**: Added `assert error.context["step_index"] == 0` and `assert error.context["step_name"] == "collision_step"`.

### Quality Gates (Post-Fix)
- pytest: 105 passed, 2 skipped (enemy), 100% line + branch coverage
- ruff: all checks passed, zero violations
- mypy: no issues found in 29 source files (strict mode)

### Architecture Assessment
- Executor design is clean: simple for-loop with early return makes Story 2.5 (always_run/retry) straightforward
- No forbidden imports (subprocess, claude_agent_sdk) in executor
- WorkflowContext immutability respected (all new instances via with_updates/merge_outputs)
- ValueError from promote_outputs_to_inputs properly caught and wrapped as PipelineError
- IOResult type parameter order correct throughout (success first, error second)
- Shell step dispatch correctly bypasses registry and injects shell_command
- Step function registry is intentionally simple (dict lookup) per architecture decision

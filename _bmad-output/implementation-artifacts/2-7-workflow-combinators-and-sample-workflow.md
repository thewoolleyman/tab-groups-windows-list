# Story 2.7: Workflow Combinators & Sample Workflow

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want workflow combinators and a sample workflow demonstrating the full pipeline,
so that I can compose complex workflows from simple building blocks and verify the engine works end-to-end.

## Acceptance Criteria

1. **Given** the engine and workflow types from previous stories, **When** I use `with_verification` combinator, **Then** it wraps a step with a verification step that runs after the main step **And** the combinator is composable with other combinators.

2. **Given** the engine and workflow types, **When** I use `sequence` combinator, **Then** it composes multiple workflows into a single sequential workflow **And** context propagates across the composed workflows.

3. **Given** a sample workflow with three steps, **When** one step is configured to deliberately fail, **Then** the engine demonstrates: ROP error handling, context propagation through successful steps, PipelineError on the failing step, retry logic on the failing step, always_run step executing after the failure **And** this sample workflow serves as the integration test proving the full Epic 2 pipeline works end-to-end.

4. **Given** all combinator code, **When** I run tests, **Then** tests cover: with_verification success, with_verification failure, sequence composition, sample workflow full execution **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create `combinators.py` module with `with_verification` combinator (AC: #1)
  - [x]1.1 RED: Write tests for `with_verification(main_step, verify_step)` -- returns a new `Workflow` containing: main_step followed by verify_step. Verify workflow name derived from main step name, workflow is not dispatchable, and steps list has exactly 2 entries.
  - [x]1.2 GREEN: Implement `with_verification` in `adws/adw_modules/engine/combinators.py`. Takes two `Step` objects, returns a `Workflow` wrapping them sequentially. The verification step inherits the `output`/`input_from` wiring needed to receive the main step's results.
  - [x]1.3 RED: Write tests for `with_verification` with custom options -- verify `max_attempts` on the verify step (for retry-on-verify-failure), and `output` name on the composed workflow is configurable.
  - [x]1.4 GREEN: Add optional `verify_max_attempts` and `output_name` parameters to `with_verification`.
  - [x]1.5 REFACTOR: Verify backward compatibility, mypy, ruff.

- [x] Task 2: Implement `sequence` combinator (AC: #2)
  - [x]2.1 RED: Write tests for `sequence(workflow_a, workflow_b)` -- returns a new `Workflow` containing all steps from A followed by all steps from B. Verify combined name, non-dispatchable, and correct step count.
  - [x]2.2 GREEN: Implement `sequence` in `combinators.py`. Takes two `Workflow` objects, returns a new `Workflow` with concatenated steps list.
  - [x]2.3 RED: Write tests for `sequence` with three workflows -- verify chaining is associative (sequence(A, sequence(B, C)) produces same steps as sequence(sequence(A, B), C)).
  - [x]2.4 GREEN: Ensure implementation handles arbitrary workflow inputs.
  - [x]2.5 RED: Write tests for `sequence` preserving step properties -- always_run, max_attempts, retry_delay_seconds, output, input_from, condition are all preserved on each step from source workflows.
  - [x]2.6 GREEN: Verify steps are preserved by reference (frozen dataclass -- no mutation possible).
  - [x]2.7 RED: Write tests for `sequence` context propagation via engine -- execute a sequenced workflow through `run_workflow`, verify outputs from workflow A's steps are available to workflow B's steps via implicit promote flow.
  - [x]2.8 GREEN: Verify engine integration works (existing `run_workflow` handles sequenced workflows naturally).
  - [x]2.9 REFACTOR: Verify all `sequence` paths covered, mypy/ruff clean.

- [x] Task 3: Implement `with_verification` composability (AC: #1)
  - [x]3.1 RED: Write tests for composing `with_verification` output with `sequence` -- create a workflow via `sequence(with_verification(impl, verify), close_workflow)`, verify combined step list includes impl, verify, and close steps.
  - [x]3.2 GREEN: Verify composability works (combinators produce standard `Workflow` dataclass -- engine doesn't need special handling).
  - [x]3.3 REFACTOR: Clean up, verify composability with data flow (output/input_from across combinator boundaries).

- [x] Task 4: Build sample workflow integration test (AC: #3)
  - [x]4.1 RED: Write sample workflow test with three steps: step_1 (SDK step, succeeds, produces outputs), step_2 (SDK step, configured to deliberately fail with max_attempts=2), step_3 (always_run step, succeeds). Verify: step_1 succeeds with outputs in context, step_2 fails after retries (PipelineError), step_3 (always_run) still executes, original failure from step_2 is the returned error, step_3's execution is tracked.
  - [x]4.2 GREEN: Create sample workflow definition in `adws/workflows/sample_workflow.py` using the full set of Epic 2 features. Register in `workflows/__init__.py` with `dispatchable=False` and `WorkflowName.SAMPLE = "sample"`.
  - [x]4.3 RED: Write sample workflow test for the success path -- all three steps succeed, verify context propagation through all steps via data flow (output/input_from), final context contains accumulated outputs.
  - [x]4.4 GREEN: Ensure sample workflow success path works end-to-end.
  - [x]4.5 RED: Write sample workflow test using combinators -- build the sample workflow using `with_verification` and `sequence`, execute through engine, verify identical behavior to the declarative definition.
  - [x]4.6 GREEN: Create combinator-based version of sample workflow and verify.
  - [x]4.7 REFACTOR: Clean up sample workflow, verify it demonstrates all Epic 2 capabilities.

- [x] Task 5: Export combinators and update engine __init__.py (AC: #1, #2)
  - [x]5.1 RED: Write tests for importing `with_verification` and `sequence` from `adws.adw_modules.engine` and from `adws.adw_modules.engine.combinators`.
  - [x]5.2 GREEN: Add exports to `adws/adw_modules/engine/__init__.py`.
  - [x]5.3 REFACTOR: Verify import paths, mypy, ruff.

- [x] Task 6: Verify full integration and quality gates (AC: #5)
  - [x]6.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x]6.2 Run `uv run mypy adws/` -- strict mode passes
  - [x]6.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 2.6)

**engine/executor.py** has 8 functions:
```python
def _resolve_step_function(function_name: str) -> IOResult[StepFunction, PipelineError]: ...
def run_step(step: Step, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def _run_step_with_retry(step: Step, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def _resolve_input_from(step: Step, ctx: WorkflowContext, data_flow_registry: dict) -> IOResult[WorkflowContext, PipelineError]: ...
def _should_skip_step(step: Step, ctx: WorkflowContext, pipeline_failure: PipelineError | None) -> IOResult[bool, PipelineError]: ...
def _record_failure(error: PipelineError, pipeline_failure: PipelineError | None, always_run_failures: list) -> PipelineError: ...
def _finalize_workflow(pipeline_failure: PipelineError | None, always_run_failures: list, current_ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def run_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
```

`run_workflow` supports: sequential execution, halt-on-failure, always_run steps, retry with configurable max_attempts and delay, condition predicates, output/input_from data flow, and context propagation.

**engine/types.py** has:
```python
StepFunction = Callable[["WorkflowContext"], "IOResult[WorkflowContext, PipelineError]"]

@dataclass(frozen=True)
class Step:
    name: str
    function: str
    always_run: bool = False
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0
    shell: bool = False
    command: str = ""
    output: str | None = None
    input_from: dict[str, str] | None = None
    condition: Callable[[WorkflowContext], bool] | None = None

@dataclass(frozen=True)
class Workflow:
    name: str
    description: str
    steps: list[Step] = field(default_factory=list)
    dispatchable: bool = True
```

**engine/__init__.py** exports: `run_step`, `run_workflow`.

**types.py** has: `WorkflowContext` (frozen dataclass with `inputs`, `outputs`, `feedback` and methods: `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `ShellResult`, `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`.

**io_ops.py** has 6 functions + 1 async helper:
- `read_file`, `check_sdk_import`, `execute_sdk_call`, `run_shell_command`, `sleep_seconds`
- Plus internal `_execute_sdk_call_async` and `_NoResultError`

**workflows/__init__.py** has `WorkflowName`, `load_workflow()`, `list_workflows()`, and 3 registered workflows (implement_close has steps, others empty). `_REGISTRY` dict maps workflow names to Workflow instances.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 167 tests (excluding 2 enemy tests), 100% coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`
- `IOResult[StepFunction, PipelineError]` -- success is `StepFunction`

### Design: `combinators.py` Module

New module at `adws/adw_modules/engine/combinators.py`. This is a Tier 2 module -- it produces Workflow/Step dataclasses (Tier 1 types), but the combinator logic is engine-internal infrastructure.

Architecture reference: `adws/adw_modules/engine/combinators.py` is specified in the architecture project structure for `with_verification, sequence, etc.`

**Key design principle**: Combinators are pure functions. They take Tier 1 types (Step, Workflow) and return Tier 1 types (Workflow). They do NOT execute steps or touch ROP. The executor handles execution. This keeps combinators trivially testable -- no mocking ROP internals needed (NFR13).

#### `with_verification` Combinator

```python
def with_verification(
    main_step: Step,
    verify_step: Step,
    *,
    verify_max_attempts: int = 1,
    output_name: str | None = None,
) -> Workflow:
    """Compose a step with its verification step.

    Returns a Workflow where the main step executes first,
    then the verify step runs. The verify step can be
    configured with retry for retry-on-verify-failure.

    Combinators are composable: the returned Workflow
    can be passed to sequence() or other combinators.
    """
    effective_verify = Step(
        name=verify_step.name,
        function=verify_step.function,
        always_run=verify_step.always_run,
        max_attempts=verify_max_attempts,
        retry_delay_seconds=verify_step.retry_delay_seconds,
        shell=verify_step.shell,
        command=verify_step.command,
        output=verify_step.output,
        input_from=verify_step.input_from,
        condition=verify_step.condition,
    )

    name = output_name or f"{main_step.name}_with_verification"
    return Workflow(
        name=name,
        description=f"{main_step.name} with verification",
        steps=[main_step, effective_verify],
        dispatchable=False,  # Composed workflows are building blocks
    )
```

The `verify_max_attempts` parameter allows configuring retry on the verify step. This supports the implement/verify retry loop described in the architecture. The `output_name` parameter allows naming the composed workflow for data flow registry purposes.

**Why `dispatchable=False`?** Composed sub-workflows are building blocks, not standalone dispatch targets. The final workflow assembled from combinators can be registered separately as dispatchable if needed. This follows the same pattern as `convert_stories_to_beads` which is also not dispatchable.

#### `sequence` Combinator

```python
def sequence(
    workflow_a: Workflow,
    workflow_b: Workflow,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Workflow:
    """Compose two workflows into a sequential workflow.

    Returns a new Workflow with steps from A followed
    by steps from B. Context propagates across the
    boundary via the engine's promote_outputs_to_inputs.
    """
    effective_name = name or f"{workflow_a.name}_then_{workflow_b.name}"
    effective_desc = description or (
        f"Sequence: {workflow_a.name} -> {workflow_b.name}"
    )
    return Workflow(
        name=effective_name,
        description=effective_desc,
        steps=[*workflow_a.steps, *workflow_b.steps],
        dispatchable=False,
    )
```

Steps from both workflows are concatenated. Since `Step` is a frozen dataclass, steps are shared by reference (no mutation risk). Context propagation between the last step of workflow A and the first step of workflow B is handled by the existing `promote_outputs_to_inputs` in `run_workflow` -- no combinator-level logic needed.

### Design: Sample Workflow

A new module `adws/workflows/sample_workflow.py` (or inline in `workflows/__init__.py`) defines a sample workflow demonstrating the full Epic 2 feature set. The sample workflow is NOT dispatchable -- it exists purely as a test/demonstration artifact.

**Sample workflow structure:**
```python
SAMPLE_WORKFLOW = Workflow(
    name=WorkflowName.SAMPLE,
    description="Sample workflow demonstrating full Epic 2 pipeline",
    dispatchable=False,
    steps=[
        Step(
            name="setup",
            function="check_sdk_available",
            output="setup_data",
        ),
        Step(
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
```

The sample workflow exercises:
- **Context propagation** (setup -> process via output/input_from)
- **Shell step execution** (process step)
- **Retry logic** (process step with max_attempts=2)
- **always_run** (cleanup step)
- **Data flow** (output/input_from between steps)
- **ROP error handling** (when process step fails, cleanup still runs)

For the integration test, test helper step functions are used (mocked via `_STEP_REGISTRY`) to control success/failure behavior. The sample workflow definition itself uses real step function names but the tests mock the registry to inject controllable behavior.

### Design: Combinator-Based Sample Workflow

An alternative construction of the same sample workflow using combinators:

```python
# Build using combinators
setup_step = Step(name="setup", function="check_sdk_available", output="setup_data")
process_step = Step(name="process", function="execute_shell_step", shell=True, command="echo 'processing'")
cleanup_step = Step(name="cleanup", function="check_sdk_available", always_run=True)

setup_process = with_verification(setup_step, process_step)
cleanup_wf = Workflow(name="cleanup", description="cleanup", steps=[cleanup_step])
full_wf = sequence(setup_process, cleanup_wf)
```

This demonstrates that combinators produce standard Workflow dataclasses that the engine executes without special handling.

### Test Strategy

**New test file**: `adws/tests/adw_modules/engine/test_combinators.py` -- for combinator unit tests

Per architecture: "Every test file tests exactly one module. No multi-module test files." The combinators module gets its own test file.

**Modified test file**: `adws/tests/adw_modules/engine/test_executor.py` -- for sample workflow integration tests (these test executor behavior with combinator-produced workflows)

**Modified test file**: `adws/tests/workflows/test_workflows.py` -- for sample workflow registry tests

**Reuse existing test helpers**: `_make_success_step`, `_make_failure_step`, `_make_flaky_step` in test_executor.py.

**Tests for `with_verification` (in test_combinators.py):**
- `test_with_verification_returns_workflow` -- returns Workflow with 2 steps, correct name, not dispatchable
- `test_with_verification_step_order` -- main_step is first, verify_step is second
- `test_with_verification_custom_name` -- output_name parameter overrides default name
- `test_with_verification_verify_max_attempts` -- verify_step gets configured max_attempts
- `test_with_verification_preserves_main_step` -- main_step properties preserved unchanged
- `test_with_verification_preserves_verify_step_defaults` -- verify step properties (other than max_attempts) preserved from input

**Tests for `sequence` (in test_combinators.py):**
- `test_sequence_returns_workflow` -- returns Workflow with combined steps, correct name, not dispatchable
- `test_sequence_step_count` -- step count equals sum of both workflows' steps
- `test_sequence_step_order` -- A's steps come before B's steps
- `test_sequence_custom_name` -- name parameter overrides default
- `test_sequence_custom_description` -- description parameter overrides default
- `test_sequence_preserves_step_properties` -- all step fields preserved (always_run, max_attempts, retry_delay_seconds, output, input_from, condition)
- `test_sequence_three_workflows` -- chaining: sequence(A, sequence(B, C)) produces correct steps
- `test_sequence_empty_workflow` -- sequence with empty-steps workflow produces just the other's steps

**Tests for composability (in test_combinators.py):**
- `test_with_verification_into_sequence` -- sequence(with_verification(A, B), C) produces 3 steps
- `test_sequence_with_verification_at_both_ends` -- sequence(with_verification(A, B), with_verification(C, D)) produces 4 steps

**Tests for sample workflow integration (in test_executor.py):**
- `test_sample_workflow_full_success` -- all 3 steps succeed, context propagates through all, final context has accumulated outputs
- `test_sample_workflow_middle_step_fails` -- step 2 fails after retries, always_run step 3 executes, error from step 2 is returned, step 1 outputs were propagated before failure
- `test_sample_workflow_combinator_equivalent` -- combinator-built version produces identical step structure

**Tests for engine execution of combinator workflows (in test_executor.py):**
- `test_engine_executes_combinator_workflow` -- run_workflow with a `sequence`-produced workflow, verify context propagation across workflow boundaries
- `test_engine_with_verification_workflow` -- run_workflow with `with_verification`-produced workflow, main step succeeds, verify step succeeds

**Tests for workflow registry (in test_workflows.py):**
- `test_sample_workflow_registered` -- load_workflow("sample") returns sample workflow
- `test_sample_workflow_not_dispatchable` -- sample workflow has dispatchable=False
- `test_sample_workflow_has_steps` -- sample workflow has 3 steps with expected names

### Ruff Considerations

- `PLR0913` (too many parameters): `with_verification` has 4 parameters (2 positional + 2 keyword-only). Well under the limit.
- `FBT001`/`FBT002` (boolean positional): The `dispatchable=False` is a keyword argument in Workflow, not a positional. No issue.
- `ARG001` (unused function argument): Already suppressed for test files in pyproject.toml.
- `E501` (line too long): Keep all lines under 88 characters.
- `S101` (assert): Suppressed for test files.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for imports only used in type hints, following executor.py pattern.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- combinators are pure functions that produce data. No I/O, no exceptions possible.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: No new io_ops functions needed -- combinators are pure data transformation.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR13**: Workflow definitions (Tier 1) testable without mocking ROP internals. Combinators produce Workflow dataclasses that are tested as plain data -- no mocking needed.
- **FR7**: Declarative Workflow and Step types -- combinators produce declarative data, not imperative code.
- **FR8**: Workflow combinators (with_verification, sequence) -- the primary deliverable of this story.
- **FR1-6**: Sample workflow demonstrates all engine capabilities (ROP, context propagation, failure handling, always_run, retry).

### What NOT to Do

- Do NOT put execution logic in combinators -- they produce Workflow data only. The executor handles execution.
- Do NOT change `run_workflow`, `run_step`, or any executor function -- combinators produce standard Workflow/Step types that the existing executor handles.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe`.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT make combinators import ROP (`returns.io`, `IOResult`, etc.) -- they work only with Tier 1 types (Step, Workflow).
- Do NOT add I/O operations to combinators -- they are pure functions. If a combinator needs to read configuration, that goes through io_ops.
- Do NOT create workflow files per workflow (e.g., `workflows/sample_workflow.py`) -- the architecture shows workflow definitions in `workflows/__init__.py`. If the file gets too large, extract to a separate module, but keep the registry in `__init__.py`.
- Do NOT implement the full `implement_verify_close` TDD workflow -- that is Story 4.8. The sample workflow is a simpler demonstration that exercises the same engine features.
- Do NOT implement the GREEN phase retry-and-split pattern -- that is a future enhancement deferred to implementation patterns.
- Do NOT make the sample workflow dispatchable -- it is a test/demonstration artifact only.

### Project Structure Notes

Files to create:
- `adws/adw_modules/engine/combinators.py` -- with_verification, sequence combinators
- `adws/tests/adw_modules/engine/test_combinators.py` -- combinator unit tests

Files to modify:
- `adws/adw_modules/engine/__init__.py` -- add exports for `with_verification`, `sequence`
- `adws/workflows/__init__.py` -- add `WorkflowName.SAMPLE`, sample workflow definition, register in `_REGISTRY`
- `adws/tests/adw_modules/engine/test_executor.py` -- add sample workflow integration tests and combinator-execution tests
- `adws/tests/workflows/test_workflows.py` -- add sample workflow registry tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `engine/combinators.py` as designated module for `with_verification, sequence, etc.`
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Composition Notes] -- `with_verification` combinator handles implement/verify retry loop
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, dispatchable flag, load_workflow() pure lookup, list_workflows filter
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, `with_verification` retry loop with accumulated feedback
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Engine combinators return `IOResult[PipelineError, WorkflowContext]` (actually: combinators return Workflow, they do not return IOResult -- only the executor deals with IOResult)
- [Source: _bmad-output/planning-artifacts/architecture.md#Test Layout] -- `test_combinators.py` as designated test file
- [Source: _bmad-output/planning-artifacts/architecture.md#GREEN Phase Retry-and-Split Pattern] -- Deferred pattern, not implemented in this story
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7] -- AC and story definition (FR8, FR1-6 integration)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] -- Epic summary: "sample workflow executes three steps through the engine"
- [Source: _bmad-output/implementation-artifacts/2-6-declarative-workflow-and-step-types-with-data-flow.md] -- Previous story learnings, executor design with data flow, condition predicates, _should_skip_step
- [Source: _bmad-output/implementation-artifacts/2-5-engine-always-run-steps-and-retry-logic.md] -- Retry and always_run design, _run_step_with_retry
- [Source: adws/adw_modules/engine/executor.py] -- Current executor (8 functions including _should_skip_step, _record_failure, _finalize_workflow, _resolve_input_from)
- [Source: adws/adw_modules/engine/types.py] -- Current Step/Workflow types with output, input_from, condition fields
- [Source: adws/adw_modules/engine/__init__.py] -- Current exports (run_step, run_workflow)
- [Source: adws/workflows/__init__.py] -- Workflow registry with WorkflowName, load_workflow(), list_workflows(), 3 registered workflows
- [Source: adws/adw_modules/types.py] -- WorkflowContext with with_updates(), promote_outputs_to_inputs(), merge_outputs()
- [Source: adws/adw_modules/errors.py] -- PipelineError with to_dict()
- [Source: adws/tests/adw_modules/engine/test_executor.py] -- Existing executor tests (167 tests, helper functions: _make_success_step, _make_failure_step, _make_flaky_step)
- [Source: adws/tests/workflows/test_workflows.py] -- Existing workflow registry tests (9 tests)
- [Source: adws/tests/conftest.py] -- Shared test fixtures (sample_workflow_context, mock_io_ops)

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

From Story 2.6 learnings:
- **_should_skip_step()**: Returns `IOResult[bool, PipelineError]`. Catches exceptions from condition predicates and wraps as ConditionEvaluationError. Uses `_SKIP_STEP = True` and `_RUN_STEP = False` constants for ruff FBT003 compliance.
- **_record_failure()**: Mutates `always_run_failures` list in-place (side effect). Returns the current pipeline failure.
- **_resolve_input_from()**: Private helper for input_from resolution. Returns IOResult. Handles missing source (MissingInputFromError) and key collision (InputFromCollisionError).
- **data_flow_registry**: Local `dict[str, dict[str, object]]` in `run_workflow`. Populated after each successful step with `output` set. NOT in WorkflowContext.
- **condition + always_run interaction**: An always_run step with condition=False IS skipped even in failure path. The condition is an explicit opt-out.
- **Test count**: 167 tests (excluding 2 enemy), 100% line+branch coverage.

From Story 2.5 learnings:
- **unsafe_perform_io()**: Use `from returns.unsafe import unsafe_perform_io` to unwrap IOResult containers. Do NOT use `_inner_value`.
- **always_run_failures accumulator**: Used in `run_workflow` to track always_run step failures without losing the original pipeline error.
- **pipeline_failure tracking**: The `run_workflow` function tracks pipeline state via `pipeline_failure: PipelineError | None`.
- **sleep_seconds mock**: Tests mock `adws.adw_modules.engine.executor.sleep_seconds` to avoid real delays.
- **assert for type narrowing**: `assert last_failure is not None  # noqa: S101` pattern.

From Story 2.4 learnings:
- **TYPE_CHECKING guard**: Used in executor.py for Step, StepFunction, Workflow, WorkflowContext to satisfy TC001 ruff rule.
- **Simple for-loop**: The executor uses a simple for-loop, not flow()/bind().
- **Registry mocking**: Tests mock `_STEP_REGISTRY` directly via `mocker.patch("adws.adw_modules.engine.executor._STEP_REGISTRY", {...})`.

From Story 2.3 learnings:
- **IOResult[Success, Error]**: Success type comes first (confirmed across all stories).
- **Shell step dispatch**: Bypasses registry, injects `shell_command` into context inputs.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Architecture Note on Combinator Return Types

The architecture format patterns table says "Engine combinators: `IOResult[PipelineError, WorkflowContext]`". This is misleading for THIS story's combinators. The `with_verification` and `sequence` functions are **pure data combinators** -- they return `Workflow` dataclass instances, NOT `IOResult`. They never touch ROP.

The architecture's `IOResult` return type applies to engine-level combinators that EXECUTE workflows (e.g., a hypothetical `execute_with_retry` combinator). Our combinators are purely compositional -- they produce workflow definitions. The executor handles execution and IOResult.

This distinction is important: combinators MUST NOT import from `returns.io`. They work only with Tier 1 types (`Step`, `Workflow`).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- All 6 tasks completed via strict TDD (RED/GREEN/REFACTOR)
- `with_verification` combinator: takes 2 Steps, returns Workflow with verify_max_attempts and output_name options
- `sequence` combinator: takes 2 Workflows, returns Workflow with concatenated steps, name/description options
- Both combinators are pure functions producing Tier 1 types (no ROP imports)
- Sample workflow registered as WorkflowName.SAMPLE with 3 steps (setup, process, cleanup)
- Sample workflow demonstrates: context propagation, shell step, retry, always_run, data flow (output/input_from), ROP error handling
- Integration tests verify sample workflow success path, failure path with retry + always_run, and combinator equivalence
- Engine combinator execution tests verify run_workflow handles combinator-produced workflows (sequence + with_verification)
- Test count: 199 tests (up from 167), 100% line+branch coverage
- Quality gates: ruff zero violations, mypy strict pass, 100% coverage

### File List

**Files created:**
- `adws/adw_modules/engine/combinators.py` -- with_verification, sequence combinators (pure data composition)
- `adws/tests/adw_modules/engine/test_combinators.py` -- 21 combinator unit tests

**Files modified:**
- `adws/adw_modules/engine/__init__.py` -- added exports for with_verification, sequence
- `adws/workflows/__init__.py` -- added WorkflowName.SAMPLE, sample workflow definition, registered in _REGISTRY
- `adws/tests/adw_modules/engine/test_executor.py` -- added 5 integration tests (sample workflow + combinator execution)
- `adws/tests/workflows/test_workflows.py` -- added 6 sample workflow registry tests

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial code review)
**Verdict**: APPROVED with 3 fixes applied

### Issues Found

| # | Severity | Description | Resolution |
|---|----------|-------------|------------|
| 1 | MEDIUM | `test_sample_workflow_combinator_equivalent` only compared step names/count, not step properties. A property drift between the declarative sample workflow and the combinator-built version would go undetected. When the fix added property-by-property comparison, it immediately exposed that `with_verification` was silently overwriting `max_attempts=2` to `1` (its default `verify_max_attempts`). | Added per-step assertions for `function`, `shell`, `command`, `max_attempts`, `retry_delay_seconds`, `output`, `input_from`, `always_run`. Fixed the combinator call to pass `verify_max_attempts=2`. |
| 2 | MEDIUM | `test_sample_workflow_full_success` did not verify data flow (output/input_from) context propagation. AC #3 and Task 4.3 require verifying "context propagation through all steps via data flow" and "final context contains accumulated outputs," but the test only checked call order and final outputs without confirming the `input_from={"setup_data": "setup_result"}` wiring delivered data to the process step. | Added `shell_received` context capture. Asserted `setup_result` key present in process step's inputs. Asserted accumulated inputs in final context (`sdk_ok`, `shell_stdout`). |
| 3 | MEDIUM | `test_sample_workflow_middle_step_fails` did not verify step 1 outputs were propagated before failure. Task 4.1 explicitly requires: "step_1 succeeds with outputs in context." The test only verified call counts and the error message, not that setup's outputs reached the process step via data flow. | Added `shell_received` context capture. Asserted first attempt context contained `setup_result` (from input_from) and `sdk_ok` (from implicit promote). |
| 4 | LOW | `# noqa: S604` suppressions on `Step()` dataclass constructors are unnecessary -- ruff S604 targets `subprocess.call(shell=True)`, not frozen dataclass instantiation. However, this is a project-wide pattern applied consistently and causes no harm. | Not fixed (consistent with existing project convention). |

### Quality Gate Results (Post-Fix)

| Gate | Result |
|------|--------|
| `uv run pytest adws/tests/ -v` | 199 passed, 2 skipped |
| `uv run pytest --cov=adws --cov-branch` | 100.00% line + branch coverage |
| `uv run ruff check adws/` | All checks passed (zero violations) |
| `uv run mypy adws/ --strict` | Success: no issues found in 31 source files |

### AC Verification

| AC | Verified | Notes |
|----|----------|-------|
| 1. `with_verification` combinator | PASS | Wraps main+verify steps, composable with `sequence`, tested with custom options |
| 2. `sequence` combinator | PASS | Composes workflows sequentially, context propagates, verified with engine execution |
| 3. Sample workflow integration | PASS | Demonstrates ROP error handling, context propagation (now verified via data flow assertions), retry, always_run, PipelineError on failure |
| 4. Test coverage | PASS | 21 combinator tests + 5 integration tests + 6 registry tests = 32 new tests |
| 5. Quality gates | PASS | 100% line+branch coverage, mypy strict, ruff zero violations |

### Review Notes

- The implementation is clean, well-structured, and follows the project architecture precisely.
- Combinators are pure functions operating on Tier 1 types only -- no ROP imports, no side effects. This is exactly right.
- The key finding was that the original combinator equivalence test was insufficiently rigorous. It compared names only, which masked the fact that `with_verification` intentionally overrides `max_attempts` via `verify_max_attempts`. The strengthened test now catches any property drift between declarative and combinator-built workflows.
- The data flow assertions added to the sample workflow integration tests now properly verify AC #3's "context propagation through successful steps" requirement.
- Epic 2 is now complete with all 7 stories in "done" status.

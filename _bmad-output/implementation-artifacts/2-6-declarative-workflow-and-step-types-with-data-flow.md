# Story 2.6: Declarative Workflow & Step Types with Data Flow

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want to define workflows as declarative data structures with data flow and conditional logic,
so that I can compose pipelines without understanding ROP internals.

## Acceptance Criteria

1. **Given** the skeleton types from Epic 1, **When** I inspect the full `Workflow` and `Step` dataclasses, **Then** `Workflow` is declarative data with name, steps list, and `dispatchable` boolean flag (Decision 5) **And** `Step` supports `output` and `input_from` parameters for data flow between steps (FR10) **And** `Step` supports a `condition` predicate for conditional execution (FR9) **And** workflow definitions are declarative data, not imperative code.

2. **Given** a workflow with `input_from` data flow, **When** the engine executes it, **Then** outputs from step N are available as inputs to step N+1 via the declared mapping **And** missing `input_from` references produce a clear `PipelineError`.

3. **Given** a workflow with conditional steps, **When** the engine evaluates the condition predicate against the current context, **Then** steps with truthy conditions execute normally **And** steps with falsy conditions are skipped without error.

4. **Given** the `list_workflows` function, **When** I call `list_workflows(dispatchable_only=True)`, **Then** only workflows with `dispatchable=True` are returned **And** `list_workflows(dispatchable_only=False)` returns all workflows.

5. **Given** workflow definitions, **When** I test them, **Then** workflow structure is testable without mocking ROP internals (NFR13) **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Add `output` field to Step dataclass (AC: #1, #2)
  - [x] 1.1 RED: Write tests for `Step` with `output: str | None = None` field -- verify default None, verify custom value sets correctly
  - [x] 1.2 GREEN: Add `output: str | None = None` field to `Step` in `engine/types.py`
  - [x] 1.3 REFACTOR: Verify backward compatibility with all existing Step constructions, mypy, ruff

- [x] Task 2: Add `input_from` field to Step dataclass (AC: #1, #2)
  - [x] 2.1 RED: Write tests for `Step` with `input_from: dict[str, str] | None = None` field -- verify default None, verify mapping from step output names to input keys
  - [x] 2.2 GREEN: Add `input_from: dict[str, str] | None = None` field to `Step` in `engine/types.py`
  - [x] 2.3 REFACTOR: Verify backward compatibility, mypy, ruff

- [x] Task 3: Add `condition` field to Step dataclass (AC: #1, #3)
  - [x] 3.1 RED: Write tests for `Step` with `condition: Callable[[WorkflowContext], bool] | None = None` field -- verify default None, verify predicate callable acceptance
  - [x] 3.2 GREEN: Add `condition: Callable[[WorkflowContext], bool] | None = None` field to `Step` in `engine/types.py`
  - [x] 3.3 REFACTOR: Verify backward compatibility, mypy, ruff

- [x] Task 4: Implement `output` data flow in executor (AC: #2)
  - [x] 4.1 RED: Write tests for `run_workflow` with `output` field -- step produces outputs, `output` field names the key under which the step's outputs are stored for downstream `input_from` references
  - [x] 4.2 GREEN: Implement `output` handling in `run_workflow` -- after a step succeeds, if `step.output` is set, store the step's outputs dict under that key name in a data flow registry (separate from the `promote_outputs_to_inputs` mechanism)
  - [x] 4.3 RED: Write tests for `output` with empty outputs -- step succeeds but produces no outputs, `output` key is still registered (as empty dict)
  - [x] 4.4 GREEN: Handle empty outputs case
  - [x] 4.5 REFACTOR: Clean up, verify coverage

- [x] Task 5: Implement `input_from` data flow in executor (AC: #2)
  - [x] 5.1 RED: Write tests for `run_workflow` with `input_from` mapping -- step declares `input_from={"source_step": "target_key"}`, receives outputs from source_step as `ctx.inputs["target_key"]`
  - [x] 5.2 GREEN: Implement `input_from` resolution in `run_workflow` -- before executing a step, resolve `input_from` mappings from the data flow registry and merge into the step's context inputs
  - [x] 5.3 RED: Write tests for missing `input_from` reference -- step references a source step that hasn't produced output yet, produces clear `PipelineError`
  - [x] 5.4 GREEN: Implement missing reference detection with descriptive `PipelineError` including the missing source name and available sources
  - [x] 5.5 RED: Write tests for `input_from` with multiple mappings -- step pulls data from multiple upstream steps
  - [x] 5.6 GREEN: Implement multi-source input resolution
  - [x] 5.7 RED: Write tests for `input_from` key collision -- mapped key conflicts with existing context inputs
  - [x] 5.8 GREEN: Handle collision detection for `input_from` resolution -- produce `PipelineError` on conflict
  - [x] 5.9 REFACTOR: Clean up, verify coverage

- [x] Task 6: Implement `condition` predicate in executor (AC: #3)
  - [x] 6.1 RED: Write tests for `run_workflow` with conditional step -- condition returns True, step executes normally
  - [x] 6.2 GREEN: Implement condition check in `run_workflow` -- before `_run_step_with_retry`, evaluate `step.condition(current_ctx)` if condition is not None
  - [x] 6.3 RED: Write tests for conditional step skipped -- condition returns False, step is skipped without error, subsequent steps still execute
  - [x] 6.4 GREEN: Implement skip logic -- when condition is falsy, continue to next step without executing
  - [x] 6.5 RED: Write tests for conditional step with data flow -- skipped step's `output` is NOT registered in data flow registry, downstream `input_from` referencing it fails with clear error
  - [x] 6.6 GREEN: Ensure skipped steps do not register outputs
  - [x] 6.7 RED: Write tests for conditional step in failure path -- condition step after pipeline failure with `always_run=False` is still skipped (normal step skip takes priority)
  - [x] 6.8 GREEN: Ensure condition evaluation does not override the normal-skip-after-failure logic
  - [x] 6.9 RED: Write tests for conditional `always_run` step -- always_run step with condition evaluates condition even in failure path, executes only if condition is True
  - [x] 6.10 GREEN: Implement conditional evaluation for always_run steps
  - [x] 6.11 REFACTOR: Clean up, verify all condition + data flow + always_run interactions covered

- [x] Task 7: Verify `list_workflows` dispatchable filter (AC: #4)
  - [x] 7.1 RED: Write tests for `list_workflows(dispatchable_only=True)` -- returns only dispatchable workflows (implement_close, implement_verify_close), excludes non-dispatchable (convert_stories_to_beads)
  - [x] 7.2 GREEN: Verify existing `list_workflows` implementation handles this correctly (it already does -- this task validates via test)
  - [x] 7.3 RED: Write tests for `list_workflows(dispatchable_only=False)` -- returns all workflows including non-dispatchable
  - [x] 7.4 GREEN: Verify existing implementation passes
  - [x] 7.5 REFACTOR: Ensure workflow structure tests do not mock ROP internals (NFR13)

- [x] Task 8: End-to-end data flow integration tests (AC: #2, #3, #5)
  - [x] 8.1 RED: Write integration test for three-step workflow with output + input_from data flow -- step 1 outputs data, step 2 reads via input_from, step 3 reads from both
  - [x] 8.2 GREEN: Verify integration passes with existing implementation
  - [x] 8.3 RED: Write integration test combining condition + data flow + always_run -- conditional step skipped, always_run step executes, data flow from non-skipped steps works
  - [x] 8.4 GREEN: Verify integration passes
  - [x] 8.5 REFACTOR: Verify full coverage, all quality gates pass

- [x] Task 9: Verify full integration and quality gates (AC: #6)
  - [x] 9.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- 159 tests pass, 100% line+branch coverage
  - [x] 9.2 Run `uv run mypy adws/` -- strict mode passes (0 issues in 29 files)
  - [x] 9.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 2.5)

**engine/executor.py** has 4 functions:
```python
def _resolve_step_function(function_name: str) -> IOResult[StepFunction, PipelineError]: ...
def run_step(step: Step, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def _run_step_with_retry(step: Step, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def run_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
```

`run_workflow` currently does sequential execution with always_run + retry:
```python
def run_workflow(workflow, ctx):
    current_ctx = ctx
    pipeline_failure: PipelineError | None = None
    always_run_failures: list[dict[str, object]] = []

    for i, step in enumerate(workflow.steps):
        if pipeline_failure is not None and not step.always_run:
            continue

        result = _run_step_with_retry(step, current_ctx)

        if isinstance(result, IOFailure):
            error = unsafe_perform_io(result.failure())
            if pipeline_failure is None:
                pipeline_failure = error
            else:
                always_run_failures.append(error.to_dict())
            continue

        current_ctx = unsafe_perform_io(result.unwrap())

        if i < len(workflow.steps) - 1:
            try:
                current_ctx = current_ctx.promote_outputs_to_inputs()
            except ValueError as exc:
                collision = PipelineError(...)
                if pipeline_failure is None:
                    pipeline_failure = collision
                continue

    if pipeline_failure is not None:
        if always_run_failures:
            # Attach always_run failures to original error context
            pipeline_failure = PipelineError(
                ..., context={...pipeline_failure.context, "always_run_failures": always_run_failures}
            )
        return IOFailure(pipeline_failure)
    return IOSuccess(current_ctx)
```

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

**io_ops.py** has 5 functions + 1 async helper:
- `read_file`, `check_sdk_import`, `execute_sdk_call`, `run_shell_command`, `sleep_seconds`
- Plus internal `_execute_sdk_call_async` and `_NoResultError`

**workflows/__init__.py** -- Has `WorkflowName`, `load_workflow()`, `list_workflows()`, and 3 registered workflows (implement_close has steps, others empty).

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 125 tests (excluding 2 enemy tests), 100% coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`
- `IOResult[StepFunction, PipelineError]` -- success is `StepFunction`

### Design: New Step Fields

Three new fields on the `Step` dataclass in `engine/types.py`:

```python
@dataclass(frozen=True)
class Step:
    name: str
    function: str
    always_run: bool = False
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0
    shell: bool = False
    command: str = ""
    # NEW fields for Story 2.6:
    output: str | None = None          # Named output key for data flow registry
    input_from: dict[str, str] | None = None  # Map: {source_output_name: target_input_key}
    condition: Callable[[WorkflowContext], bool] | None = None  # Predicate for conditional execution
```

All have defaults (None), so backward compatibility is preserved -- every existing `Step()` construction continues to work unchanged.

#### `output` Field

When `output` is set (e.g., `output="step1_data"`), the executor registers that step's `outputs` dict under the given key in a data flow registry. This is a named reference point that downstream steps can pull from via `input_from`.

The `output` field does NOT replace `promote_outputs_to_inputs`. It is an ADDITIONAL mechanism for explicit, named data flow. The existing promote mechanism continues to work for implicit sequential flow. The two mechanisms coexist:

- **Implicit flow** (existing): `promote_outputs_to_inputs()` merges all outputs into inputs for the next step. Works for simple sequential pipelines.
- **Explicit flow** (new): `output` + `input_from` names specific data and maps it to specific input keys. Works for complex multi-source data flow.

The data flow registry is a simple dict managed within `run_workflow`:
```python
data_flow_registry: dict[str, dict[str, object]] = {}
```

After a step with `output` set succeeds:
```python
if step.output:
    data_flow_registry[step.output] = dict(current_ctx.outputs)
```

#### `input_from` Field

The `input_from` dict maps source output names (keys in `data_flow_registry`) to target input keys in the step's context. Before executing a step with `input_from`, the executor resolves each mapping:

```python
if step.input_from:
    resolved_inputs = dict(current_ctx.inputs)
    for source_name, target_key in step.input_from.items():
        if source_name not in data_flow_registry:
            return IOFailure(PipelineError(
                step_name=step.name,
                error_type="MissingInputFromError",
                message=f"Step '{step.name}' references output '{source_name}' via input_from, but no step has produced output with that name. Available: {sorted(data_flow_registry.keys())}",
                context={...},
            ))
        resolved_inputs[target_key] = data_flow_registry[source_name]
    current_ctx = current_ctx.with_updates(inputs=resolved_inputs)
```

**Collision detection**: If `target_key` already exists in `current_ctx.inputs`, produce a `PipelineError` rather than silently overwriting.

**Missing reference detection**: If `source_name` is not in `data_flow_registry`, produce a `PipelineError` with the missing name and available registered names.

#### `condition` Field

The `condition` field is a callable predicate: `Callable[[WorkflowContext], bool] | None`. When set, the executor evaluates it before executing the step:

```python
if step.condition is not None and not step.condition(current_ctx):
    # Skip this step -- do NOT register output, do NOT count as failure
    continue
```

**Important interactions:**
- **condition + always_run**: If an always_run step has a condition, the condition IS evaluated even in the failure path. The step only executes if the condition is truthy. This allows conditional cleanup.
- **condition + data flow**: If a step is skipped due to condition=False, its `output` is NOT registered in the data flow registry. Downstream steps referencing it via `input_from` will get a `MissingInputFromError`.
- **condition + pipeline failure**: Non-always_run steps are already skipped when `pipeline_failure is not None`. The condition check only applies to steps that would otherwise execute.

#### `condition` Callable and Frozen Dataclass

The `Step` dataclass is `frozen=True`. Callable fields work fine in frozen dataclasses -- the `frozen` constraint prevents reassignment of the attribute, but callables are immutable objects themselves. The one nuance is that `Callable` is not directly hashable, but `frozen=True` only affects `__setattr__`, not `__hash__`. If a hash is needed (unlikely for Step), we would need `eq=False`, but our current usage does not require hashing Steps.

**mypy consideration**: The `condition` field type uses `Callable[[WorkflowContext], bool]`. Since `WorkflowContext` is in a different module, use the TYPE_CHECKING import guard pattern already established in `engine/types.py`.

### Design: Executor Changes

The executor needs three additions woven into the existing `run_workflow` loop:

1. **Data flow registry**: A `dict[str, dict[str, object]]` initialized at the top of `run_workflow`. Populated after each successful step that has `output` set.

2. **input_from resolution**: Before executing each step, if `step.input_from` is set, resolve the mappings from the registry and merge into context inputs.

3. **condition evaluation**: Before executing each step (after the existing pipeline_failure skip check), if `step.condition` is set and returns False, skip the step.

The ordering of checks in the loop should be:
```python
for i, step in enumerate(workflow.steps):
    # 1. Skip non-always_run steps if pipeline failed (EXISTING)
    if pipeline_failure is not None and not step.always_run:
        continue

    # 2. Evaluate condition predicate (NEW)
    if step.condition is not None and not step.condition(current_ctx):
        continue

    # 3. Resolve input_from mappings (NEW)
    if step.input_from:
        ... resolve and merge, or return error ...

    # 4. Execute step with retry (EXISTING)
    result = _run_step_with_retry(step, current_ctx)

    # 5. Handle result (EXISTING)
    ...

    # 6. Register output in data flow registry (NEW)
    if step.output:
        data_flow_registry[step.output] = dict(current_ctx.outputs)

    # 7. Promote outputs to inputs for next step (EXISTING)
    ...
```

**Important**: The condition check for always_run steps in the failure path needs special handling. The current logic is:
```python
if pipeline_failure is not None and not step.always_run:
    continue
```

For conditional always_run steps, the condition should be evaluated AFTER the always_run check passes:
```python
# Skip non-always_run steps if pipeline failed
if pipeline_failure is not None and not step.always_run:
    continue

# Evaluate condition (applies to both normal and always_run steps)
if step.condition is not None and not step.condition(current_ctx):
    continue
```

This means a conditional always_run step with a falsy condition IS skipped, even in the failure path. This is correct behavior -- the condition is an explicit opt-out.

### Design: input_from Resolution Error Handling

The `input_from` resolution happens before step execution. If resolution fails (missing source or collision), it should be treated the same as any other step failure:

- If `pipeline_failure is None`: the resolution error BECOMES the pipeline failure
- If `pipeline_failure is not None` (we're in always_run territory): the resolution error is added to `always_run_failures`

This is already handled naturally by the existing error handling in `run_workflow` -- we just need to produce the right `IOFailure`/`PipelineError` at the resolution point. However, since `input_from` resolution happens BEFORE `_run_step_with_retry`, we need to handle it as a separate path. The cleanest approach is to extract resolution into a helper function:

```python
def _resolve_input_from(
    step: Step,
    ctx: WorkflowContext,
    data_flow_registry: dict[str, dict[str, object]],
) -> IOResult[WorkflowContext, PipelineError]:
    """Resolve input_from mappings and return updated context."""
    if step.input_from is None:
        return IOSuccess(ctx)

    resolved_inputs = dict(ctx.inputs)
    for source_name, target_key in step.input_from.items():
        if source_name not in data_flow_registry:
            available = sorted(data_flow_registry.keys())
            return IOFailure(PipelineError(
                step_name=step.name,
                error_type="MissingInputFromError",
                message=f"Step '{step.name}' references output '{source_name}' via input_from, but no step has produced output with that name. Available: {available}",
                context={"source_name": source_name, "available": available, "step_name": step.name},
            ))
        if target_key in resolved_inputs:
            return IOFailure(PipelineError(
                step_name=step.name,
                error_type="InputFromCollisionError",
                message=f"Step '{step.name}' input_from maps '{source_name}' to key '{target_key}' which already exists in context inputs",
                context={"source_name": source_name, "target_key": target_key, "step_name": step.name},
            ))
        resolved_inputs[target_key] = data_flow_registry[source_name]

    return IOSuccess(ctx.with_updates(inputs=resolved_inputs))
```

This follows the io_ops function pattern (returns IOResult, never raises), making it natural to integrate into the `run_workflow` loop. Since this is executor-internal logic (not I/O), it does NOT go in io_ops.py -- it stays as a private helper in executor.py.

### Test Strategy

**Test file**: `adws/tests/adw_modules/engine/test_executor.py` (MODIFY existing file) -- for executor-level data flow and condition tests

**Test file**: `adws/tests/adw_modules/engine/test_types.py` (MODIFY existing file) -- for new Step field tests

**Test file**: `adws/tests/workflows/test_workflow_init.py` (MODIFY existing file) -- for list_workflows dispatchable filter tests (if they don't already exist)

**Reuse existing test helpers**: `_make_success_step`, `_make_failure_step`, `_make_flaky_step` are already defined in test_executor.py.

**New test helpers needed:**

```python
def _make_conditional_step(
    condition_result: bool,
    output_key: str,
    output_value: object,
) -> tuple[_StepFn, Callable[[WorkflowContext], bool]]:
    """Create a step with a condition predicate."""
    def condition(ctx: WorkflowContext) -> bool:
        return condition_result

    def step(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(ctx.merge_outputs({output_key: output_value}))

    return step, condition
```

**Tests for Step fields (in test_types.py):**
- `test_step_output_default` -- verify default is None
- `test_step_output_configured` -- verify custom value
- `test_step_input_from_default` -- verify default is None
- `test_step_input_from_configured` -- verify dict mapping
- `test_step_condition_default` -- verify default is None
- `test_step_condition_configured` -- verify callable accepted
- `test_step_backward_compatible` -- existing Step() calls still work

**Tests for output data flow (new class in test_executor.py):**
- `test_output_registered_in_data_flow` -- step with output set, next step can reference it
- `test_output_empty_outputs_registered` -- step produces no outputs but output key is still registered (empty dict)
- `test_output_not_set_no_registration` -- step without output field does NOT register in data flow
- `test_output_overwrite` -- two steps with same output name, later one overwrites (or error -- document the policy choice)

**Tests for input_from data flow (new class in test_executor.py):**
- `test_input_from_resolves_single_source` -- maps data from one upstream step
- `test_input_from_resolves_multiple_sources` -- maps data from multiple upstream steps
- `test_input_from_missing_source_error` -- references nonexistent output, gets clear PipelineError with available sources listed
- `test_input_from_collision_error` -- mapped key conflicts with existing input
- `test_input_from_and_promote_coexist` -- both implicit and explicit flow work in same workflow

**Tests for condition predicate (new class in test_executor.py):**
- `test_condition_true_executes` -- condition returns True, step runs normally
- `test_condition_false_skips` -- condition returns False, step skipped, no error
- `test_condition_false_no_output_registered` -- skipped step's output NOT in data flow registry
- `test_condition_false_subsequent_steps_run` -- steps after skipped step still execute
- `test_condition_none_always_executes` -- no condition set, step always runs (backward compat)
- `test_condition_always_run_failure_path` -- always_run step with condition in failure path: condition evaluated, executes if True
- `test_condition_always_run_false_skipped` -- always_run step with condition=False in failure path: skipped even though always_run
- `test_condition_receives_current_context` -- condition callable receives current context (not initial), can inspect accumulated state

**Integration tests (new class in test_executor.py):**
- `test_full_data_flow_pipeline` -- 3 steps with output/input_from wiring, data flows correctly
- `test_condition_plus_data_flow_plus_always_run` -- conditional step skipped, always_run runs, data flow from non-skipped works

**Tests for list_workflows (in existing workflow test file):**
- `test_list_workflows_dispatchable_only` -- returns only dispatchable workflows
- `test_list_workflows_all` -- returns all workflows including non-dispatchable

### Ruff Considerations

- `PLR0912` (too many branches): The `run_workflow` loop is getting complex with condition + input_from + output added. If ruff triggers this, extract `_resolve_input_from` as a private helper (already planned).
- `PLR0913` (too many parameters): `_resolve_input_from` takes 3 parameters -- well under the limit.
- `FBT001`/`FBT002` (boolean positional): The `condition` field returns `bool` -- this is a dataclass field, not a function parameter. The predicate callable returns bool, which is fine.
- `ARG001` (unused function argument): Already suppressed for test files.
- `E501` (line too long): Keep all lines under 88 characters.
- `S101` (assert): Suppressed for test files.
- `S604` (shell=True in Step construction): Suppress inline in tests with `# noqa: S604`.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- all errors wrapped in IOResult/PipelineError. input_from resolution errors return IOFailure, not raise.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: No new io_ops functions needed -- executor changes are pure orchestration logic.
- **NFR11**: mypy strict mode -- all function signatures fully typed, condition Callable type properly specified.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR13**: Workflow definitions (Tier 1) testable without mocking ROP internals. Step fields are plain data types (str, dict, callable). Tests verify structure, not ROP behavior.
- **FR7**: Declarative Workflow and Step types -- workflows remain declarative data, not imperative code.
- **FR9**: Conditional steps via context predicates -- condition field on Step.
- **FR10**: Data flow via output/input_from parameters -- explicit named data flow between steps.

### What NOT to Do

- Do NOT change the `run_step` function -- it remains unchanged. All changes go into `run_workflow` and the Step dataclass.
- Do NOT change existing test assertions or existing function signatures (except adding new fields with defaults to Step).
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()`, `add_feedback()`, or `merge_outputs()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe`.
- Do NOT implement combinators (`with_verification`, `sequence`) -- that is Story 2.7.
- Do NOT add new io_ops functions -- the data flow and condition logic is pure orchestration within the executor.
- Do NOT make `condition` a string that's eval'd -- it MUST be a real `Callable`. Workflow definitions that need serialization can wrap the condition in a factory function.
- Do NOT remove or bypass `promote_outputs_to_inputs` -- the existing implicit flow continues to work alongside the new explicit flow. Both mechanisms coexist.
- Do NOT change the existing `_STEP_REGISTRY` or `_resolve_step_function` -- they are unrelated to data flow.
- Do NOT put data flow registry in `WorkflowContext` -- it is executor-internal state, not pipeline-visible state. Keep it as a local variable in `run_workflow`.

### Project Structure Notes

Files to create:
- None (all modifications to existing files)

Files to modify:
- `adws/adw_modules/engine/types.py` -- add `output`, `input_from`, `condition` fields to Step
- `adws/adw_modules/engine/executor.py` -- add `_resolve_input_from` private helper, update `run_workflow` for condition + input_from + output
- `adws/tests/adw_modules/engine/test_executor.py` -- add data flow, input_from, condition test classes
- `adws/tests/adw_modules/engine/test_types.py` -- add Step field tests for output, input_from, condition

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist, step internal structure, workflow definition pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, dispatchable flag, load_workflow() pure lookup, list_workflows filter
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, workflow composition
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries] -- Four-layer pipeline, Tier 1/Tier 2 separation
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6] -- AC and story definition (FR7, FR9, FR10)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7] -- Next story (combinators) depends on types from this story
- [Source: _bmad-output/implementation-artifacts/2-5-engine-always-run-steps-and-retry-logic.md] -- Previous story learnings, executor design, test patterns
- [Source: _bmad-output/implementation-artifacts/2-4-engine-core-sequential-execution-and-error-handling.md] -- Executor core, context propagation, registry pattern
- [Source: adws/adw_modules/engine/types.py] -- Current Step/Workflow types (adding output, input_from, condition)
- [Source: adws/adw_modules/engine/executor.py] -- Current executor (4 functions: _resolve_step_function, run_step, _run_step_with_retry, run_workflow)
- [Source: adws/adw_modules/types.py] -- WorkflowContext with with_updates(), promote_outputs_to_inputs()
- [Source: adws/adw_modules/errors.py] -- PipelineError with to_dict()
- [Source: adws/workflows/__init__.py] -- Workflow registry, load_workflow(), list_workflows(), WorkflowName
- [Source: adws/tests/adw_modules/engine/test_executor.py] -- Existing executor tests (125 tests, helper functions)
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

From Story 2.5 learnings:
- **unsafe_perform_io()**: Use `from returns.unsafe import unsafe_perform_io` to unwrap IOResult containers. Do NOT use `_inner_value`.
- **always_run_failures accumulator**: Used in `run_workflow` to track always_run step failures without losing the original pipeline error. New data flow code must preserve this pattern.
- **pipeline_failure tracking**: The `run_workflow` function tracks pipeline state via `pipeline_failure: PipelineError | None`. New condition/data flow logic must integrate with this, not replace it.
- **sleep_seconds mock**: Tests mock `adws.adw_modules.engine.executor.sleep_seconds` to avoid real delays. Data flow tests do not need this unless retry is involved.
- **assert for type narrowing**: `assert last_failure is not None  # noqa: S101` pattern for type narrowing guards.

From Story 2.4 learnings:
- **TYPE_CHECKING guard**: Used in executor.py for Step, StepFunction, Workflow, WorkflowContext to satisfy TC001 ruff rule.
- **Simple for-loop**: The executor uses a simple for-loop. The condition and data flow checks weave into this loop naturally.
- **Registry mocking**: Tests mock `_STEP_REGISTRY` directly via `mocker.patch("adws.adw_modules.engine.executor._STEP_REGISTRY", {...})`.
- **Context propagation collision**: ValueError from `promote_outputs_to_inputs()` is caught and wrapped as PipelineError.

From Story 2.3 learnings:
- **IOResult[Success, Error]**: Success type comes first (confirmed across all stories).
- **Shell step dispatch**: Bypasses registry, injects `shell_command` into context inputs.

From Story 2.2 learnings:
- **Coverage omit**: `conftest.py` and `enemy/*` excluded from coverage measurement.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen. The `condition` callable and `input_from` dict are fine as frozen fields.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None -- clean implementation, no debugging needed.

### Completion Notes List

- Tasks 1-3: Added `output`, `input_from`, `condition` fields to Step dataclass with full backward compatibility. All 3 fields have None defaults so existing Step constructions work unchanged.
- Tasks 4-6: Implemented data flow registry, `_resolve_input_from` helper, condition predicate evaluation, and `_should_skip_step`/`_record_failure`/`_finalize_workflow` helpers in executor. Refactored `run_workflow` to reduce complexity (C901/PLR0912) by extracting 4 private helper functions.
- Task 7: Added specific assertions for dispatchable filter verifying exact workflow inclusion/exclusion. Existing implementation already correct.
- Task 8: Integration tests verify 3-step data flow pipeline and condition + data flow + always_run interaction.
- Task 9: All 159 tests pass, 100% line+branch coverage, mypy strict clean, ruff zero violations.
- Test count increased from 125 to 159 (34 new tests).
- Implicit (promote_outputs_to_inputs) and explicit (output/input_from) data flow coexist as designed.

### File List

- `adws/adw_modules/engine/types.py` -- Added output, input_from, condition fields to Step dataclass
- `adws/adw_modules/engine/executor.py` -- Added _resolve_input_from, _should_skip_step, _record_failure, _finalize_workflow helpers; updated run_workflow for condition/data flow
- `adws/tests/adw_modules/engine/test_types.py` -- Added 7 tests for new Step fields (output, input_from, condition, backward compat)
- `adws/tests/adw_modules/engine/test_executor.py` -- Added 24 tests across 6 new test classes (TestOutputDataFlow, TestInputFromDataFlow, TestConditionPredicate, TestDataFlowIntegration, TestResolveInputFrom + input_from_error_always_run test); review added 8 more tests (TestShouldSkipStep + condition exception tests) = 32 total new executor tests
- `adws/tests/workflows/test_workflows.py` -- Added 3 tests for dispatchable filter specifics and declarative data verification

## Senior Developer Review

### Reviewer
Claude Opus 4.5 (adversarial code review)

### Review Date
2026-02-01

### Issues Found

| # | Severity | Description | Status |
|---|----------|-------------|--------|
| 1 | HIGH | `_should_skip_step` did not catch exceptions from `condition` predicates. If `step.condition(ctx)` raised, the exception propagated uncaught through `run_workflow`, violating NFR1 (no uncaught exceptions). All errors must be wrapped in IOResult/PipelineError. | FIXED |
| 2 | MEDIUM | `_should_skip_step` docstring was incomplete -- failed to mention that always_run steps with a falsy condition are also skipped in the failure path, which is the critical nuanced interaction between `always_run` and `condition`. | FIXED |
| 3 | MEDIUM | Story File List section claimed "27 tests across 6 new test classes" in test_executor.py. Actual count was 24 tests across 6 classes (7+24+3=34 total new, which was correct). Per-file breakdown was inaccurate. | FIXED |
| 4 | LOW | `_record_failure` has a side-effect (mutating `always_run_failures` list in-place) not indicated by its return type (`PipelineError`). The mutation of the accumulator list is an implicit contract. Not a bug since tests verify the behavior, but a subtle design smell. | NOTED |

### Fixes Applied

**Issue 1 (HIGH)**: Changed `_should_skip_step` return type from `bool` to `IOResult[bool, PipelineError]`. Added `try/except` around `step.condition(ctx)` that catches all exceptions and wraps them as `ConditionEvaluationError` PipelineError with exception type and message in context. Updated `run_workflow` to handle the IOResult return -- condition exceptions are now treated the same as any other step failure (becomes pipeline_failure or appended to always_run_failures). Added module-level `_SKIP_STEP = True` and `_RUN_STEP = False` constants to satisfy ruff FBT003 (no boolean literals in function calls).

**Issue 2 (MEDIUM)**: Rewrote `_should_skip_step` docstring to explicitly document all skip rules including the always_run + condition interaction.

**Issue 3 (MEDIUM)**: Corrected File List to show actual 24 new executor tests (not 27), plus 8 review-added tests = 32 total new executor tests.

### Tests Added
- `TestConditionPredicate::test_condition_exception_produces_error` -- condition predicate raises, PipelineError returned
- `TestConditionPredicate::test_condition_exception_always_run_failure` -- condition exception on always_run step in failure path, tracked in always_run_failures
- `TestShouldSkipStep::test_skip_non_always_run_after_failure` -- direct unit test for helper
- `TestShouldSkipStep::test_no_skip_always_run_after_failure` -- direct unit test for helper
- `TestShouldSkipStep::test_skip_false_condition` -- direct unit test for helper
- `TestShouldSkipStep::test_no_skip_true_condition` -- direct unit test for helper
- `TestShouldSkipStep::test_no_skip_no_condition` -- direct unit test for helper
- `TestShouldSkipStep::test_condition_exception_returns_failure` -- direct unit test for exception handling

### Quality Gate Results (Post-Fix)
- pytest: 167 passed, 2 skipped (enemy tests)
- coverage: 100% line + branch (109 stmts, 48 branches in executor.py)
- ruff: All checks passed
- mypy: Success, no issues found in 29 source files

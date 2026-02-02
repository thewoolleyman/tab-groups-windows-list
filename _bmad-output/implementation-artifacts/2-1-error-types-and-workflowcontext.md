# Story 2.1: Error Types & WorkflowContext

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want foundational data types for pipeline errors and workflow state,
so that all pipeline components have a consistent contract for error propagation and context sharing.

## Acceptance Criteria

1. **Given** the skeleton from Epic 1, **When** I inspect `adws/adw_modules/errors.py`, **Then** `PipelineError` is a dataclass with fields: `step_name` (str), `error_type` (str), `message` (str), `context` (dict) **And** it is immutable and serializable for logging.

2. **Given** the skeleton from Epic 1, **When** I inspect `adws/adw_modules/types.py` (or a new `workflow_context.py`), **Then** `WorkflowContext` is defined with `inputs` (dict), `outputs` (dict), and `feedback` (list) fields **And** context supports accumulating feedback from failed verify attempts **And** context supports propagating outputs from one step as inputs to the next.

3. **Given** both types are defined, **When** I run `uv run pytest adws/tests/`, **Then** tests validate PipelineError construction, serialization, and field access **And** tests validate WorkflowContext input/output propagation and feedback accumulation **And** 100% coverage is maintained (NFR9).

## Tasks / Subtasks

- [ ] Task 1: Evolve PipelineError for full pipeline use (AC: #1)
  - [ ] 1.1 RED: Write tests for PipelineError serialization (`to_dict()` method) -- must be serializable for JSONL logging
  - [ ] 1.2 GREEN: Implement `to_dict()` on PipelineError that returns a plain dict suitable for `json.dumps()`
  - [ ] 1.3 RED: Write tests for PipelineError `__str__` representation for human-readable logging
  - [ ] 1.4 GREEN: Implement `__str__` on PipelineError
  - [ ] 1.5 REFACTOR: Clean up, verify 100% coverage

- [ ] Task 2: Evolve WorkflowContext for pipeline context propagation (AC: #2)
  - [ ] 2.1 RED: Write tests for feedback accumulation -- `add_feedback()` returns new context with appended feedback entry
  - [ ] 2.2 GREEN: Implement `add_feedback(entry: str) -> WorkflowContext` method
  - [ ] 2.3 RED: Write tests for output-to-input propagation -- `promote_outputs_to_inputs()` returns new context with outputs merged into inputs
  - [ ] 2.4 GREEN: Implement `promote_outputs_to_inputs() -> WorkflowContext`
  - [ ] 2.5 RED: Write tests for `merge_outputs()` -- merging new outputs into existing context outputs
  - [ ] 2.6 GREEN: Implement `merge_outputs(new_outputs: dict) -> WorkflowContext`
  - [ ] 2.7 REFACTOR: Clean up, verify 100% coverage

- [ ] Task 3: Verify full integration and quality gates (AC: #3)
  - [ ] 3.1 Run `uv run pytest adws/tests/` -- all tests pass, 100% line + branch coverage
  - [ ] 3.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 3.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Epic 1 Skeleton)

**PipelineError** already exists in `adws/adw_modules/errors.py`:
```python
@dataclass(frozen=True)
class PipelineError:
    step_name: str
    error_type: str
    message: str
    context: dict[str, object] = field(default_factory=dict)
```
- Already frozen, already has the required fields per AC #1
- **What's missing**: serialization support (`to_dict()`) and string representation (`__str__`) for logging use cases in the engine (JSONL hook logs, structured error output)

**WorkflowContext** already exists in `adws/adw_modules/types.py`:
```python
@dataclass(frozen=True)
class WorkflowContext:
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)

    def with_updates(self, inputs=None, outputs=None, feedback=None) -> WorkflowContext:
        return replace(self, ...)
```
- Already frozen with `with_updates()` for immutable updates
- **What's missing**: convenience methods for the engine's common operations:
  - `add_feedback()` -- accumulate feedback from failed verify attempts (FR16)
  - `promote_outputs_to_inputs()` -- propagate outputs from one step as inputs to the next (FR3)
  - `merge_outputs()` -- merge step outputs into context without replacing all existing outputs

### Existing Tests (30 total, 100% coverage)

- `test_errors.py`: 3 tests (construction, default context, frozen)
- `test_types.py`: 6 tests (construction, defaults, frozen, with_updates)
- These tests remain valid -- new tests ADD to them

### Architecture Compliance

- **File locations**: Modifications go in existing files `adws/adw_modules/errors.py` and `adws/adw_modules/types.py` -- do NOT create new files like `workflow_context.py`
- **Epics note**: The AC mentions `workflow_context.py` as an option, but the skeleton already has WorkflowContext in `types.py` -- keep it there per established convention
- **Frozen dataclass pattern**: All modifications must preserve `frozen=True` -- return new instances, never mutate
- **IOResult type order**: `IOResult[SuccessType, ErrorType]` -- success first (corrected in Epic 1 learnings from Story 1.2)
- **No new io_ops functions needed**: This story is pure domain types -- no I/O involved
- **No new step functions needed**: These are foundational types consumed by steps, not steps themselves

### Critical Constraints

- **NFR9**: 100% line + branch coverage -- every new method/line must have a test
- **NFR11**: mypy strict mode -- all type annotations must be correct
- **NFR12**: ruff ALL rules -- zero lint violations
- **Immutability**: WorkflowContext and PipelineError are both `frozen=True`. Methods return NEW instances. Never mutate.
- **Serialization**: PipelineError `to_dict()` must produce JSON-serializable output (no Path objects, no custom types in context dict values that aren't serializable)

### What NOT to Do

- Do NOT create a separate `workflow_context.py` file -- WorkflowContext lives in `types.py`
- Do NOT add ROP types (IOResult) to these domain types -- they are Tier 1 pure data
- Do NOT add io_ops imports -- these types have no I/O dependency
- Do NOT create an error type union yet (e.g., `PipelineError = SdkError | BeadsError | ...`) -- the architecture shows this pattern but it's for later stories when those specific error types are introduced. For now, PipelineError is a single dataclass.
- Do NOT change existing test assertions -- add new tests alongside existing ones
- Do NOT import `json` in the types module -- `to_dict()` returns a plain dict; the caller decides whether to serialize to JSON

### Project Structure Notes

- All source in `adws/adw_modules/` -- flat layout, NOT nested under `src/`
- Tests mirror source: `adws/tests/adw_modules/test_errors.py`, `adws/tests/adw_modules/test_types.py`
- Absolute imports only: `from adws.adw_modules.errors import PipelineError`
- Test naming: `test_<unit>_<scenario>` (e.g., `test_pipeline_error_to_dict_includes_all_fields`)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist, frozen dataclass pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- PipelineError used in IOResult returns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1] -- AC and story definition
- [Source: _bmad-output/implementation-artifacts/1-2-skeleton-layer-implementations-and-tdd-foundation.md] -- Previous story learnings (IOResult type order, shallow frozen limitation)
- [Source: adws/adw_modules/errors.py] -- Current PipelineError implementation
- [Source: adws/adw_modules/types.py] -- Current WorkflowContext implementation
- [Source: adws/tests/adw_modules/test_errors.py] -- Current PipelineError tests (3 tests)
- [Source: adws/tests/adw_modules/test_types.py] -- Current WorkflowContext tests (6 tests)

### Git Intelligence (Recent Commits)

```
dad526b fix: Adversarial code review fixes for Story 1.3
6f846f1 feat: Add Python quality gates to CI pipeline (Story 1.3)
17cca59 fix: Adversarial code review fixes for Story 1.2 (6 issues resolved)
842e59b feat: Implement skeleton layers across all four pipeline tiers with TDD (Story 1.2)
e67c522 test(RED): Add failing tests for PipelineError (Story 1.2, Task 1)
```

Pattern: RED commits use prefix `test(RED):`, feature commits use `feat:`, review fixes use `fix:`.

### Previous Story Intelligence

From Story 1.2 learnings:
- **IOResult[Success, Error]**: Success type comes first (architecture doc was initially wrong, corrected)
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; dict/list fields are mutable in-place. The docstring correctly notes this. Callers must use `with_updates()`.
- **Module reload in tests**: If a test patches module-level imports, wrap in try/finally with reload in finally block
- **Coverage omit**: `conftest.py` is omitted from coverage via `[tool.coverage.run]` in pyproject.toml

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Change Log

- 2026-02-01: Story created with comprehensive context from Epic 1 artifacts, architecture, and PRD analysis

### File List

- `adws/adw_modules/errors.py` -- Modified (add to_dict, __str__ to PipelineError)
- `adws/adw_modules/types.py` -- Modified (add add_feedback, promote_outputs_to_inputs, merge_outputs to WorkflowContext)
- `adws/tests/adw_modules/test_errors.py` -- Modified (add serialization and string representation tests)
- `adws/tests/adw_modules/test_types.py` -- Modified (add feedback accumulation, output propagation, merge tests)

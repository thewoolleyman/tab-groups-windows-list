# Story 3.3: Feedback Accumulation & Retry Context

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want verify failures to accumulate as structured feedback that flows into implementation retries,
so that the implementation agent knows exactly what failed and can fix it on retry.

## Acceptance Criteria

1. **Given** a verify workflow execution that fails, **When** the engine processes the failure, **Then** structured feedback is accumulated in `WorkflowContext.feedback` (FR16) **And** feedback includes: which tool failed, specific error messages, affected files, attempt number.

2. **Given** accumulated feedback from previous verify attempts, **When** the engine passes context to a subsequent `/implement` retry, **Then** the full feedback history is available as explicit context (FR17) **And** the implementation agent receives all previous failure details, not just the most recent.

3. **Given** multiple verify-implement cycles, **When** feedback accumulates across attempts, **Then** each attempt's feedback is preserved with its attempt number **And** feedback does not duplicate -- each cycle adds new entries.

4. **Given** all feedback accumulation code, **When** I run tests, **Then** tests cover: single failure feedback, multi-attempt accumulation, feedback passed to retry context **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create `VerifyFeedback` structured data type in types.py (AC: #1)
  - [x] 1.1 RED: Write tests for `VerifyFeedback` frozen dataclass construction with fields: `tool_name` (str), `errors` (list[str]), `raw_output` (str), `attempt` (int), `step_name` (str). Verify immutability, default factory for errors, field access.
  - [x] 1.2 GREEN: Implement `VerifyFeedback` as a frozen dataclass in `adws/adw_modules/types.py`.
  - [x] 1.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `accumulate_verify_feedback()` pure function (AC: #1, #3)
  - [x] 2.1 RED: Write test for `accumulate_verify_feedback` accepting a `PipelineError` from a verify step failure (error_type="VerifyFailed") and an attempt number. Verify it extracts tool_name, errors, raw_output from `PipelineError.context` and returns a `VerifyFeedback` instance.
  - [x] 2.2 GREEN: Implement `accumulate_verify_feedback(error: PipelineError, attempt: int) -> VerifyFeedback` as a pure function in a new module `adws/adw_modules/steps/accumulate_verify_feedback.py`.
  - [x] 2.3 RED: Write test for `accumulate_verify_feedback` handling a PipelineError with missing context keys (e.g., no `tool_name` in context). Verify it falls back to sensible defaults (step_name from PipelineError, "unknown" for tool_name, empty errors list).
  - [x] 2.4 GREEN: Implement fallback handling for missing context keys.
  - [x] 2.5 RED: Write test for `accumulate_verify_feedback` handling a non-verify PipelineError (error_type != "VerifyFailed"). Verify it still produces a valid VerifyFeedback using the PipelineError's fields.
  - [x] 2.6 GREEN: Implement handling for non-verify errors.
  - [x] 2.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create `build_feedback_context()` function for retry context assembly (AC: #2, #3)
  - [x] 3.1 RED: Write test for `build_feedback_context` that takes a `WorkflowContext` with accumulated feedback entries (list of VerifyFeedback serialized to dicts in `ctx.feedback`) and returns a formatted context string suitable for passing to an SDK implementation agent. Verify it includes all tool names, all errors, all attempt numbers.
  - [x] 3.2 GREEN: Implement `build_feedback_context(ctx: WorkflowContext) -> str` in `adws/adw_modules/steps/build_feedback_context.py`. Formats accumulated feedback as structured text for the implementation agent.
  - [x] 3.3 RED: Write test for `build_feedback_context` with empty feedback list. Verify it returns a string indicating no previous failures.
  - [x] 3.4 GREEN: Implement empty feedback handling.
  - [x] 3.5 RED: Write test for `build_feedback_context` with multi-attempt feedback (attempt 1 with jest failure, attempt 2 with ruff failure). Verify the output includes BOTH attempts' feedback in chronological order, each tagged with its attempt number.
  - [x] 3.6 GREEN: Implement multi-attempt chronological formatting.
  - [x] 3.7 RED: Write test that `build_feedback_context` does not duplicate feedback -- calling with same feedback list twice produces identical output.
  - [x] 3.8 GREEN: Verify idempotent behavior (pure function, no side effects).
  - [x] 3.9 REFACTOR: Clean up formatting, verify mypy/ruff.

- [x] Task 4: Create `add_verify_feedback_to_context()` step function (AC: #1, #2)
  - [x] 4.1 RED: Write test for `add_verify_feedback_to_context(ctx, error, attempt)` that takes a WorkflowContext, a PipelineError from a verify failure, and an attempt number. Verify it returns a new WorkflowContext with the `VerifyFeedback` dict appended to `ctx.feedback` via `add_feedback()`.
  - [x] 4.2 GREEN: Implement `add_verify_feedback_to_context` in `adws/adw_modules/steps/add_verify_feedback.py`. Uses `accumulate_verify_feedback` to build the feedback entry, serializes to string representation, and appends via `ctx.add_feedback()`.
  - [x] 4.3 RED: Write test for `add_verify_feedback_to_context` with existing feedback in context. Verify new feedback is APPENDED (not replacing existing entries), preserving the full history (AC #2, #3).
  - [x] 4.4 GREEN: Implement append behavior using existing `add_feedback()` method.
  - [x] 4.5 RED: Write test for `add_verify_feedback_to_context` with multiple sequential calls (simulating multi-attempt accumulation). Verify all entries are preserved in order with correct attempt numbers.
  - [x] 4.6 GREEN: Implement sequential accumulation.
  - [x] 4.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Export new functions from steps/__init__.py (AC: #1, #2)
  - [x] 5.1 RED: Write tests for importing `accumulate_verify_feedback`, `build_feedback_context`, `add_verify_feedback_to_context` from `adws.adw_modules.steps`.
  - [x] 5.2 GREEN: Add exports to `adws/adw_modules/steps/__init__.py` in a new "Feedback accumulation steps (Story 3.3)" conceptual group.
  - [x] 5.3 REFACTOR: Verify import paths, mypy, ruff.

- [x] Task 6: Integration test -- verify-implement retry cycle with feedback (AC: #1, #2, #3)
  - [x] 6.1 RED: Write integration test simulating a verify-implement retry cycle: (1) run verify workflow, capture failure, (2) call `add_verify_feedback_to_context` with the failure, (3) call `build_feedback_context` on the updated context, (4) verify the feedback string contains tool name, errors, and attempt number. Uses mocked step functions.
  - [x] 6.2 GREEN: Ensure all components integrate correctly. The verify workflow produces PipelineErrors with the expected context structure from Story 3.2, and the feedback functions consume them correctly.
  - [x] 6.3 RED: Write integration test for multi-cycle accumulation: (1) verify fails (jest), add feedback attempt 1, (2) verify fails (ruff), add feedback attempt 2, (3) build_feedback_context includes BOTH failures. Verify no duplication.
  - [x] 6.4 GREEN: Ensure multi-cycle accumulation works end-to-end.
  - [x] 6.5 REFACTOR: Clean up integration tests, verify all scenarios covered.

- [x] Task 7: Verify full integration and quality gates (AC: #5)
  - [x] 7.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 7.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 7.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 3.2)

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

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`.

**engine/executor.py** has 8 functions: `_resolve_step_function`, `run_step`, `_run_step_with_retry`, `_resolve_input_from`, `_should_skip_step`, `_record_failure`, `_finalize_workflow`, `run_workflow`. `_STEP_REGISTRY` has 6 entries.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants), `load_workflow()`, `list_workflows()`, 5 registered workflows (implement_close, implement_verify_close, convert_stories_to_beads, verify, sample). `_REGISTRY` dict maps names to workflows.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 251 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: VerifyFeedback Data Type

New frozen dataclass in `adws/adw_modules/types.py`:

```python
@dataclass(frozen=True)
class VerifyFeedback:
    """Structured feedback from a failed verify attempt.

    Captures which tool failed, what errors occurred, and which
    attempt this represents. Used for accumulation across
    verify-implement retry cycles (FR16, FR17).
    """

    tool_name: str
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""
    attempt: int = 1
    step_name: str = ""
```

Fields:
- `tool_name`: Which verify tool failed ("jest", "playwright", "mypy", "ruff")
- `errors`: Parsed error messages from the tool output (from VerifyResult.errors via PipelineError.context)
- `raw_output`: Full raw output for debugging (from VerifyResult.raw_output via PipelineError.context)
- `attempt`: Which retry cycle produced this feedback (1-indexed)
- `step_name`: The step that produced this failure (e.g., "run_jest_step")

This type bridges the gap between the verify pipeline (Story 3.2) which produces `PipelineError` with verify context, and the implementation retry (Epic 4) which needs structured feedback. The `VerifyFeedback` is the structured intermediate format that accumulates in `WorkflowContext.feedback`.

### Design: Feedback Flow Architecture

The feedback accumulation connects three existing components:

```
Verify Workflow (Story 3.2)        Feedback Accumulation (This Story)        Implement Retry (Epic 4)

  run_jest_step fails              accumulate_verify_feedback()               build_feedback_context()
  -> PipelineError(                  -> VerifyFeedback(                         -> "Attempt 1:
       step_name="run_jest_step",         tool_name="jest",                        jest failed:
       error_type="VerifyFailed",         errors=["FAIL ..."],                     - FAIL src/...
       context={                          raw_output="...",                         Attempt 2:
         "tool_name": "jest",             attempt=1,                               ruff failed:
         "errors": ["FAIL ..."],          step_name="run_jest_step",               - E501 ..."
         "raw_output": "..."              )
       }                              -> ctx.add_feedback(str(feedback))
     )
```

**Key design decisions:**

1. **VerifyFeedback is a pure data type** -- no I/O, no ROP. It is constructed from PipelineError data and serialized to a string for `ctx.feedback` storage.

2. **Feedback stored as strings in ctx.feedback** -- the existing `WorkflowContext.feedback` is `list[str]`. The `VerifyFeedback` is serialized to a structured string format that `build_feedback_context` can parse. This avoids changing the `WorkflowContext` type from Epic 2.

3. **Structured string format** -- each feedback entry in `ctx.feedback` is a structured string (not JSON, not arbitrary text) that includes tool_name, errors, attempt, and step_name. The format is designed to be human-readable (for implementation agent consumption) and machine-parseable (for `build_feedback_context`).

4. **Serialization approach** -- `VerifyFeedback` instances are serialized to a delimited string format: `VERIFY_FEEDBACK|tool=<name>|attempt=<n>|step=<step>|errors=<err1>;;<err2>|raw=<output>`. This preserves structure while fitting into the `list[str]` feedback container. The `build_feedback_context` function can parse these entries back and format them for the agent.

5. **Pure functions, no io_ops needed** -- all feedback accumulation functions are pure logic (no I/O). They do NOT go through io_ops. They ARE step-level helpers that operate on WorkflowContext and PipelineError data. This means they do not follow the io_ops pattern and do not need io_ops mocking in tests.

### Design: accumulate_verify_feedback()

```python
def accumulate_verify_feedback(
    error: PipelineError,
    attempt: int,
) -> VerifyFeedback:
    """Extract structured feedback from a verify step failure.

    Parses PipelineError.context for tool_name, errors, raw_output.
    Falls back to PipelineError fields when context keys are missing.
    Works for both VerifyFailed errors and other error types.
    """
```

This function bridges PipelineError (from verify steps) to VerifyFeedback (for accumulation). It is a pure function -- no I/O, no IOResult return. It extracts data from PipelineError.context which is populated by verify steps (Story 3.2) with keys: `tool_name`, `errors`, `raw_output`.

### Design: build_feedback_context()

```python
def build_feedback_context(ctx: WorkflowContext) -> str:
    """Format accumulated feedback as structured context for retry.

    Reads ctx.feedback entries, parses VerifyFeedback entries,
    and produces a human-readable + agent-consumable summary.
    Non-VerifyFeedback entries are included as-is.
    """
```

This function produces the explicit context that FR17 requires: "the full feedback history is available as explicit context." The output is a formatted string that an implementation agent can read to understand what failed and why across all previous attempts.

Example output:
```
## Previous Verify Failures

### Attempt 1
- **jest** (step: run_jest_step) -- 1 error(s):
  - FAIL src/tests/popup.test.ts

### Attempt 2
- **ruff** (step: run_ruff_step) -- 2 error(s):
  - adws/adw_modules/types.py:10:1: E501 Line too long
  - adws/adw_modules/io_ops.py:5:1: F401 `os` imported but unused
```

This format is optimized for agent consumption -- it is structured enough for an AI implementation agent to parse and act on, while also being human-readable for debugging.

### Design: add_verify_feedback_to_context()

```python
def add_verify_feedback_to_context(
    ctx: WorkflowContext,
    error: PipelineError,
    attempt: int,
) -> WorkflowContext:
    """Accumulate a verify failure as feedback in context.

    Creates VerifyFeedback from the error, serializes it,
    and appends to ctx.feedback via add_feedback().
    Returns new WorkflowContext (immutable update).
    """
```

This is the entry point for the feedback accumulation flow. It combines `accumulate_verify_feedback` + serialization + `ctx.add_feedback()`. It is NOT a standard step function (it takes additional parameters beyond just `ctx`), so it does NOT follow the `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` step signature. Instead, it is a helper function used by the engine or workflow orchestration code.

### Design: Why Not a Standard Step Function?

The feedback accumulation functions are NOT standard pipeline step functions because:

1. `accumulate_verify_feedback` takes a `PipelineError` + `int`, not just `WorkflowContext`
2. `build_feedback_context` returns a `str`, not `IOResult[WorkflowContext, PipelineError]`
3. `add_verify_feedback_to_context` takes extra parameters beyond `WorkflowContext`

These are **utility functions** used by the engine/orchestration layer (specifically the `with_verification` combinator or the implement_verify_close workflow in Epic 4). They operate on domain data types, not I/O, so they return direct values, not IOResult.

However, they live in `adws/adw_modules/steps/` because they are step-adjacent logic that participates in the pipeline data flow. They follow the step creation checklist minus the io_ops dependency (since they are pure functions).

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/test_types.py` -- add VerifyFeedback tests (extend existing file)
- `adws/tests/adw_modules/steps/test_accumulate_verify_feedback.py` -- accumulate function tests
- `adws/tests/adw_modules/steps/test_build_feedback_context.py` -- build function tests
- `adws/tests/adw_modules/steps/test_add_verify_feedback.py` -- add function tests
- `adws/tests/integration/test_feedback_accumulation.py` -- integration tests for full verify-implement retry cycle

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_accumulate_verify_feedback_from_verify_failed_error`
- `test_accumulate_verify_feedback_missing_context_keys`
- `test_build_feedback_context_single_attempt`
- `test_build_feedback_context_multi_attempt`
- `test_build_feedback_context_empty_feedback`
- `test_add_verify_feedback_appends_to_existing`
- `test_feedback_cycle_single_failure_integration`
- `test_feedback_cycle_multi_attempt_integration`

**No mock targets needed** -- all feedback accumulation functions are pure logic. Tests construct PipelineError and WorkflowContext instances directly, no mocking required. Integration tests mock `_STEP_REGISTRY` to simulate the verify workflow execution, same as Story 3.2.

**For accumulate_verify_feedback, test 3 paths:**
1. **VerifyFailed with full context**: PipelineError has error_type="VerifyFailed" and complete context (tool_name, errors, raw_output). Verify VerifyFeedback has all fields populated.
2. **Missing context keys**: PipelineError has error_type="VerifyFailed" but context is missing some keys. Verify fallback behavior (step_name from error, "unknown" tool, empty errors).
3. **Non-verify error**: PipelineError has different error_type (e.g., "TimeoutError"). Verify still produces valid VerifyFeedback from available data.

**For build_feedback_context, test 4 paths:**
1. **Empty feedback**: No feedback entries. Returns "no previous failures" message.
2. **Single attempt**: One VerifyFeedback entry. Output includes tool name, errors, attempt number.
3. **Multi-attempt**: Multiple entries from different attempts. Output includes all attempts in order, no duplication.
4. **Mixed entries**: Feedback list contains both VerifyFeedback serialized strings and plain retry feedback strings (from engine retry logic). Both are included.

**For add_verify_feedback_to_context, test 3 paths:**
1. **Empty initial feedback**: ctx.feedback is empty. After call, has exactly 1 entry.
2. **Existing feedback**: ctx.feedback has prior entries. After call, has prior entries + 1 new entry. Prior entries preserved.
3. **Sequential calls**: Call twice with different errors/attempts. All entries preserved in order.

**Integration tests:**
- Simulate full verify-implement retry cycle with mocked step registry
- Verify feedback flows correctly from verify failure -> accumulation -> retry context

### Ruff Considerations

- `FBT001`/`FBT002` (boolean positional): Not applicable -- no boolean params in feedback functions.
- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files. Attempt numbers 1, 2 are fine in tests.
- `E501` (line too long): Keep all lines under 88 characters.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- pure functions, no raises.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Feedback functions are PURE -- no I/O at all.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **FR16**: Structured feedback accumulated in `WorkflowContext.feedback` from failed verify attempts.
- **FR17**: Full feedback history passed as explicit context to subsequent implement retries via `build_feedback_context`.

### What NOT to Do

- Do NOT create the `/implement` command or implement_verify_close workflow -- that is Epic 4. This story only provides the feedback accumulation utilities.
- Do NOT modify the engine executor or `_run_step_with_retry` -- the existing retry logic handles step-level retries. This story's feedback is for WORKFLOW-level retry (verify-implement cycles), not step-level retry.
- Do NOT change `WorkflowContext` structure -- use the existing `feedback: list[str]` field with serialized VerifyFeedback strings.
- Do NOT change any verify steps from Story 3.2 -- the PipelineError structure they produce is already correct.
- Do NOT add io_ops functions -- all feedback functions are pure logic.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `add_feedback()` or `with_updates()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT create standard step functions (with `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` signature) for the feedback utilities -- they take extra parameters and return non-IOResult types.
- Do NOT change the verify workflow or verify step functions -- they already produce the correct PipelineError structure.
- Do NOT add feedback functions to `_STEP_REGISTRY` in executor.py -- they are NOT standard step functions and cannot be dispatched by the engine.
- Do NOT use JSON serialization for feedback entries -- use a structured string format that is both human-readable and parseable.
- Do NOT prematurely integrate with the implement_verify_close workflow -- that integration happens in Epic 4 (Story 4.8). This story provides the building blocks only.

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/accumulate_verify_feedback.py` -- pure function to extract VerifyFeedback from PipelineError
- `adws/adw_modules/steps/build_feedback_context.py` -- pure function to format accumulated feedback for agent consumption
- `adws/adw_modules/steps/add_verify_feedback.py` -- helper to append VerifyFeedback to WorkflowContext.feedback
- `adws/tests/adw_modules/steps/test_accumulate_verify_feedback.py` -- accumulate function tests
- `adws/tests/adw_modules/steps/test_build_feedback_context.py` -- build function tests
- `adws/tests/adw_modules/steps/test_add_verify_feedback.py` -- add function tests
- `adws/tests/integration/test_feedback_accumulation.py` -- integration tests for verify-implement cycle

Files to modify:
- `adws/adw_modules/types.py` -- add `VerifyFeedback` frozen dataclass
- `adws/adw_modules/steps/__init__.py` -- add exports for feedback functions
- `adws/tests/adw_modules/test_types.py` -- add VerifyFeedback tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3] -- AC and story definition (FR16, FR17)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] -- Epic summary: "Failed verify attempts accumulate feedback that flows into subsequent retry context."
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK Integration Design, io_ops boundary pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, with_verification combinator retry loop, accumulated feedback
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- WorkflowContext update pattern, step-to-step communication via context
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow Through TDD Workflow] -- Shows ctx.feedback accumulation in verify_tests_pass retry loop
- [Source: _bmad-output/planning-artifacts/architecture.md#Step 5 -- Communication Patterns] -- "Steps communicate exclusively through WorkflowContext"
- [Source: _bmad-output/planning-artifacts/architecture.md#Quality Verification (FR12-17)] -- FR16 (accumulate feedback), FR17 (pass to retries)
- [Source: adws/adw_modules/types.py] -- WorkflowContext (with add_feedback(), feedback: list[str]), VerifyResult
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass (step_name, error_type, message, context)
- [Source: adws/adw_modules/steps/run_jest_step.py] -- Verify step pattern producing PipelineError with context={tool_name, errors, raw_output}
- [Source: adws/adw_modules/engine/executor.py] -- _run_step_with_retry uses ctx.add_feedback() for step-level retry messages
- [Source: adws/adw_modules/engine/combinators.py] -- with_verification combinator (future consumer in Epic 4)
- [Source: adws/workflows/__init__.py] -- _VERIFY workflow definition with always_run steps
- [Source: adws/tests/conftest.py] -- Shared fixtures (sample_workflow_context, mock_io_ops)
- [Source: _bmad-output/implementation-artifacts/3-2-verify-pipeline-steps-and-quality-gate-workflow.md] -- Previous story: verify step modules produce PipelineError with VerifyFailed error_type and context keys (tool_name, errors, raw_output)
- [Source: _bmad-output/implementation-artifacts/3-1-verify-io-ops-shell-functions.md] -- VerifyResult data type, io_ops verify functions, _build_verify_result shared helper

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

From Story 3.2 learnings:
- **Verify step PipelineError structure**: Steps produce `PipelineError(step_name="run_<tool>_step", error_type="VerifyFailed", context={"tool_name": ..., "errors": [...], "raw_output": ...})`. This is the input contract for `accumulate_verify_feedback`.
- **always_run failure tracking**: `always_run_failures` in run_workflow tracks multi-step failures. The verify workflow uses always_run=True on all steps, so failures from multiple tools are captured in the `always_run_failures` list.
- **_STEP_REGISTRY mocking**: Tests mock `adws.adw_modules.engine.executor._STEP_REGISTRY` directly. Integration tests for feedback cycle can reuse this pattern.
- **Test count at Story 3.2 completion**: 251 tests (excluding 2 enemy), 100% line+branch coverage.

From Story 3.1 learnings:
- **VerifyResult**: Frozen dataclass with `tool_name`, `passed`, `errors` (default_factory=list), `raw_output` (default="").
- **bind pattern**: All verify functions use `result.bind(_handle_result)`. IOFailure propagation is automatic via bind.
- **Nonzero exit is NOT IOFailure in io_ops**: io_ops returns IOSuccess(VerifyResult(passed=False)) for tool failures. Steps convert to IOFailure(PipelineError).

From Story 2.5 learnings:
- **ctx.add_feedback()**: Already exists on WorkflowContext. Returns new context with feedback entry appended. Used by `_run_step_with_retry` for step-level retry feedback.
- **pipeline_failure tracking**: run_workflow tracks via `pipeline_failure: PipelineError | None`.
- **always_run_failures**: List of dicts from failed always_run steps. Attached to final PipelineError context.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Relationship to Epic 4

This story provides the **building blocks** for feedback accumulation. The **integration** with the implement_verify_close workflow happens in Epic 4 (specifically Story 4.8). The flow will be:

1. This story: `accumulate_verify_feedback` + `build_feedback_context` + `add_verify_feedback_to_context`
2. Story 4.7 (implement step): The implement step receives `build_feedback_context(ctx)` output as part of the agent prompt context
3. Story 4.8 (implement_verify_close workflow): The workflow orchestration calls `add_verify_feedback_to_context` after verify failures and before implement retries

This story is self-contained and testable without Epic 4 code. Integration tests use mocked step functions to simulate the workflow-level retry cycle.

### No Engine Changes Required

The existing engine executor already supports feedback accumulation at the step level via `_run_step_with_retry` calling `ctx.add_feedback()`. This story operates at the WORKFLOW level -- accumulating feedback across verify-implement cycles, not within a single step's retry loop. No engine changes are needed.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- All 7 tasks completed with strict TDD (Red-Green-Refactor)
- 25 new tests added (276 total, up from 251)
- 100% line + branch coverage maintained
- mypy strict: 0 issues across 47 source files
- ruff: all checks passed, zero violations
- All feedback functions are pure (no I/O, no io_ops dependency)
- VerifyFeedback serialized as structured strings in ctx.feedback (no JSON, no WorkflowContext changes)
- Serialization format: `VERIFY_FEEDBACK|tool=<name>|attempt=<n>|step=<step>|errors=<err1>;;<err2>|raw=<output>`
- Integration tests verify full verify-implement retry cycle with mocked step registry
- TC001 import guard applied where appropriate (PipelineError in TYPE_CHECKING for annotation-only usage)

### File List

Files created:
- `adws/adw_modules/steps/accumulate_verify_feedback.py` -- pure function: PipelineError -> VerifyFeedback
- `adws/adw_modules/steps/build_feedback_context.py` -- pure function: WorkflowContext -> formatted feedback string
- `adws/adw_modules/steps/add_verify_feedback.py` -- helper: serialize + append VerifyFeedback to ctx.feedback
- `adws/tests/adw_modules/steps/test_accumulate_verify_feedback.py` -- 4 tests (3 paths + import test)
- `adws/tests/adw_modules/steps/test_build_feedback_context.py` -- 9 tests (single, empty, multi, idempotent, mixed, same-attempt, empty errors, whitespace, malformed + import test)
- `adws/tests/adw_modules/steps/test_add_verify_feedback.py` -- 4 tests (empty, existing, sequential + import test)
- `adws/tests/integration/__init__.py` -- integration test package init
- `adws/tests/integration/test_feedback_accumulation.py` -- 2 integration tests (single-cycle, multi-cycle)

Files modified:
- `adws/adw_modules/types.py` -- added VerifyFeedback frozen dataclass
- `adws/adw_modules/steps/__init__.py` -- added feedback function exports (alphabetically sorted)
- `adws/tests/adw_modules/test_types.py` -- added 5 VerifyFeedback tests

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial code review)
**Date**: 2026-02-02
**Verdict**: PASS (after 3 fixes applied)

### Issues Found: 3

#### Issue 1 -- HIGH: Pipe delimiter injection in serialization

**Files**: `adws/adw_modules/steps/add_verify_feedback.py`, `adws/adw_modules/steps/build_feedback_context.py`

`_serialize_feedback` used `|` as the field delimiter but did NOT escape `|` in field values (tool_name, errors, step_name, raw_output). Real-world tool output (jest, ruff, mypy, playwright) regularly contains pipe characters. The `_parse_feedback_entry` parser splits on `|` first, so any pipe in any field value corrupted the parse, silently losing data from real verify failures.

**Fix**: Added `_escape_field()` that escapes `|` to `\x7C` in all fields except `raw` (which is always last). Added `_unescape_field()` in the parser. Made `raw` the terminal field so it can contain unescaped pipes -- the parser extracts it via `body.find("|raw=")` before splitting the rest on `|`.

#### Issue 2 -- HIGH: Error delimiter injection in serialization

**Files**: `adws/adw_modules/steps/add_verify_feedback.py`, `adws/adw_modules/steps/build_feedback_context.py`

`_serialize_feedback` joined errors with `;;` but did NOT escape `;;` in individual error messages. If any error message contained the literal `;;`, the round-trip produced more errors than were serialized, corrupting feedback for the implementation agent.

**Fix**: `_escape_field()` also escapes `;;` to `\x3B\x3B`. In the parser, `_parse_errors()` splits on `;;` first, then unescapes each individual error string -- ordering matters because the unescape must happen AFTER the delimiter split, not before.

#### Issue 3 -- MEDIUM: Error count mismatch in `_format_entry`

**File**: `adws/adw_modules/steps/build_feedback_context.py`

The error count displayed (`{error_count} error(s)`) was calculated via `len(errors)` which counted all items from `split(";;")` including empty strings. But the bullet list filtered out whitespace-only errors. This meant the count could say "3 error(s)" while only showing 2 bullets, confusing the agent.

**Fix**: Extracted `_parse_errors()` helper that filters whitespace-only entries BEFORE counting. `_format_entry` now uses filtered errors for both count and display.

### Tests Added: 7

- `test_parse_feedback_entry_missing_raw_field` -- covers no-`|raw=` branch (was uncovered)
- `test_parse_feedback_pipe_in_raw_preserved` -- pipe in raw_output survives parse
- `test_unescape_field_reverses_escaping` -- unescape restores `|` and `;;`
- `test_parse_errors_unescapes_items` -- per-item unescape after `;;` split
- `test_parse_errors_empty_string` -- empty input returns empty list
- `test_escape_field_escapes_pipe_and_semicolons` -- escape correctness
- `test_serialize_round_trip_with_pipes_in_raw` -- end-to-end serialize/parse with pipes

### Quality Gates (Post-Fix)

- **pytest**: 283 passed, 2 skipped (enemy), 100% line + branch coverage
- **mypy --strict**: 0 issues in 47 source files
- **ruff check**: All checks passed, zero violations

### AC Verification

1. AC#1 (structured feedback): PASS -- `accumulate_verify_feedback` extracts tool_name, errors, raw_output, attempt, step_name from PipelineError into VerifyFeedback. Now resilient to special characters in field values.
2. AC#2 (full history as context): PASS -- `build_feedback_context` formats all feedback entries chronologically. `raw` field now correctly preserved even with pipe characters.
3. AC#3 (no duplication, attempt numbering): PASS -- each cycle adds new entries, attempt headers deduplicated. Tests verify `count("### Attempt N") == 1`.
4. AC#4 (test coverage): PASS -- 283 tests, 100% line + branch coverage, all scenarios covered including delimiter injection edge cases.
5. AC#5 (quality gates): PASS -- pytest 100%, mypy strict clean, ruff zero violations.

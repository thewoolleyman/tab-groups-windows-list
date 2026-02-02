# Story 4.6: verify_tests_fail Step (RED Gate)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want a RED gate that confirms tests fail for the right expected reason,
so that broken tests (SyntaxError) are caught before proceeding to implementation.

## Acceptance Criteria

1. **Given** tests written by the `write_failing_tests` step, **When** `verify_tests_fail` executes as a shell step, **Then** it runs the test suite and confirms tests fail.

2. **Given** tests fail with valid failure types, **When** the step evaluates failure reasons, **Then** `ImportError` and `AssertionError` are accepted as valid RED failures **And** the step succeeds, allowing progression to GREEN phase.

3. **Given** tests fail with invalid failure types, **When** the step evaluates failure reasons, **Then** `SyntaxError` is rejected as a broken test (not a valid RED failure) **And** the step fails with a PipelineError explaining the tests are broken, not correctly RED.

4. **Given** tests unexpectedly pass, **When** the step evaluates results, **Then** the step fails with a PipelineError explaining tests should fail in RED phase.

5. **Given** `verify_tests_fail` code, **When** I run tests, **Then** tests cover: valid failure (ImportError), valid failure (AssertionError), invalid failure (SyntaxError), unexpected pass **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Define valid and invalid failure type constants (AC: #2, #3)
  - [x] 1.1 RED: Write test for `VALID_RED_FAILURES` constant in `adws/adw_modules/steps/verify_tests_fail.py`. Verify it is a `frozenset[str]` containing at least `"ImportError"`, `"AssertionError"`, `"NotImplementedError"`, and `"AttributeError"`. These are the expected failure types per the RED_PHASE_SYSTEM_PROMPT in `write_failing_tests.py`.
  - [x] 1.2 GREEN: Implement `VALID_RED_FAILURES` as a module-level `frozenset` in `adws/adw_modules/steps/verify_tests_fail.py`.
  - [x] 1.3 RED: Write test for `INVALID_RED_FAILURES` constant. Verify it is a `frozenset[str]` containing at least `"SyntaxError"`, `"IndentationError"`, and `"NameError"`. These indicate broken test code, not valid RED failures.
  - [x] 1.4 GREEN: Implement `INVALID_RED_FAILURES` as a module-level `frozenset`.
  - [x] 1.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `_parse_pytest_output()` pure helper function (AC: #1, #2, #3, #4)
  - [x] 2.1 RED: Write test for `_parse_pytest_output(stdout: str, stderr: str) -> ParsedTestResult`. Given pytest output with `1 failed` in the summary line and `ImportError` in the traceback, verify it returns a `ParsedTestResult` with `tests_ran=True`, `all_passed=False`, `failure_types={"ImportError"}`, `failure_count=1`. `ParsedTestResult` is a frozen dataclass with fields: `tests_ran` (bool), `all_passed` (bool), `failure_types` (frozenset[str]), `failure_count` (int), `raw_output` (str).
  - [x] 2.2 GREEN: Implement `ParsedTestResult` frozen dataclass and `_parse_pytest_output` in `adws/adw_modules/steps/verify_tests_fail.py`. Uses regex to parse pytest summary line and extract error class names from traceback lines.
  - [x] 2.3 RED: Write test for `_parse_pytest_output` with output containing multiple failure types (both `AssertionError` and `ImportError` in different tests). Verify `failure_types` is `{"AssertionError", "ImportError"}`.
  - [x] 2.4 GREEN: Implement multi-failure-type extraction.
  - [x] 2.5 RED: Write test for `_parse_pytest_output` with output showing all tests passed (`0 failed` or no `failed` in summary, nonzero `passed` count). Verify `all_passed=True`, `failure_types=frozenset()`, `failure_count=0`.
  - [x] 2.6 GREEN: Implement all-passed detection.
  - [x] 2.7 RED: Write test for `_parse_pytest_output` with output containing `SyntaxError` in the traceback (collection-phase error, not a test failure). Verify `failure_types={"SyntaxError"}`. Note: pytest treats SyntaxError as a collection error -- the test does not even run.
  - [x] 2.8 GREEN: Implement SyntaxError extraction from collection errors.
  - [x] 2.9 RED: Write test for `_parse_pytest_output` with output showing `no tests ran` (empty test suite or all deselected). Verify `tests_ran=False`.
  - [x] 2.10 GREEN: Implement no-tests-ran detection.
  - [x] 2.11 RED: Write test for `_parse_pytest_output` with empty stdout and stderr. Verify `tests_ran=False`, `all_passed=False`, `failure_types=frozenset()`, `failure_count=0`.
  - [x] 2.12 GREEN: Implement empty output handling.
  - [x] 2.13 RED: Write test for `_parse_pytest_output` with `NotImplementedError` in traceback. Verify it appears in `failure_types`.
  - [x] 2.14 GREEN: Implement NotImplementedError extraction (should already work from general pattern).
  - [x] 2.15 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create `_classify_failures()` pure helper function (AC: #2, #3)
  - [x] 3.1 RED: Write test for `_classify_failures(parsed: ParsedTestResult) -> FailureClassification`. Given a `ParsedTestResult` with `failure_types={"ImportError"}`, verify it returns a `FailureClassification` with `is_valid_red=True`, `invalid_types=frozenset()`, `valid_types={"ImportError"}`. `FailureClassification` is a frozen dataclass with fields: `is_valid_red` (bool), `valid_types` (frozenset[str]), `invalid_types` (frozenset[str]).
  - [x] 3.2 GREEN: Implement `FailureClassification` frozen dataclass and `_classify_failures`.
  - [x] 3.3 RED: Write test for `_classify_failures` with `failure_types={"SyntaxError"}`. Verify `is_valid_red=False`, `invalid_types={"SyntaxError"}`, `valid_types=frozenset()`.
  - [x] 3.4 GREEN: Implement invalid type detection.
  - [x] 3.5 RED: Write test for `_classify_failures` with mixed types `{"ImportError", "SyntaxError"}`. Verify `is_valid_red=False` (any invalid type makes the whole classification invalid), `invalid_types={"SyntaxError"}`, `valid_types={"ImportError"}`.
  - [x] 3.6 GREEN: Implement mixed-type classification -- any invalid type means not valid RED.
  - [x] 3.7 RED: Write test for `_classify_failures` with `failure_types={"AssertionError", "NotImplementedError"}`. Verify `is_valid_red=True`, `valid_types={"AssertionError", "NotImplementedError"}`, `invalid_types=frozenset()`.
  - [x] 3.8 GREEN: Implement multi-valid-type classification.
  - [x] 3.9 RED: Write test for `_classify_failures` with an unknown failure type (e.g., `"RuntimeError"`) that is in neither VALID nor INVALID sets. Verify `is_valid_red=True` -- unknown types are treated as valid (conservative: only explicitly invalid types are rejected). `valid_types` should include `"RuntimeError"` and `invalid_types=frozenset()`.
  - [x] 3.10 GREEN: Implement unknown-type handling (default to valid).
  - [x] 3.11 RED: Write test for `_classify_failures` with empty `failure_types=frozenset()`. Verify `is_valid_red=True`, both sets empty (no failures = no invalid failures).
  - [x] 3.12 GREEN: Implement empty failure types handling.
  - [x] 3.13 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create `verify_tests_fail()` step function (AC: #1, #2, #3, #4)
  - [x] 4.1 RED: Write test for `verify_tests_fail(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `io_ops.run_shell_command` returns a `ShellResult` with `return_code=1` (tests failed) and stdout containing `ImportError` tracebacks, verify it returns `IOSuccess(WorkflowContext)` with `outputs` containing `{"red_gate_passed": True, "failure_types": ["ImportError"], "failure_count": N}`.
  - [x] 4.2 GREEN: Implement `verify_tests_fail` in `adws/adw_modules/steps/verify_tests_fail.py`. Calls `io_ops.run_shell_command` with the pytest command, parses output via `_parse_pytest_output`, classifies via `_classify_failures`, returns IOSuccess when classification is valid RED.
  - [x] 4.3 RED: Write test for `verify_tests_fail` when tests unexpectedly pass (return_code=0, `all_passed=True`). Verify it returns `IOFailure(PipelineError)` with `step_name="verify_tests_fail"`, `error_type="TestsPassedInRedPhase"`, and a message explaining tests should fail in RED phase.
  - [x] 4.4 GREEN: Implement unexpected-pass failure path.
  - [x] 4.5 RED: Write test for `verify_tests_fail` when tests fail with `SyntaxError` (invalid failure). Verify it returns `IOFailure(PipelineError)` with `error_type="InvalidRedFailure"` and a message listing the invalid types and explaining the tests are broken.
  - [x] 4.6 GREEN: Implement invalid-failure-type detection path.
  - [x] 4.7 RED: Write test for `verify_tests_fail` when `io_ops.run_shell_command` returns `IOFailure(PipelineError)` (shell execution itself failed, e.g., pytest not found). Verify it returns `IOFailure(PipelineError)` with `step_name="verify_tests_fail"` and `error_type` preserved from the io_ops error.
  - [x] 4.8 GREEN: Implement shell command failure handling using `.lash()` for re-attribution.
  - [x] 4.9 RED: Write test for `verify_tests_fail` when tests fail with mixed valid and invalid types (e.g., `{"ImportError", "SyntaxError"}`). Verify it returns `IOFailure(PipelineError)` with `error_type="InvalidRedFailure"` -- any invalid type fails the gate.
  - [x] 4.10 GREEN: Implement mixed-type failure path.
  - [x] 4.11 RED: Write test for `verify_tests_fail` when no tests ran (`tests_ran=False`). Verify it returns `IOFailure(PipelineError)` with `error_type="NoTestsRan"` and a message explaining no tests were discovered.
  - [x] 4.12 GREEN: Implement no-tests-ran failure path.
  - [x] 4.13 RED: Write test for `verify_tests_fail` with `AssertionError` failures. Verify `IOSuccess` with `failure_types` containing `"AssertionError"`.
  - [x] 4.14 GREEN: Ensure AssertionError path works (should already work from general implementation).
  - [x] 4.15 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Define the pytest command for the RED gate (AC: #1)
  - [x] 5.1 RED: Write test for `RED_GATE_PYTEST_COMMAND` constant in `verify_tests_fail.py`. Verify it is a string containing `"uv run pytest"` and `"-m 'not enemy'"`. The command runs the test suite excluding enemy tests.
  - [x] 5.2 GREEN: Implement `RED_GATE_PYTEST_COMMAND` as a module-level constant. The command should be: `"uv run pytest adws/tests/ -m 'not enemy' --no-header -q"`. The `--no-header -q` flags produce compact output that is easier to parse.
  - [x] 5.3 RED: Write test that `verify_tests_fail` passes the correct command to `io_ops.run_shell_command`. Mock `run_shell_command` and verify it was called with `RED_GATE_PYTEST_COMMAND`.
  - [x] 5.4 GREEN: Ensure `verify_tests_fail` uses `RED_GATE_PYTEST_COMMAND` in the shell call.
  - [x] 5.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Register `verify_tests_fail` in step infrastructure (AC: #1)
  - [x] 6.1 RED: Write test that `verify_tests_fail` is importable from `adws.adw_modules.steps` (via `steps/__init__.py`).
  - [x] 6.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x] 6.3 RED: Write test that `_STEP_REGISTRY` in `engine/executor.py` contains `"verify_tests_fail"` mapped to the correct function.
  - [x] 6.4 GREEN: Add `"verify_tests_fail"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x] 6.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 7: Integration test -- full verify_tests_fail step flow (AC: #1, #2, #3, #4, #5)
  - [x] 7.1 RED: Write integration test: invoke `verify_tests_fail` with a WorkflowContext. Mock `io_ops.run_shell_command` to return `IOSuccess(ShellResult(return_code=1, stdout=<pytest output with ImportError tracebacks>, ...))`. Verify: IOSuccess returned, outputs contain `red_gate_passed=True`, `failure_types` includes `"ImportError"`, the correct pytest command was invoked.
  - [x] 7.2 GREEN: Ensure integration path works end-to-end with mocked io_ops.
  - [x] 7.3 RED: Write integration test: mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=0, stdout=<all tests passed output>, ...))`. Verify IOFailure with `error_type="TestsPassedInRedPhase"`.
  - [x] 7.4 GREEN: Ensure unexpected-pass integration path works correctly.
  - [x] 7.5 RED: Write integration test: mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=1, stdout=<output with SyntaxError>, ...))`. Verify IOFailure with `error_type="InvalidRedFailure"` and message containing "SyntaxError".
  - [x] 7.6 GREEN: Ensure invalid-failure integration path works correctly.
  - [x] 7.7 RED: Write integration test: mock `run_shell_command` to return `IOFailure(PipelineError(...))` simulating pytest command not found. Verify IOFailure propagates with `step_name="verify_tests_fail"`.
  - [x] 7.8 GREEN: Ensure shell failure integration path works correctly.
  - [x] 7.9 RED: Write integration test: mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=5, stdout="no tests ran", ...))`. Verify IOFailure with `error_type="NoTestsRan"`. Note: pytest exit code 5 means no tests were collected.
  - [x] 7.10 GREEN: Ensure no-tests-ran integration path works correctly.
  - [x] 7.11 REFACTOR: Clean up integration tests, verify all scenarios covered.

- [x] Task 8: Verify full integration and quality gates (AC: #6)
  - [x] 8.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 8.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 8.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 4.5)

**io_ops.py** has 16 public functions + 2 private helpers + 1 async helper + 1 internal exception:
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
def read_prime_file(path: str) -> IOResult[str, PipelineError]: ...
def get_directory_tree(root: str, *, max_depth: int = 3) -> IOResult[str, PipelineError]: ...
def load_command_workflow(workflow_name: str) -> IOResult[Workflow, PipelineError]: ...
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError, _find_project_root(), _build_tree_lines()
```

**types.py** has: `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**commands/** package has:
- `types.py` -- `CommandSpec` frozen dataclass
- `registry.py` -- `COMMAND_REGISTRY` (MappingProxyType, 6 commands), `get_command()`, `list_commands()`
- `dispatch.py` -- `run_command()` with verify, prime, build specialized handlers
- `verify.py` -- `VerifyCommandResult`, `run_verify_command()`
- `prime.py` -- `PrimeContextResult`, `PrimeFileSpec`, `run_prime_command()`
- `build.py` -- `BuildCommandResult`, `_build_failure_metadata`, `_finalize_on_success`, `_finalize_on_failure`, `run_build_command()`
- `__init__.py` -- exports all command types and functions

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`, `write_failing_tests`.

**engine/executor.py** has 8 functions. `_STEP_REGISTRY` has 7 entries: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `write_failing_tests`.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants), `load_workflow()`, `list_workflows()`, 5 registered workflows. `_IMPLEMENT_VERIFY_CLOSE` currently has empty steps list (placeholder for Story 4.8).

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 450 tests (excluding 3 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: verify_tests_fail Step Architecture

This is the second step in the `implement_verify_close` TDD workflow (Decision 6). It acts as the RED gate -- confirming that tests written by `write_failing_tests` actually fail for expected reasons before implementation begins. It is a shell step that runs pytest and analyzes the output.

```
write_failing_tests outputs (ctx.inputs after promote_outputs_to_inputs)
    |
    v
verify_tests_fail (shell step -- RED gate)
    |
    v (calls io_ops.run_shell_command with pytest)
    |
    v (parses pytest output for failure types)
    |
    v (classifies: valid RED vs broken test)
    |
    v
IOSuccess: WorkflowContext.outputs = {"red_gate_passed": True, "failure_types": [...], ...}
    -- OR --
IOFailure: PipelineError with error_type = "TestsPassedInRedPhase" | "InvalidRedFailure" | "NoTestsRan"
```

**Key design decisions:**

1. **Step is NOT an `execute_shell_step` passthrough** -- unlike the `verify_tests_pass` shell steps in the workflows (which just check return code 0), this step needs to ANALYZE the output. It calls `io_ops.run_shell_command` directly (like `execute_shell_step` does) but interprets the result with failure-type classification logic. A nonzero exit code is the EXPECTED outcome (tests should fail in RED phase).

2. **Uses existing `io_ops.run_shell_command`** -- no new io_ops functions are needed. The step builds the pytest command, calls `run_shell_command`, and interprets the ShellResult. The `run_shell_command` function returns both stdout and stderr in the ShellResult regardless of exit code, which is exactly what this step needs for output analysis.

3. **Pure helper separation** -- the step is decomposed into:
   - `_parse_pytest_output(stdout, stderr)` -- extracts failure types from pytest output
   - `_classify_failures(parsed)` -- determines if failures are valid RED or broken
   - `verify_tests_fail(ctx)` -- orchestrates the flow: run pytest -> parse -> classify -> decide

4. **Three failure modes:**
   - `TestsPassedInRedPhase`: return_code=0, all tests passed. Tests should fail in RED phase.
   - `InvalidRedFailure`: Tests failed but with SyntaxError/IndentationError/NameError (broken test code).
   - `NoTestsRan`: No tests were collected or run (pytest exit code 5 or empty output).

5. **One success mode:**
   - Tests failed with valid types (ImportError, AssertionError, NotImplementedError, AttributeError): RED gate passes, workflow proceeds to GREEN phase.

6. **Unknown failure types are treated as valid** -- if pytest reports a failure type not in either the VALID or INVALID sets (e.g., `RuntimeError`, `ValueError`), it is treated as valid RED. Only explicitly known broken types (`SyntaxError`, `IndentationError`, `NameError`) are rejected. This is conservative: we do not want to block valid TDD patterns where a new error type is expected.

7. **No new io_ops functions** -- this step reuses `run_shell_command`. The io_ops function count stays at 16.

### Design: Pytest Output Parsing

Pytest output has structured patterns for extracting failure information:

**Failure types from tracebacks:**
```
E   ImportError: No module named 'adws.adw_modules.steps.new_step'
E   AssertionError: assert False
E   NotImplementedError
```
Pattern: Lines starting with `E   ` followed by an error class name and colon/message.

**Collection errors (SyntaxError):**
```
ERRORS
_ ERROR collecting adws/tests/test_foo.py _
adws/tests/test_foo.py:10: in <module>
    ...
E     SyntaxError: invalid syntax
```

**Summary line:**
```
1 failed, 2 passed in 0.5s
```
or
```
no tests ran
```

**Regex patterns for extraction:**
- Error types from E lines: `r'^E\s+(\w+Error)\b'` (multiline)
- Summary line failures: `r'(\d+) failed'`
- No tests ran: `r'no tests ran'`
- All passed (no failures): presence of `passed` without `failed` in summary

### Design: Failure Type Classification

The classification follows a simple rule: **any invalid type makes the entire classification invalid**.

```python
VALID_RED_FAILURES: frozenset[str] = frozenset({
    "ImportError",
    "AssertionError",
    "NotImplementedError",
    "AttributeError",
})

INVALID_RED_FAILURES: frozenset[str] = frozenset({
    "SyntaxError",
    "IndentationError",
    "NameError",
})
```

Classification logic:
1. `invalid_types = failure_types & INVALID_RED_FAILURES`
2. `valid_types = failure_types - INVALID_RED_FAILURES`
3. `is_valid_red = len(invalid_types) == 0`

Note: types not in either set (e.g., `RuntimeError`) are included in `valid_types` by this logic. This is intentional.

### Design: Context Flow

**Input context expected (from write_failing_tests via promote_outputs_to_inputs):**
```python
ctx.inputs = {
    "issue_description": "Full Beads issue description...",
    "issue_id": "BEADS-123",
    # From write_failing_tests outputs (promoted):
    "test_files": ["adws/tests/steps/test_new_step.py", ...],
    "red_phase_complete": True,
}
```

**Output context produced on success:**
```python
ctx.outputs = {
    "red_gate_passed": True,
    "failure_types": ["ImportError", ...],
    "failure_count": 3,
}
```

**Note:** The step does NOT use `ctx.inputs["test_files"]` to select which tests to run. It runs the FULL test suite (`uv run pytest adws/tests/ -m 'not enemy'`) because the RED gate validates the entire test suite state, not just the new tests. New tests may have introduced dependencies on modules that affect existing tests. The `test_files` input is available for informational purposes but does not influence the pytest command.

### Design: Pytest Exit Codes

Pytest exit codes relevant to this step:
- `0`: All tests passed (RED gate fails -- `TestsPassedInRedPhase`)
- `1`: Some tests failed (RED gate may pass or fail depending on failure types)
- `2`: Test execution interrupted by user (treat as shell failure)
- `3`: Internal error (treat as shell failure)
- `4`: pytest command line usage error (treat as shell failure)
- `5`: No tests collected (RED gate fails -- `NoTestsRan`)

Exit codes 2, 3, 4 are unlikely in automated execution but should be handled gracefully. The step treats them as test failures and parses the output for failure types. If no parseable failure types are found, the step should still succeed (the tests did fail, which is what RED expects) unless the parsed result indicates no tests ran.

**Revised decision:** Exit code 1 with valid failure types -> IOSuccess. Exit code 0 -> IOFailure(TestsPassedInRedPhase). Exit code 5 -> IOFailure(NoTestsRan). Exit codes 2-4 -> parse output; if failure types found, classify normally; if not, return IOFailure with appropriate error.

### Design: Step Registration

The step is registered in two places:
1. `steps/__init__.py` -- exported for import
2. `engine/executor.py` `_STEP_REGISTRY` -- registered for engine dispatch

After registration, the `implement_verify_close` workflow (Story 4.8) can reference it as `Step(name="verify_tests_fail", function="verify_tests_fail")`.

**NOTE:** This story does NOT update the `_IMPLEMENT_VERIFY_CLOSE` workflow definition. That is Story 4.8's responsibility. This story only creates and registers the step.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_verify_tests_fail.py` -- tests for constants, ParsedTestResult, FailureClassification, _parse_pytest_output, _classify_failures, verify_tests_fail (unit + integration)

**Modified test files**:
- Tests for `_STEP_REGISTRY` in executor tests -- verify registry contains `"verify_tests_fail"`
- `steps/__init__.py` wiring tests -- verify `verify_tests_fail` is importable from `adws.adw_modules.steps`

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_valid_red_failures_contains_import_error`
- `test_valid_red_failures_contains_assertion_error`
- `test_valid_red_failures_is_frozenset`
- `test_invalid_red_failures_contains_syntax_error`
- `test_invalid_red_failures_contains_indentation_error`
- `test_invalid_red_failures_contains_name_error`
- `test_parse_pytest_output_import_error`
- `test_parse_pytest_output_multiple_failure_types`
- `test_parse_pytest_output_all_passed`
- `test_parse_pytest_output_syntax_error`
- `test_parse_pytest_output_no_tests_ran`
- `test_parse_pytest_output_empty`
- `test_parse_pytest_output_not_implemented_error`
- `test_classify_failures_valid_import_error`
- `test_classify_failures_invalid_syntax_error`
- `test_classify_failures_mixed_types`
- `test_classify_failures_multiple_valid`
- `test_classify_failures_unknown_type`
- `test_classify_failures_empty`
- `test_verify_tests_fail_valid_red`
- `test_verify_tests_fail_tests_passed`
- `test_verify_tests_fail_invalid_failure`
- `test_verify_tests_fail_shell_failure`
- `test_verify_tests_fail_mixed_types`
- `test_verify_tests_fail_no_tests_ran`
- `test_verify_tests_fail_assertion_error`
- `test_verify_tests_fail_command_used`
- `test_verify_tests_fail_step_registry`
- `test_verify_tests_fail_importable`
- `test_red_gate_pytest_command_constant`

**Mock targets for step tests**:
- `adws.adw_modules.io_ops.run_shell_command` -- mock shell execution for unit tests

### Pytest Output Fixtures

Tests should use realistic pytest output fixtures. Example fixtures:

**Import error output:**
```
adws/tests/steps/test_new_step.py:3: in <module>
    from adws.adw_modules.steps.new_step import new_step
E   ImportError: No module named 'adws.adw_modules.steps.new_step'
ERRORS
1 error in 0.05s
```

**Assertion error output:**
```
FAILED adws/tests/steps/test_new_step.py::test_new_step_returns_success
adws/tests/steps/test_new_step.py:15: in test_new_step_returns_success
    assert result == expected
E   AssertionError: assert None == 'expected'
1 failed in 0.10s
```

**Syntax error output:**
```
ERRORS
_ ERROR collecting adws/tests/steps/test_broken.py _
adws/tests/steps/test_broken.py:5: in <module>
E     SyntaxError: invalid syntax
1 error in 0.02s
```

**All passed output:**
```
450 passed, 3 deselected in 2.50s
```

**No tests ran:**
```
no tests ran in 0.01s
```

### Ruff Considerations

- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files.
- `E501` (line too long): Keep all lines under 88 characters. Long pytest output fixture strings should use implicit string concatenation.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.
- `FBT003` (boolean positional in return): `red_gate_passed=True` in outputs dict is a dict value, not a function parameter -- no issue.
- `S604` (shell command in function call): `run_shell_command` is the io_ops boundary -- no suppression needed in the step itself (suppression is in io_ops.py).

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- `verify_tests_fail` returns IOResult, never raises.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. The step calls `io_ops.run_shell_command` for the pytest execution.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **Decision 6**: RED gate verifies test failures are expected, not broken. Shell verification step is the objective arbiter.
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Step Naming**: One public function `verify_tests_fail` matching the filename.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).

### What NOT to Do

- Do NOT implement any production code in this step -- it is the RED gate, not the GREEN phase.
- Do NOT add new io_ops functions -- reuse the existing `run_shell_command`.
- Do NOT update the `_IMPLEMENT_VERIFY_CLOSE` workflow definition -- that is Story 4.8.
- Do NOT create a command with a specialized dispatch handler -- this is a step, not a command.
- Do NOT change the verify command, prime command, or build command.
- Do NOT change any existing step functions, workflows, or engine logic.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT use `unsafe_perform_io` in production code (steps). Only use `.bind()` and `.lash()` for composing IOResult chains.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT change the engine executor (except adding to `_STEP_REGISTRY`), combinators, or any registered workflow definitions.
- Do NOT read BMAD files during workflow execution (NFR19) -- context comes from WorkflowContext, not files.
- Do NOT run specific test files -- the RED gate runs the FULL test suite (`adws/tests/ -m 'not enemy'`).
- Do NOT treat `execute_shell_step` as a reusable base -- `verify_tests_fail` has different semantics (nonzero exit = expected, output parsing required).

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/verify_tests_fail.py` -- `VALID_RED_FAILURES`, `INVALID_RED_FAILURES`, `RED_GATE_PYTEST_COMMAND`, `ParsedTestResult`, `FailureClassification`, `_parse_pytest_output()`, `_classify_failures()`, `verify_tests_fail()`
- `adws/tests/adw_modules/steps/test_verify_tests_fail.py` -- all step tests (unit + integration)

Files to modify:
- `adws/adw_modules/steps/__init__.py` -- add `verify_tests_fail` import and export
- `adws/adw_modules/engine/executor.py` -- add `"verify_tests_fail"` to `_STEP_REGISTRY`
- Relevant test files for registry verification (executor tests)

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.6] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] -- Epic summary: "Developer can invoke /implement, /verify, /build, and /prime commands. /implement executes the full TDD-enforced workflow."
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement: verify_tests_fail confirms RED, validates failure types (expected vs broken)
- [Source: _bmad-output/planning-artifacts/architecture.md#TDD Workflow Composition] -- implement_verify_close workflow: step 2 is verify_tests_fail (shell step, confirms RED)
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow Through TDD Workflow] -- verify_tests_fail asserts: non-zero exit, valid failure types
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step internal structure, step creation checklist, RED phase annotation pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Scaffold Story DoD] -- verify_tests_fail step exists and correctly validates failure types
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] -- Steps communicate via WorkflowContext, verify_tests_fail consumes test_files from write_failing_tests
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR29: "/implement command with TDD workflow"
- [Source: adws/adw_modules/io_ops.py#run_shell_command] -- Shell execution boundary function (returns ShellResult regardless of exit code)
- [Source: adws/adw_modules/types.py] -- ShellResult (return_code, stdout, stderr, command), WorkflowContext
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (7 entries), run_step (shell step dispatch)
- [Source: adws/adw_modules/steps/__init__.py] -- current step exports (10 steps)
- [Source: adws/adw_modules/steps/write_failing_tests.py] -- RED phase step (produces test_files in outputs), RED_PHASE_SYSTEM_PROMPT (defines expected failure types)
- [Source: adws/adw_modules/steps/execute_shell_step.py] -- Reference for shell step pattern (but verify_tests_fail has different semantics)
- [Source: adws/workflows/__init__.py] -- _IMPLEMENT_VERIFY_CLOSE (empty steps, placeholder for Story 4.8)
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/4-5-write-failing-tests-step-red-phase.md] -- Previous story: write_failing_tests step, RED_PHASE_SYSTEM_PROMPT, test file extraction, 450 tests
- [Source: _bmad-output/implementation-artifacts/4-4-build-command-and-implement-close-workflow.md] -- Build command pattern, Beads finalize, command-level finalize design decision

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

From Story 4.5 learnings:
- **ROP composition pattern**: `write_failing_tests` uses `.lash()` for failure re-attribution and `.bind()` for success processing. `verify_tests_fail` should follow the same pattern: `.lash()` to re-attribute `run_shell_command` failures to `step_name="verify_tests_fail"`, then interpret the ShellResult for classification.
- **Pure helper separation**: `_build_red_phase_request`, `_extract_test_files`, `_process_sdk_response` are all pure helpers. `verify_tests_fail` should similarly separate: `_parse_pytest_output` (pure), `_classify_failures` (pure), `verify_tests_fail` (orchestrates I/O + pure logic).
- **Step registration**: Added to both `steps/__init__.py` and `engine/executor.py` `_STEP_REGISTRY` (now 7 entries). This story adds one more (8 entries).
- **450 tests**: Current test count (excluding 3 enemy tests), 100% line+branch coverage.
- **io_ops at 16 functions**: This story adds NO new io_ops functions (reuses run_shell_command).
- **Test agent system prompt**: The `RED_PHASE_SYSTEM_PROMPT` lists expected failure types: ImportError, AssertionError, NotImplementedError, AttributeError. The `verify_tests_fail` step's VALID_RED_FAILURES should match these types.

From Story 4.4 learnings:
- **Command-level finalize**: Not relevant here -- this is a step, not a command.
- **Shell injection protection**: io_ops Beads functions use `shlex.quote()`. Not relevant here since `verify_tests_fail` uses a constant pytest command, not user-provided input.

From Story 4.3 / 4.2 / 4.1 learnings:
- **Dispatch routing**: Not relevant -- this is a step, not a command.
- **ROP .bind()/.lash()**: Use `.bind()` for success composition, `.lash()` for failure re-attribution.

### Relationship to Subsequent Stories

This story is the second of the TDD workflow steps (Decision 6):

1. **Story 4.1 (done)**: Command pattern -- registry, dispatch, .md entry points
2. **Story 4.2 (done)**: `/verify` command -- specialized handler, workflow-backed
3. **Story 4.3 (done)**: `/prime` command -- specialized handler, non-workflow
4. **Story 4.4 (done)**: `/build` command -- implement_close workflow + Beads finalize
5. **Story 4.5 (done)**: `write_failing_tests` step (RED phase) -- SDK step with test agent
6. **Story 4.6 (this)**: `verify_tests_fail` step (RED gate) -- shell step validating failure types
7. **Story 4.7**: `implement` and `refactor` steps (GREEN & REFACTOR phases) -- SDK steps with implementation and refactor agents
8. **Story 4.8**: `implement_verify_close` workflow + `/implement` command -- composes all steps into the full TDD workflow

The `verify_tests_fail` step consumes `test_files` and `red_phase_complete` from `write_failing_tests` outputs (promoted to inputs by the engine). Its outputs (`red_gate_passed`, `failure_types`, `failure_count`) flow to the `implement` step (Story 4.7) via the same promotion mechanism.

### io_ops.py Size Note

This story adds NO new io_ops functions. `verify_tests_fail` reuses the existing `run_shell_command`. The io_ops function count stays at 16 public functions. The next story (4.7) will add SDK step functions for implement and refactor, which also reuse `execute_sdk_call`.

### Difference from execute_shell_step

`execute_shell_step` (the existing generic shell step) treats nonzero exit codes as failures. `verify_tests_fail` has inverted semantics: nonzero exit code = expected (tests should fail), zero exit code = failure (tests should not pass in RED phase). This is why `verify_tests_fail` is its own step function rather than a wrapper around `execute_shell_step`.

Both steps call `io_ops.run_shell_command` directly, but their interpretation of the result differs completely:

| Aspect | `execute_shell_step` | `verify_tests_fail` |
|--------|---------------------|---------------------|
| Exit code 0 | IOSuccess | IOFailure (TestsPassedInRedPhase) |
| Exit code 1 | IOFailure (ShellCommandFailed) | IOSuccess (if valid failure types) or IOFailure (if invalid) |
| Output parsing | None (raw stdout/stderr in outputs) | Failure type extraction and classification |
| Command source | `ctx.inputs["shell_command"]` | `RED_GATE_PYTEST_COMMAND` constant |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 8 tasks completed via strict TDD (RED-GREEN-REFACTOR)
- 40 new tests added (490 total, excluding 3 enemy tests)
- 100% line + branch coverage maintained
- mypy strict mode: no issues in 67 source files
- ruff: all checks passed, zero violations
- Step registered in both steps/__init__.py and engine/executor.py _STEP_REGISTRY (now 8 entries)
- No new io_ops functions added (reuses existing run_shell_command)
- Pure helper separation: _parse_pytest_output (parsing), _classify_failures (classification), verify_tests_fail (orchestration)
- Three failure modes: TestsPassedInRedPhase, InvalidRedFailure, NoTestsRan
- One success mode: valid RED failures (ImportError, AssertionError, NotImplementedError, AttributeError)
- Unknown failure types treated as valid (conservative approach)

### File List

- `adws/adw_modules/steps/verify_tests_fail.py` (NEW) -- VALID_RED_FAILURES, INVALID_RED_FAILURES, RED_GATE_PYTEST_COMMAND, ParsedTestResult, FailureClassification, _parse_pytest_output(), _classify_failures(), _interpret_shell_result(), verify_tests_fail()
- `adws/tests/adw_modules/steps/test_verify_tests_fail.py` (NEW) -- 40 tests covering constants, parsing, classification, step function, command, registration, integration
- `adws/adw_modules/steps/__init__.py` (MODIFIED) -- added verify_tests_fail import and export
- `adws/adw_modules/engine/executor.py` (MODIFIED) -- added verify_tests_fail to _STEP_REGISTRY (now 8 entries)

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial code review mode)
**Date**: 2026-02-02
**Verdict**: APPROVED with 3 fixes applied

### Issues Found and Resolved

**Issue 1 (MEDIUM) -- FIXED: Inline `re.search` not pre-compiled**
- Location: `verify_tests_fail.py` line 110-112
- Problem: The error count regex `r"(\d+) error"` was used via inline `re.search()` instead of a pre-compiled module-level constant, inconsistent with all four other regex patterns in the module (`_ERROR_TYPE_PATTERN`, `_FAILED_COUNT_PATTERN`, `_NO_TESTS_RAN_PATTERN`, `_PASSED_PATTERN`).
- Fix: Extracted to module-level `_ERROR_COUNT_PATTERN = re.compile(r"(\d+) errors? in ")`.

**Issue 2 (MEDIUM) -- FIXED: Overly loose error count regex**
- Location: `verify_tests_fail.py` line 110 (same as Issue 1)
- Problem: The pattern `r"(\d+) error"` could false-match on arbitrary text containing "error" (e.g., "100 error messages were logged" in captured stdout). Pytest's actual summary format is `N error in X.XXs` or `N errors in X.XXs`.
- Fix: Tightened pattern to `r"(\d+) errors? in "` which anchors to the pytest summary format, rejecting false positives from arbitrary text while matching both singular and plural forms.
- Verified: All existing test fixtures continue to match correctly.

**Issue 3 (MEDIUM) -- FIXED: Missing frozen dataclass test for FailureClassification**
- Location: `test_verify_tests_fail.py`
- Problem: `ParsedTestResult` had a `test_parsed_test_result_is_frozen` test verifying the frozen dataclass contract, but `FailureClassification` (also a frozen dataclass per Task 3.1) had no corresponding test. The symmetry gap could mask a regression if someone changes the class definition.
- Fix: Added `TestFailureClassification::test_failure_classification_is_frozen` test.

**Issue 4 (LOW) -- FIXED: Weak assertions in raw_output test**
- Location: `test_verify_tests_fail.py::TestParsePytestOutput::test_parse_pytest_output_raw_output_captured`
- Problem: Test passed non-empty but unparseable text ("some stdout", "some stderr") and only asserted `raw_output` content. It did not verify `tests_ran` or `all_passed` behavior for this edge case. This is the only test exercising the "non-empty but no recognizable pytest patterns" path.
- Fix: Added assertions for `tests_ran is False` and `all_passed is False`.

**Issue 5 (LOW -- NOT FIXED, observation only): `_interpret_shell_result` tested only indirectly**
- Observation: The `_interpret_shell_result` function is tested exclusively through `verify_tests_fail` integration tests. Direct unit tests for this function would strengthen the test pyramid. However, 100% branch coverage is achieved, so this is informational only.

### Quality Gate Results (Post-Fix)

| Gate | Result |
|------|--------|
| pytest (491 tests, excluding 3 enemy) | All passed |
| Coverage (line + branch) | 100.00% |
| mypy --strict (67 source files) | No issues |
| ruff check | All checks passed |

### AC Verification

| AC | Status | Evidence |
|----|--------|----------|
| AC1: Shell step runs pytest, confirms tests fail | PASS | `verify_tests_fail` calls `io_ops.run_shell_command(RED_GATE_PYTEST_COMMAND)`, tests verify via mock |
| AC2: ImportError/AssertionError accepted as valid RED | PASS | `VALID_RED_FAILURES` frozenset contains both; `_classify_failures` returns `is_valid_red=True`; 6 tests verify |
| AC3: SyntaxError rejected as broken test | PASS | `INVALID_RED_FAILURES` frozenset contains SyntaxError; `_classify_failures` returns `is_valid_red=False`; 4 tests verify |
| AC4: Unexpected pass returns PipelineError | PASS | `_interpret_shell_result` returns `IOFailure(PipelineError(..., error_type="TestsPassedInRedPhase"))` when `all_passed=True`; 2 tests verify |
| AC5: Test coverage for all scenarios | PASS | 41 tests covering valid failure, invalid failure, mixed, unexpected pass, no tests ran, empty output, shell failure, registration, command constant |
| AC6: 100% coverage, mypy strict, ruff clean | PASS | All three gates pass post-fix |

### Architecture Compliance

- NFR1 (no uncaught exceptions): `verify_tests_fail` returns IOResult, never raises -- COMPLIANT
- NFR9 (100% coverage): 100% line + branch -- COMPLIANT
- NFR10 (I/O behind io_ops): Only calls `io_ops.run_shell_command` -- COMPLIANT
- NFR11 (mypy strict): Passes with 0 issues -- COMPLIANT
- NFR12 (ruff ALL): Zero violations -- COMPLIANT
- Decision 6 (RED gate verifies expected failures): Correct classification logic -- COMPLIANT
- Step signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` -- COMPLIANT
- IOResult order: `IOResult[SuccessType, ErrorType]` (success first) -- COMPLIANT
- ROP pattern: `.lash()` for failure re-attribution, `.bind()` for success composition -- COMPLIANT
- No mutation: Always returns new `WorkflowContext` via `with_updates()` -- COMPLIANT

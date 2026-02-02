# Story 3.1: Verify io_ops Shell Functions

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want io_ops functions for each quality gate tool,
so that the verify pipeline can invoke test runners and linters through the established I/O boundary.

## Acceptance Criteria

1. **Given** `run_shell_command` from Epic 2 exists in io_ops, **When** I inspect io_ops verify functions, **Then** `run_jest_tests()` executes `npm test` and parses output for pass/fail status, failure messages, and affected files (FR13) **And** `run_playwright_tests()` executes `npm run test:e2e` and parses output similarly (FR14) **And** `run_mypy_check()` executes `uv run mypy adws/` and parses type errors (FR15) **And** `run_ruff_check()` executes `uv run ruff check adws/` and parses lint violations (FR15).

2. **Given** each io_ops verify function, **When** it returns results, **Then** the return type is `IOResult[VerifyResult, PipelineError]` following the io_ops pattern **And** `VerifyResult` contains structured data: tool name, pass/fail, error list, raw output.

3. **Given** a tool execution fails (nonzero exit code), **When** io_ops processes the result, **Then** failure details are captured in structured form (not just raw stderr) **And** the PipelineError includes the tool name and parseable error output.

4. **Given** all io_ops verify functions, **When** I run tests, **Then** both success and failure paths are covered for each function **And** tests mock `run_shell_command` at the io_ops boundary (NFR10) **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create `VerifyResult` data type in types.py (AC: #2)
  - [x] 1.1 RED: Write tests for `VerifyResult` frozen dataclass construction with fields: `tool_name` (str), `passed` (bool), `errors` (list[str]), `raw_output` (str). Verify immutability, default factory for errors, and field access.
  - [x] 1.2 GREEN: Implement `VerifyResult` as a frozen dataclass in `adws/adw_modules/types.py`.
  - [x] 1.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Implement `run_jest_tests()` in io_ops.py (AC: #1, #3)
  - [x] 2.1 RED: Write tests for `run_jest_tests` success path -- mock `run_shell_command` returning exit code 0 with sample Jest stdout. Verify returns `IOResult[VerifyResult, PipelineError]` with `tool_name="jest"`, `passed=True`, `errors=[]`, and `raw_output` containing the stdout.
  - [x] 2.2 GREEN: Implement `run_jest_tests()` in io_ops.py. Calls `run_shell_command("npm test")` and transforms the `ShellResult` into a `VerifyResult`.
  - [x] 2.3 RED: Write tests for `run_jest_tests` failure path -- mock `run_shell_command` returning nonzero exit code with sample Jest failure output. Verify returns `IOResult[VerifyResult, PipelineError]` with `passed=False`, `errors` list populated with parsed failure messages from stdout/stderr.
  - [x] 2.4 GREEN: Implement failure parsing -- extract failure messages from Jest output into `errors` list.
  - [x] 2.5 RED: Write test for `run_jest_tests` when `run_shell_command` itself returns `IOFailure` (e.g., timeout, command not found). Verify the IOFailure propagates as-is.
  - [x] 2.6 GREEN: Implement IOFailure propagation from `run_shell_command`.
  - [x] 2.7 REFACTOR: Clean up, verify 100% coverage on jest function.

- [x] Task 3: Implement `run_playwright_tests()` in io_ops.py (AC: #1, #3)
  - [x] 3.1 RED: Write tests for `run_playwright_tests` success path -- mock `run_shell_command` returning exit code 0 with sample Playwright stdout. Verify returns `IOResult[VerifyResult, PipelineError]` with `tool_name="playwright"`, `passed=True`, `errors=[]`.
  - [x] 3.2 GREEN: Implement `run_playwright_tests()` in io_ops.py. Calls `run_shell_command("npm run test:e2e")`.
  - [x] 3.3 RED: Write tests for `run_playwright_tests` failure path -- nonzero exit code with failure output. Verify `passed=False`, `errors` populated.
  - [x] 3.4 GREEN: Implement failure parsing for Playwright output.
  - [x] 3.5 RED: Write test for `run_playwright_tests` when `run_shell_command` returns `IOFailure`. Verify propagation.
  - [x] 3.6 GREEN: Implement IOFailure propagation.
  - [x] 3.7 REFACTOR: Clean up, verify 100% coverage.

- [x] Task 4: Implement `run_mypy_check()` in io_ops.py (AC: #1, #3)
  - [x] 4.1 RED: Write tests for `run_mypy_check` success path -- mock `run_shell_command` returning exit code 0 with sample mypy "Success: no issues found" stdout. Verify returns `IOResult[VerifyResult, PipelineError]` with `tool_name="mypy"`, `passed=True`, `errors=[]`.
  - [x] 4.2 GREEN: Implement `run_mypy_check()` in io_ops.py. Calls `run_shell_command("uv run mypy adws/")`.
  - [x] 4.3 RED: Write tests for `run_mypy_check` failure path -- nonzero exit with sample mypy error output (e.g., `"adws/adw_modules/types.py:5: error: ..."`). Verify `passed=False`, `errors` list contains each type error line.
  - [x] 4.4 GREEN: Implement failure parsing -- parse mypy output for lines matching the `file:line: error:` pattern.
  - [x] 4.5 RED: Write test for `run_mypy_check` when `run_shell_command` returns `IOFailure`. Verify propagation.
  - [x] 4.6 GREEN: Implement IOFailure propagation.
  - [x] 4.7 REFACTOR: Clean up, verify 100% coverage.

- [x] Task 5: Implement `run_ruff_check()` in io_ops.py (AC: #1, #3)
  - [x] 5.1 RED: Write tests for `run_ruff_check` success path -- mock `run_shell_command` returning exit code 0 with sample ruff "All checks passed!" stdout. Verify returns `IOResult[VerifyResult, PipelineError]` with `tool_name="ruff"`, `passed=True`, `errors=[]`.
  - [x] 5.2 GREEN: Implement `run_ruff_check()` in io_ops.py. Calls `run_shell_command("uv run ruff check adws/")`.
  - [x] 5.3 RED: Write tests for `run_ruff_check` failure path -- nonzero exit with sample ruff violation output (e.g., `"adws/adw_modules/types.py:10:1: E501 ..."`). Verify `passed=False`, `errors` list contains each violation line.
  - [x] 5.4 GREEN: Implement failure parsing -- parse ruff output for violation lines.
  - [x] 5.5 RED: Write test for `run_ruff_check` when `run_shell_command` returns `IOFailure`. Verify propagation.
  - [x] 5.6 GREEN: Implement IOFailure propagation.
  - [x] 5.7 REFACTOR: Clean up, verify 100% coverage.

- [x] Task 6: Implement shared `_build_verify_result` helper (AC: #2, #3)
  - [x] 6.1 RED: Shared helper `_build_verify_result` emerged from refactoring. Wrote 3 tests: success path, failure path, stdout+stderr combination.
  - [x] 6.2 GREEN: Extracted `_build_verify_result(shell_result, tool_name, error_filter)` as common builder. Each verify function passes a tool-specific filter predicate.
  - [x] 6.3 REFACTOR: Final cleanup, DRY pass across all four verify functions. All use shared helper.

- [x] Task 7: Verify full integration and quality gates (AC: #5)
  - [x] 7.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- 218 passed, 100% line+branch coverage
  - [x] 7.2 Run `uv run mypy adws/` -- strict mode passes (31 source files)
  - [x] 7.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 2.7 / Epic 2 completion)

**io_ops.py** has 6 functions + 1 async helper + 1 internal exception:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_shell_command(command: str, *, timeout: int | None = None, cwd: str | None = None) -> IOResult[ShellResult, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[None, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError exception
```

**Pattern established for io_ops functions:**
- Returns `IOResult[SuccessType, ErrorType]` (success first, error second -- returns v0.26.0)
- Catches specific exceptions, never bare `except Exception`
- Transforms external types into domain types before returning
- Never contains domain logic -- just I/O translation

**run_shell_command** is the key dependency. It already:
- Executes shell commands via `subprocess.run(shell=True)`
- Returns `IOResult[ShellResult, PipelineError]`
- `ShellResult` is a frozen dataclass with `return_code`, `stdout`, `stderr`, `command`
- Nonzero exit codes are valid results (IOSuccess), NOT errors. The calling function decides policy.
- IOFailure only for actual I/O failures (timeout, command not found, OS error)

**types.py** has: `WorkflowContext`, `ShellResult`, `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`.

**engine/** has: `executor.py` (run_step, run_workflow, retry, data flow), `types.py` (Step, Workflow, StepFunction), `combinators.py` (with_verification, sequence).

**workflows/__init__.py** has: `WorkflowName`, `load_workflow()`, `list_workflows()`, 4 registered workflows (implement_close, implement_verify_close, convert_stories_to_beads, sample).

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 199 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`
- `IOResult[AdwsResponse, PipelineError]` -- success is `AdwsResponse`
- **New pattern**: `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`

### Design: `VerifyResult` Data Type

New frozen dataclass in `adws/adw_modules/types.py`:

```python
@dataclass(frozen=True)
class VerifyResult:
    """Structured result from a quality gate tool execution."""

    tool_name: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""
```

Fields:
- `tool_name`: Identifies which tool ran ("jest", "playwright", "mypy", "ruff")
- `passed`: Whether the tool reported success (exit code 0 AND no error patterns)
- `errors`: Parsed error/violation messages from the tool output. Empty on success.
- `raw_output`: Full stdout+stderr for debugging and feedback accumulation (Story 3.3)

The `errors` list is the key design choice -- it provides structured, parseable failure data for the feedback accumulation in Story 3.3. Raw output alone is too noisy for retries; parsed errors give the implementation agent actionable information.

### Design: Verify io_ops Functions

Each verify function follows the same pattern:

```python
def run_<tool>() -> IOResult[VerifyResult, PipelineError]:
    """Execute <tool> and return structured result."""
    result = run_shell_command("<command>")
    # If run_shell_command itself failed (IOFailure), propagate it
    # If run_shell_command succeeded (IOSuccess with ShellResult):
    #   - Parse the ShellResult (stdout, stderr, return_code)
    #   - Build a VerifyResult with tool_name, passed, errors, raw_output
    #   - Return IOSuccess(VerifyResult)
```

**IMPORTANT: Nonzero exit codes are NOT IOFailure.** `run_shell_command` returns `IOSuccess(ShellResult)` even for nonzero exit. The verify function decides the policy:
- Exit code 0 -> `VerifyResult(passed=True, errors=[])`
- Exit code != 0 -> `VerifyResult(passed=False, errors=[...parsed...])`

IOFailure from this function only occurs when `run_shell_command` itself returns IOFailure (timeout, command not found, etc.).

This is a deliberate design choice. A test failure is not a pipeline I/O error -- it's a valid tool result that the pipeline needs to process. Treating nonzero exits as IOFailure would short-circuit the ROP pipeline, preventing the verify workflow (Story 3.2) from running all checks.

#### `run_jest_tests()`

```python
def run_jest_tests() -> IOResult[VerifyResult, PipelineError]:
    """Execute npm test (Jest) and return structured result (FR13)."""
```

- Command: `npm test`
- Parse strategy: Jest outputs `FAIL` prefixed lines for test file failures, and `PASS` prefixed lines for successes. On failure, look for lines matching `FAIL` prefix and `Error:` / `expect(` patterns.
- Success: exit code 0
- Failure: exit code != 0, parse failure lines from stdout

#### `run_playwright_tests()`

```python
def run_playwright_tests() -> IOResult[VerifyResult, PipelineError]:
    """Execute npm run test:e2e (Playwright) and return structured result (FR14)."""
```

- Command: `npm run test:e2e`
- Parse strategy: Playwright outputs summary lines. On failure, look for `failed` count in summary and individual test failure messages.
- Success: exit code 0
- Failure: exit code != 0, parse failure lines

#### `run_mypy_check()`

```python
def run_mypy_check() -> IOResult[VerifyResult, PipelineError]:
    """Execute uv run mypy adws/ and return structured result (FR15)."""
```

- Command: `uv run mypy adws/`
- Parse strategy: mypy outputs errors in `file:line: error: message` format. Parse each matching line into the errors list.
- Success: exit code 0 and stdout contains "Success" or no error lines
- Failure: exit code != 0, parse error lines from stdout

#### `run_ruff_check()`

```python
def run_ruff_check() -> IOResult[VerifyResult, PipelineError]:
    """Execute uv run ruff check adws/ and return structured result (FR15)."""
```

- Command: `uv run ruff check adws/`
- Parse strategy: ruff outputs violations in `file:line:col: RULE message` format. Parse each matching line into errors list.
- Success: exit code 0
- Failure: exit code != 0, parse violation lines from stdout

### Design: Error Parsing Strategy

The four verify functions need to parse tool-specific output into structured `errors` lists. The parsing should be:
1. **Tolerant**: Don't fail if output format changes slightly -- capture what we can
2. **Line-based**: Split stdout/stderr by newlines, filter for error-matching patterns
3. **Additive**: Collect ALL errors, not just the first one

Each function has its own parsing logic because the output formats differ significantly:
- Jest: `FAIL src/tests/foo.test.ts` and `Error: expect(received)...`
- Playwright: `X failed` summary and per-test failure blocks
- mypy: `file:line: error: message [error-code]`
- ruff: `file:line:col: RULE message`

If a common pattern emerges during implementation, extract a shared helper (Task 6). But do NOT prematurely abstract -- the parsing details differ enough that a forced abstraction would be worse than duplication.

### Design: `bind` Pattern for IOResult Chaining

The verify functions need to chain `run_shell_command` -> parse result. Use the `bind` pattern already established in `execute_shell_step.py`:

```python
def run_jest_tests() -> IOResult[VerifyResult, PipelineError]:
    result = run_shell_command("npm test")

    def _handle_result(
        shell_result: ShellResult,
    ) -> IOResult[VerifyResult, PipelineError]:
        # Parse and build VerifyResult
        ...
        return IOSuccess(VerifyResult(...))

    return result.bind(_handle_result)
```

This pattern:
- Automatically propagates IOFailure from `run_shell_command` (no manual error checking)
- Only calls `_handle_result` if `run_shell_command` succeeded
- Returns the same IOResult container type (`IOResult[VerifyResult, PipelineError]`)

### Test Strategy

**Test file**: `adws/tests/adw_modules/test_io_ops.py` (add to existing file)

Per architecture: "Every test file tests exactly one module." All io_ops tests go in the existing `test_io_ops.py`.

**Mock target**: `adws.adw_modules.io_ops.run_shell_command` -- mock the INTERNAL call within io_ops, not the external module. Each verify function calls `run_shell_command` internally, so we mock it at the io_ops module level.

**Test naming convention**: `test_run_<tool>_<scenario>`, e.g.:
- `test_run_jest_tests_success`
- `test_run_jest_tests_failure_with_errors`
- `test_run_jest_tests_shell_failure_propagates`

**For each verify function, test 3 paths:**
1. **Success**: `run_shell_command` returns `IOSuccess(ShellResult(return_code=0, ...))` -> verify `VerifyResult(passed=True, errors=[])`
2. **Tool failure**: `run_shell_command` returns `IOSuccess(ShellResult(return_code=1, ...))` -> verify `VerifyResult(passed=False, errors=[...parsed...])`
3. **IO failure**: `run_shell_command` returns `IOFailure(PipelineError(...))` -> verify IOFailure propagates

**Sample tool outputs for test fixtures:**

Jest success:
```
Test Suites: 5 passed, 5 total
Tests:       23 passed, 23 total
```

Jest failure:
```
FAIL src/tests/popup.test.ts
  Tab Groups
    > should handle empty groups
      expect(received).toBe(expected)
Test Suites: 1 failed, 4 passed, 5 total
Tests:       1 failed, 22 passed, 23 total
```

mypy success:
```
Success: no issues found in 31 source files
```

mypy failure:
```
adws/adw_modules/types.py:5: error: Missing return statement  [return]
adws/adw_modules/io_ops.py:42: error: Incompatible types  [arg-type]
Found 2 errors in 2 files (checked 31 source files)
```

ruff success (exit code 0, empty or "All checks passed!" stdout)

ruff failure:
```
adws/adw_modules/types.py:10:1: E501 Line too long (120 > 88)
adws/adw_modules/io_ops.py:5:1: F401 `os` imported but unused
Found 2 errors.
```

### Ruff Considerations

- `FBT001`/`FBT002` (boolean positional): `VerifyResult(passed=True)` is a keyword argument in a frozen dataclass. No issue.
- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files. Return codes like `0`, `1` are fine in tests.
- `E501`: Keep all lines under 88 characters.
- `TCH001`/`TCH002`: Use TYPE_CHECKING guard where needed, following existing io_ops.py pattern.

### Architecture Compliance

- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. The verify functions live IN io_ops.py, calling run_shell_command internally. Steps (Story 3.2) will call these io_ops functions.
- **NFR11**: mypy strict mode -- VerifyResult and function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **FR13**: `run_jest_tests()` executes `npm test` and parses output.
- **FR14**: `run_playwright_tests()` executes `npm run test:e2e` and parses output.
- **FR15**: `run_mypy_check()` and `run_ruff_check()` execute Python quality tools.
- **Epic 3 note**: These io_ops functions are the foundation. Story 3.2 wraps them as pipeline steps. Story 3.3 accumulates their failures as feedback. This story is intentionally scoped to JUST the io_ops layer.

### What NOT to Do

- Do NOT create pipeline steps in this story -- steps are Story 3.2. This story is io_ops layer only.
- Do NOT create a workflow definition -- the verify workflow is Story 3.2.
- Do NOT implement feedback accumulation -- that is Story 3.3.
- Do NOT change `run_shell_command` -- it already works correctly. Build on top of it.
- Do NOT treat nonzero exit codes as IOFailure -- nonzero exit is a valid tool result (`VerifyResult(passed=False)`). IOFailure is ONLY for actual I/O errors (timeout, command not found).
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- this story doesn't touch WorkflowContext at all.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe`.
- Do NOT mock anything in Enemy Unit Tests (but this story has no EUTs -- the verify functions call run_shell_command, not external APIs).
- Do NOT import subprocess directly in the verify functions -- they call `run_shell_command` which handles subprocess internally. The verify functions are one layer above raw I/O.
- Do NOT create separate files for each verify function -- they all live in `io_ops.py` following the single-boundary pattern (NFR10).
- Do NOT prematurely abstract a shared parser -- let each function have its own inline parsing. Extract a common helper ONLY if clear duplication emerges during refactoring (Task 6).

### Project Structure Notes

Files to create:
- None (all additions go into existing files)

Files to modify:
- `adws/adw_modules/types.py` -- add `VerifyResult` frozen dataclass
- `adws/adw_modules/io_ops.py` -- add `run_jest_tests()`, `run_playwright_tests()`, `run_mypy_check()`, `run_ruff_check()`
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for all four verify functions and VerifyResult
- `adws/tests/adw_modules/test_types.py` -- add tests for VerifyResult construction and immutability

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] -- AC and story definition (FR13, FR14, FR15)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] -- Epic summary: "Story ordering critical: verify steps wrap shell execution from Epic 2 (FR11). Each verify sub-step (npm test, npm run test:e2e, uv run mypy, uv run ruff) is an io_ops shell function before it becomes a pipeline step."
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK Integration Design, io_ops boundary pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 3] -- Tool config (mypy strict, ruff ALL, pytest 100% coverage)
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- io_ops function pattern, step creation checklist
- [Source: _bmad-output/planning-artifacts/architecture.md#io_ops.py Scaling Consideration] -- Single file pattern works, io_ops/ package escape hatch if needed
- [Source: _bmad-output/planning-artifacts/architecture.md#Quality Verification (FR12-17)] -- "Inline shell steps in implement_verify_close.py", "verify_tests_fail.py (shell steps)"
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Composition Notes] -- "Verification logic (FR12-FR17) is NOT a dedicated step module. It is composed from inline shell Step definitions."
- [Source: adws/adw_modules/io_ops.py] -- Current io_ops (6 functions, run_shell_command is the key dependency)
- [Source: adws/adw_modules/types.py] -- Current types (WorkflowContext, ShellResult, AdwsRequest, AdwsResponse)
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/steps/execute_shell_step.py] -- Existing shell step using `result.bind(_handle_success)` pattern
- [Source: adws/tests/adw_modules/test_io_ops.py] -- Existing io_ops tests (28 tests for run_shell_command etc.)
- [Source: adws/tests/adw_modules/test_types.py] -- Existing types tests
- [Source: adws/tests/conftest.py] -- Shared test fixtures (sample_workflow_context, mock_io_ops)
- [Source: _bmad-output/implementation-artifacts/2-7-workflow-combinators-and-sample-workflow.md] -- Previous story learnings, IOResult type order, current state summary
- [Source: _bmad-output/implementation-artifacts/2-2-io-ops-sdk-client-and-enemy-unit-tests.md] -- SDK io_ops pattern, execute_sdk_call implementation, bind pattern

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

From Story 2.7 learnings:
- **Combinator pattern**: Pure functions producing Tier 1 types, no ROP imports in combinators.
- **Sample workflow**: Registered in workflows/__init__.py, not separate file.
- **Test count at Epic 2 completion**: 199 tests (excluding 2 enemy), 100% line+branch coverage.
- **Integration tests**: Test engine execution of combinator-produced workflows via mocked _STEP_REGISTRY.

From Story 2.3 learnings:
- **run_shell_command design**: Nonzero exit codes are IOSuccess(ShellResult), NOT IOFailure. The calling step decides policy for nonzero returns.
- **execute_shell_step pattern**: Uses `result.bind(_handle_success)` to chain run_shell_command -> parse result. This is the pattern to follow for verify functions.
- **Shell step dispatch**: Bypasses registry, injects shell_command into context inputs.

From Story 2.2 learnings:
- **IOResult[Success, Error]**: Success type comes first (confirmed across all stories).
- **Async handling**: io_ops bridges async SDK to sync via asyncio.run().
- **bind pattern**: Already used in execute_shell_step.py for chaining shell results.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Architecture Note on Verify Function Placement

The architecture says "Verification logic (FR12-FR17) is NOT a dedicated step module. It is composed from inline shell Step definitions within the implement_verify_close workflow." This means Story 3.2 will compose these io_ops functions into Step definitions, NOT create separate step files like `run_jest_tests_step.py`. The io_ops functions in THIS story are the foundation; the steps are inline compositions.

This is consistent with the architecture's `Quality Verification (FR12-17)` mapping to `Inline shell steps in implement_verify_close.py`.

However, the epic file for Story 3.1 explicitly calls for io_ops functions that return `IOResult[VerifyResult, PipelineError]`. This is the correct layer -- io_ops handles the tool execution and output parsing. The step layer (Story 3.2) wraps these in the standard `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` step signature.

### io_ops.py Growth Consideration

After this story, io_ops.py will have ~10 functions (up from 6). The architecture notes that the single-file pattern works up to ~300 lines / ~15 functions. With 4 new functions each likely 20-40 lines, we'll be at ~10 functions and ~300-350 lines. This approaches the escape hatch threshold for splitting into an `io_ops/` package, but should still be manageable as a single file for now. Flag for review after this story.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- **Test count**: 218 tests (up from 199), 100% line+branch coverage.
- **VerifyResult**: Frozen dataclass with tool_name, passed, errors (default_factory=list), raw_output (default=""). Placed before ShellResult in types.py.
- **Shared helper**: `_build_verify_result(shell_result, tool_name, error_filter)` extracted during Task 6 refactoring. Each verify function passes a tool-specific filter predicate (lambda or named function). This eliminates duplication of raw output combination, pass/fail logic, and error collection.
- **bind pattern**: All four verify functions use `result.bind(_handle_result)` exactly as established in execute_shell_step.py. IOFailure propagation is automatic via bind -- no manual error checking needed.
- **Callable import**: `Callable` imported under `TYPE_CHECKING` guard in io_ops.py (following existing Path pattern). Works because `from __future__ import annotations` makes all annotations strings at runtime.
- **io_ops.py size**: Now 91 statements (was ~71). 10 public functions + 1 shared helper + 1 async helper + 1 internal exception. Still well within the single-file threshold.
- **Error parsing strategies**: Jest filters `FAIL ` prefix lines; Playwright filters lines containing "failed" or "Error:"; mypy filters lines containing ": error:"; ruff filters lines containing ": " but not starting with "Found ".
- **No new files created**: All additions in existing files per story design.

### File List

- `adws/adw_modules/types.py` -- Added `VerifyResult` frozen dataclass
- `adws/adw_modules/io_ops.py` -- Added `_build_verify_result()`, `run_jest_tests()`, `run_playwright_tests()`, `run_mypy_check()`, `run_ruff_check()`
- `adws/tests/adw_modules/test_io_ops.py` -- Added 15 tests: 3 for _build_verify_result helper, 3 each for jest/playwright/mypy/ruff (success, failure, IOFailure propagation)
- `adws/tests/adw_modules/test_types.py` -- Added 4 tests for VerifyResult (construction, defaults, frozen, default_factory)

## Senior Developer Review

### Review Model

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Review Date

2026-02-02

### Issues Found: 4

#### Issue 1 (MEDIUM) -- FIXED: Ruff error filter produces false positives on non-violation lines

**Location**: `adws/adw_modules/io_ops.py`, `_ruff_filter` inside `run_ruff_check()`

**Problem**: The original filter `": " in line and not line.startswith("Found ")` is too permissive. Any line containing `": "` would be captured as an error, including informational output like `"ruff v0.14.14: configuration loaded"`, `"Checking: adws/"`, or `"warning: Some warning here"`. This would pollute the `errors` list with non-violation noise lines, misleading downstream consumers (Story 3.3 feedback accumulation).

**Fix**: Replaced with a structural check that validates the `file:line:col:` prefix pattern -- splitting on `:` and verifying parts[1] and parts[2] are digits. This matches only real ruff violation lines (`adws/foo.py:10:1: E501 ...`) and rejects all noise.

**Test added**: `test_run_ruff_check_filters_noise_lines` -- verifies that output containing a `"warning: unexpected config"` noise line plus a real violation only captures the violation (1 error, not 2).

#### Issue 2 (MEDIUM) -- FIXED: Tests do not verify the command argument passed to run_shell_command

**Location**: `adws/tests/adw_modules/test_io_ops.py`, all four verify function success tests

**Problem**: AC#1 explicitly requires specific commands: `run_jest_tests()` must execute `"npm test"`, `run_playwright_tests()` must execute `"npm run test:e2e"`, `run_mypy_check()` must execute `"uv run mypy adws/"`, `run_ruff_check()` must execute `"uv run ruff check adws/"`. The tests mocked `run_shell_command` at module level but never asserted what command was passed. If someone changed the command string in io_ops.py (e.g., `"npm test"` to `"npm run test"`), all tests would still pass silently.

**Fix**: Added `mock_shell.assert_called_once_with("<expected_command>")` to each verify function's success test. The mock is now captured as a return value from `mocker.patch` and the command is verified after the call.

#### Issue 3 (LOW) -- FIXED: Playwright failure test missing error content assertions

**Location**: `adws/tests/adw_modules/test_io_ops.py`, `test_run_playwright_tests_failure_with_errors`

**Problem**: The test asserted `len(vr.errors) > 0` but never checked what was in the errors list. Compare to Jest (asserts `"FAIL"` in errors), mypy (asserts `"Missing return"` and `"Incompatible types"`), and ruff (asserts `"E501"` and `"F401"`). The Playwright test was weaker than its siblings.

**Fix**: Added `assert any("Error:" in e for e in vr.errors)` and `assert any("failed" in e for e in vr.errors)` to verify both Playwright error line patterns are captured.

#### Issue 4 (LOW) -- NOT FIXED (acceptable): Empty errors list possible on failure path

**Location**: `adws/adw_modules/io_ops.py`, `_build_verify_result`

**Problem**: If a tool exits with nonzero code but no output lines match the error filter, the result is `VerifyResult(passed=False, errors=[])`. This is semantically odd -- the tool failed but no structured errors were captured.

**Decision**: Not fixed. The `raw_output` field still contains the full output for debugging. Story 3.3 (feedback accumulation) can fall back to `raw_output` when `errors` is empty. The design doc explicitly says parsing should be "tolerant" and "capture what we can." Forcing a synthetic error message would add complexity without clear benefit.

### Quality Gates (Post-Fix)

- **pytest**: 219 passed, 2 skipped (up from 218 -- added ruff noise filter test)
- **coverage**: 100% line + branch (2318 statements, 84 branches)
- **ruff**: All checks passed (zero violations)
- **mypy**: Success, no issues found in 31 source files (strict mode)

### AC Verification

1. AC#1: PASS -- `run_jest_tests()` calls `"npm test"`, `run_playwright_tests()` calls `"npm run test:e2e"`, `run_mypy_check()` calls `"uv run mypy adws/"`, `run_ruff_check()` calls `"uv run ruff check adws/"`. All commands verified by tests via `assert_called_once_with`.
2. AC#2: PASS -- All verify functions return `IOResult[VerifyResult, PipelineError]`. `VerifyResult` is a frozen dataclass with `tool_name`, `passed`, `errors`, `raw_output`.
3. AC#3: PASS -- Nonzero exit codes produce `VerifyResult(passed=False, errors=[...])` with parsed error lines. IOFailure only propagates from `run_shell_command` itself (timeout, command not found).
4. AC#4: PASS -- 3 test paths per function (success, tool failure, IO failure) + 3 tests for shared helper + 1 ruff noise regression test + 4 VerifyResult type tests. Mocking at io_ops boundary. 100% coverage.
5. AC#5: PASS -- pytest 219 passed, 100% line+branch, mypy strict, ruff zero violations.

### Verdict: APPROVED

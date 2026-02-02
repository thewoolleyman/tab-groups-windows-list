# Story 2.3: Step Function Type & Shell Command Execution

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want a formalized step function type and shell command execution capability,
so that I can define pipeline steps with a consistent signature and execute subprocess commands as steps.

## Acceptance Criteria

1. **Given** the error types from Story 2.1, **When** I inspect the step function type definition, **Then** the step signature is `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` **And** one public function per step file matching the filename **And** absolute imports only (`from adws.adw_modules.X import Y`).

2. **Given** the io_ops boundary, **When** I inspect `io_ops.py` shell execution, **Then** `run_shell_command` function exists that executes subprocess commands **And** it returns `IOResult[ShellResult, PipelineError]`, catches specific exceptions, and transforms to `PipelineError` on failure **And** it captures stdout and stderr for context propagation.

3. **Given** shell execution is implemented, **When** a step is marked as a shell command (FR11), **Then** the engine can execute it via `run_shell_command` instead of an SDK call **And** shell step output is captured in `WorkflowContext.outputs`.

4. **Given** all step-related code, **When** I run tests, **Then** shell command success and failure paths are both tested **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Add ShellResult type and StepFunction type alias (AC: #1, #2)
  - [x] 1.1 RED: Write tests for `ShellResult` dataclass construction (return_code, stdout, stderr fields)
  - [x] 1.2 GREEN: Implement `ShellResult` frozen dataclass in `types.py`
  - [x] 1.3 RED: Write tests for `StepFunction` type alias validation (callable with correct signature)
  - [x] 1.4 GREEN: Add `StepFunction` type alias to `engine/types.py`
  - [x] 1.5 REFACTOR: Clean up, verify mypy passes, 100% coverage

- [x] Task 2: Add shell-related error types (AC: #2)
  - [x] 2.1 RED: Write tests for `ShellCommandError` construction with return_code, stdout, stderr, command fields
  - [x] 2.2 GREEN: Add `ShellCommandError` frozen dataclass to `errors.py` and add to `PipelineError` union (if union is used) or ensure it is a valid PipelineError construction
  - [x] 2.3 REFACTOR: Verify error types serialize correctly in `to_dict()`, verify coverage

- [x] Task 3: Implement `run_shell_command` in io_ops.py (AC: #2)
  - [x] 3.1 RED: Write unit tests for `run_shell_command` success path (command runs, returns ShellResult with stdout/stderr)
  - [x] 3.2 GREEN: Implement `run_shell_command` in io_ops.py -- uses subprocess.run, returns `IOResult[ShellResult, PipelineError]`
  - [x] 3.3 RED: Write unit tests for `run_shell_command` failure paths (nonzero exit code, command not found, timeout, OSError)
  - [x] 3.4 GREEN: Implement error handling -- catch subprocess exceptions, return IOFailure with PipelineError
  - [x] 3.5 REFACTOR: Clean up, verify 100% coverage

- [x] Task 4: Add `shell` flag to Step dataclass and `execute_shell_step` function (AC: #1, #3)
  - [x] 4.1 RED: Write tests for `Step` dataclass with `shell=True` flag and `command` field
  - [x] 4.2 GREEN: Add `shell` bool and `command` str fields to `Step` in `engine/types.py`
  - [x] 4.3 RED: Write tests for `execute_shell_step` that calls `run_shell_command` and places output into `WorkflowContext.outputs`
  - [x] 4.4 GREEN: Implement `execute_shell_step` in `adws/adw_modules/steps/execute_shell_step.py`
  - [x] 4.5 REFACTOR: Export from `steps/__init__.py`, verify full quality gates

- [x] Task 5: Verify full integration and quality gates (AC: #4, #5)
  - [x] 5.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all unit tests pass, 100% coverage
  - [x] 5.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 5.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 2.2)

**io_ops.py** has 3 functions:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
```
Plus internal async helper `_execute_sdk_call_async()` and `_NoResultError` exception class.

**types.py** has:
- `WorkflowContext` frozen dataclass with `inputs`, `outputs`, `feedback` fields and convenience methods: `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`
- `AdwsRequest` / `AdwsResponse` Pydantic models with `ConfigDict(frozen=True)`
- `DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"`
- `PermissionMode` Literal type

**engine/types.py** has:
- `Step(name, function, always_run, max_attempts)` frozen dataclass
- `Workflow(name, description, steps, dispatchable)` frozen dataclass

**errors.py** has:
- `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`

**steps/__init__.py** exports: `check_sdk_available`

**steps/check_sdk_available.py** -- existing step with correct signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 65 tests, 100% coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[str, PipelineError]` -- success is `str`, error is `PipelineError`
- `IOResult[bool, PipelineError]` -- success is `bool`
- `IOResult[AdwsResponse, PipelineError]` -- success is `AdwsResponse`
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`

The new `run_shell_command` MUST follow: `IOResult[ShellResult, PipelineError]`

### Step Function Signature

All step functions follow this exact signature:
```python
def step_name(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]:
```

There is already one example: `check_sdk_available.py`. The new `execute_shell_step` MUST follow the same pattern.

### Step Function Type Alias

Add to `engine/types.py`:
```python
from typing import Callable
from returns.io import IOResult
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext

StepFunction = Callable[[WorkflowContext], IOResult[WorkflowContext, PipelineError]]
```

This formalizes the contract. The engine (Story 2.4) will use this type to enforce step signatures.

**IMPORTANT NOTE on circular imports**: `engine/types.py` currently only imports from `dataclasses` and has no cross-module imports. Adding imports from `adws.adw_modules.errors` and `adws.adw_modules.types` is fine because `errors.py` and `types.py` do not import from `engine/types.py`. However, be mindful that:
- `WorkflowContext` is in `adws.adw_modules.types` (NOT in `engine/types.py`)
- Steps import from `adws.adw_modules.types` for `WorkflowContext`
- Steps import from `adws.adw_modules.io_ops` for I/O functions
- Steps NEVER import from `adws.adw_modules.engine` -- composition happens in workflows

If the `StepFunction` type alias in `engine/types.py` causes circular import issues, use `TYPE_CHECKING` guard:
```python
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from returns.io import IOResult
    from adws.adw_modules.errors import PipelineError
    from adws.adw_modules.types import WorkflowContext

StepFunction = Callable[["WorkflowContext"], "IOResult[WorkflowContext, PipelineError]"]
```

### ShellResult Data Type

Add to `adws/adw_modules/types.py` (alongside WorkflowContext):
```python
@dataclass(frozen=True)
class ShellResult:
    """Result of a shell command execution."""
    return_code: int
    stdout: str
    stderr: str
    command: str
```

This is a domain type that steps receive from io_ops. It lives in `types.py`, not in `io_ops.py`.

### run_shell_command Implementation Pattern

The `run_shell_command` function in `io_ops.py` follows the established pattern: returns `IOResult`, catches specific exceptions, transforms to domain types.

```python
import subprocess

def run_shell_command(
    command: str,
    *,
    timeout: int | None = None,
    cwd: str | None = None,
) -> IOResult[ShellResult, PipelineError]:
    """Execute shell command. Returns IOResult, never raises."""
    try:
        result = subprocess.run(
            command,
            shell=True,  # noqa: S603
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return IOSuccess(ShellResult(
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=command,
        ))
    except subprocess.TimeoutExpired:
        return IOFailure(PipelineError(
            step_name="io_ops.run_shell_command",
            error_type="TimeoutError",
            message=f"Command timed out after {timeout}s: {command}",
            context={"command": command, "timeout": timeout},
        ))
    except FileNotFoundError:
        return IOFailure(PipelineError(
            step_name="io_ops.run_shell_command",
            error_type="FileNotFoundError",
            message=f"Command not found: {command}",
            context={"command": command},
        ))
    except OSError as exc:
        return IOFailure(PipelineError(
            step_name="io_ops.run_shell_command",
            error_type=type(exc).__name__,
            message=f"OS error running command: {exc}",
            context={"command": command},
        ))
```

**IMPORTANT on `shell=True`**: Using `shell=True` is required for shell command strings (like `npm test`, `uv run pytest`). Ruff S603 will flag `subprocess.run` with `shell=True`. Use `# noqa: S603` suppression since this is intentional behavior for shell step execution. Also suppress S602 (subprocess-popen-with-shell-equals-true) if triggered. Document the suppression rationale in the code.

**Note on nonzero exit codes**: A nonzero return code from `subprocess.run` is NOT an exception -- it is a valid `ShellResult` with `return_code != 0`. The step function (`execute_shell_step`) decides what to do with nonzero codes, not `run_shell_command`. This keeps io_ops functions pure I/O translators without domain logic.

### execute_shell_step Implementation Pattern

New step file: `adws/adw_modules/steps/execute_shell_step.py`

```python
"""Execute a shell command and capture results in workflow context."""
from returns.io import IOResult, IOSuccess, IOFailure

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import run_shell_command
from adws.adw_modules.types import WorkflowContext


def execute_shell_step(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]:
    """Execute shell command from context, capture output."""
    command = ctx.inputs.get("shell_command")
    if not isinstance(command, str) or not command:
        return IOFailure(PipelineError(
            step_name="execute_shell_step",
            error_type="ValueError",
            message="No shell_command found in context inputs",
            context={"inputs_keys": list(ctx.inputs.keys())},
        ))

    result = run_shell_command(command)

    def handle_success(shell_result):
        if shell_result.return_code != 0:
            return IOFailure(PipelineError(
                step_name="execute_shell_step",
                error_type="ShellCommandFailed",
                message=f"Command exited with code {shell_result.return_code}",
                context={
                    "command": command,
                    "return_code": shell_result.return_code,
                    "stdout": shell_result.stdout,
                    "stderr": shell_result.stderr,
                },
            ))
        return IOSuccess(ctx.merge_outputs({
            "shell_stdout": shell_result.stdout,
            "shell_stderr": shell_result.stderr,
            "shell_return_code": shell_result.return_code,
        }))

    return result.bind(handle_success)
```

Key design decisions:
- Command string comes from `ctx.inputs["shell_command"]` -- the engine sets this from the `Step.command` field
- Nonzero exit code produces `IOFailure` with full stdout/stderr context for debugging
- Success path merges stdout/stderr into `WorkflowContext.outputs`
- Uses `result.bind()` for monadic chaining (io_ops failure propagates automatically)

### Step Dataclass Enhancement

The `Step` dataclass in `engine/types.py` needs two new fields:
```python
@dataclass(frozen=True)
class Step:
    name: str
    function: str
    always_run: bool = False
    max_attempts: int = 1
    shell: bool = False     # NEW: if True, execute as shell command (FR11)
    command: str = ""        # NEW: shell command string (used when shell=True)
```

When `shell=True`:
- The engine uses `execute_shell_step` instead of an SDK call
- `command` is placed into `ctx.inputs["shell_command"]` before step execution
- The `function` field is ignored (or can be set to `"execute_shell_step"`)

When `shell=False` (default, backward-compatible):
- The engine uses the SDK call pattern from `function` field
- `command` is ignored

### Test Strategy

**Unit tests for `run_shell_command`** (in `adws/tests/adw_modules/test_io_ops.py`):

Mock target: `subprocess.run` (patch at `adws.adw_modules.io_ops.subprocess.run` or `subprocess.run` depending on import style)

Tests needed:
- `test_run_shell_command_success` -- mock subprocess.run returns CompletedProcess, verify ShellResult fields
- `test_run_shell_command_nonzero_exit` -- mock returns CompletedProcess with returncode=1, verify ShellResult still returned (NOT IOFailure)
- `test_run_shell_command_timeout` -- mock raises TimeoutExpired, verify IOFailure
- `test_run_shell_command_file_not_found` -- mock raises FileNotFoundError, verify IOFailure
- `test_run_shell_command_os_error` -- mock raises OSError, verify IOFailure
- `test_run_shell_command_with_cwd` -- verify cwd parameter is passed to subprocess
- `test_run_shell_command_with_timeout` -- verify timeout parameter is passed to subprocess

**Unit tests for `execute_shell_step`** (new file: `adws/tests/adw_modules/steps/test_execute_shell_step.py`):

Mock target: `adws.adw_modules.io_ops.run_shell_command`

Tests needed:
- `test_execute_shell_step_success` -- command succeeds, outputs in context
- `test_execute_shell_step_nonzero_exit` -- command fails (return_code != 0), IOFailure
- `test_execute_shell_step_missing_command` -- no shell_command in inputs, IOFailure
- `test_execute_shell_step_empty_command` -- empty string command, IOFailure
- `test_execute_shell_step_io_failure` -- run_shell_command returns IOFailure, propagates

**Unit tests for `ShellResult`** (in `adws/tests/adw_modules/test_types.py`):
- `test_shell_result_construction` -- all fields populated correctly
- `test_shell_result_frozen` -- attribute reassignment raises FrozenInstanceError

**Unit tests for `Step` changes** (in `adws/tests/adw_modules/engine/test_types.py`):
- `test_step_shell_defaults` -- verify shell=False and command="" by default
- `test_step_shell_command` -- verify Step(shell=True, command="npm test") construction
- `test_step_backward_compatible` -- existing Step construction still works

**Unit tests for `StepFunction` type alias** (in `adws/tests/adw_modules/engine/test_types.py`):
- `test_step_function_type_is_callable` -- verify it is a Callable type

### Ruff Considerations

- `S603` (subprocess-without-shell-equals-true) / `S602` (subprocess-popen-with-shell-equals-true): Suppress with `# noqa` in `run_shell_command`. This is intentional for shell command execution.
- `S108` (hardcoded temp directory): Avoid `/tmp/` in test data strings. Use `/some/path` instead.
- `E501` (line too long): Keep all lines under 88 characters.
- `PLR0911` (too many return statements): If `run_shell_command` has too many return statements, consolidate exception handlers.
- `FBT001`/`FBT002` (boolean positional/default): The `shell` field on Step dataclass is fine as a keyword-only dataclass field.

### Architecture Compliance

- **NFR10**: `io_ops.py` is the ONLY file that uses `subprocess` -- steps call `run_shell_command`, never `subprocess` directly
- **NFR9**: 100% line + branch coverage on all adws/ code
- **NFR11**: mypy strict mode -- `ShellResult` and `StepFunction` need proper type annotations
- **NFR12**: ruff ALL rules -- zero lint violations (with justified `# noqa` for S603)
- **FR11**: Developer can mark steps as shell commands for direct subprocess execution
- **Step creation checklist**: errors.py -> io_ops.py -> step -> __init__.py -> tests -> verify

### What NOT to Do

- Do NOT import `subprocess` in any step file -- only `io_ops.py` imports `subprocess`
- Do NOT make `run_shell_command` return IOFailure on nonzero exit code -- the step decides policy, io_ops does translation only
- Do NOT create a separate shell executor module -- shell execution is an io_ops function, shell step is a step
- Do NOT change existing test assertions or existing function signatures
- Do NOT add `StepFunction` to `adws/adw_modules/types.py` -- it belongs in `engine/types.py` because it is the engine's contract
- Do NOT change `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`
- Do NOT use `subprocess.Popen` -- use `subprocess.run` for simplicity
- Do NOT add `shell=True` as a `subprocess.run` call with `shell=False` -- we need `shell=True` for command strings like `npm test`
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/execute_shell_step.py` -- new step module
- `adws/tests/adw_modules/steps/test_execute_shell_step.py` -- new test file

Files to modify:
- `adws/adw_modules/types.py` -- add `ShellResult` dataclass
- `adws/adw_modules/errors.py` -- no structural change needed (PipelineError is already generic enough for shell errors via `error_type` field)
- `adws/adw_modules/io_ops.py` -- add `run_shell_command` function and `subprocess` import
- `adws/adw_modules/engine/types.py` -- add `shell`, `command` fields to `Step`; add `StepFunction` type alias
- `adws/adw_modules/steps/__init__.py` -- export `execute_shell_step`
- `adws/tests/adw_modules/test_io_ops.py` -- add `run_shell_command` tests
- `adws/tests/adw_modules/test_types.py` -- add `ShellResult` tests
- `adws/tests/adw_modules/engine/test_types.py` -- add `Step` shell field tests and `StepFunction` tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist, io_ops function pattern, step internal structure
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK boundary design, io_ops as single mock point
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, shell verification steps
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] -- Next story (engine core) depends on step types from this story
- [Source: _bmad-output/implementation-artifacts/2-2-io-ops-sdk-client-and-enemy-unit-tests.md] -- Previous story learnings, current code state
- [Source: adws/adw_modules/io_ops.py] -- Current io_ops (3 functions + async helper)
- [Source: adws/adw_modules/types.py] -- Current types (WorkflowContext, AdwsRequest, AdwsResponse)
- [Source: adws/adw_modules/engine/types.py] -- Current engine types (Step, Workflow)
- [Source: adws/adw_modules/errors.py] -- Current errors (PipelineError)
- [Source: adws/adw_modules/steps/check_sdk_available.py] -- Reference step implementation
- [Source: adws/tests/conftest.py] -- Shared test fixtures

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

From Story 2.2 learnings:
- **IOResult[Success, Error]**: Success type comes first (established in Story 2.1, confirmed in 2.2)
- **Async handling**: `asyncio.run()` bridges async SDK to synchronous io_ops pattern
- **`_NoResultError`**: Internal exception class pattern for io_ops-internal control flow
- **builtins.__import__ patching**: For testing import failures (e.g., check_sdk_import)
- **ruff ARG001**: Added to test file ignores for unused fixture parameters
- **Coverage omit**: `conftest.py` and `enemy/*` excluded from coverage measurement
- **PermissionMode Literal**: Type safety via Literal type for constrained string values
- **DEFAULT_CLAUDE_MODEL**: Constants extracted to module level, not hardcoded in models

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen
- **ruff S108**: Avoid `/tmp/` literal strings in test data
- **ruff E501**: Keep docstrings under 88 chars

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: ShellResult frozen dataclass added to types.py; StepFunction type alias added to engine/types.py using TYPE_CHECKING guard to avoid circular imports; Callable imported from collections.abc per ruff UP035
- Task 2: PipelineError is already generic enough for shell errors via error_type field; added tests confirming shell-specific error patterns serialize correctly via to_dict()
- Task 3: run_shell_command added to io_ops.py using subprocess.run with shell=True (noqa S602); handles TimeoutExpired, FileNotFoundError, OSError; nonzero exit codes are valid ShellResult (not IOFailure); 7 tests added
- Task 4: Step dataclass extended with shell (bool, default False) and command (str, default "") fields; execute_shell_step reads shell_command from ctx.inputs, returns IOFailure on nonzero exit; exported from steps/__init__.py; S604 added to test file ignores (false positive on dataclass field)
- Task 5: All 86 tests pass, 100% line+branch coverage, ruff zero violations, mypy strict passes

### Change Log

- 2026-02-01: Story created with comprehensive context from all planning artifacts, architecture patterns, and previous story intelligence
- 2026-02-01: All 5 tasks implemented via strict TDD. 21 new tests added (65 -> 86). Story moved to review.
- 2026-02-01: Senior developer review completed. 4 issues found (all MEDIUM), all fixed. 2 new tests added (86 -> 88). Story moved to done.

### File List

**Files created:**
- `adws/adw_modules/steps/execute_shell_step.py` -- shell command step module
- `adws/tests/adw_modules/steps/test_execute_shell_step.py` -- tests for execute_shell_step (7 tests)

**Files modified:**
- `adws/adw_modules/types.py` -- added ShellResult frozen dataclass
- `adws/adw_modules/io_ops.py` -- added run_shell_command function with subprocess import
- `adws/adw_modules/engine/types.py` -- added StepFunction type alias, shell/command fields to Step
- `adws/adw_modules/steps/__init__.py` -- export execute_shell_step
- `adws/tests/adw_modules/test_types.py` -- added ShellResult tests (2 tests)
- `adws/tests/adw_modules/test_io_ops.py` -- added run_shell_command tests (8 tests)
- `adws/tests/adw_modules/engine/test_types.py` -- added Step shell/StepFunction tests (4 tests)
- `adws/tests/adw_modules/test_errors.py` -- added shell error serialization tests (2 tests)
- `pyproject.toml` -- S604 removed from global test ignores (moved to inline noqa)

## Senior Developer Review (AI)

**Reviewer:** Claude Opus 4.5 (claude-opus-4-5-20251101)
**Date:** 2026-02-01
**Verdict:** PASS -- all issues fixed, all quality gates green

### AC Verification

| AC | Status | Notes |
|----|--------|-------|
| AC1: Step signature `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` | PASS | `execute_shell_step` and `check_sdk_available` both follow the exact signature. Absolute imports used throughout. One public function per step file. |
| AC2: `run_shell_command` in io_ops.py | PASS | Returns `IOResult[ShellResult, PipelineError]`. Catches `TimeoutExpired`, `FileNotFoundError`, `OSError`. Captures stdout/stderr. |
| AC3: Shell steps via `run_shell_command`, output in `WorkflowContext.outputs` | PASS | `execute_shell_step` reads `shell_command` from `ctx.inputs`, calls `run_shell_command`, merges stdout/stderr/return_code into outputs. |
| AC4: Success and failure paths tested, 100% coverage | PASS | All paths tested. 100% line + branch coverage confirmed. |
| AC5: All tests pass, 100% coverage, mypy strict, ruff zero violations | PASS | 88 tests pass. 100% coverage. mypy strict clean. ruff clean. |

### Issues Found and Fixed

| # | Severity | File | Issue | Fix |
|---|----------|------|-------|-----|
| 1 | MEDIUM | `adws/tests/adw_modules/engine/test_types.py:75` | **Tautological assertion in StepFunction test.** `assert origin is Callable or origin is not None` always passes for any generic type (e.g. `list[int]` would pass). The test was useless -- it could never fail for a wrong type. | Replaced with assertion that checks `origin is Callable` strictly, validates arg count is 2, and verifies param/return type strings contain `WorkflowContext` and `IOResult`. |
| 2 | MEDIUM | `pyproject.toml:39` | **Overly broad S604 ruff suppression.** S604 (`call-with-shell-equals-true`) was suppressed globally for all test files, but only triggered on one dataclass constructor `Step(shell=True)` -- a false positive. Global suppression could mask real security violations in future test code. | Removed S604 from global `per-file-ignores`. Added inline `# noqa: S604` on the specific `Step()` call in `test_step_shell_command`. |
| 3 | MEDIUM | `adws/adw_modules/steps/execute_shell_step.py:19` | **Whitespace-only command passes validation.** `"   "` (whitespace only) is truthy in Python, so `not command` is False, bypassing the guard. A whitespace-only string would be sent to `subprocess.run`. | Changed validation from `not command` to `not command.strip()`. Added `test_execute_shell_step_whitespace_only_command` test. |
| 4 | MEDIUM | `adws/tests/adw_modules/test_io_ops.py` | **No test verifies critical subprocess.run flags.** The safety-critical flags `shell=True`, `capture_output=True`, `text=True`, `check=False` had zero test coverage. A regression removing any of these would go undetected. | Added `test_run_shell_command_passes_critical_flags` that asserts all four flags on the mock's `call_args.kwargs`. |

### Quality Gate Results (Post-Fix)

```
Tests:    88 passed, 2 deselected (enemy tests)
Coverage: 100% line + branch (808 statements, 24 branches, 0 missing)
Ruff:     All checks passed
Mypy:     Success: no issues found in 27 source files
```

### Low-Severity Observations (Not Fixed)

- `test_execute_shell_step_nonzero_exit` does not assert `error.context["command"]` or `error.context["stdout"]`, only `return_code` and `stderr`. These fields ARE present in the implementation but not verified by tests. Low risk since the success path test covers the full output set.
- Test docstrings still say "RED: ... does not exist yet" from TDD phase. These are cosmetic artifacts of the TDD workflow and do not affect correctness.

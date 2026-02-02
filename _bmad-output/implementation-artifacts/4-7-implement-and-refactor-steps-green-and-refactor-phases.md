# Story 4.7: implement & refactor Steps (GREEN & REFACTOR Phases)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want GREEN and REFACTOR phase steps using dedicated agent roles,
so that implementation and cleanup are separate concerns with distinct system prompts.

## Acceptance Criteria

1. **Given** the step function signature from Epic 2, **When** `implement_step` executes (GREEN phase), **Then** it makes a fresh SDK call via `ClaudeSDKClient` with an implementation agent system prompt **And** the agent receives the Beads issue description as context (NFR19 -- never reads BMAD files) **And** the agent receives accumulated feedback from any previous verify failures (FR17).

2. **Given** the step function signature, **When** `refactor` step executes (REFACTOR phase), **Then** it makes a fresh SDK call via `ClaudeSDKClient` with a refactor agent system prompt (Decision 6) **And** the agent focuses on cleanup without changing behavior.

3. **Given** both SDK steps, **When** I inspect the test suite, **Then** EUTs exist for both io_ops SDK functions proving real API communication (EUT* constraint) **And** unit tests with mocked io_ops exist for fast CI feedback **And** 100% coverage is maintained (NFR9).

4. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Define `GREEN_PHASE_SYSTEM_PROMPT` constant for the implementation agent (AC: #1)
  - [x]1.1 RED: Write test for `GREEN_PHASE_SYSTEM_PROMPT` constant in `adws/adw_modules/steps/implement_step.py`. Verify it is a non-empty string. Verify it contains key instructions: "implement minimum code to pass", "do not refactor", "do not add features beyond what tests require", "all tests must pass", "100% coverage". Verify it mentions the io_ops boundary pattern. Verify it mentions `bypassPermissions` mode for file writes.
  - [x]1.2 GREEN: Implement `GREEN_PHASE_SYSTEM_PROMPT` as a module-level constant in `adws/adw_modules/steps/implement_step.py`.
  - [x]1.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `_build_green_phase_request()` pure helper function (AC: #1)
  - [x]2.1 RED: Write test for `_build_green_phase_request(ctx: WorkflowContext) -> AdwsRequest`. Given a WorkflowContext with `inputs={"issue_description": "Story content here...", "test_files": ["adws/tests/test_foo.py"], "red_gate_passed": True}`, verify it returns an `AdwsRequest` with `system_prompt=GREEN_PHASE_SYSTEM_PROMPT`, `prompt` containing the issue description and test file information, `model` set to `DEFAULT_CLAUDE_MODEL`, `permission_mode="bypassPermissions"`.
  - [x]2.2 GREEN: Implement `_build_green_phase_request` in `adws/adw_modules/steps/implement_step.py`. Pure function that constructs the `AdwsRequest` from context inputs.
  - [x]2.3 RED: Write test for `_build_green_phase_request` when `issue_description` is missing from inputs. Verify it still produces a valid `AdwsRequest` with a prompt indicating no issue description was provided (graceful degradation, matching `write_failing_tests` pattern).
  - [x]2.4 GREEN: Implement missing-input graceful degradation.
  - [x]2.5 RED: Write test for `_build_green_phase_request` when ctx has `feedback` entries (from previous failed verify_tests_pass attempts). Verify the prompt includes the accumulated feedback so the implementation agent can learn from prior failures (FR17).
  - [x]2.6 GREEN: Implement feedback inclusion in the prompt.
  - [x]2.7 RED: Write test for `_build_green_phase_request` when `test_files` is present in inputs (promoted from write_failing_tests outputs). Verify the prompt includes the test file paths so the agent knows which tests to make pass.
  - [x]2.8 GREEN: Implement test_files inclusion in the prompt.
  - [x]2.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create `_extract_implementation_files()` pure helper function (AC: #1)
  - [x]3.1 RED: Write test for `_extract_implementation_files(response: AdwsResponse) -> list[str]`. Given an `AdwsResponse` with `result` containing text mentioning source file paths like `adws/adw_modules/steps/new_step.py`, verify it extracts the paths as a list of strings. Verify it only extracts paths matching the `adws/adw_modules/` prefix pattern (source files, not test files).
  - [x]3.2 GREEN: Implement `_extract_implementation_files` in `adws/adw_modules/steps/implement_step.py`. Uses regex to find source file paths in the response result text.
  - [x]3.3 RED: Write test for `_extract_implementation_files` when the response contains no recognizable source file paths. Verify it returns an empty list (graceful, same as `_extract_test_files` pattern).
  - [x]3.4 GREEN: Implement empty-result handling.
  - [x]3.5 RED: Write test for `_extract_implementation_files` when the response `result` is None (error response). Verify it returns an empty list.
  - [x]3.6 GREEN: Implement None-result handling.
  - [x]3.7 RED: Write test for `_extract_implementation_files` with duplicate paths in response. Verify returned list has no duplicates (deduplication) and preserves insertion order.
  - [x]3.8 GREEN: Implement deduplication with insertion order preservation (same `seen` set + append pattern as `_extract_test_files`).
  - [x]3.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create `_process_implement_response()` and `implement_step()` step function (AC: #1)
  - [x]4.1 RED: Write test for `_process_implement_response(response: AdwsResponse, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given an `AdwsResponse` with `is_error=False` and result mentioning source files, verify it returns `IOSuccess(WorkflowContext)` with `outputs` containing `{"implementation_files": [...], "green_phase_complete": True}`.
  - [x]4.2 GREEN: Implement `_process_implement_response` in `adws/adw_modules/steps/implement_step.py`.
  - [x]4.3 RED: Write test for `_process_implement_response` when `is_error=True`. Verify it returns `IOFailure(PipelineError)` with `error_type="SdkResponseError"` and `step_name="implement_step"`.
  - [x]4.4 GREEN: Implement SDK error response handling.
  - [x]4.5 RED: Write test for `implement_step(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `io_ops.execute_sdk_call` returns `IOSuccess(AdwsResponse(result="Modified files: adws/adw_modules/...", is_error=False))`, verify it returns `IOSuccess(WorkflowContext)` with `outputs` containing `implementation_files` and `green_phase_complete=True`.
  - [x]4.6 GREEN: Implement `implement_step` following the `write_failing_tests` pattern: build request -> call SDK -> process response via `.lash()` and `.bind()`.
  - [x]4.7 RED: Write test for `implement_step` when `io_ops.execute_sdk_call` returns `IOFailure(PipelineError(...))`. Verify it returns `IOFailure(PipelineError)` with `step_name="implement_step"` and `error_type` preserved from the io_ops error.
  - [x]4.8 GREEN: Implement SDK call failure handling using `.lash()` for failure re-attribution.
  - [x]4.9 RED: Write test for `implement_step` when SDK response has `is_error=True`. Verify it returns `IOFailure(PipelineError)` with `error_type="SdkResponseError"`.
  - [x]4.10 GREEN: Implement is_error response handling.
  - [x]4.11 RED: Write test for `implement_step` when SDK response is successful but `_extract_implementation_files` returns empty list. Verify it still returns `IOSuccess(WorkflowContext)` with `outputs={"implementation_files": [], "green_phase_complete": True}` -- the step succeeds even if no source files are explicitly identified.
  - [x]4.12 GREEN: Implement empty implementation file list handling.
  - [x]4.13 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Define `REFACTOR_PHASE_SYSTEM_PROMPT` constant for the refactor agent (AC: #2)
  - [x]5.1 RED: Write test for `REFACTOR_PHASE_SYSTEM_PROMPT` constant in `adws/adw_modules/steps/refactor_step.py`. Verify it is a non-empty string. Verify it contains key instructions: "refactor only", "do not change behavior", "all tests must still pass", "improve code quality", "follow established patterns". Verify it mentions `bypassPermissions` mode.
  - [x]5.2 GREEN: Implement `REFACTOR_PHASE_SYSTEM_PROMPT` as a module-level constant in `adws/adw_modules/steps/refactor_step.py`.
  - [x]5.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Create `_build_refactor_phase_request()` pure helper function (AC: #2)
  - [x]6.1 RED: Write test for `_build_refactor_phase_request(ctx: WorkflowContext) -> AdwsRequest`. Given a WorkflowContext with `inputs={"issue_description": "Story content...", "implementation_files": ["adws/adw_modules/steps/new_step.py"], "green_phase_complete": True}`, verify it returns an `AdwsRequest` with `system_prompt=REFACTOR_PHASE_SYSTEM_PROMPT`, `prompt` containing the issue description and implementation file information, `model` set to `DEFAULT_CLAUDE_MODEL`, `permission_mode="bypassPermissions"`.
  - [x]6.2 GREEN: Implement `_build_refactor_phase_request` in `adws/adw_modules/steps/refactor_step.py`. Pure function.
  - [x]6.3 RED: Write test for `_build_refactor_phase_request` when `issue_description` is missing from inputs. Verify graceful degradation (valid AdwsRequest with fallback prompt).
  - [x]6.4 GREEN: Implement missing-input graceful degradation.
  - [x]6.5 RED: Write test for `_build_refactor_phase_request` when `implementation_files` is present in inputs (promoted from implement_step outputs). Verify the prompt includes the file paths so the refactor agent knows which files were modified.
  - [x]6.6 GREEN: Implement implementation_files inclusion in the prompt.
  - [x]6.7 RED: Write test for `_build_refactor_phase_request` when ctx has `feedback` entries. Verify feedback is included in the prompt.
  - [x]6.8 GREEN: Implement feedback inclusion.
  - [x]6.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 7: Create `_extract_refactored_files()` pure helper function (AC: #2)
  - [x]7.1 RED: Write test for `_extract_refactored_files(response: AdwsResponse) -> list[str]`. Given an `AdwsResponse` with `result` containing text mentioning source file paths like `adws/adw_modules/steps/new_step.py`, verify it extracts paths as a deduplicated list with insertion order preserved. Pattern: `adws/` prefix (may include both source and test files modified during refactor).
  - [x]7.2 GREEN: Implement `_extract_refactored_files` in `adws/adw_modules/steps/refactor_step.py`. Uses regex to find `adws/` paths.
  - [x]7.3 RED: Write test for `_extract_refactored_files` with no recognizable paths. Verify empty list.
  - [x]7.4 GREEN: Implement empty-result handling.
  - [x]7.5 RED: Write test for `_extract_refactored_files` with None result. Verify empty list.
  - [x]7.6 GREEN: Implement None-result handling.
  - [x]7.7 RED: Write test for `_extract_refactored_files` with duplicates. Verify deduplication with insertion order.
  - [x]7.8 GREEN: Implement deduplication.
  - [x]7.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 8: Create `_process_refactor_response()` and `refactor_step()` step function (AC: #2)
  - [x]8.1 RED: Write test for `_process_refactor_response(response: AdwsResponse, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given an `AdwsResponse` with `is_error=False`, verify it returns `IOSuccess(WorkflowContext)` with `outputs` containing `{"refactored_files": [...], "refactor_phase_complete": True}`.
  - [x]8.2 GREEN: Implement `_process_refactor_response`.
  - [x]8.3 RED: Write test for `_process_refactor_response` when `is_error=True`. Verify `IOFailure(PipelineError)` with `error_type="SdkResponseError"` and `step_name="refactor_step"`.
  - [x]8.4 GREEN: Implement SDK error response handling.
  - [x]8.5 RED: Write test for `refactor_step(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `io_ops.execute_sdk_call` returns `IOSuccess(AdwsResponse(result="Refactored files: adws/adw_modules/...", is_error=False))`, verify it returns `IOSuccess(WorkflowContext)` with outputs containing `refactored_files` and `refactor_phase_complete=True`.
  - [x]8.6 GREEN: Implement `refactor_step` following the same ROP pattern as `write_failing_tests` and `implement_step`.
  - [x]8.7 RED: Write test for `refactor_step` when `io_ops.execute_sdk_call` returns `IOFailure(PipelineError(...))`. Verify `IOFailure(PipelineError)` with `step_name="refactor_step"` and error preserved.
  - [x]8.8 GREEN: Implement SDK call failure handling using `.lash()` for failure re-attribution.
  - [x]8.9 RED: Write test for `refactor_step` when SDK response has `is_error=True`. Verify `IOFailure(PipelineError)` with `error_type="SdkResponseError"`.
  - [x]8.10 GREEN: Implement is_error response handling.
  - [x]8.11 RED: Write test for `refactor_step` when SDK response is successful but `_extract_refactored_files` returns empty list. Verify `IOSuccess` with `outputs={"refactored_files": [], "refactor_phase_complete": True}`.
  - [x]8.12 GREEN: Implement empty refactored file list handling.
  - [x]8.13 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 9: Register both steps in step infrastructure (AC: #1, #2)
  - [x]9.1 RED: Write test that `implement_step` is importable from `adws.adw_modules.steps` (via `steps/__init__.py`).
  - [x]9.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x]9.3 RED: Write test that `refactor_step` is importable from `adws.adw_modules.steps`.
  - [x]9.4 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x]9.5 RED: Write test that `_STEP_REGISTRY` in `engine/executor.py` contains `"implement_step"` mapped to the correct function.
  - [x]9.6 GREEN: Add `"implement_step"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x]9.7 RED: Write test that `_STEP_REGISTRY` in `engine/executor.py` contains `"refactor_step"` mapped to the correct function.
  - [x]9.8 GREEN: Add `"refactor_step"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x]9.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 10: Create Enemy Unit Tests for implement_step and refactor_step SDK calls (AC: #3)
  - [x]10.1 RED: Write EUT (`@pytest.mark.enemy`) in `adws/tests/enemy/test_implement_step_sdk.py` that tests `implement_step` with a REAL SDK call. Build a WorkflowContext with a simple issue_description input and test_files list. Call `implement_step(ctx)`. Verify the result is `IOSuccess` and the response is an `AdwsResponse` with `is_error=False`. Use a constrained prompt (max_turns=1) and safe prompt to avoid filesystem side effects, following the write_failing_tests EUT pattern.
  - [x]10.2 GREEN: Ensure the step works with the real SDK.
  - [x]10.3 RED: Write EUT (`@pytest.mark.enemy`) in `adws/tests/enemy/test_refactor_step_sdk.py` that tests `refactor_step` with a REAL SDK call. Build a WorkflowContext with a simple issue_description and implementation_files list. Call `refactor_step(ctx)`. Verify `IOSuccess` with `is_error=False`. Use constrained prompt (max_turns=1) to avoid side effects.
  - [x]10.4 GREEN: Ensure the step works with the real SDK.
  - [x]10.5 REFACTOR: Review EUTs for clarity and coverage.

- [x] Task 11: Integration tests -- full step flows (AC: #1, #2, #3)
  - [x]11.1 RED: Write integration test for `implement_step`: invoke with WorkflowContext containing `{"issue_description": "Implement email validation", "test_files": ["adws/tests/test_email.py"], "red_gate_passed": True}` in inputs and feedback `["Previous attempt: AssertionError in test_email"]`. Mock `io_ops.execute_sdk_call` to return successful response. Verify: IOSuccess returned, outputs contain implementation_files, green_phase_complete is True, the request prompt sent to SDK included issue description, test files, and feedback.
  - [x]11.2 GREEN: Ensure implement_step integration path works with mocked io_ops.
  - [x]11.3 RED: Write integration test for `implement_step` with io_ops returning IOFailure. Verify IOFailure propagates with `step_name="implement_step"`.
  - [x]11.4 GREEN: Ensure failure path works.
  - [x]11.5 RED: Write integration test for `implement_step` with `AdwsResponse` that has `is_error=True` and `error_message="Rate limited"`. Verify IOFailure with `error_type="SdkResponseError"`.
  - [x]11.6 GREEN: Ensure SDK error response path works.
  - [x]11.7 RED: Write integration test for `refactor_step`: invoke with WorkflowContext containing `{"issue_description": "...", "implementation_files": ["adws/adw_modules/steps/new_step.py"], "green_phase_complete": True}`. Mock `io_ops.execute_sdk_call` to return successful response. Verify: IOSuccess, outputs contain refactored_files and refactor_phase_complete.
  - [x]11.8 GREEN: Ensure refactor_step integration path works.
  - [x]11.9 RED: Write integration test for `refactor_step` with io_ops returning IOFailure. Verify IOFailure with `step_name="refactor_step"`.
  - [x]11.10 GREEN: Ensure failure path works.
  - [x]11.11 RED: Write integration test for `refactor_step` with `is_error=True` response. Verify IOFailure with `error_type="SdkResponseError"`.
  - [x]11.12 GREEN: Ensure SDK error response path works.
  - [x]11.13 REFACTOR: Clean up integration tests, verify all scenarios covered.

- [x] Task 12: Verify full integration and quality gates (AC: #4)
  - [x]12.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x]12.2 Run `uv run mypy adws/` -- strict mode passes
  - [x]12.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 4.6)

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

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`, `write_failing_tests`, `verify_tests_fail`.

**engine/executor.py** has 8 functions. `_STEP_REGISTRY` has 8 entries: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `write_failing_tests`, `verify_tests_fail`.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants), `load_workflow()`, `list_workflows()`, 5 registered workflows. `_IMPLEMENT_VERIFY_CLOSE` currently has empty steps list (placeholder for Story 4.8).

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 491 tests (excluding 3 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: Two Steps, One Pattern

Both `implement_step` and `refactor_step` follow the exact same architectural pattern as `write_failing_tests` (Story 4.5). Each is an SDK step that:
1. Builds an `AdwsRequest` with a phase-specific system prompt
2. Calls `io_ops.execute_sdk_call`
3. Processes the response to extract file paths and update context

The ONLY differences are:
- The system prompt content (GREEN vs REFACTOR focus)
- The context output keys (`implementation_files` vs `refactored_files`, `green_phase_complete` vs `refactor_phase_complete`)
- The step_name used in PipelineError attribution
- The file extraction pattern (GREEN extracts `adws/adw_modules/` paths; REFACTOR extracts any `adws/` paths since it may touch both source and tests)

```
verify_tests_fail outputs (ctx.inputs after promote_outputs_to_inputs)
    |
    v
implement_step (SDK step -- implementation agent, GREEN phase)
    |
    v (calls io_ops.execute_sdk_call with GREEN_PHASE_SYSTEM_PROMPT)
    |
    v (extracts implementation file paths from response)
    |
    v
WorkflowContext.outputs = {"implementation_files": [...], "green_phase_complete": True}
    |
    v (engine promotes outputs to inputs for next step)
    |
    v
verify_tests_pass (shell step -- confirms GREEN) -- Story 4.8
    |
    v
refactor_step (SDK step -- refactor agent, REFACTOR phase)
    |
    v (calls io_ops.execute_sdk_call with REFACTOR_PHASE_SYSTEM_PROMPT)
    |
    v (extracts refactored file paths from response)
    |
    v
WorkflowContext.outputs = {"refactored_files": [...], "refactor_phase_complete": True}
```

### Design: Step Naming Convention

The step file and function are named `implement_step` (not just `implement`) to avoid collision with Python's reserved keyword considerations and to match the pattern that each step file contains one public function matching the filename:
- `implement_step.py` contains `implement_step()`
- `refactor_step.py` contains `refactor_step()`

The engine `_STEP_REGISTRY` entries use these names: `"implement_step"` and `"refactor_step"`.

### Design: GREEN Phase System Prompt

The system prompt is the architectural control that makes this an "implementation agent" (Decision 6). It must contain:

```python
GREEN_PHASE_SYSTEM_PROMPT = """\
You are a TDD Implementation Agent in the GREEN phase. Your ONLY \
job is to write the minimum code to make failing tests pass.

## Rules
1. Write MINIMUM implementation code to make all tests pass.
2. Do NOT refactor. Do NOT add features beyond what tests require.
3. Do NOT modify any test files.
4. All tests must pass after your changes.
5. Maintain 100% line and branch coverage.

## Implementation Conventions
- All I/O must go through adws/adw_modules/io_ops.py (NFR10)
- Use absolute imports: from adws.adw_modules.X import Y
- One public function per step module matching the filename
- Follow existing patterns in the codebase

## Output
List all source files you created or modified, one per line, \
with their full paths.
"""
```

### Design: REFACTOR Phase System Prompt

```python
REFACTOR_PHASE_SYSTEM_PROMPT = """\
You are a TDD Refactor Agent in the REFACTOR phase. Your ONLY \
job is to clean up code without changing behavior.

## Rules
1. Refactor only. Do NOT change behavior.
2. All tests must still pass after your changes.
3. Maintain 100% line and branch coverage.
4. Improve readability, reduce duplication, simplify.
5. Follow established project patterns.

## Refactoring Conventions
- All I/O must remain behind adws/adw_modules/io_ops.py (NFR10)
- Use absolute imports: from adws.adw_modules.X import Y
- Preserve existing function signatures
- Do NOT add new features or change test expectations

## Output
List all files you modified, one per line, with their full paths.
"""
```

### Design: File Extraction Patterns

**implement_step** extracts source files: `r'(adws/adw_modules/\S+\.py)'`
- Only matches production code paths under `adws/adw_modules/`
- Excludes test files (the GREEN phase should not modify tests)

**refactor_step** extracts any project files: `r'(adws/\S+\.py)'`
- Matches both source and test files under `adws/`
- Refactoring may touch test helper organization, imports, etc.
- Broader pattern since refactoring can span more of the codebase

Both use the same deduplication pattern as `_extract_test_files`: `seen` set + ordered append.

### Design: Context Flow

**implement_step input context (from verify_tests_fail via promote_outputs_to_inputs):**
```python
ctx.inputs = {
    "issue_description": "Full Beads issue description...",
    "issue_id": "BEADS-123",
    # From write_failing_tests (promoted):
    "test_files": ["adws/tests/steps/test_new_step.py", ...],
    "red_phase_complete": True,
    # From verify_tests_fail (promoted):
    "red_gate_passed": True,
    "failure_types": ["ImportError", ...],
    "failure_count": 3,
}
ctx.feedback = [
    # From previous failed verify_tests_pass attempts (if retried):
    "Retry 1/3 for step 'verify_tests_pass': 2 tests failed",
]
```

**implement_step output context:**
```python
ctx.outputs = {
    "implementation_files": ["adws/adw_modules/steps/new_step.py", ...],
    "green_phase_complete": True,
}
```

**refactor_step input context (from verify_tests_pass via promote_outputs_to_inputs):**
```python
ctx.inputs = {
    # Everything accumulated from prior steps:
    "issue_description": "...",
    "test_files": [...],
    "implementation_files": [...],
    "green_phase_complete": True,
    # ... etc
}
```

**refactor_step output context:**
```python
ctx.outputs = {
    "refactored_files": ["adws/adw_modules/steps/new_step.py", ...],
    "refactor_phase_complete": True,
}
```

### Design: AdwsRequest Configuration

Both steps use the same request configuration pattern:

```python
AdwsRequest(
    model=DEFAULT_CLAUDE_MODEL,
    system_prompt=<phase-specific prompt>,
    prompt=<constructed from issue_description + test_files/implementation_files + feedback>,
    permission_mode="bypassPermissions",  # Agents need to write/modify files
    max_turns=None,  # Let the agent work until done
)
```

The `permission_mode="bypassPermissions"` is critical for both steps -- the implementation agent needs to create/modify source files, and the refactor agent needs to modify existing files. Without this, the SDK would require user approval for each file write.

### Design: Step Registration

Both steps are registered in two places each:
1. `steps/__init__.py` -- exported for import
2. `engine/executor.py` `_STEP_REGISTRY` -- registered for engine dispatch

After registration, the `implement_verify_close` workflow (Story 4.8) can reference them as:
- `Step(name="implement", function="implement_step")`
- `Step(name="refactor", function="refactor_step")`

**NOTE:** This story does NOT update the `_IMPLEMENT_VERIFY_CLOSE` workflow definition. That is Story 4.8's responsibility. This story only creates and registers the steps.

### Test Strategy

**New test files** (one per step module + EUTs):
- `adws/tests/adw_modules/steps/test_implement_step.py` -- tests for GREEN_PHASE_SYSTEM_PROMPT, _build_green_phase_request, _extract_implementation_files, _process_implement_response, implement_step (unit + integration)
- `adws/tests/adw_modules/steps/test_refactor_step.py` -- tests for REFACTOR_PHASE_SYSTEM_PROMPT, _build_refactor_phase_request, _extract_refactored_files, _process_refactor_response, refactor_step (unit + integration)
- `adws/tests/enemy/test_implement_step_sdk.py` -- EUT for implement_step real SDK call
- `adws/tests/enemy/test_refactor_step_sdk.py` -- EUT for refactor_step real SDK call

**Modified test files**:
- Tests for `_STEP_REGISTRY` in executor tests -- verify registry contains `"implement_step"` and `"refactor_step"`
- `steps/__init__.py` wiring tests -- verify both steps are importable from `adws.adw_modules.steps`

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_green_phase_system_prompt_not_empty`
- `test_green_phase_system_prompt_contains_minimum_code`
- `test_green_phase_system_prompt_contains_no_refactor`
- `test_green_phase_system_prompt_contains_io_ops_boundary`
- `test_build_green_phase_request_with_description`
- `test_build_green_phase_request_no_description`
- `test_build_green_phase_request_with_feedback`
- `test_build_green_phase_request_with_test_files`
- `test_extract_implementation_files_single_file`
- `test_extract_implementation_files_multiple_files`
- `test_extract_implementation_files_no_matches`
- `test_extract_implementation_files_none_result`
- `test_extract_implementation_files_deduplication`
- `test_process_implement_response_success`
- `test_process_implement_response_is_error`
- `test_implement_step_success`
- `test_implement_step_sdk_failure`
- `test_implement_step_sdk_error_response`
- `test_implement_step_empty_implementation_files`
- `test_implement_step_step_registry`
- `test_implement_step_importable`
- `test_refactor_phase_system_prompt_not_empty`
- `test_refactor_phase_system_prompt_contains_refactor_only`
- `test_refactor_phase_system_prompt_contains_no_behavior_change`
- `test_build_refactor_phase_request_with_description`
- `test_build_refactor_phase_request_no_description`
- `test_build_refactor_phase_request_with_feedback`
- `test_build_refactor_phase_request_with_implementation_files`
- `test_extract_refactored_files_single_file`
- `test_extract_refactored_files_no_matches`
- `test_extract_refactored_files_none_result`
- `test_extract_refactored_files_deduplication`
- `test_process_refactor_response_success`
- `test_process_refactor_response_is_error`
- `test_refactor_step_success`
- `test_refactor_step_sdk_failure`
- `test_refactor_step_sdk_error_response`
- `test_refactor_step_empty_refactored_files`
- `test_refactor_step_step_registry`
- `test_refactor_step_importable`

**Mock targets for step tests**:
- `adws.adw_modules.io_ops.execute_sdk_call` -- mock SDK call for unit tests (same target as write_failing_tests)

**EUTs** (enemy tests):
- NO mocking at all
- Real `ANTHROPIC_API_KEY` required
- Real SDK call through `execute_sdk_call` -> `_execute_sdk_call_async` -> `claude_agent_sdk.query`
- Use constrained prompt (max_turns=1) and safe prompt to avoid filesystem side effects
- Follow the write_failing_tests EUT pattern (Option A: call `io_ops.execute_sdk_call` directly with constrained prompt)

### EUT Safety Consideration

Both EUTs must be designed carefully because `implement_step` and `refactor_step` with `permission_mode="bypassPermissions"` could modify the filesystem. For each EUT:

**Pattern (same as Story 4.5 EUT):** Create a specialized test that calls `io_ops.execute_sdk_call` directly with a constrained prompt (e.g., "Respond with: I would modify the following files: adws/adw_modules/steps/example.py") rather than the full step function. This tests the SDK round-trip without filesystem side effects.

The EUT validates that `io_ops.execute_sdk_call` works with the GREEN/REFACTOR phase request format (AdwsRequest with phase-specific system_prompt, permission_mode, etc.). It does NOT need to validate the agent actually writes good code -- that is the verify_tests_pass step's job.

### Ruff Considerations

- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files.
- `E501` (line too long): Keep all lines under 88 characters. System prompt strings should use implicit string concatenation or backslash continuation.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.
- `FBT003` (boolean positional in return): `green_phase_complete=True` and `refactor_phase_complete=True` in outputs dicts are dict values, not function parameters -- no issue.
- `ERA001` (commented out code): Do not leave commented-out code in prompt constants.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- both steps return IOResult, never raise.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Both steps call `io_ops.execute_sdk_call` for the SDK interaction.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR18**: Claude via SDK API only (through `io_ops.execute_sdk_call`).
- **NFR19**: Never reads BMAD files -- issue description comes from `ctx.inputs["issue_description"]`.
- **Decision 1**: Steps use `AdwsRequest`/`AdwsResponse` Pydantic boundary models.
- **Decision 6**: GREEN phase with dedicated implementation agent, REFACTOR phase with dedicated refactor agent. Separate SDK calls from test agent (write_failing_tests) and from each other.
- **EUT***: Enemy Unit Tests prove real SDK communication with real API calls for both steps.
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Step Naming**: One public function per step file matching the filename.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).

### What NOT to Do

- Do NOT add new io_ops functions -- reuse the existing `execute_sdk_call`. Both steps call `io_ops.execute_sdk_call` exactly like `write_failing_tests`.
- Do NOT update the `_IMPLEMENT_VERIFY_CLOSE` workflow definition -- that is Story 4.8.
- Do NOT create commands with specialized dispatch handlers -- these are steps, not commands.
- Do NOT change the verify command, prime command, or build command.
- Do NOT change any existing step functions (`write_failing_tests`, `verify_tests_fail`, etc.), workflows, or engine logic.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT use `unsafe_perform_io` in production code (steps). Only use `.bind()` and `.lash()` for composing IOResult chains.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT make the EUTs modify the filesystem -- design them to be side-effect-free (constrained prompts with max_turns=1).
- Do NOT read BMAD files during workflow execution (NFR19) -- the issue description comes from the context, not from BMAD files.
- Do NOT change the engine executor (except adding to `_STEP_REGISTRY`), combinators, or any registered workflow definitions.
- Do NOT add verify_tests_pass shell steps -- those are composed in the workflow definition (Story 4.8), not as step modules.

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/implement_step.py` -- `GREEN_PHASE_SYSTEM_PROMPT`, `_build_green_phase_request()`, `_extract_implementation_files()`, `_process_implement_response()`, `implement_step()`
- `adws/adw_modules/steps/refactor_step.py` -- `REFACTOR_PHASE_SYSTEM_PROMPT`, `_build_refactor_phase_request()`, `_extract_refactored_files()`, `_process_refactor_response()`, `refactor_step()`
- `adws/tests/adw_modules/steps/test_implement_step.py` -- all implement_step tests (unit + integration)
- `adws/tests/adw_modules/steps/test_refactor_step.py` -- all refactor_step tests (unit + integration)
- `adws/tests/enemy/test_implement_step_sdk.py` -- EUT for implement_step real SDK call
- `adws/tests/enemy/test_refactor_step_sdk.py` -- EUT for refactor_step real SDK call

Files to modify:
- `adws/adw_modules/steps/__init__.py` -- add `implement_step` and `refactor_step` imports and exports
- `adws/adw_modules/engine/executor.py` -- add `"implement_step"` and `"refactor_step"` to `_STEP_REGISTRY` (10 entries total)
- Relevant test files for registry verification (executor tests)

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.7] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] -- Epic summary: "Developer can invoke /implement, /verify, /build, and /prime commands. /implement executes the full TDD-enforced workflow."
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement: agent-to-agent pair programming, separate system prompts per phase (test agent, implementation agent, refactor agent)
- [Source: _bmad-output/planning-artifacts/architecture.md#TDD Workflow Composition] -- implement_verify_close workflow: step 3 is implement (GREEN), step 5 is refactor (REFACTOR)
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow Through TDD Workflow] -- implement produces ctx.implementation_files, refactor produces ctx.refactored_files
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK integration: AdwsRequest/AdwsResponse at SDK boundary, execute_sdk_call in io_ops
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step internal structure, step creation checklist (errors -> io_ops -> step -> __init__ -> tests -> verify)
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form, function matches filename
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] -- Step-to-step communication via WorkflowContext
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Steps never import I/O directly, single mock point at io_ops
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR29: "/implement command with TDD workflow"
- [Source: _bmad-output/planning-artifacts/architecture.md#Enemy Unit Tests] -- EUT design: REAL API calls, NOTHING mocked, credentials required
- [Source: adws/adw_modules/io_ops.py] -- execute_sdk_call (existing SDK boundary function)
- [Source: adws/adw_modules/types.py] -- AdwsRequest, AdwsResponse, WorkflowContext, DEFAULT_CLAUDE_MODEL, PermissionMode
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (8 entries), run_step, _run_step_with_retry
- [Source: adws/adw_modules/steps/__init__.py] -- current step exports (11 steps)
- [Source: adws/adw_modules/steps/write_failing_tests.py] -- RED phase step pattern to follow: RED_PHASE_SYSTEM_PROMPT, _build_red_phase_request, _extract_test_files, _process_sdk_response, write_failing_tests
- [Source: adws/adw_modules/steps/verify_tests_fail.py] -- RED gate step (produces red_gate_passed, failure_types, failure_count in outputs)
- [Source: adws/workflows/__init__.py] -- _IMPLEMENT_VERIFY_CLOSE (empty steps, placeholder for Story 4.8)
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: adws/tests/enemy/test_write_failing_tests_sdk.py] -- EUT pattern to follow: constrained prompt, max_turns=1, no filesystem side effects
- [Source: adws/tests/enemy/test_sdk_proxy.py] -- EUT pattern: real API calls, no mocking, credential-dependent
- [Source: _bmad-output/implementation-artifacts/4-6-verify-tests-fail-step-red-gate.md] -- Previous story: verify_tests_fail step, 491 tests, 8 registry entries
- [Source: _bmad-output/implementation-artifacts/4-5-write-failing-tests-step-red-phase.md] -- Previous story: write_failing_tests step pattern (model for implement_step and refactor_step), ROP composition with .lash()/.bind(), EUT safety design

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

From Story 4.6 learnings:
- **Step registration**: Added to both `steps/__init__.py` and `engine/executor.py` `_STEP_REGISTRY` (now 8 entries). This story adds two more (10 entries).
- **491 tests**: Current test count (excluding 3 enemy tests), 100% line+branch coverage.
- **io_ops at 16 functions**: This story adds NO new io_ops functions (reuses execute_sdk_call).
- **Pure helper separation**: `_parse_pytest_output`, `_classify_failures`, `_interpret_shell_result` are pure helpers. `implement_step` and `refactor_step` should similarly separate: `_build_*_request` (pure), `_extract_*_files` (pure), `_process_*_response` (pure), step function (orchestrates I/O + pure logic).
- **ROP composition**: `.lash()` for failure re-attribution, `.bind()` for success processing. Same pattern for both new steps.
- **Regex pre-compilation**: All regex patterns should be module-level compiled constants (learned from Story 4.6 review Issue 1).

From Story 4.5 learnings:
- **write_failing_tests is the model**: Both `implement_step` and `refactor_step` follow the EXACT same structure as `write_failing_tests`. The difference is only the system prompt, context keys, and file extraction pattern.
- **ROP composition pattern**: Uses `.lash()` for failure re-attribution and `.bind()` for success processing. `implement_step` and `refactor_step` follow this identically.
- **_process_sdk_response pattern**: Separated as helper for is_error response handling. Both new steps should have `_process_implement_response` and `_process_refactor_response` helpers.
- **EUT constrained prompt**: Uses max_turns=1 and a prompt that asks the agent to describe what it would do rather than actually doing it. Both new EUTs follow this pattern.
- **No new io_ops functions**: Both steps reuse `execute_sdk_call`. The io_ops function count stays at 16.

From Story 4.4 learnings:
- **Command-level finalize**: Not relevant here -- these are steps, not commands. Finalize is handled in the workflow (Story 4.8).

From Story 4.3 / 4.2 / 4.1 learnings:
- **Not commands**: These are pipeline steps, not commands. No specialized dispatch handlers needed.
- **ROP .bind()/.lash()**: Use `.bind()` for success composition, `.lash()` for failure re-attribution.

### Relationship to Subsequent Stories

This story is the third set of TDD workflow steps (Decision 6):

1. **Story 4.1 (done)**: Command pattern -- registry, dispatch, .md entry points
2. **Story 4.2 (done)**: `/verify` command -- specialized handler, workflow-backed
3. **Story 4.3 (done)**: `/prime` command -- specialized handler, non-workflow
4. **Story 4.4 (done)**: `/build` command -- implement_close workflow + Beads finalize
5. **Story 4.5 (done)**: `write_failing_tests` step (RED phase) -- SDK step with test agent
6. **Story 4.6 (done)**: `verify_tests_fail` step (RED gate) -- shell step validating failure types
7. **Story 4.7 (this)**: `implement_step` and `refactor_step` (GREEN & REFACTOR phases) -- SDK steps with implementation and refactor agents
8. **Story 4.8**: `implement_verify_close` workflow + `/implement` command -- composes all steps into the full TDD workflow

The `implement_step` step consumes `test_files`, `red_gate_passed`, `failure_types`, and `red_phase_complete` from prior steps (promoted to inputs by the engine). Its output (`implementation_files`, `green_phase_complete`) flows to `verify_tests_pass` and then `refactor_step` via the same promotion mechanism. The `refactor_step` consumes `implementation_files` and `green_phase_complete` and produces `refactored_files` and `refactor_phase_complete`.

### io_ops.py Size Note

This story adds NO new io_ops functions. Both `implement_step` and `refactor_step` reuse the existing `execute_sdk_call`. The io_ops function count stays at 16 public functions.

### Structural Symmetry with write_failing_tests

The three SDK steps (`write_failing_tests`, `implement_step`, `refactor_step`) are structurally symmetric. Each has:
1. A module-level system prompt constant (`*_PHASE_SYSTEM_PROMPT`)
2. A `_build_*_request(ctx) -> AdwsRequest` pure helper
3. A `_extract_*_files(response) -> list[str]` pure helper
4. A `_process_*_response(response, ctx) -> IOResult[...]` pure helper
5. A public step function matching the filename
6. Registration in `steps/__init__.py` and `engine/executor.py`

This symmetry is intentional -- it makes each step independently testable and independently comprehensible.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- 551 tests pass (up from 491), 5 enemy tests deselected
- 100% line + branch coverage on all adws/ code
- mypy strict mode: zero issues in 73 source files
- ruff: zero violations
- Both steps follow the write_failing_tests structural pattern exactly
- _STEP_REGISTRY now has 10 entries (was 8)
- steps/__init__.py now exports 13 steps (was 11)
- No new io_ops functions added (reuses execute_sdk_call)
- implement_step extracts adws/adw_modules/ paths only (source, not tests)
- refactor_step extracts adws/ paths broadly (source + tests)
- Both use pre-compiled regex patterns at module level
- Both use ROP composition: .lash() for failure re-attribution, .bind() for success

### File List

**Created:**
- `adws/adw_modules/steps/implement_step.py` -- GREEN phase step: GREEN_PHASE_SYSTEM_PROMPT, _build_green_phase_request, _extract_implementation_files, _process_implement_response, implement_step
- `adws/adw_modules/steps/refactor_step.py` -- REFACTOR phase step: REFACTOR_PHASE_SYSTEM_PROMPT, _build_refactor_phase_request, _extract_refactored_files, _process_refactor_response, refactor_step
- `adws/tests/adw_modules/steps/test_implement_step.py` -- 30 tests for implement_step (unit + integration + registration)
- `adws/tests/adw_modules/steps/test_refactor_step.py` -- 30 tests for refactor_step (unit + integration + registration)
- `adws/tests/enemy/test_implement_step_sdk.py` -- EUT for implement_step real SDK call
- `adws/tests/enemy/test_refactor_step_sdk.py` -- EUT for refactor_step real SDK call

**Modified:**
- `adws/adw_modules/steps/__init__.py` -- added implement_step and refactor_step imports/exports
- `adws/adw_modules/engine/executor.py` -- added implement_step and refactor_step to _STEP_REGISTRY (10 entries)

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial code review)
**Review Date**: 2026-02-02
**Verdict**: APPROVED with 2 fixes applied

### Issues Found

| # | Severity | Description | Status |
|---|----------|-------------|--------|
| 1 | MEDIUM | `GREEN_PHASE_SYSTEM_PROMPT` missing `bypassPermissions` mention (Task 1.1 spec: "Verify it mentions bypassPermissions mode for file writes"). No test existed to catch this gap. | FIXED |
| 2 | MEDIUM | `REFACTOR_PHASE_SYSTEM_PROMPT` missing `bypassPermissions` mention (Task 5.1 spec: "Verify it mentions bypassPermissions mode"). No test existed to catch this gap. | FIXED |
| 3 | LOW | Regex patterns `_IMPL_FILE_PATTERN` and `_REFACTOR_FILE_PATTERN` can false-positive match `.pyc`/`.pyo` extensions (e.g., `adws/adw_modules/foo.pyc` matches as `adws/adw_modules/foo.py`). Pre-existing pattern from `write_failing_tests` -- consistent but imprecise. Not fixed to maintain pattern consistency. | NOTED |
| 4 | LOW | Integration tests do not assert `system_prompt`, `model`, or `permission_mode` on the SDK request sent during the integration flow. Covered by unit tests for `_build_*_request`. Consistent with `write_failing_tests` integration test pattern. | NOTED |

### Fixes Applied

**Fix 1 & 2**: Added `"- File writes use bypassPermissions mode\n"` line to both `GREEN_PHASE_SYSTEM_PROMPT` (implement_step.py line 39) and `REFACTOR_PHASE_SYSTEM_PROMPT` (refactor_step.py line 39). Added corresponding `test_green_phase_system_prompt_contains_bypass_permissions` and `test_refactor_phase_system_prompt_contains_bypass_permissions` tests. Test count increased from 549 to 551.

### Quality Gates (Post-Fix)

- pytest: 551 passed, 5 deselected (enemy tests)
- coverage: 100% line + branch (5423 statements, 268 branches)
- ruff: All checks passed
- mypy: Success, no issues found in 73 source files

### Architecture Compliance

- NFR1: No uncaught exceptions -- both steps return IOResult, never raise
- NFR9: 100% line + branch coverage maintained
- NFR10: All I/O behind io_ops.py boundary (both steps call io_ops.execute_sdk_call)
- NFR11: mypy strict mode passes
- NFR12: ruff zero violations
- NFR18: Claude via SDK API only
- NFR19: No BMAD file reads -- issue_description from context
- Decision 6: Separate system prompts per phase (GREEN, REFACTOR)
- EUT*: Enemy tests exist for both steps

### Code Quality Assessment

The implementation is clean and follows the established `write_failing_tests` pattern precisely. Both `implement_step` and `refactor_step` are structurally symmetric SDK steps with: module-level system prompt constant, pure `_build_*_request` helper, pure `_extract_*_files` helper with pre-compiled regex, pure `_process_*_response` helper, and public step function using ROP composition via `.lash()` and `.bind()`. Registration in both `steps/__init__.py` and `engine/executor.py` `_STEP_REGISTRY` is correct. The test coverage is thorough with 30 tests per step (unit, integration, registration).

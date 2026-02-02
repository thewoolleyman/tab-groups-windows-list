# Story 4.5: write_failing_tests Step (RED Phase)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want a RED phase step that writes failing tests via a dedicated test agent,
so that TDD enforcement starts with verified failing tests before any implementation.

## Acceptance Criteria

1. **Given** the step function signature from Epic 2, **When** `write_failing_tests` executes, **Then** it makes a fresh SDK call via `ClaudeSDKClient` with a test agent system prompt (Decision 6) **And** the agent writes tests with `"""RED: <expected failure reason>"""` annotation on each test **And** the step is a separate SDK call from the implementation step (agent-to-agent pairing).

2. **Given** the test agent produces tests, **When** the step completes successfully, **Then** test files are written to the project **And** the `WorkflowContext.outputs` contains the list of test files created.

3. **Given** `write_failing_tests` io_ops SDK function, **When** I inspect the test suite, **Then** an EUT exists proving real SDK communication with real API calls (EUT* constraint) **And** unit tests with mocked io_ops exist for fast CI feedback **And** 100% coverage is maintained (NFR9).

4. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Define `RED_PHASE_SYSTEM_PROMPT` constant for the test agent (AC: #1)
  - [x] 1.1 RED: Write test for `RED_PHASE_SYSTEM_PROMPT` constant in `adws/adw_modules/steps/write_failing_tests.py`. Verify it is a non-empty string. Verify it contains key instructions: "write tests only", "do not implement", "RED:" annotation requirement, testing pyramid guidance (unit tests mock io_ops), expected failure types (ImportError, AssertionError, NotImplementedError). Verify it mentions the `adws/tests/` test directory path.
  - [x] 1.2 GREEN: Implement `RED_PHASE_SYSTEM_PROMPT` as a module-level constant in `adws/adw_modules/steps/write_failing_tests.py`.
  - [x] 1.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `_build_red_phase_request()` pure helper function (AC: #1)
  - [x] 2.1 RED: Write test for `_build_red_phase_request(ctx: WorkflowContext) -> AdwsRequest`. Given a WorkflowContext with `inputs={"issue_description": "Story content here..."}`, verify it returns an `AdwsRequest` with `system_prompt=RED_PHASE_SYSTEM_PROMPT`, `prompt` containing the issue description, `model` set to `DEFAULT_CLAUDE_MODEL`. Verify the prompt instructs the agent to write tests based on the acceptance criteria from the issue description.
  - [x] 2.2 GREEN: Implement `_build_red_phase_request` in `adws/adw_modules/steps/write_failing_tests.py`. Pure function that constructs the `AdwsRequest` from context.
  - [x] 2.3 RED: Write test for `_build_red_phase_request` when `issue_description` is missing from inputs. Verify it still produces a valid `AdwsRequest` with a prompt indicating no issue description was provided (graceful degradation, not failure -- the SDK call itself may produce useful output or the agent may read from the project).
  - [x] 2.4 GREEN: Implement missing-input graceful degradation.
  - [x] 2.5 RED: Write test for `_build_red_phase_request` when ctx has `feedback` entries (from previous failed attempts). Verify the prompt includes the accumulated feedback so the test agent can learn from prior failures.
  - [x] 2.6 GREEN: Implement feedback inclusion in the prompt.
  - [x] 2.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create `_extract_test_files()` pure helper function (AC: #2)
  - [x] 3.1 RED: Write test for `_extract_test_files(response: AdwsResponse) -> list[str]`. Given an `AdwsResponse` with `result` containing text mentioning test file paths like `adws/tests/adw_modules/steps/test_new_step.py`, verify it extracts the paths as a list of strings. Verify it only extracts paths matching the `adws/tests/` prefix pattern.
  - [x] 3.2 GREEN: Implement `_extract_test_files` in `adws/adw_modules/steps/write_failing_tests.py`. Uses regex to find test file paths in the response result text.
  - [x] 3.3 RED: Write test for `_extract_test_files` when the response contains no recognizable test file paths. Verify it returns an empty list (not an error -- the agent may have written tests but not explicitly listed them).
  - [x] 3.4 GREEN: Implement empty-result handling.
  - [x] 3.5 RED: Write test for `_extract_test_files` when the response `result` is None (error response). Verify it returns an empty list.
  - [x] 3.6 GREEN: Implement None-result handling.
  - [x] 3.7 RED: Write test for `_extract_test_files` with duplicate paths in response. Verify returned list has no duplicates (deduplication).
  - [x] 3.8 GREEN: Implement deduplication.
  - [x] 3.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create `write_failing_tests()` step function (AC: #1, #2)
  - [x] 4.1 RED: Write test for `write_failing_tests(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `io_ops.execute_sdk_call` returns `IOSuccess(AdwsResponse(result="Created test files: adws/tests/...", is_error=False))`, verify it returns `IOSuccess(WorkflowContext)` with `outputs` containing `{"test_files": ["adws/tests/..."], "red_phase_complete": True}`.
  - [x] 4.2 GREEN: Implement `write_failing_tests` in `adws/adw_modules/steps/write_failing_tests.py`. Calls `_build_red_phase_request(ctx)` to build the request, then `io_ops.execute_sdk_call(request)` to execute, then `_extract_test_files(response)` to get the file list.
  - [x] 4.3 RED: Write test for `write_failing_tests` when `io_ops.execute_sdk_call` returns `IOFailure(PipelineError(...))`. Verify it returns `IOFailure(PipelineError)` with `step_name="write_failing_tests"` and `error_type` preserved from the io_ops error.
  - [x] 4.4 GREEN: Implement SDK call failure handling. Use `.bind()` for ROP composition.
  - [x] 4.5 RED: Write test for `write_failing_tests` when the SDK response has `is_error=True`. Verify it returns `IOFailure(PipelineError)` with `error_type="SdkResponseError"` and `message` containing the response error_message.
  - [x] 4.6 GREEN: Implement SDK error response handling.
  - [x] 4.7 RED: Write test for `write_failing_tests` when the SDK response is successful but `_extract_test_files` returns an empty list. Verify it still returns `IOSuccess(WorkflowContext)` with `outputs={"test_files": [], "red_phase_complete": True}` -- the step succeeds even if no test files are explicitly identified (the agent may have created them without listing).
  - [x] 4.8 GREEN: Implement empty test file list handling.
  - [x] 4.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Register `write_failing_tests` in step infrastructure (AC: #1)
  - [x] 5.1 RED: Write test that `write_failing_tests` is importable from `adws.adw_modules.steps` (via `steps/__init__.py`).
  - [x] 5.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x] 5.3 RED: Write test that `_STEP_REGISTRY` in `engine/executor.py` contains `"write_failing_tests"` mapped to the correct function.
  - [x] 5.4 GREEN: Add `"write_failing_tests"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x] 5.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Create Enemy Unit Test for write_failing_tests SDK call (AC: #3)
  - [x] 6.1 RED: Write EUT (`@pytest.mark.enemy`) in `adws/tests/enemy/test_write_failing_tests_sdk.py` that tests `write_failing_tests` with a REAL SDK call. Build a WorkflowContext with a simple issue_description input ("Write a test for a function that adds two numbers"). Call `write_failing_tests(ctx)`. Verify the result is `IOSuccess` and the response is an `AdwsResponse` with `is_error=False`. This test makes a REAL API call -- nothing mocked.
  - [x] 6.2 GREEN: Ensure the step works with the real SDK (the step function already implemented in Task 4 should work -- this validates it against the real API).
  - [x] 6.3 REFACTOR: Review EUT for clarity and coverage.

- [x] Task 7: Integration test -- full write_failing_tests step flow (AC: #1, #2, #3)
  - [x] 7.1 RED: Write integration test: invoke `write_failing_tests` with a WorkflowContext containing `{"issue_description": "Implement a function that validates email addresses"}` in inputs and feedback from a prior attempt `["Previous test had SyntaxError"]`. Mock `io_ops.execute_sdk_call` to return a successful response mentioning test files. Verify: IOSuccess returned, outputs contain test_files list, red_phase_complete is True, the request prompt sent to the SDK included both the issue description and the feedback.
  - [x] 7.2 GREEN: Ensure integration path works end-to-end with mocked io_ops.
  - [x] 7.3 RED: Write integration test: invoke `write_failing_tests` with a WorkflowContext where io_ops returns IOFailure (simulate SDK unavailable). Verify IOFailure propagates with correct step_name.
  - [x] 7.4 GREEN: Ensure SDK failure path works correctly.
  - [x] 7.5 RED: Write integration test: invoke `write_failing_tests` with an `AdwsResponse` that has `is_error=True` and `error_message="Rate limited"`. Verify IOFailure with error_type="SdkResponseError" and message containing "Rate limited".
  - [x] 7.6 GREEN: Ensure SDK error response path works correctly.
  - [x] 7.7 REFACTOR: Clean up integration tests, verify all scenarios covered.

- [x] Task 8: Verify full integration and quality gates (AC: #4)
  - [x] 8.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 8.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 8.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 4.4)

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

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`.

**engine/executor.py** has 8 functions. `_STEP_REGISTRY` has 6 entries: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants), `load_workflow()`, `list_workflows()`, 5 registered workflows. `_IMPLEMENT_VERIFY_CLOSE` currently has empty steps list (placeholder).

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 427 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: write_failing_tests Step Architecture

This is the first step in the `implement_verify_close` TDD workflow (Decision 6). It creates a test agent via a fresh SDK call that writes failing tests from the story acceptance criteria. The step follows the established step creation pattern.

```
Beads issue description (in ctx.inputs["issue_description"])
    |
    v
write_failing_tests (SDK step -- test agent, RED phase)
    |
    v (calls io_ops.execute_sdk_call with RED_PHASE_SYSTEM_PROMPT)
    |
    v (extracts test file paths from response)
    |
    v
WorkflowContext.outputs = {"test_files": [...], "red_phase_complete": True}
```

**Key design decisions:**

1. **Step is NOT a command** -- it is a pipeline step function that runs within the `implement_verify_close` workflow. It follows the step signature `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. It is NOT a command with a specialized dispatch handler.

2. **Uses existing `io_ops.execute_sdk_call`** -- no new io_ops functions are needed. The existing `execute_sdk_call` handles the SDK interaction. The step builds an `AdwsRequest` with the RED phase system prompt and delegates to io_ops.

3. **System prompt is the key differentiator** -- the test agent is implemented by providing a RED-phase-specific system prompt to `execute_sdk_call`. The system prompt instructs the agent to:
   - Write tests only, do not implement
   - Annotate every test with `"""RED: <expected failure reason>"""`
   - Follow the testing pyramid (unit tests mock io_ops boundary)
   - Expect valid failure types: ImportError, AssertionError, NotImplementedError
   - Place tests in `adws/tests/` mirroring source structure
   - Use `bypassPermissions` mode so the agent can write files

4. **Test file extraction** -- the step extracts test file paths from the SDK response using regex pattern matching on `adws/tests/` paths. This is best-effort -- the agent may create files without explicitly listing them. The step succeeds even with an empty extracted list.

5. **Feedback integration** -- when retried after a `verify_tests_fail` failure, the accumulated feedback (from `ctx.feedback`) is included in the prompt so the test agent can correct its mistakes (e.g., fix SyntaxErrors reported by the verify step).

6. **No new io_ops functions** -- this step reuses `execute_sdk_call`. Unlike Story 4.4 which added Beads-specific io_ops functions, this story only creates a step and its supporting pure helpers.

### Design: RED Phase System Prompt

The system prompt is the architectural control that makes this a "test agent" (Decision 6). It must contain:

```python
RED_PHASE_SYSTEM_PROMPT = """\
You are a TDD Test Agent in the RED phase. Your ONLY job is to write \
failing tests.

## Rules
1. Write tests ONLY. Do NOT implement any production code.
2. Every test MUST have a docstring starting with: \
\"\"\"RED: <expected failure reason>\"\"\"
3. Tests should fail for EXPECTED reasons:
   - ImportError (module does not exist yet)
   - AssertionError (function returns wrong value)
   - NotImplementedError (function is a stub)
   - AttributeError (class missing expected attribute)
4. Tests must NOT fail for BROKEN reasons:
   - SyntaxError (your test code is broken)
   - IndentationError (your test code is broken)
   - NameError in test code (your test code is broken)

## Testing Conventions
- Place tests in adws/tests/ mirroring the source structure
- Use pytest as the test framework
- Mock all I/O at the adws.adw_modules.io_ops boundary
- Follow test naming: test_<function>_<scenario>
- One test file per source module

## Output
List all test files you created, one per line, with their full paths.
"""
```

The exact wording may be refined during implementation, but the key constraints (write tests only, RED annotation, expected failure types, testing conventions) must be present.

### Design: AdwsRequest Configuration

The `AdwsRequest` for the RED phase SDK call:

```python
AdwsRequest(
    model=DEFAULT_CLAUDE_MODEL,
    system_prompt=RED_PHASE_SYSTEM_PROMPT,
    prompt=<constructed from issue_description + feedback>,
    permission_mode="bypassPermissions",  # Agent needs to write test files
    max_turns=None,  # Let the agent work until done
)
```

The `permission_mode="bypassPermissions"` is critical -- the test agent needs to create and write test files to disk. Without this, the SDK would require user approval for each file write.

### Design: Test File Extraction

The `_extract_test_files` function uses regex to find paths matching:
```
adws/tests/<any path>.py
```

Pattern: `r'(adws/tests/\S+\.py)'`

This captures any Python file under the `adws/tests/` directory mentioned in the response. Deduplication removes repeated mentions. The function handles None result (error responses) and empty matches gracefully.

### Design: Context Flow

**Input context expected:**
```python
ctx.inputs = {
    "issue_description": "Full Beads issue description...",
    # Optionally from previous steps:
    "issue_id": "BEADS-123",
}
ctx.feedback = [
    # From previous failed verify_tests_fail attempts:
    "Retry 1/3 for step 'verify_tests_fail': SyntaxError in test_foo.py line 42",
]
```

**Output context produced:**
```python
ctx.outputs = {
    "test_files": ["adws/tests/steps/test_new_step.py", ...],
    "red_phase_complete": True,
}
```

The `test_files` list flows to the next step (`verify_tests_fail`) via the engine's `promote_outputs_to_inputs()` mechanism.

### Design: Step Registration

The step is registered in two places:
1. `steps/__init__.py` -- exported for import
2. `engine/executor.py` `_STEP_REGISTRY` -- registered for engine dispatch

After registration, the `implement_verify_close` workflow (Story 4.8) can reference it as `Step(name="write_failing_tests", function="write_failing_tests")`.

**NOTE:** This story does NOT update the `_IMPLEMENT_VERIFY_CLOSE` workflow definition. That is Story 4.8's responsibility. This story only creates and registers the step.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_write_failing_tests.py` -- tests for RED_PHASE_SYSTEM_PROMPT, _build_red_phase_request, _extract_test_files, write_failing_tests (unit + integration)
- `adws/tests/enemy/test_write_failing_tests_sdk.py` -- EUT for real SDK call

**Modified test files**:
- `adws/tests/adw_modules/steps/test_steps_init.py` (if exists) or add import test to existing wiring tests -- verify `write_failing_tests` is importable from `adws.adw_modules.steps`
- Tests for `_STEP_REGISTRY` in executor tests -- verify registry contains `"write_failing_tests"`

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_red_phase_system_prompt_not_empty`
- `test_red_phase_system_prompt_contains_write_tests_only`
- `test_red_phase_system_prompt_contains_red_annotation`
- `test_red_phase_system_prompt_contains_expected_failures`
- `test_build_red_phase_request_with_description`
- `test_build_red_phase_request_no_description`
- `test_build_red_phase_request_with_feedback`
- `test_extract_test_files_single_file`
- `test_extract_test_files_multiple_files`
- `test_extract_test_files_no_matches`
- `test_extract_test_files_none_result`
- `test_extract_test_files_deduplication`
- `test_write_failing_tests_success`
- `test_write_failing_tests_sdk_failure`
- `test_write_failing_tests_sdk_error_response`
- `test_write_failing_tests_empty_test_files`
- `test_write_failing_tests_step_registry`
- `test_write_failing_tests_importable`

**Mock targets for step tests**:
- `adws.adw_modules.io_ops.execute_sdk_call` -- mock SDK call for unit tests

**EUT** (enemy test):
- NO mocking at all
- Real `ANTHROPIC_API_KEY` required
- Real SDK call through `execute_sdk_call` -> `_execute_sdk_call_async` -> `claude_agent_sdk.query`
- Uses `bypassPermissions` mode (the EUT should use a safe, constrained prompt to avoid file writes during testing -- e.g., "List the test files you would create" rather than "Create the test files")

### EUT Safety Consideration

The EUT must be designed carefully because `write_failing_tests` with `permission_mode="bypassPermissions"` could modify the filesystem. For the EUT:

**Option A (selected):** Create a specialized test that calls `io_ops.execute_sdk_call` directly with a constrained prompt (e.g., "Respond with: I would create the following test files: adws/tests/test_example.py") rather than the full `write_failing_tests` step. This tests the SDK round-trip without filesystem side effects.

**Option B (rejected):** Run `write_failing_tests` in a temp directory. Rejected because the SDK agent would need the real project context to be meaningful, and temp directory isolation is complex.

The EUT validates that `io_ops.execute_sdk_call` works with the RED phase request format (AdwsRequest with system_prompt, permission_mode, etc.). It does NOT need to validate the agent actually creates good test files -- that is the verify_tests_fail step's job.

### Ruff Considerations

- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files.
- `E501` (line too long): Keep all lines under 88 characters. The `RED_PHASE_SYSTEM_PROMPT` is a long string -- use implicit string concatenation or backslash continuation to keep lines short.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.
- `FBT003` (boolean positional in return): The `red_phase_complete=True` in outputs dict is a dict value, not a function parameter -- no issue.
- `ERA001` (commented out code): Do not leave commented-out code in the prompt constant.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- `write_failing_tests` returns IOResult, never raises.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. The step calls `io_ops.execute_sdk_call` for the SDK interaction.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR18**: Claude via SDK API only (through `io_ops.execute_sdk_call`).
- **Decision 1**: Step uses `AdwsRequest`/`AdwsResponse` Pydantic boundary models.
- **Decision 6**: RED phase with dedicated test agent system prompt, separate SDK call from implementation.
- **EUT***: Enemy Unit Test proves real SDK communication with real API calls.
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Step Naming**: One public function `write_failing_tests` matching the filename.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).

### What NOT to Do

- Do NOT implement any production code in this step -- it is the RED phase agent, not the GREEN phase agent.
- Do NOT add new io_ops functions -- reuse the existing `execute_sdk_call`.
- Do NOT update the `_IMPLEMENT_VERIFY_CLOSE` workflow definition -- that is Story 4.8.
- Do NOT create a command with a specialized dispatch handler -- this is a step, not a command.
- Do NOT change the verify command, prime command, or build command.
- Do NOT change any existing step functions, workflows, or engine logic.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT use `unsafe_perform_io` in production code (steps). Only use `.bind()` for composing IOResult chains.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT make the EUT modify the filesystem -- design it to be side-effect-free (read-only SDK call).
- Do NOT read BMAD files during workflow execution (NFR19) -- the issue description comes from the context, not from BMAD files.
- Do NOT change the engine executor, combinators, or any registered workflow definitions.

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/write_failing_tests.py` -- `RED_PHASE_SYSTEM_PROMPT`, `_build_red_phase_request()`, `_extract_test_files()`, `write_failing_tests()`
- `adws/tests/adw_modules/steps/test_write_failing_tests.py` -- all step tests (unit + integration)
- `adws/tests/enemy/test_write_failing_tests_sdk.py` -- EUT for real SDK call

Files to modify:
- `adws/adw_modules/steps/__init__.py` -- add `write_failing_tests` import and export
- `adws/adw_modules/engine/executor.py` -- add `"write_failing_tests"` to `_STEP_REGISTRY`
- Relevant test files for registry verification (executor tests)

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] -- Epic summary: "Developer can invoke /implement, /verify, /build, and /prime commands. /implement executes the full TDD-enforced workflow."
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement: agent-to-agent pair programming, write_failing_tests step, RED phase annotation pattern, verify_tests_fail validates failure types
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK integration: AdwsRequest/AdwsResponse at SDK boundary, execute_sdk_call in io_ops
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step internal structure pattern, step creation checklist (errors -> io_ops -> step -> __init__ -> tests -> verify)
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form, function matches filename
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] -- Step-to-step communication via WorkflowContext
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Flow Through TDD Workflow] -- write_failing_tests produces ctx.test_files, consumed by verify_tests_fail
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Steps never import I/O directly, single mock point at io_ops
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR29: "/implement command with TDD workflow"
- [Source: _bmad-output/planning-artifacts/architecture.md#Enemy Unit Tests] -- EUT design: REAL API calls, NOTHING mocked, credentials required
- [Source: adws/adw_modules/io_ops.py] -- execute_sdk_call (existing SDK boundary function)
- [Source: adws/adw_modules/types.py] -- AdwsRequest, AdwsResponse, WorkflowContext, DEFAULT_CLAUDE_MODEL, PermissionMode
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY, run_step, _run_step_with_retry
- [Source: adws/adw_modules/steps/__init__.py] -- current step exports (9 steps)
- [Source: adws/workflows/__init__.py] -- _IMPLEMENT_VERIFY_CLOSE (empty steps, placeholder for Story 4.8)
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/4-4-build-command-and-implement-close-workflow.md] -- Previous story: Build command pattern, Beads finalize, 427 tests
- [Source: _bmad-output/implementation-artifacts/4-3-prime-command-for-context-loading.md] -- Previous story: Prime command, dispatch routing, io_ops patterns

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

From Story 4.4 learnings:
- **Command-level finalize**: Finalize logic (bd close/update) is in the command layer, not the step layer. `write_failing_tests` is a step -- it does NOT finalize anything.
- **Shell injection protection**: io_ops Beads functions use `shlex.quote()`. Not relevant here since write_failing_tests uses execute_sdk_call, not shell commands.
- **427 tests**: Current test count (excluding 2 enemy tests), 100% line+branch coverage.
- **io_ops at 16 functions**: Crossed ~15 threshold. This story adds NO new io_ops functions (reuses execute_sdk_call).
- **Failure metadata format**: `ADWS_FAILED|attempt=N|...` -- not directly relevant but establishes the structured metadata pattern.

From Story 4.3 learnings:
- **Dispatch routing ordering**: unknown -> verify -> prime -> build -> no-workflow -> generic. NOT relevant here -- this is a step, not a command.
- **_extract_io_value pattern**: Avoid `unsafe_perform_io` in production code. Use `.bind()` composition.

From Story 4.2 learnings:
- **ROP .bind()/.lash() pattern**: Use `.bind()` for success composition. `write_failing_tests` should chain: build request -> execute SDK -> process response using `.bind()`.

From Story 2.2 learnings:
- **EUT design**: Test REAL SDK with REAL API calls. The EUT for write_failing_tests tests the real SDK round-trip with a RED-phase-specific request. Use a constrained prompt to avoid filesystem side effects.
- **execute_sdk_call interface**: Takes `AdwsRequest`, returns `IOResult[AdwsResponse, PipelineError]`. The step builds the request and interprets the response.

### Relationship to Subsequent Stories

This story is the first of the TDD workflow steps (Decision 6):

1. **Story 4.1 (done)**: Command pattern -- registry, dispatch, .md entry points
2. **Story 4.2 (done)**: `/verify` command -- specialized handler, workflow-backed
3. **Story 4.3 (done)**: `/prime` command -- specialized handler, non-workflow
4. **Story 4.4 (done)**: `/build` command -- implement_close workflow + Beads finalize
5. **Story 4.5 (this)**: `write_failing_tests` step (RED phase) -- SDK step with test agent
6. **Story 4.6**: `verify_tests_fail` step (RED gate) -- shell step validating failure types. Consumes `test_files` from 4.5's outputs.
7. **Story 4.7**: `implement` and `refactor` steps (GREEN & REFACTOR phases) -- SDK steps with implementation and refactor agents
8. **Story 4.8**: `implement_verify_close` workflow + `/implement` command -- composes all steps into the full TDD workflow

The `write_failing_tests` step produces `test_files` in its outputs, which `verify_tests_fail` (Story 4.6) consumes via the engine's `promote_outputs_to_inputs()` mechanism. Getting the output contract right here is critical for the downstream step.

### io_ops.py Size Note

This story adds NO new io_ops functions. `write_failing_tests` reuses the existing `execute_sdk_call`. The io_ops function count stays at 16 public functions. The next story (4.6) may add a shell command variant but likely also reuses `run_shell_command`.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- 450 tests pass (excluding 3 enemy tests), 100% line+branch coverage
- mypy strict mode: Success, no issues in 65 source files
- ruff: All checks passed, zero violations
- No new io_ops functions added (reuses execute_sdk_call)
- Step registered in steps/__init__.py and engine/executor.py _STEP_REGISTRY (7 entries now)
- ROP composition uses .lash() for failure re-attribution and .bind() for success processing
- _process_sdk_response separated as helper for is_error response handling
- EUT uses constrained prompt (max_turns=1) to avoid filesystem side effects
- Test count increased from 427 to 450 (23 new tests)

### File List

Created:
- adws/adw_modules/steps/write_failing_tests.py -- RED_PHASE_SYSTEM_PROMPT, _build_red_phase_request(), _extract_test_files(), _process_sdk_response(), write_failing_tests()
- adws/tests/adw_modules/steps/test_write_failing_tests.py -- 20 tests (unit + integration)
- adws/tests/enemy/test_write_failing_tests_sdk.py -- 1 EUT for real SDK call

Modified:
- adws/adw_modules/steps/__init__.py -- added write_failing_tests import and export
- adws/adw_modules/engine/executor.py -- added write_failing_tests to _STEP_REGISTRY (7 entries)
- _bmad-output/implementation-artifacts/sprint-status.yaml -- status updated to review

## Senior Developer Review

### Reviewer: Claude Opus 4.5 (Adversarial Code Review)

### Review Date: 2026-02-02

### Quality Gates (Post-Fix)

| Gate | Result |
|------|--------|
| pytest (450 tests, excl. 3 enemy) | PASS |
| Coverage (line + branch) | 100% |
| ruff (all rules) | PASS (zero violations) |
| mypy (strict mode) | PASS (65 source files) |

### Issues Found: 5 (3 MEDIUM, 2 LOW)

#### ISSUE 1 (MEDIUM) -- FIXED: Incomplete assertions in `test_build_red_phase_request_no_description`

**File:** `adws/tests/adw_modules/steps/test_write_failing_tests.py`
**Problem:** The no-description test path only checked `isinstance`, `model`, and `prompt`. It did NOT verify `system_prompt == RED_PHASE_SYSTEM_PROMPT` or `permission_mode == "bypassPermissions"`. The with-description test covered these, but the no-description path was a gap. A regression that conditionally set wrong system_prompt or permission_mode when issue_description is missing would go undetected.
**Fix:** Added `assert request.system_prompt == RED_PHASE_SYSTEM_PROMPT` and `assert request.permission_mode == "bypassPermissions"` to the test.

#### ISSUE 2 (MEDIUM) -- FIXED: Incomplete assertions in `test_build_red_phase_request_with_feedback`

**File:** `adws/tests/adw_modules/steps/test_write_failing_tests.py`
**Problem:** The feedback test only asserted feedback content appeared in the prompt. It did not verify `system_prompt`, `model`, or `permission_mode`. A regression that corrupted these fields when feedback is present would be invisible.
**Fix:** Added assertions for `system_prompt`, `model`, and `permission_mode` to match the with-description test pattern.

#### ISSUE 3 (MEDIUM) -- FIXED: Deduplication test did not verify insertion order

**File:** `adws/tests/adw_modules/steps/test_write_failing_tests.py`
**Problem:** `test_extract_test_files_deduplication` used `len(files) == 2` and `in files` membership checks. This would pass even if the implementation returned files in arbitrary order (e.g., `list(set(...))`). The implementation carefully preserves insertion order via a `seen` set + append pattern, but the test did not enforce this contract.
**Fix:** Changed assertion to `assert files == ["adws/tests/test_foo.py", "adws/tests/test_bar.py"]` which verifies both deduplication AND insertion order.

#### ISSUE 4 (LOW) -- NOT FIXED: EUT uses expensive model

**File:** `adws/tests/enemy/test_write_failing_tests_sdk.py`
**Problem:** The EUT uses `DEFAULT_CLAUDE_MODEL` (Sonnet) for the real API call, while the existing EUT in `test_sdk_proxy.py` uses `"claude-haiku-3-5-20241022"` for cost efficiency. The EUT only validates SDK round-trip mechanics, not response quality, so the cheaper model suffices.
**Reason not fixed:** The story spec (Task 6.1) explicitly builds the request using `RED_PHASE_SYSTEM_PROMPT` and the default model to test the exact request format the step would use in production. Using a different model would diverge from the production path. This is a design tradeoff, not a bug. Documented for team awareness.

#### ISSUE 5 (LOW) -- NOT FIXED: Story completion notes say "20 tests" but actual count is 23

**File:** Story completion notes
**Problem:** The "Completion Notes List" and "File List" say "20 tests (unit + integration)" but `pytest -v` shows 23 tests in `test_write_failing_tests.py`.
**Reason not fixed:** This is a documentation inaccuracy in the story metadata, not a code defect. Does not affect quality gates or functionality.

### Architecture Assessment

The implementation is clean and follows established patterns well:

1. **ROP composition** with `.lash()` for failure re-attribution and `.bind()` for success processing correctly separates the SDK failure path (io_ops returns IOFailure) from the SDK error response path (is_error=True in AdwsResponse).

2. **Pure helper separation** (`_build_red_phase_request`, `_extract_test_files`, `_process_sdk_response`) makes the step function testable and each helper independently verifiable.

3. **io_ops boundary respected** -- the step calls `io_ops.execute_sdk_call` and nothing else for I/O, consistent with the project's architectural boundary.

4. **Step registration** in both `steps/__init__.py` and `engine/executor.py` follows the established pattern from previous steps.

5. **Context immutability** maintained via `with_updates()` -- no mutation of WorkflowContext.

### Verdict: APPROVED (after fixes applied)

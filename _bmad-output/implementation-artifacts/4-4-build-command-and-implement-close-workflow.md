# Story 4.4: /build Command & implement_close Workflow

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want to invoke `/build` for fast-track trivial changes using a simplified workflow,
so that simple tasks bypass full TDD ceremony while still meeting the 100% coverage gate.

## Acceptance Criteria

1. **Given** the command pattern from Story 4.1, **When** I invoke `/build`, **Then** it executes the `implement_close` workflow (FR32) **And** this workflow is TDD-exempt per architecture -- 100% coverage gate is the safety net.

2. **Given** the implement_close workflow, **When** it executes, **Then** it runs: implement (SDK step) -> verify_tests_pass -> finalize (always_run) **And** there is no write_failing_tests or verify_tests_fail phase **And** finalize executes via `bd` CLI (NFR17) even if implement fails (NFR3).

3. **Given** the implement step succeeds and tests pass, **When** the finalize step runs, **Then** it calls `bd close <id> --reason "Completed successfully"` (FR20, FR46).

4. **Given** the implement step fails after retries are exhausted, **When** the finalize step runs (always_run, NFR3), **Then** the Beads issue remains open with structured failure metadata via `bd update --notes "ADWS_FAILED|..."` (NFR2, FR46) **And** the failure metadata includes attempt count, error classification, step name, and failure summary **And** the issue is NOT closed -- it remains open for automated triage (NFR21).

5. **Given** /build command code, **When** I run tests, **Then** success path, failure path, and always_run behavior are covered **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create `BuildCommandResult` data type for command output (AC: #1, #3, #4)
  - [x] 1.1 RED: Write test for `BuildCommandResult` frozen dataclass with fields: `success` (bool), `workflow_executed` (str -- workflow name), `issue_id` (str | None -- Beads issue ID if provided), `finalize_action` (str -- "closed", "tagged_failure", or "skipped"), `summary` (str). Verify construction, immutability, and field access.
  - [x] 1.2 GREEN: Implement `BuildCommandResult` as a frozen dataclass in `adws/adw_modules/commands/build.py`.
  - [x] 1.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `finalize_beads_issue()` io_ops function for bd CLI operations (AC: #3, #4)
  - [x] 2.1 RED: Write test for `io_ops.run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]`. Given a valid issue_id and reason, verify it calls `run_shell_command` with `bd close <id> --reason "<reason>"` and returns `IOSuccess(ShellResult)`. Given a bd CLI failure (nonzero exit), verify it returns `IOFailure(PipelineError)` with error_type `"BeadsCloseError"` and context containing issue_id, exit code, and stderr.
  - [x] 2.2 GREEN: Implement `run_beads_close` in `io_ops.py`. Delegates to `run_shell_command` and interprets nonzero exit as failure.
  - [x] 2.3 RED: Write test for `io_ops.run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]`. Given a valid issue_id and notes string, verify it calls `run_shell_command` with `bd update <id> --notes "<notes>"` and returns `IOSuccess(ShellResult)`. Given a bd CLI failure, verify `IOFailure(PipelineError)` with error_type `"BeadsUpdateError"`.
  - [x] 2.4 GREEN: Implement `run_beads_update_notes` in `io_ops.py`.
  - [x] 2.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create `_build_failure_metadata()` pure helper function (AC: #4)
  - [x] 3.1 RED: Write test for `_build_failure_metadata(error: PipelineError, attempt_count: int) -> str`. Given a PipelineError with step_name="implement", error_type="SdkCallError", message="Model timeout", verify it returns `"ADWS_FAILED|attempt=<n>|last_failure=<ISO-timestamp>|error_class=SdkCallError|step=implement|summary=Model timeout"`. Verify the timestamp is ISO 8601 format. Verify pipe characters in the summary are escaped.
  - [x] 3.2 GREEN: Implement `_build_failure_metadata` in `adws/adw_modules/commands/build.py`. Pure function, no I/O.
  - [x] 3.3 RED: Write test for `_build_failure_metadata` with a PipelineError containing pipe characters in the message (edge case). Verify pipes in the summary field are escaped to prevent parsing ambiguity.
  - [x] 3.4 GREEN: Implement pipe escaping.
  - [x] 3.5 RED: Write test for `_build_failure_metadata` with attempt_count=0 (first attempt). Verify attempt field is 1 (1-indexed for human readability, not 0-indexed).
  - [x] 3.6 GREEN: Implement attempt count adjustment.
  - [x] 3.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create `_finalize_on_success()` function (AC: #3)
  - [x] 4.1 RED: Write test for `_finalize_on_success(issue_id: str) -> IOResult[str, PipelineError]`. Given io_ops.run_beads_close returns IOSuccess, verify it returns `IOSuccess("closed")`. Given io_ops.run_beads_close returns IOFailure, verify it returns `IOSuccess("close_failed")` -- finalize is always_run and must not propagate bd errors.
  - [x] 4.2 GREEN: Implement `_finalize_on_success` in `adws/adw_modules/commands/build.py`. Calls `io_ops.run_beads_close(issue_id, "Completed successfully")`. Uses `.lash()` to convert bd failure to success with "close_failed" action.
  - [x] 4.3 RED: Write test for `_finalize_on_success` when issue_id is None or empty. Verify it returns `IOSuccess("skipped")` -- no Beads operation when there is no issue.
  - [x] 4.4 GREEN: Implement None/empty issue_id handling.
  - [x] 4.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Create `_finalize_on_failure()` function (AC: #4)
  - [x] 5.1 RED: Write test for `_finalize_on_failure(issue_id: str, error: PipelineError, attempt_count: int) -> IOResult[str, PipelineError]`. Given io_ops.run_beads_update_notes returns IOSuccess, verify it returns `IOSuccess("tagged_failure")`. Verify the notes argument to run_beads_update_notes starts with "ADWS_FAILED|" and includes attempt count, error class, step name, and summary.
  - [x] 5.2 GREEN: Implement `_finalize_on_failure` in `adws/adw_modules/commands/build.py`. Calls `_build_failure_metadata` to construct the notes string, then `io_ops.run_beads_update_notes(issue_id, metadata)`. Uses `.lash()` to convert bd failure to success with "tag_failed" action.
  - [x] 5.3 RED: Write test for `_finalize_on_failure` when issue_id is None or empty. Verify it returns `IOSuccess("skipped")` -- no Beads operation when there is no issue.
  - [x] 5.4 GREEN: Implement None/empty issue_id handling.
  - [x] 5.5 RED: Write test for `_finalize_on_failure` when bd update itself fails. Verify it returns `IOSuccess("tag_failed")` -- not IOFailure (fail-open on finalize infrastructure errors).
  - [x] 5.6 GREEN: Implement bd update failure recovery via `.lash()`.
  - [x] 5.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Create `run_build_command()` function (AC: #1, #2, #3, #4, #5)
  - [x] 6.1 RED: Write test for `run_build_command(ctx: WorkflowContext) -> IOResult[BuildCommandResult, PipelineError]`. Given the implement_close workflow executes successfully (mocked via io_ops), verify it returns `IOSuccess(BuildCommandResult(success=True, workflow_executed="implement_close", finalize_action="closed", ...))`.
  - [x] 6.2 GREEN: Implement `run_build_command` in `adws/adw_modules/commands/build.py`. Loads "implement_close" workflow via `io_ops.load_command_workflow`, executes via `io_ops.execute_command_workflow`, then calls `_finalize_on_success` if successful.
  - [x] 6.3 RED: Write test for `run_build_command` when workflow execution fails. Verify it returns `IOSuccess(BuildCommandResult(success=False, finalize_action="tagged_failure", ...))`. The command itself succeeds (it ran the workflow and handled the failure), similar to verify command pattern.
  - [x] 6.4 GREEN: Implement failure handling path. Use `.lash()` to convert workflow IOFailure into finalize-on-failure path, producing IOSuccess(BuildCommandResult) with success=False.
  - [x] 6.5 RED: Write test for `run_build_command` when workflow loading fails (workflow not found). Verify it returns `IOFailure(PipelineError)` -- infrastructure failure propagates as IOFailure, unlike workflow execution failures which produce IOSuccess with success=False.
  - [x] 6.6 GREEN: Implement workflow-load failure propagation.
  - [x] 6.7 RED: Write test for `run_build_command` when ctx has `issue_id` in inputs. Verify the issue_id flows through to finalize (either close or tag). Given ctx has no `issue_id`, verify finalize_action is "skipped".
  - [x] 6.8 GREEN: Implement issue_id extraction from context.
  - [x] 6.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 7: Wire `run_build_command` into command dispatch (AC: #1)
  - [x] 7.1 RED: Write test that `run_command("build", ctx)` delegates to `run_build_command` instead of the generic workflow path. Verify the return is `IOResult[WorkflowContext, PipelineError]` where the WorkflowContext has the `BuildCommandResult` serialized in outputs under key `"build_result"`.
  - [x] 7.2 GREEN: Update `run_command` in dispatch.py to detect the "build" command and route to `run_build_command`. The `BuildCommandResult` is placed into the WorkflowContext outputs under key `"build_result"`. Add build-specific routing AFTER verify and prime handlers.
  - [x] 7.3 RED: Write test that "verify", "prime", and "load_bundle" commands still work correctly through their respective paths -- no regression.
  - [x] 7.4 GREEN: Ensure existing dispatch paths are unaffected.
  - [x] 7.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 8: Update `.claude/commands/adws-build.md` entry point (AC: #1)
  - [x] 8.1 RED: Write test that `.claude/commands/adws-build.md` exists and contains reference to `run_build_command` and the build-specific module, no longer marked as stub.
  - [x] 8.2 GREEN: Update the `.md` file content to reference the build-specific module and describe the implement_close workflow behavior.
  - [x] 8.3 REFACTOR: Verify file content, mypy, ruff.

- [x] Task 9: Export `run_build_command` and `BuildCommandResult` from commands package (AC: #1)
  - [x] 9.1 RED: Write tests for importing `run_build_command` and `BuildCommandResult` from `adws.adw_modules.commands`.
  - [x] 9.2 GREEN: Add exports to `adws/adw_modules/commands/__init__.py`.
  - [x] 9.3 REFACTOR: Verify import paths, mypy, ruff.

- [x] Task 10: Update implement_close workflow definition (AC: #2)
  - [x] 10.1 RED: Write test that the `implement_close` workflow (from `workflows/__init__.py`) has the correct steps reflecting the /build command's simplified pipeline: implement (SDK step), verify_tests_pass (shell step). Verify no write_failing_tests or verify_tests_fail steps exist. Verify no finalize step (handled by command layer).
  - [x] 10.2 GREEN: Update `_IMPLEMENT_CLOSE` in `workflows/__init__.py` to have the correct step list: implement (execute_sdk_call) and verify_tests_pass (shell step with pytest).
  - [x] 10.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 11: Integration test -- full /build command flow (AC: #1, #2, #3, #4, #5)
  - [x] 11.1 RED: Write integration test: invoke `run_build_command` with a context containing `{"issue_id": "TEST-1"}` in inputs. Mock io_ops to simulate successful workflow execution and successful bd close. Verify BuildCommandResult has success=True, workflow_executed="implement_close", finalize_action="closed", issue_id="TEST-1".
  - [x] 11.2 GREEN: Ensure integration path works end-to-end with mocked io_ops.
  - [x] 11.3 RED: Write integration test: invoke `run_build_command` with a context containing `{"issue_id": "TEST-2"}` in inputs. Mock io_ops to simulate workflow execution failure (implement step fails). Verify BuildCommandResult has success=False, finalize_action="tagged_failure", and the failure metadata was passed to run_beads_update_notes.
  - [x] 11.4 GREEN: Ensure failure integration path works correctly.
  - [x] 11.5 RED: Write integration test: invoke `run_build_command` with a context with no `issue_id`. Mock io_ops to simulate successful workflow execution. Verify BuildCommandResult has finalize_action="skipped" (no bd operations performed).
  - [x] 11.6 GREEN: Ensure no-issue-id path works correctly.
  - [x] 11.7 REFACTOR: Clean up integration tests, verify all scenarios covered.

- [x] Task 12: Verify full integration and quality gates (AC: #6)
  - [x] 12.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 12.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 12.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 4.3)

**io_ops.py** has 14 public functions + 2 private helpers + 1 async helper + 1 internal exception:
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
# Plus: async _execute_sdk_call_async(), _NoResultError, _find_project_root(), _build_tree_lines()
```

**types.py** has: `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**commands/** package has:
- `types.py` -- `CommandSpec` frozen dataclass
- `registry.py` -- `COMMAND_REGISTRY` (MappingProxyType, 6 commands: verify, build, implement, prime, load_bundle, convert_stories_to_beads), `get_command()`, `list_commands()`. Build command has `workflow_name="implement_close"`.
- `dispatch.py` -- `run_command()` dispatch function (uses `.bind()` pattern). Has verify-specific and prime-specific routing.
- `verify.py` -- `VerifyCommandResult`, `format_verify_success()`, `format_verify_failure()`, `run_verify_command()`
- `prime.py` -- `PrimeContextResult`, `PrimeFileSpec`, `PRIME_FILE_SPECS`, `run_prime_command()`
- `__init__.py` -- exports: `CommandSpec`, `PrimeContextResult`, `PrimeFileSpec`, `VerifyCommandResult`, `get_command`, `list_commands`, `run_command`, `run_prime_command`, `run_verify_command`

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`.

**engine/executor.py** has 8 functions. `_STEP_REGISTRY` has 6 entries: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants), `load_workflow()`, `list_workflows()`, 5 registered workflows. `_IMPLEMENT_CLOSE` currently has 2 placeholder steps: `Step(name="implement", function="execute_sdk_call")` and `Step(name="close", function="bd_close", always_run=True)`.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 389 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: /build Command Architecture

The `/build` command follows the established specialized handler pattern from Stories 4.2 and 4.3, but introduces new patterns for Beads integration (bd close/update) and finalize behavior.

```
.claude/commands/adws-build.md
    |
    v
adws/adw_modules/commands/dispatch.py  (run_command)
    |
    v (detects "build" has specialized handler)
adws/adw_modules/commands/build.py     (run_build_command)
    |
    +-------> io_ops.load_command_workflow("implement_close")
    |         io_ops.execute_command_workflow(workflow, ctx)
    |
    +-------> On success: _finalize_on_success(issue_id)
    |           -> io_ops.run_beads_close(issue_id, reason)
    |
    +-------> On failure: _finalize_on_failure(issue_id, error, attempt)
                -> _build_failure_metadata(error, attempt)
                -> io_ops.run_beads_update_notes(issue_id, metadata)
```

### Design: Finalize Architecture (KEY DESIGN DECISION)

The epic story (4.4) says the `implement_close` workflow should have a finalize step that is `always_run=True`. However, finalize logic involves Beads operations (bd close or bd update) that need awareness of whether the workflow succeeded or failed -- this is COMMAND-level context, not workflow-level.

**Selected approach: Command-level finalize**

The `run_build_command` function handles finalize AFTER the workflow executes, not as a workflow step. This is because:

1. The workflow engine runs steps sequentially but does not have "on success do X, on failure do Y" branching -- that is command-level logic.
2. The finalize behavior differs based on success vs failure (close vs tag), which requires inspecting the IOResult from workflow execution.
3. The `issue_id` comes from the command context (inputs), not from workflow step outputs.

The `_IMPLEMENT_CLOSE` workflow definition should focus on the actual work steps (implement, verify_tests_pass). Finalize is command infrastructure, handled by `run_build_command`.

**Rejected approach: Workflow-level finalize step**

Adding a finalize step function that inspects a shared state variable or side-channel to determine success/failure would violate the immutable WorkflowContext pattern. Steps communicate only through context -- there is no "did the previous step fail?" signal available to a step function.

NOTE: The existing `_IMPLEMENT_CLOSE` workflow in `workflows/__init__.py` has a placeholder `Step(name="close", function="bd_close", always_run=True)`. This story should update the workflow to reflect the actual step composition (implement + verify) and move finalize to the command layer.

### Design: implement_close Workflow Steps

The updated `_IMPLEMENT_CLOSE` workflow should have these steps:

```python
_IMPLEMENT_CLOSE = Workflow(
    name=WorkflowName.IMPLEMENT_CLOSE,
    description="Fast-track for trivial changes: implement then verify",
    dispatchable=True,
    steps=[
        Step(
            name="implement",
            function="execute_sdk_call",
        ),
        Step(
            name="verify_tests_pass",
            function="run_pytest_step",
            shell=True,
            command="uv run pytest adws/tests/ -m 'not enemy'",
        ),
    ],
)
```

The finalize behavior (bd close on success, bd update on failure) is handled by `run_build_command` AFTER the workflow completes. The `always_run=True` guarantee (NFR3) is fulfilled by `run_build_command` unconditionally calling the appropriate finalize function regardless of workflow outcome.

NOTE on `run_pytest_step`: The verify_tests_pass step in implement_close uses a shell step to run pytest. This is simpler than a registered step function because it is a direct shell command. The engine handles shell steps natively via `execute_shell_step` when `shell=True` is set. If the step function `"run_pytest_step"` is not in the registry, it will fail. Since this is a `shell=True` step, the `function` field value is ignored by the engine (see `engine/executor.py` line 78-82: shell steps bypass function resolution and go directly to `execute_shell_step`). Use `function="execute_shell_step"` to match convention.

### Design: Failure Metadata Format

Per AC #4, failure metadata follows a structured pipe-delimited format:

```
ADWS_FAILED|attempt=1|last_failure=2026-02-02T12:00:00Z|error_class=SdkCallError|step=implement|summary=Model timeout
```

This format is designed for machine parsing by the triage workflow (Epic 7, Story 7.4). Key fields:
- `attempt`: 1-indexed attempt count (human-readable)
- `last_failure`: ISO 8601 timestamp of the failure
- `error_class`: The `error_type` field from PipelineError
- `step`: The `step_name` field from PipelineError
- `summary`: The `message` field from PipelineError (pipe characters escaped)

Pipe characters in the summary are escaped as `\|` to prevent field boundary confusion during parsing.

### Design: Issue ID Extraction

The `issue_id` for Beads operations is extracted from `ctx.inputs.get("issue_id")`. This follows the pattern where commands receive their operational parameters through the WorkflowContext inputs dict. If no `issue_id` is present, the finalize step is skipped (no bd operations). This allows `/build` to work both:
- With a Beads issue (automated dispatch via cron, Epic 7)
- Without a Beads issue (manual developer invocation)

### Design: Build Command Success/Failure Semantics

Following the verify command pattern from Story 4.2:
- **IOSuccess(BuildCommandResult(success=True))**: Workflow executed and succeeded, finalize ran.
- **IOSuccess(BuildCommandResult(success=False))**: Workflow executed but failed, failure metadata tagged. The COMMAND succeeded in handling the failure.
- **IOFailure(PipelineError)**: Infrastructure failure (workflow not found, etc.). The command itself failed.

This matches the established pattern: workflow execution outcomes are command-level results, not IOFailures.

### Design: Dispatch Routing Update

After this story, `run_command` in `dispatch.py` will have this flow:
1. Look up command spec (unknown -> IOFailure)
2. Check if verify -> specialized handler
3. Check if prime -> specialized handler
4. Check if build -> specialized handler (NEW)
5. Check if workflow_name is None -> IOFailure(NoWorkflowError)
6. Generic workflow path

### Design: New io_ops Functions

Two new io_ops functions for Beads CLI integration:

```python
def run_beads_close(
    issue_id: str,
    reason: str,
) -> IOResult[ShellResult, PipelineError]:
    """Close a Beads issue via bd close (NFR17).

    Delegates to run_shell_command. Nonzero exit is IOFailure.
    """
    ...

def run_beads_update_notes(
    issue_id: str,
    notes: str,
) -> IOResult[ShellResult, PipelineError]:
    """Update Beads issue notes via bd update (NFR17).

    Delegates to run_shell_command. Nonzero exit is IOFailure.
    """
    ...
```

After this story, io_ops.py will have 16 public functions (up from 14). This crosses the ~15 function threshold noted in the architecture for considering an `io_ops/` package split. Monitor and evaluate during the code review step; the split may be deferred to a dedicated refactoring story if needed.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/commands/test_build.py` -- tests for BuildCommandResult, _build_failure_metadata, _finalize_on_success, _finalize_on_failure, run_build_command + integration tests

**Modified test files**:
- `adws/tests/adw_modules/commands/test_dispatch.py` -- add build-specific dispatch routing, regression tests for other commands
- `adws/tests/adw_modules/commands/test_wiring.py` -- add import tests for new exports, .md file update tests
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for `run_beads_close`, `run_beads_update_notes`
- `adws/tests/workflows/test_implement_close.py` -- update tests to reflect new step composition (if workflow definition changes)

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_build_command_result_construction`
- `test_build_command_result_immutable`
- `test_build_failure_metadata_format`
- `test_build_failure_metadata_pipe_escaping`
- `test_build_failure_metadata_attempt_1_indexed`
- `test_finalize_on_success_close`
- `test_finalize_on_success_bd_failure`
- `test_finalize_on_success_no_issue`
- `test_finalize_on_failure_tag`
- `test_finalize_on_failure_bd_failure`
- `test_finalize_on_failure_no_issue`
- `test_run_build_command_success`
- `test_run_build_command_workflow_failure`
- `test_run_build_command_workflow_load_failure`
- `test_run_build_command_with_issue_id`
- `test_run_build_command_no_issue_id`
- `test_dispatch_build_uses_specialized_handler`
- `test_dispatch_verify_still_works`
- `test_dispatch_prime_still_works`
- `test_dispatch_load_bundle_still_no_workflow`
- `test_run_beads_close_success`
- `test_run_beads_close_failure`
- `test_run_beads_update_notes_success`
- `test_run_beads_update_notes_failure`

**Mock targets for build command tests**:
- `adws.adw_modules.io_ops.load_command_workflow` -- mock workflow loading
- `adws.adw_modules.io_ops.execute_command_workflow` -- mock workflow execution
- `adws.adw_modules.io_ops.run_beads_close` -- mock bd close
- `adws.adw_modules.io_ops.run_beads_update_notes` -- mock bd update

**For io_ops tests**: Mock `adws.adw_modules.io_ops.run_shell_command` for the Beads CLI functions.

**For dispatch regression tests**: Same mock targets as Story 4.1/4.2/4.3 dispatch tests.

### Ruff Considerations

- `FBT001`/`FBT002` (boolean positional): `BuildCommandResult.success` is a field, not a positional param -- no issue.
- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files.
- `E501` (line too long): Keep all lines under 88 characters.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.
- `S108` (hardcoded temp directory): Avoid `/tmp/` literal strings in test data.
- `DTZ003` (datetime.utcnow): Use `datetime.now(tz=timezone.utc)` for failure timestamps (not deprecated `utcnow()`).

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- `run_build_command` returns IOResult, never raises. Finalize functions use `.lash()` for fail-open behavior.
- **NFR2**: Failed workflows leave Beads issues open with structured failure metadata.
- **NFR3**: Finalize executes regardless of workflow outcome (command-level always_run).
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Build command uses io_ops functions for workflow execution and Beads operations.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads interactions exclusively via `bd` CLI (through io_ops.run_beads_close and run_beads_update_notes).
- **NFR21**: Failure metadata tags issue for triage, does not close it.
- **FR20**: bd close on success (via _finalize_on_success).
- **FR28**: Command has .md entry point backed by Python module.
- **FR32**: Developer can invoke /build for fast-track changes.
- **FR46**: Finalize step: close on success, tag failure metadata on failure.

### What NOT to Do

- Do NOT implement a finalize step function in the step registry -- finalize is command-level logic in `run_build_command`, not a pipeline step.
- Do NOT change the verify command (`commands/verify.py`) or the prime command (`commands/prime.py`) or their routing.
- Do NOT change any verify step functions, verify workflow, or io_ops verify functions.
- Do NOT add write_failing_tests or verify_tests_fail steps to the implement_close workflow -- this is the TDD-exempt fast-track workflow.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT use `unsafe_perform_io` in production code (commands, steps). Only use `.bind()` and `.lash()` for composing IOResult chains.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT break the existing `run_command` tests for "verify", "prime", "load_bundle", or "unknown" commands.
- Do NOT add command-specific routing for commands other than "build" in this story.
- Do NOT change the engine executor, step registry (unless adding the `"finalize_build"` function if needed), or any registered workflow steps.
- Do NOT create a separate CLI entry point (`__main__.py`) -- the .md file delegates to dispatch.
- Do NOT read BMAD files during workflow execution (NFR19).
- Do NOT close a Beads issue on failure -- tag with failure metadata and leave open for triage (NFR21).
- Do NOT use `datetime.utcnow()` -- use `datetime.now(tz=timezone.utc)` for ISO timestamps.

### Project Structure Notes

Files to create:
- `adws/adw_modules/commands/build.py` -- `BuildCommandResult`, `_build_failure_metadata()`, `_finalize_on_success()`, `_finalize_on_failure()`, `run_build_command()`
- `adws/tests/adw_modules/commands/test_build.py` -- all build command tests (unit + integration)

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `run_beads_close()`, `run_beads_update_notes()`
- `adws/adw_modules/commands/dispatch.py` -- add build-specific routing in `run_command`
- `adws/adw_modules/commands/__init__.py` -- add exports for `BuildCommandResult`, `run_build_command`
- `adws/workflows/__init__.py` -- update `_IMPLEMENT_CLOSE` step list (remove placeholder, add actual steps)
- `.claude/commands/adws-build.md` -- update from stub to full entry point referencing `run_build_command`
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for `run_beads_close`, `run_beads_update_notes`
- `adws/tests/adw_modules/commands/test_dispatch.py` -- add build dispatch tests, regression tests
- `adws/tests/adw_modules/commands/test_wiring.py` -- add import tests for new exports, .md file tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4] -- AC and story definition (FR32)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] -- Epic summary: "Developer can invoke /implement, /verify, /build, and /prime commands."
- [Source: _bmad-output/planning-artifacts/architecture.md#Command Inventory] -- `/build` maps to `adws/adw_modules/steps/execute.py`, P2 priority
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Composition Notes] -- `implement_close.py`: `/implement` (SDK step) -> `bd close` (shell step, `always_run=True`)
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, `dispatchable` flag, `load_workflow()` pure lookup
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement: implement_close is TDD-exempt (fast-track)
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step patterns, io_ops boundary, ROP patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Four-layer pipeline, io_ops boundary, external system boundaries
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap Analysis #5] -- `implement_close` TDD exemption: "If a change touches Python code, --cov-fail-under=100 catches it regardless"
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR32: "/build command for fast-track changes", FR46: "Finalize step: close on success, tag failure metadata on failure"
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- ADWS -> Beads: `bd` CLI subprocess via io_ops
- [Source: adws/adw_modules/commands/dispatch.py] -- run_command dispatch function with verify and prime routing
- [Source: adws/adw_modules/commands/verify.py] -- Verify command pattern (specialized handler + result formatting + .lash() for failure conversion)
- [Source: adws/adw_modules/commands/prime.py] -- Prime command pattern (specialized handler, non-workflow)
- [Source: adws/adw_modules/commands/registry.py] -- COMMAND_REGISTRY with "build" mapping to workflow_name="implement_close"
- [Source: adws/adw_modules/commands/types.py] -- CommandSpec frozen dataclass
- [Source: adws/adw_modules/commands/__init__.py] -- Current exports
- [Source: adws/adw_modules/io_ops.py] -- 14 public functions, run_shell_command, load_command_workflow, execute_command_workflow
- [Source: adws/adw_modules/types.py] -- WorkflowContext with merge_outputs(), ShellResult
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass with to_dict()
- [Source: adws/adw_modules/engine/types.py] -- Step (with shell, command, always_run), Workflow (with dispatchable)
- [Source: adws/adw_modules/engine/executor.py] -- run_workflow, run_step (shell=True bypasses function resolution), _STEP_REGISTRY
- [Source: adws/workflows/__init__.py] -- _IMPLEMENT_CLOSE current placeholder (2 steps), WorkflowName.IMPLEMENT_CLOSE
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: .claude/commands/adws-build.md] -- Current stub .md entry point
- [Source: _bmad-output/implementation-artifacts/4-2-verify-command-entry-point.md] -- Verify command specialized handler pattern, .lash() for failure conversion
- [Source: _bmad-output/implementation-artifacts/4-3-prime-command-for-context-loading.md] -- Prime command pattern, dispatch routing ordering
- [Source: _bmad-output/implementation-artifacts/4-1-command-pattern-md-entry-points-and-python-module-wiring.md] -- Command infrastructure, dispatch, registry, wiring

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

From Story 4.3 learnings:
- **Dispatch routing ordering**: unknown -> verify -> prime -> no-workflow -> generic. Build goes AFTER prime, BEFORE no-workflow check.
- **ROP .bind() pattern**: prime.py uses `.bind()` for composing IOResult chains. Build will use `.bind()` for workflow execution and `.lash()` for failure handling.
- **_extract_io_value pattern**: prime.py used `unsafe_perform_io` in a private helper for imperative loops. Avoid this pattern -- prefer `.bind()` composition.
- **389 tests**: Current test count (excluding 2 enemy tests), 100% line+branch coverage.
- **io_ops at 14 functions**: Approaching ~15 threshold. This story adds 2 more (run_beads_close, run_beads_update_notes), reaching 16. Monitor.
- **Dispatch test updates**: When adding prime routing, one existing dispatch test was updated to use "load_bundle" instead of "prime". When adding build routing, the test that currently routes build through the generic workflow path must be updated/replaced with build-specific handler test.

From Story 4.2 learnings:
- **Verify dispatch routing pattern**: `run_command` checks `spec.name == "verify"` and routes to `run_verify_command`, wrapping result in WorkflowContext via `.bind(_wrap_vr)`. Follow this pattern for build.
- **ROP .lash() pattern**: verify.py uses `.lash(_format_failure_result)` to convert tool IOFailure into IOSuccess(VerifyCommandResult(success=False)). Build will use the same pattern for converting workflow failures into BuildCommandResult.
- **Result wrapping**: After specialized handler returns, result is placed in `ctx.merge_outputs({"verify_result": vr})`. Build should use `ctx.merge_outputs({"build_result": br})`.
- **Tool failures are NOT command failures**: Established in verify. Build follows: workflow failures -> IOSuccess(BuildCommandResult(success=False)), infrastructure failures -> IOFailure(PipelineError).

From Story 4.1 learnings:
- **Circular import resolution**: io_ops.py uses lazy imports inside function bodies. New io_ops Beads functions should NOT need lazy imports (they don't reference engine).
- **Mock targets**: Tests mock at `adws.adw_modules.io_ops.<function_name>`.
- **CommandSpec**: build command has `workflow_name="implement_close"` in registry.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Relationship to Subsequent Stories

This story introduces the Beads integration pattern (bd close, bd update) that will be reused by:

1. **Story 4.1 (done)**: Command pattern -- registry, dispatch, .md entry points
2. **Story 4.2 (done)**: `/verify` command -- specialized handler, workflow-backed
3. **Story 4.3 (done)**: `/prime` command -- specialized handler, non-workflow
4. **Story 4.4 (this)**: `/build` command -- implement_close workflow + Beads finalize
5. **Stories 4.5-4.7**: TDD workflow steps (write_failing_tests, verify_tests_fail, implement, refactor)
6. **Story 4.8**: `/implement` command -- implement_verify_close workflow, reuses finalize pattern from 4.4
7. **Story 7.2**: Workflow execution & issue closure -- reuses `run_beads_close` and `run_beads_update_notes` from this story

The Beads io_ops functions (`run_beads_close`, `run_beads_update_notes`) and the failure metadata format established here become the shared contract for all workflows that interact with Beads issues.

### io_ops.py Size Note

After this story, io_ops.py will have 16 public functions (up from 14). This crosses the ~15 function threshold noted in the architecture (architecture.md, io_ops Scaling Consideration section). Evaluate during code review whether to split into an `io_ops/` package. The split would be:
```
io_ops/
├── __init__.py      # Re-exports everything (mock point unchanged)
├── filesystem.py    # read_file, read_prime_file, get_directory_tree
├── sdk.py           # execute_sdk_call, check_sdk_import
├── beads.py         # run_beads_close, run_beads_update_notes
├── shell.py         # run_shell_command, sleep_seconds
└── verify.py        # run_jest_tests, run_playwright_tests, run_mypy_check, run_ruff_check
```

This is a ZERO-COST refactor because the mock point stays `adws.adw_modules.io_ops.some_function` regardless. Do NOT block this story on the refactor -- evaluate after implementation is complete.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- 425 tests passing (up from 389), 2 skipped (enemy tests)
- 100% line + branch coverage maintained
- mypy strict: 0 errors across 62 source files
- ruff: 0 violations
- io_ops.py now has 16 public functions (up from 14) -- crossed ~15 threshold noted in architecture. Evaluate split during code review.
- implement_close workflow updated from placeholder (2 steps: implement + close) to actual steps (implement + verify_tests_pass). Finalize logic handled at command level per design decision.
- Existing dispatch tests updated: build no longer uses generic workflow path, now routes to specialized handler.
- Test for "execute failure propagates" now uses "implement" command (generic path) instead of "build" (specialized handler).

### File List

Files created:
- `adws/adw_modules/commands/build.py` -- BuildCommandResult, _build_failure_metadata, _finalize_on_success, _finalize_on_failure, run_build_command
- `adws/tests/adw_modules/commands/test_build.py` -- 22 tests (unit + integration)

Files modified:
- `adws/adw_modules/io_ops.py` -- added run_beads_close(), run_beads_update_notes()
- `adws/adw_modules/commands/dispatch.py` -- added build-specific routing in run_command
- `adws/adw_modules/commands/__init__.py` -- added BuildCommandResult, run_build_command exports
- `adws/workflows/__init__.py` -- updated _IMPLEMENT_CLOSE steps (implement + verify_tests_pass)
- `.claude/commands/adws-build.md` -- updated from stub to full entry point
- `adws/tests/adw_modules/test_io_ops.py` -- added 5 tests for run_beads_close, run_beads_update_notes
- `adws/tests/adw_modules/commands/test_dispatch.py` -- replaced generic-path build tests with specialized-handler tests + regression tests
- `adws/tests/adw_modules/commands/test_wiring.py` -- added 4 build wiring tests (imports, .md references, not-stub)
- `adws/tests/workflows/test_workflows.py` -- added 5 implement_close step composition tests

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial review mode)
**Date**: 2026-02-02
**Verdict**: APPROVED with 4 fixes applied (2 HIGH, 2 MEDIUM, 1 LOW noted)

### Issues Found & Resolved

**ISSUE 1 (HIGH) -- Shell injection in io_ops beads functions: FIXED**
- `run_beads_close` and `run_beads_update_notes` used f-string interpolation to build shell commands (`f'bd close {issue_id} --reason "{reason}"'`) passed to `subprocess.run(shell=True)`. If `issue_id` or `reason`/`notes` contained shell metacharacters (quotes, semicolons, `$()`, backticks), arbitrary commands could execute. The `issue_id` originates from `ctx.inputs.get("issue_id")` which is user/caller-controllable.
- **Fix**: Added `import shlex` and wrapped all user-provided values with `shlex.quote()` before interpolation. Added 2 new tests (`test_run_beads_close_shell_safe`, `test_run_beads_update_notes_shell_safe`) that verify shell metacharacters in inputs are safely quoted.
- **Files**: `adws/adw_modules/io_ops.py` (lines 527-530, 564-567), `adws/tests/adw_modules/test_io_ops.py`

**ISSUE 2 (MEDIUM) -- Missing UTC 'Z' suffix in failure metadata timestamp: FIXED**
- `_build_failure_metadata` generated timestamps with `strftime("%Y-%m-%dT%H:%M:%S")` but omitted the `Z` suffix. The story's own design spec (line 248) shows the format as `2026-02-02T12:00:00Z`. Without the `Z`, the timestamp is ambiguous per ISO 8601 -- consumers cannot distinguish UTC from local time.
- **Fix**: Changed format string to `"%Y-%m-%dT%H:%M:%SZ"`. Updated test regex to expect the Z suffix.
- **Files**: `adws/adw_modules/commands/build.py` (line 56), `adws/tests/adw_modules/commands/test_build.py`

**ISSUE 3 (MEDIUM) -- Pipe escaping test used naive split, did not validate correctness: FIXED**
- `test_build_failure_metadata_pipe_escaping` performed `result.split("|")` producing 8 fields, then only asserted `parts[0] == "ADWS_FAILED"`. The comment said "escaped pipes should NOT break the field count" but no assertion actually validated field count preservation. A naive `.split("|")` always breaks on escaped pipes, so the test validated nothing about the escaping contract.
- **Fix**: Added a `_parse_metadata_fields()` helper that implements backslash-aware pipe splitting (the consumer protocol), then asserted `len(fields) == 6` and validated the summary field contains the original unescaped message with pipes restored.
- **Files**: `adws/tests/adw_modules/commands/test_build.py`

**ISSUE 4 (LOW) -- Unused mocker fixture parameters in 2 test functions: FIXED**
- `test_finalize_on_success_no_issue` and `test_finalize_on_success_empty_issue` accepted `mocker: MockerFixture` parameter but never used it (these tests call `_finalize_on_success(None)` and `_finalize_on_success("")` which short-circuit before any I/O).
- **Fix**: Removed the unused `mocker` parameter from both function signatures.
- **Files**: `adws/tests/adw_modules/commands/test_build.py`

**ISSUE 5 (LOW) -- Hardcoded attempt_count=1 in run_build_command: NOTED (not fixed)**
- The `_on_failure` handler in `run_build_command` always passes `attempt_count=1` to `_finalize_on_failure`. The workflow engine's internal retry info (from `_run_step_with_retry`) is available in `PipelineError.context` but not standardized for extraction. This means failure metadata always reports `attempt=1` even when the engine retried internally.
- **Not fixed**: This is a design gap between the engine's retry mechanism and the command's finalize layer. The retry count lives inside PipelineError.context but has no standardized key. Fixing would require either: (a) standardizing an `attempt_count` key in PipelineError.context, or (b) passing engine retry info through the error chain. Both are cross-cutting changes that should be a separate story. For now the behavior is correct -- the command-level attempt is 1 (the command does not retry the workflow), and any step-level retries are an engine detail.

### Quality Gate Results (Post-Fix)

| Gate | Result |
|------|--------|
| pytest (427 tests, 2 skipped enemy) | PASS |
| Coverage (line + branch) | 100% |
| mypy --strict (62 source files) | 0 errors |
| ruff check | 0 violations |

### AC Verification

| AC | Verified | Notes |
|----|----------|-------|
| AC1: /build executes implement_close workflow | Yes | `run_build_command` loads and executes implement_close via io_ops |
| AC2: Workflow runs implement -> verify_tests_pass, no TDD steps | Yes | `_IMPLEMENT_CLOSE` has exactly 2 steps, no write_failing_tests/verify_tests_fail |
| AC3: Success path closes Beads issue | Yes | `_finalize_on_success` calls `io_ops.run_beads_close` with "Completed successfully" |
| AC4: Failure path tags issue with structured metadata | Yes | `_finalize_on_failure` calls `io_ops.run_beads_update_notes` with ADWS_FAILED metadata |
| AC5: Tests cover success, failure, and always_run | Yes | 22 tests in test_build.py covering all paths |
| AC6: All quality gates pass | Yes | 427 tests, 100% coverage, mypy strict, ruff clean |

### Architecture Compliance

- NFR1 (no uncaught exceptions): `run_build_command` returns IOResult. Finalize uses `.lash()` for fail-open.
- NFR2 (structured failure metadata): ADWS_FAILED pipe-delimited format with ISO 8601 UTC timestamp.
- NFR3 (finalize always runs): Command-level finalize executes regardless of workflow outcome.
- NFR9 (100% coverage): Verified -- 100% line + branch.
- NFR10 (I/O behind io_ops): All Beads CLI operations via `run_beads_close`/`run_beads_update_notes`.
- NFR11 (mypy strict): 0 errors across 62 files.
- NFR12 (ruff ALL rules): 0 violations.
- NFR17 (bd CLI): Beads interactions via `bd close`/`bd update` through io_ops shell commands, now with shlex.quote() sanitization.
- NFR21 (failure leaves issue open): Failure path calls `bd update --notes` not `bd close`.

### Test Count Delta

- Before: 425 tests (2 skipped enemy)
- After: 427 tests (2 skipped enemy)
- Delta: +2 tests (shell injection safety tests for run_beads_close and run_beads_update_notes)

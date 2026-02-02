# Story 7.2: Workflow Execution & Issue Closure

Status: ready-for-dev

## Story

As an ADWS developer,
I want dispatched workflows to execute through the engine and close their Beads issue on success,
so that completed work is automatically tracked without manual intervention.

## Acceptance Criteria

1. **Given** a dispatched workflow from Story 7.1, **When** the engine executes it, **Then** the full workflow runs through the engine with ROP error handling (NFR1) **And** context propagation, retry logic, and always_run steps function as defined in Epic 2.

2. **Given** workflow execution succeeds, **When** the finalize step runs (always_run, NFR3), **Then** `bd close <id> --reason "Completed successfully"` is called via io_ops (FR20, FR46, NFR17) **And** the closure includes a success summary in the close reason.

3. **Given** workflow execution fails after retries are exhausted, **When** the finalize step runs (always_run, NFR3), **Then** the Beads issue remains open with structured failure metadata via `bd update --notes "ADWS_FAILED|..."` (NFR2, FR46) **And** failure metadata includes: attempt count, error classification, step name, failure summary **And** the issue is NOT closed -- it remains open for automated triage (NFR21).

4. **Given** all execution and finalize code, **When** I run tests, **Then** tests cover: successful execution and close, failure with structured metadata tagging, finalize always runs in both paths **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Create `execute_dispatched_workflow` function in `adw_dispatch.py` (AC: #1)
  - [ ] 1.1 RED: Write test for `execute_dispatched_workflow(ctx: WorkflowContext) -> IOResult[DispatchExecutionResult, PipelineError]` in `adws/tests/test_adw_dispatch.py`. Given a `WorkflowContext` with `inputs` containing `"issue_id"="ISSUE-42"`, `"issue_description"="Story content"`, `"workflow_tag"="implement_verify_close"`, and `"workflow"=<Workflow object>`, mock `io_ops.execute_command_workflow` to return `IOSuccess(WorkflowContext(...))`. Verify it returns `IOSuccess(DispatchExecutionResult)` with `success=True`, `workflow_executed="implement_verify_close"`, `issue_id="ISSUE-42"`, `finalize_action="closed"`, and a success summary. Also mock `io_ops.run_beads_close` to return `IOSuccess(ShellResult(...))`.
  - [ ] 1.2 GREEN: Create `DispatchExecutionResult` frozen dataclass in `adws/adw_dispatch.py` with fields: `success` (bool), `workflow_executed` (str), `issue_id` (str | None), `finalize_action` (str), `summary` (str). Implement `execute_dispatched_workflow` that: (a) extracts the `Workflow` object from `ctx.inputs["workflow"]`, (b) calls `io_ops.execute_command_workflow(workflow, ctx)`, (c) on success calls `finalize_on_success(issue_id)` from `_finalize`, (d) wraps in `DispatchExecutionResult` and returns `IOSuccess`.
  - [ ] 1.3 RED: Write test for `execute_dispatched_workflow` when `ctx.inputs` is missing `"workflow"`. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="execute_dispatched_workflow"`.
  - [ ] 1.4 GREEN: Implement missing input validation for `"workflow"` key.
  - [ ] 1.5 RED: Write test for `execute_dispatched_workflow` when `ctx.inputs["workflow"]` is not a `Workflow` instance (e.g., a string). Verify it returns `IOFailure(PipelineError)` with `error_type="InvalidInputError"` and `step_name="execute_dispatched_workflow"`.
  - [ ] 1.6 GREEN: Implement type validation for the `workflow` input.
  - [ ] 1.7 RED: Write test for `execute_dispatched_workflow` when `ctx.inputs` is missing `"issue_id"`. The function should still execute the workflow but finalize with `"skipped"` (no Beads issue to close). Verify `finalize_action="skipped"`.
  - [ ] 1.8 GREEN: Implement optional issue_id handling -- extract with `.get("issue_id")`, pass to finalize (which handles `None` gracefully).
  - [ ] 1.9 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 2: Handle workflow execution failure with finalize (AC: #3)
  - [ ] 2.1 RED: Write test for `execute_dispatched_workflow` when `io_ops.execute_command_workflow` returns `IOFailure(PipelineError)`. Mock `io_ops.run_beads_update_notes` to return `IOSuccess(ShellResult(...))`. Verify it returns `IOSuccess(DispatchExecutionResult)` with `success=False`, `finalize_action="tagged_failure"`, and `summary` containing the error message. The function uses `.lash()` to handle the failure path (fail-open finalize, NFR3).
  - [ ] 2.2 GREEN: Implement the failure path in `execute_dispatched_workflow`. When workflow execution fails, call `finalize_on_failure(issue_id, error, attempt_count)` from `_finalize`. The `attempt_count` is 1 for now (the dispatch path executes the workflow once; retry is handled by the engine internally). Wrap in `DispatchExecutionResult(success=False)`.
  - [ ] 2.3 RED: Write test for `execute_dispatched_workflow` when workflow fails AND `io_ops.run_beads_update_notes` also fails (bd update fails). Verify it returns `IOSuccess(DispatchExecutionResult)` with `success=False`, `finalize_action="tag_failed"`. The finalize helper already handles this via `.lash()` returning `"tag_failed"`.
  - [ ] 2.4 GREEN: Ensure the existing `finalize_on_failure` `.lash()` pattern propagates `"tag_failed"` correctly.
  - [ ] 2.5 RED: Write test for `execute_dispatched_workflow` when workflow succeeds AND `io_ops.run_beads_close` fails (bd close fails). Verify it returns `IOSuccess(DispatchExecutionResult)` with `success=True`, `finalize_action="close_failed"`. The `finalize_on_success` helper already handles this via `.lash()`.
  - [ ] 2.6 GREEN: Ensure the existing `finalize_on_success` `.lash()` pattern propagates `"close_failed"` correctly.
  - [ ] 2.7 RED: Write test for `execute_dispatched_workflow` when workflow fails and `issue_id` is `None`. Verify `finalize_action="skipped"` (no Beads call made).
  - [ ] 2.8 GREEN: Ensure `finalize_on_failure` returns `"skipped"` when `issue_id` is `None`.
  - [ ] 2.9 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 3: Create `dispatch_and_execute` orchestrator function (AC: #1, #2, #3)
  - [ ] 3.1 RED: Write test for `dispatch_and_execute(issue_id: str) -> IOResult[DispatchExecutionResult, PipelineError]` in `adws/tests/test_adw_dispatch.py`. This is the full pipeline: dispatch (from Story 7.1) + execute + finalize. Given `issue_id="ISSUE-42"`, mock `io_ops.read_issue_description` to return a description with `{implement_verify_close}` tag, mock `io_ops.execute_command_workflow` to return `IOSuccess(WorkflowContext(...))`, mock `io_ops.run_beads_close` to return `IOSuccess(ShellResult(...))`. Verify it returns `IOSuccess(DispatchExecutionResult)` with `success=True`, `workflow_executed="implement_verify_close"`, `issue_id="ISSUE-42"`, `finalize_action="closed"`.
  - [ ] 3.2 GREEN: Implement `dispatch_and_execute` in `adws/adw_dispatch.py`. Call `dispatch_workflow(issue_id)` (from Story 7.1). If successful, call `execute_dispatched_workflow(ctx)`. Return the result. If dispatch itself fails (unknown tag, non-dispatchable, etc.), propagate the IOFailure directly -- no finalize needed because no workflow was started.
  - [ ] 3.3 RED: Write test for `dispatch_and_execute` when dispatch fails (e.g., unknown workflow tag). Verify it returns `IOFailure(PipelineError)` with `error_type="UnknownWorkflowTagError"`. No finalize should be called because no workflow was started.
  - [ ] 3.4 GREEN: Ensure dispatch failures propagate directly without finalize.
  - [ ] 3.5 RED: Write test for `dispatch_and_execute` when dispatch succeeds but workflow execution fails. Verify it returns `IOSuccess(DispatchExecutionResult(success=False))` with `finalize_action="tagged_failure"`.
  - [ ] 3.6 GREEN: Ensure execution failure with finalize flows through correctly.
  - [ ] 3.7 RED: Write test for `dispatch_and_execute` with empty `issue_id`. Verify it returns `IOFailure(PipelineError)` with `error_type="ValueError"` (from `dispatch_workflow` validation).
  - [ ] 3.8 GREEN: Ensure empty issue_id propagation from dispatch_workflow.
  - [ ] 3.9 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 4: Verify finalize metadata format compliance (AC: #3)
  - [ ] 4.1 RED: Write test verifying the failure metadata format produced by `build_failure_metadata` matches the format expected by Story 7.4 (triage parser): `ADWS_FAILED|attempt=N|last_failure=TIMESTAMP|error_class=CLASS|step=STEP|summary=TEXT`. Given a `PipelineError(step_name="implement", error_type="SdkCallError", message="SDK timeout")` with `attempt_count=1`, verify the output string starts with `ADWS_FAILED|attempt=1|last_failure=` and contains `|error_class=SdkCallError|step=implement|summary=SDK timeout`.
  - [ ] 4.2 GREEN: `build_failure_metadata` already exists in `_finalize.py` and produces this format. Verify the test passes against the existing implementation. If any field is missing or differently named, adjust. NOTE: This is a validation task -- the implementation exists from Story 4.4. The test confirms Story 7.2 requirements are met by the existing code.
  - [ ] 4.3 RED: Write test verifying that failure metadata with pipe characters in the error message are properly escaped. Given `message="step A | step B failed"`, verify the summary field contains `step A \\|  step B failed` (pipes escaped).
  - [ ] 4.4 GREEN: Verify existing `build_failure_metadata` escapes pipes correctly (it already does via `error.message.replace("|", "\\|")`).
  - [ ] 4.5 REFACTOR: Clean up.

- [ ] Task 5: Verify NFR19 compliance in execution path (AC: #1)
  - [ ] 5.1 RED: Write test confirming that `execute_dispatched_workflow` never reads BMAD files (NFR19). Mock `io_ops.read_bmad_file` and verify it is NOT called during execution. The only data source is the Beads issue description already in `WorkflowContext.inputs`.
  - [ ] 5.2 GREEN: Confirm the implementation does not import or call any BMAD-related io_ops functions.
  - [ ] 5.3 RED: Write test confirming that `dispatch_and_execute` never reads BMAD files through the full flow.
  - [ ] 5.4 GREEN: Confirm NFR19 compliance in the full orchestrator.
  - [ ] 5.5 REFACTOR: Clean up.

- [ ] Task 6: Integration tests for full dispatch-execute-finalize flow (AC: #1, #2, #3, #4)
  - [ ] 6.1 RED: Write integration test for successful dispatch-execute-close: Given a Beads issue with `{implement_verify_close}` tag, mock `io_ops.read_issue_description` to return the description, mock `io_ops.execute_command_workflow` to return `IOSuccess`, mock `io_ops.run_beads_close` to return `IOSuccess`. Call `dispatch_and_execute("ISSUE-42")`. Verify the returned `DispatchExecutionResult` has `success=True`, `finalize_action="closed"`, `workflow_executed="implement_verify_close"`.
  - [ ] 6.2 GREEN: Ensure full success flow works end-to-end.
  - [ ] 6.3 RED: Write integration test for dispatch-execute-failure-tag: Given a Beads issue with `{implement_close}` tag, mock `io_ops.read_issue_description`, mock `io_ops.execute_command_workflow` to return `IOFailure(PipelineError(...))`, mock `io_ops.run_beads_update_notes` to return `IOSuccess`. Verify `DispatchExecutionResult` has `success=False`, `finalize_action="tagged_failure"`. Verify `io_ops.run_beads_update_notes` was called with an `ADWS_FAILED|...` metadata string.
  - [ ] 6.4 GREEN: Ensure failure with metadata tagging works end-to-end.
  - [ ] 6.5 RED: Write integration test verifying that `io_ops.run_beads_close` is NOT called when workflow fails. Only `io_ops.run_beads_update_notes` should be called for the failure path.
  - [ ] 6.6 GREEN: Ensure close is not called on failure path.
  - [ ] 6.7 RED: Write integration test verifying that `io_ops.run_beads_update_notes` is NOT called when workflow succeeds. Only `io_ops.run_beads_close` should be called for the success path.
  - [ ] 6.8 GREEN: Ensure update_notes is not called on success path.
  - [ ] 6.9 RED: Write integration test for dispatch failure (unknown tag) -- verify no workflow execution occurs and no finalize call is made. Neither `io_ops.execute_command_workflow` nor `io_ops.run_beads_close` nor `io_ops.run_beads_update_notes` should be called.
  - [ ] 6.10 GREEN: Ensure dispatch failures short-circuit cleanly.
  - [ ] 6.11 RED: Write integration test verifying NFR19 across the full flow: `io_ops.read_bmad_file` is never called.
  - [ ] 6.12 GREEN: Confirm NFR19 compliance.
  - [ ] 6.13 REFACTOR: Clean up integration tests.

- [ ] Task 7: Verify full integration and quality gates (AC: #5)
  - [ ] 7.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 7.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 7.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 7.1)

**adw_dispatch.py** exists with `dispatch_workflow(issue_id: str) -> IOResult[WorkflowContext, PipelineError]`. This function reads a Beads issue, extracts its workflow tag, validates the workflow exists and is dispatchable, and returns a prepared `WorkflowContext`. It does NOT execute the workflow. This story extends `adw_dispatch.py` with execution and finalize capabilities.

**io_ops.py** has ~29 public functions. Key functions for this story (all already exist):
```python
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
def read_issue_description(issue_id: str) -> IOResult[str, PipelineError]: ...
```

**_finalize.py** exists in `adws/adw_modules/commands/` with shared finalize helpers (from Story 4.4):
```python
def build_failure_metadata(error: PipelineError, attempt_count: int) -> str: ...
def finalize_on_success(issue_id: str | None) -> IOResult[str, PipelineError]: ...
def finalize_on_failure(issue_id: str | None, error: PipelineError, attempt_count: int) -> IOResult[str, PipelineError]: ...
```

These helpers handle:
- `finalize_on_success`: calls `run_beads_close(issue_id, "Completed successfully")`, returns `"closed"` on success, `"close_failed"` if bd fails, `"skipped"` if no issue_id. Uses `.lash()` for fail-open (NFR3).
- `finalize_on_failure`: calls `run_beads_update_notes(issue_id, metadata)` with structured `ADWS_FAILED|...` string, returns `"tagged_failure"` on success, `"tag_failed"` if bd fails, `"skipped"` if no issue_id.
- `build_failure_metadata`: formats `ADWS_FAILED|attempt=N|last_failure=ISO|error_class=X|step=Y|summary=Z` with pipe escaping.

**commands/build.py** and **commands/implement.py** already use this pattern. The dispatch execution path follows the same structure: execute workflow -> finalize based on result.

**workflows/__init__.py** has 5 registered workflows. Two are dispatchable: `implement_close` and `implement_verify_close`.

**engine/executor.py** has `run_workflow(workflow, ctx) -> IOResult[WorkflowContext, PipelineError]`. This is wrapped by `io_ops.execute_command_workflow` which is the entry point for workflow execution.

**Current test count**: 1087 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 120 files tracked by mypy.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: Story 7.2 Architecture

This story builds on Story 7.1's dispatch mechanism by adding:

1. **Workflow execution**: Takes the `WorkflowContext` prepared by `dispatch_workflow` and runs the dispatched workflow through the engine
2. **Finalize (always_run)**: Closes the Beads issue on success, tags with failure metadata on failure
3. **Full orchestrator**: `dispatch_and_execute` combines dispatch + execute + finalize into a single entry point for the cron trigger (Story 7.3)

```
Architecture: Workflow Execution & Issue Closure

                    dispatch_and_execute(issue_id)
                              |
                    +---------+---------+
                    |                   |
                    v                   v
          dispatch_workflow()    execute_dispatched_workflow()
          (Story 7.1)                   |
          Returns WorkflowContext       |
          with issue_id,          +-----+------+
          description,            |            |
          workflow_tag,           v            v
          workflow           on success    on failure
                                |            |
                                v            v
                          finalize_on_   finalize_on_
                          success()      failure()
                                |            |
                                v            v
                          bd close       bd update
                          --reason       --notes
                          "Completed     "ADWS_FAILED|..."
                          successfully"
```

### Design: Reusing Existing Finalize Pattern

The finalize helpers in `_finalize.py` were designed for reuse across commands (build.py, implement.py). This story reuses them for the dispatch path:

- **Success path**: `finalize_on_success(issue_id)` -> `bd close <id> --reason "Completed successfully"` (FR20)
- **Failure path**: `finalize_on_failure(issue_id, error, attempt_count)` -> `bd update <id> --notes "ADWS_FAILED|..."` (FR46)

Both use `.lash()` for fail-open behavior (NFR3): if the Beads CLI call itself fails, the function still returns a successful result with a `"close_failed"` or `"tag_failed"` action string. This ensures finalize never throws, matching the `always_run` guarantee.

### Design: Result Type

The `DispatchExecutionResult` follows the same pattern as `BuildCommandResult` and `ImplementCommandResult`:

```python
@dataclass(frozen=True)
class DispatchExecutionResult:
    success: bool
    workflow_executed: str
    issue_id: str | None
    finalize_action: str  # "closed", "tagged_failure", "tag_failed", "close_failed", "skipped"
    summary: str
```

IOFailure is reserved for infrastructure errors (missing inputs, invalid workflow type). Workflow execution failures produce `IOSuccess(DispatchExecutionResult(success=False))`. This pattern keeps the success/failure semantic clear:
- `IOFailure` = dispatch infrastructure broke (cannot even attempt execution)
- `IOSuccess(success=False)` = workflow ran but failed (finalize tagged the issue)
- `IOSuccess(success=True)` = workflow succeeded (issue closed)

### Design: Separation from Commands

The dispatch execution path (`dispatch_and_execute`) is distinct from the command execution path (`run_build_command`, `run_implement_command`):

- **Commands** (build, implement): Invoked interactively by developer. Load workflow by name. May or may not have an issue_id.
- **Dispatch** (dispatch_and_execute): Invoked programmatically by cron trigger (Story 7.3). Always has an issue_id. Workflow is determined by the issue's tag, not by the user.

Both paths use the same finalize helpers (`_finalize.py`) and the same engine (`execute_command_workflow`). The difference is the entry point and how the workflow is selected.

### Design: Why `execute_dispatched_workflow` Takes WorkflowContext

The `execute_dispatched_workflow` function takes a `WorkflowContext` (not a workflow name or issue_id) because:

1. The dispatch step (Story 7.1) already validated the workflow and prepared the context
2. The function does not need to re-read the issue or re-validate the workflow
3. The `Workflow` object is in `ctx.inputs["workflow"]` -- the engine receives it directly
4. This separation allows testing the execution path independently from the dispatch path

### Design: Attempt Count

The `attempt_count` passed to `finalize_on_failure` is `1` in the dispatch path. This represents the number of times the dispatch system attempted to run the workflow (once). Individual step retries within the workflow are handled by the engine's retry logic (max_attempts on Step). The triage workflow (Story 7.4) tracks cross-dispatch attempt counts.

### Design: Context Propagation

When `dispatch_and_execute` calls `execute_dispatched_workflow`, the `WorkflowContext` flows through as-is. The engine's `run_workflow` receives the context with:
- `inputs.issue_id` = the Beads issue ID
- `inputs.issue_description` = the issue description (from bd show)
- `inputs.workflow_tag` = the extracted workflow tag name
- `inputs.workflow` = the Workflow object

The engine steps can access these via `ctx.inputs["issue_description"]` for their system prompts. This is how the implementation agent knows what to implement (NFR19 -- from Beads issue, not BMAD files).

### Test Strategy

**New test additions** (extending existing test files):
- `adws/tests/test_adw_dispatch.py` -- add `execute_dispatched_workflow` and `dispatch_and_execute` tests
- `adws/tests/integration/test_dispatch_flow.py` -- add full dispatch-execute-finalize integration tests

**No new test files needed** -- all new functions live in `adw_dispatch.py` which already has a test file from Story 7.1.

**Mock targets**:
- `adws.adw_modules.io_ops.execute_command_workflow` -- mock in execution tests
- `adws.adw_modules.io_ops.run_beads_close` -- mock in finalize success tests
- `adws.adw_modules.io_ops.run_beads_update_notes` -- mock in finalize failure tests
- `adws.adw_modules.io_ops.read_issue_description` -- mock in dispatch_and_execute tests (already mocked in Story 7.1 tests)
- `adws.adw_modules.io_ops.read_bmad_file` -- mock to VERIFY IT IS NOT CALLED (NFR19)

**Existing finalize tests**: `_finalize.py` is already fully tested. This story's tests verify that `execute_dispatched_workflow` correctly delegates to the finalize helpers. The finalize helpers' internal behavior is tested in their own test file.

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.
- Lazy imports (e.g., `from adws.workflows import load_workflow` inside function body) need `# noqa: PLC0415`.

### Architecture Compliance

- **NFR1**: ROP error handling throughout. IOFailure for infrastructure errors, IOSuccess for workflow results.
- **NFR2**: Failed workflows leave Beads issues open with structured `ADWS_FAILED` metadata.
- **NFR3**: Finalize runs regardless of success/failure via `.lash()` pattern. Never throws.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Workflow execution via `execute_command_workflow`. Beads via `run_beads_close` and `run_beads_update_notes`.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads via bd CLI only. Close and update via existing io_ops functions.
- **NFR19**: ADWS never reads BMAD files during execution. The Beads issue description is the only contract. Tests verify `io_ops.read_bmad_file` is not called.
- **NFR21**: Failed issues remain open for automated triage (Story 7.4). They are NOT closed.
- **FR20**: Close Beads issue on successful workflow completion via `bd close --reason`.
- **FR46**: Finalize step: close on success, tag failure metadata on failure.
- **Decision 5**: `load_workflow()` is pure lookup. Policy enforcement (dispatchable flag) in `adw_dispatch.py` (from Story 7.1).
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT implement the cron trigger. That is Story 7.3.
- Do NOT implement triage/failure recovery. That is Story 7.4.
- Do NOT change `dispatch_workflow` from Story 7.1 -- only extend `adw_dispatch.py` with new functions.
- Do NOT change `finalize_on_success` or `finalize_on_failure` in `_finalize.py` -- reuse them as-is.
- Do NOT change `load_workflow()` or `list_workflows()` in `workflows/__init__.py`.
- Do NOT change the engine executor logic.
- Do NOT change existing io_ops functions -- this story uses them, not modifies them.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in `adw_dispatch.py`.
- Do NOT read BMAD files from any code in this story (NFR19).
- Do NOT re-implement finalize logic -- reuse `_finalize.py` helpers.
- Do NOT create a separate finalize step module -- the finalize is integrated into the dispatch execution function using the existing command finalize pattern.

### Relationship to Adjacent Stories

- **Story 7.1** (predecessor): Issue Tag Extraction & Workflow Dispatch -- provides `dispatch_workflow()` that returns a prepared `WorkflowContext`. This story adds `execute_dispatched_workflow()` and `dispatch_and_execute()` that use the dispatched context.
- **Story 4.4** (dependency): Build command -- introduced `_finalize.py` with shared finalize helpers that this story reuses.
- **Story 4.8** (dependency): Implement command -- uses the same finalize pattern. The dispatch execution mirrors this structure.
- **Story 7.3** (successor): Cron Trigger -- calls `dispatch_and_execute()` from this story during autonomous polling. Story 7.3 is the consumer of the orchestrator function built here.
- **Story 7.4** (downstream): Triage Workflow -- processes issues tagged with `ADWS_FAILED` metadata by this story's finalize-on-failure path.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (Issue Integration section):**
> **Issue Integration (FR18-22)** | `adws/adw_dispatch.py`, `adw_trigger_cron.py` | `io_ops.py` (bd CLI calls), `workflows/__init__.py` (load_workflow)

**Architecture Decision 5 (Dispatch Registry):**
> `load_workflow()` in `workflows/__init__.py` is a pure lookup. Policy enforcement lives in `adw_dispatch.py`.

**FR20 (from epics):**
> Engine can close a Beads issue upon successful workflow completion via `bd close --reason`

**FR46 (from epics):**
> Finalize step (always_run) closes issues on success via `bd close --reason` or tags with structured failure metadata on failure via `bd update --notes`

**NFR2 (from epics):**
> Failed workflows must leave Beads issues in a recoverable state: open with structured failure metadata (`ADWS_FAILED` notes including attempt count, error classification, and failure summary)

**NFR3 (from epics):**
> `always_run` steps (e.g., `finalize`) must execute even after upstream failures

**Architecture One-Directional Flow:**
> BMAD -> Beads -> ADWS flow. Beads issues are the contract between planning and execution.

### Project Structure Notes

Files to create:
- None. All new code goes into existing `adws/adw_dispatch.py`.

Files to modify:
- `adws/adw_dispatch.py` -- add `DispatchExecutionResult`, `execute_dispatched_workflow()`, `dispatch_and_execute()`
- `adws/tests/test_adw_dispatch.py` -- add execution and finalize tests
- `adws/tests/integration/test_dispatch_flow.py` -- add dispatch-execute-finalize integration tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.2] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7] -- Epic summary: "Automated Dispatch, Cron Trigger & Self-Healing Triage"
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry: dispatchable flag, load_workflow() pure lookup, policy in adw_dispatch.py
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- ADWS -> Beads via bd CLI
- [Source: _bmad-output/planning-artifacts/architecture.md#One-Directional System Flow] -- BMAD -> Beads -> ADWS
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR18-FR22, FR46-FR48 map to Epic 7
- [Source: adws/adw_dispatch.py] -- dispatch_workflow(), existing dispatch policy
- [Source: adws/adw_modules/commands/_finalize.py] -- finalize_on_success, finalize_on_failure, build_failure_metadata
- [Source: adws/adw_modules/commands/build.py] -- BuildCommandResult pattern, execute-and-finalize pattern
- [Source: adws/adw_modules/commands/implement.py] -- ImplementCommandResult pattern, execute-and-finalize pattern
- [Source: adws/adw_modules/io_ops.py] -- execute_command_workflow, run_beads_close, run_beads_update_notes
- [Source: adws/adw_modules/engine/executor.py] -- run_workflow, _STEP_REGISTRY
- [Source: adws/adw_modules/engine/types.py] -- Workflow, Step, StepFunction
- [Source: adws/adw_modules/types.py] -- WorkflowContext frozen dataclass
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, load_workflow(), list_workflows(), _REGISTRY
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/7-1-issue-tag-extraction-and-workflow-dispatch.md] -- predecessor story

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

From Story 7.1 learnings:
- **1087 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **120 source files**: Current file count tracked by mypy.
- **io_ops at ~29 public functions**: This story does NOT add new io_ops functions -- it reuses existing ones (`execute_command_workflow`, `run_beads_close`, `run_beads_update_notes`).
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Frozen dataclasses**: All data models must be frozen.
- **Code review finding from 7.1**: `list_dispatchable_workflows()` should be used (not `list_workflows()`) when building error messages in the dispatch path. The step functions (`extract_and_validate_tag`, `read_and_extract`) correctly use `list_workflows()` because they are general-purpose.
- **Whitespace-only validation**: Issue IDs must be checked with `if not issue_id or not issue_id.strip():` per 7.1 code review finding.
- **Lazy imports**: When importing from `adws.workflows` inside function bodies (to avoid circular imports), use `# noqa: PLC0415`.
- **bind() and .lash() patterns**: The finalize helpers use `.bind()` and `.lash()` for fail-open behavior. Follow this pattern.
- **No new io_ops functions needed**: All required io_ops functions already exist.
- **No new step registry entries needed**: This story does not create new step functions -- it creates dispatch-level orchestrator functions.
- **No new workflow definitions needed**: The dispatchable workflows (`implement_close`, `implement_verify_close`) already exist.

## Code Review

**Reviewer**: Adversarial Code Review (Claude Opus 4.5)
**Date**: 2026-02-02
**Verdict**: PASS with 4 issues found and fixed

### Issues Found

**ISSUE 1 (MEDIUM) -- Integration test missing close reason argument verification**
- File: `adws/tests/integration/test_dispatch_flow.py`, `test_successful_dispatch_execute_close`
- AC #2 requires `bd close <id> --reason "Completed successfully"`. The integration test only used `mock_close.assert_called_once()` without verifying the issue_id and reason arguments. The `build.py` tests correctly verified this with `assert_called_once_with("BEADS-42", "Completed successfully")` but the dispatch integration test did not follow the same pattern. A regression changing the close reason would pass undetected.
- Fix: Changed to `mock_close.assert_called_once_with("ISSUE-42", "Completed successfully")`.

**ISSUE 2 (MEDIUM) -- Integration test missing issue_id verification on failure metadata tagging**
- File: `adws/tests/integration/test_dispatch_flow.py`, `test_dispatch_execute_failure_tags_issue`
- The test verified the notes argument starts with `ADWS_FAILED|` but never checked that the first argument (issue_id) was `"ISSUE-42"`. Per AC #3, failure metadata must be applied to the correct issue. A bug tagging the wrong issue would pass this test.
- Fix: Added `assert issue_arg == "ISSUE-42"` for the first positional argument.

**ISSUE 3 (MEDIUM) -- Unit test missing run_beads_close call assertion**
- File: `adws/tests/test_adw_dispatch.py`, `test_success_executes_and_closes`
- The test verified `finalize_action == "closed"` on the result but never asserted `run_beads_close` was actually invoked with the correct arguments. If the implementation were refactored to hardcode `"closed"` without calling the Beads API, the test would still pass. The `build.py` tests correctly assert this.
- Fix: Added `mock_close.assert_called_once_with("ISSUE-42", "Completed successfully")`.

**ISSUE 4 (LOW) -- Unit test missing run_beads_update_notes call arg verification**
- File: `adws/tests/test_adw_dispatch.py`, `test_workflow_failure_tags_issue`
- Same pattern as ISSUE 3: the test verified `finalize_action == "tagged_failure"` but never asserted the actual Beads API call was made with the correct issue_id and ADWS_FAILED metadata string.
- Fix: Added `mock_update.assert_called_once()` and verified `issue_arg == "ISSUE-42"` and `notes_arg.startswith("ADWS_FAILED|")`.

### Quality Gates (Post-Fix)

- `uv run pytest adws/tests/` -- 1109 passed, 5 skipped, 3 warnings
- `uv run pytest adws/tests/ --cov=adws --cov-branch` -- 100.00% line+branch coverage
- `uv run mypy adws/ --strict` -- Success: no issues found in 120 source files
- `uv run ruff check adws/` -- All checks passed!

### Implementation Assessment

The production code in `adw_dispatch.py` is well-structured and correct:
- `DispatchExecutionResult` is a frozen dataclass following the same pattern as `BuildCommandResult` and `ImplementCommandResult`.
- `execute_dispatched_workflow` correctly validates inputs, delegates to `finalize_on_success`/`finalize_on_failure`, and uses `.bind()/.lash()` for fail-open behavior (NFR3).
- `dispatch_and_execute` correctly chains dispatch and execution, propagating dispatch failures without finalize.
- All I/O is behind `io_ops.py` boundary (NFR10). No BMAD file reads (NFR19).
- IOResult type order is consistent: `IOResult[SuccessType, ErrorType]`.
- The semantic distinction between `IOFailure` (infrastructure errors) and `IOSuccess(success=False)` (workflow failures) is correctly maintained.

The issues were exclusively in test thoroughness -- the tests verified result shapes but did not verify the actual I/O calls matched AC requirements for specific arguments.

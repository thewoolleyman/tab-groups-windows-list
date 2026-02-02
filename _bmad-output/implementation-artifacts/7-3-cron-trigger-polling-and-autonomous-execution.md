# Story 7.3: Cron Trigger - Polling & Autonomous Execution

Status: ready-for-dev

## Story

As an ADWS developer,
I want a cron trigger that polls Beads for ready issues and executes workflows autonomously,
so that routine work is processed without manual intervention.

## Acceptance Criteria

1. **Given** the cron trigger is running, **When** it polls Beads, **Then** it calls `bd list --status=open` via io_ops to find open issues (FR21, NFR17) **And** it filters issues to those containing `{workflow_name}` tags matching dispatchable workflows **And** it applies the dispatch guard: issues with `ADWS_FAILED` or `needs_human` metadata in notes are excluded from dispatch (FR47, NFR21).

2. **Given** one or more ready issues are found (passing dispatch guard), **When** the trigger processes them, **Then** it dispatches and executes each workflow without manual intervention (FR22) **And** it uses the dispatch mechanism from Story 7.1 and execution from Story 7.2.

3. **Given** no ready issues are found (all filtered by dispatch guard or no open issues), **When** the trigger completes a poll cycle, **Then** it sleeps until the next poll interval and re-polls.

4. **Given** the trigger encounters an error during polling, **When** it processes the error, **Then** it logs the error and continues to the next poll cycle (does not crash) **And** affected issues remain in their current state for the next cycle.

5. **Given** multiple ready issues exist, **When** the trigger processes them, **Then** issues are processed sequentially (one at a time) to avoid resource contention **And** a failure on one issue does not prevent processing of subsequent issues.

6. **Given** an issue has `ADWS_FAILED` or `needs_human` metadata in its notes, **When** the dispatch guard evaluates it, **Then** the issue is skipped -- it will not be dispatched until triage clears the failure metadata or a human resolves the `needs_human` tag (NFR21).

7. **Given** all cron trigger code, **When** I run tests, **Then** tests cover: successful poll and dispatch, no ready issues, dispatch guard filtering, poll error recovery, multi-issue sequential processing, single issue failure isolation **And** 100% coverage is maintained (NFR9).

8. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Add `run_beads_list` io_ops function (AC: #1)
  - [ ] 1.1 RED: Write test for `io_ops.run_beads_list(status: str) -> IOResult[str, PipelineError]` in `adws/tests/adw_modules/test_io_ops.py`. Mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=0, stdout="ISSUE-1\nISSUE-2\n", stderr="", command="bd list --status=open"))`. Verify it returns `IOSuccess("ISSUE-1\nISSUE-2\n")` (raw stdout). The function executes `bd list --status={status}` via `run_shell_command` (NFR17).
  - [ ] 1.2 GREEN: Implement `run_beads_list(status: str) -> IOResult[str, PipelineError]` in `adws/adw_modules/io_ops.py`. Use `shlex.quote(status)` for safe shell interpolation. Delegate to `run_shell_command`. On nonzero exit, return `IOFailure(PipelineError(step_name="io_ops.run_beads_list", error_type="BeadsListError", ...))`. On success, return `IOSuccess(sr.stdout)`.
  - [ ] 1.3 RED: Write test for `run_beads_list` when `bd list` fails (nonzero exit code). Mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=1, stderr="No issues found", ...))`. Verify it returns `IOFailure(PipelineError)` with `error_type="BeadsListError"`.
  - [ ] 1.4 GREEN: Ensure the error path returns correctly.
  - [ ] 1.5 RED: Write test for `run_beads_list` when `run_shell_command` itself returns `IOFailure`. Verify the `IOFailure` propagates unchanged via `.bind()`.
  - [ ] 1.6 GREEN: Ensure shell command failures propagate via bind.
  - [ ] 1.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 2: Add `read_issue_notes` io_ops function (AC: #1, #6)
  - [ ] 2.1 RED: Write test for `io_ops.read_issue_notes(issue_id: str) -> IOResult[str, PipelineError]` in `adws/tests/adw_modules/test_io_ops.py`. This function reads an issue's notes field to check for dispatch guard metadata. Mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=0, stdout="ADWS_FAILED|attempt=1|...", stderr="", command="bd show ISSUE-42 --notes"))`. Verify it returns `IOSuccess("ADWS_FAILED|attempt=1|...")`.
  - [ ] 2.2 GREEN: Implement `read_issue_notes(issue_id: str) -> IOResult[str, PipelineError]` in `adws/adw_modules/io_ops.py`. Execute `bd show {issue_id} --notes` via `run_shell_command`. On nonzero exit, return `IOFailure(PipelineError(step_name="io_ops.read_issue_notes", error_type="BeadsShowNotesError", ...))`. On success, return `IOSuccess(sr.stdout)`. Validate non-empty `issue_id` with same pattern as `read_issue_description`.
  - [ ] 2.3 RED: Write test for `read_issue_notes` when `issue_id` is empty. Verify it returns `IOFailure(PipelineError)` with `error_type="ValueError"`.
  - [ ] 2.4 GREEN: Implement empty issue_id validation.
  - [ ] 2.5 RED: Write test for `read_issue_notes` when `bd show --notes` fails (nonzero exit). Verify `IOFailure` with `error_type="BeadsShowNotesError"`.
  - [ ] 2.6 GREEN: Ensure error path returns correctly.
  - [ ] 2.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 3: Create dispatch guard module `adws/adw_modules/steps/dispatch_guard.py` (AC: #1, #6)
  - [ ] 3.1 RED: Write test for `has_active_failure_metadata(notes: str) -> bool` in `adws/tests/adw_modules/steps/test_dispatch_guard.py`. Given `notes="ADWS_FAILED|attempt=1|last_failure=2026-02-01T00:00:00Z|error_class=SdkCallError|step=implement|summary=timeout"`, verify it returns `True`. This is a pure function -- no I/O.
  - [ ] 3.2 GREEN: Create `adws/adw_modules/steps/dispatch_guard.py`. Implement `has_active_failure_metadata(notes: str) -> bool` that checks whether the notes string contains `ADWS_FAILED` as a substring. Return `True` if found, `False` otherwise.
  - [ ] 3.3 RED: Write test for `has_active_failure_metadata` with empty notes. Verify it returns `False`.
  - [ ] 3.4 GREEN: Ensure empty string returns `False`.
  - [ ] 3.5 RED: Write test for `has_active_failure_metadata` with notes containing `needs_human`. Verify it returns `True`.
  - [ ] 3.6 GREEN: Add check for `needs_human` substring.
  - [ ] 3.7 RED: Write test for `has_active_failure_metadata` with clean notes (no failure metadata). Given `notes="Normal issue notes without any failure markers"`, verify it returns `False`.
  - [ ] 3.8 GREEN: Ensure clean notes return `False`.
  - [ ] 3.9 RED: Write test for `has_active_failure_metadata` with notes containing both `ADWS_FAILED` and `needs_human`. Verify it returns `True`.
  - [ ] 3.10 GREEN: Ensure both markers are detected.
  - [ ] 3.11 RED: Write test for `check_dispatch_guard(issue_id: str) -> IOResult[bool, PipelineError]` (step-like function using io_ops). Given `issue_id="ISSUE-42"`, mock `io_ops.read_issue_notes` to return `IOSuccess("")` (no failure metadata). Verify it returns `IOSuccess(True)` meaning the issue is eligible for dispatch.
  - [ ] 3.12 GREEN: Implement `check_dispatch_guard(issue_id: str) -> IOResult[bool, PipelineError]`. Call `io_ops.read_issue_notes(issue_id)`. On success, pass notes to `has_active_failure_metadata()`. Return `IOSuccess(True)` if no failure metadata (eligible), `IOSuccess(False)` if failure metadata found (skip).
  - [ ] 3.13 RED: Write test for `check_dispatch_guard` when notes contain `ADWS_FAILED`. Mock `io_ops.read_issue_notes` to return `IOSuccess("ADWS_FAILED|attempt=1|...")`. Verify it returns `IOSuccess(False)` (issue should be skipped).
  - [ ] 3.14 GREEN: Ensure failure metadata results in `False`.
  - [ ] 3.15 RED: Write test for `check_dispatch_guard` when `io_ops.read_issue_notes` returns `IOFailure`. The guard should be permissive on read errors -- if we cannot read notes, assume no failure metadata and allow dispatch. Verify it returns `IOSuccess(True)`. This is fail-open behavior for the guard check (similar to NFR4 fail-open pattern).
  - [ ] 3.16 GREEN: Implement fail-open behavior on notes read failure using `.lash()`.
  - [ ] 3.17 REFACTOR: Clean up, export from `steps/__init__.py`, verify mypy/ruff.

- [ ] Task 4: Create `parse_issue_list` pure function (AC: #1)
  - [ ] 4.1 RED: Write test for `parse_issue_list(raw_output: str) -> list[str]` in `adws/tests/adw_modules/steps/test_dispatch_guard.py`. Given `raw_output="ISSUE-1\nISSUE-2\nISSUE-3\n"`, verify it returns `["ISSUE-1", "ISSUE-2", "ISSUE-3"]`. This is a pure function that parses the raw stdout from `bd list` into a list of issue IDs.
  - [ ] 4.2 GREEN: Implement `parse_issue_list(raw_output: str) -> list[str]` in `dispatch_guard.py`. Split on newlines, strip whitespace, filter out empty strings.
  - [ ] 4.3 RED: Write test for `parse_issue_list` with empty input. Given `raw_output=""`, verify it returns `[]`.
  - [ ] 4.4 GREEN: Ensure empty string returns empty list.
  - [ ] 4.5 RED: Write test for `parse_issue_list` with whitespace-only lines. Given `raw_output="ISSUE-1\n  \n\nISSUE-2\n"`, verify it returns `["ISSUE-1", "ISSUE-2"]` (whitespace-only lines filtered).
  - [ ] 4.6 GREEN: Ensure whitespace-only lines are filtered.
  - [ ] 4.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 5: Create `poll_ready_issues` function (AC: #1, #6)
  - [ ] 5.1 RED: Write test for `poll_ready_issues() -> IOResult[list[str], PipelineError]` in `adws/tests/test_adw_trigger_cron.py`. Mock `io_ops.run_beads_list` to return `IOSuccess("ISSUE-1\nISSUE-2\nISSUE-3\n")`. Mock `io_ops.read_issue_description` to return descriptions: ISSUE-1 contains `{implement_verify_close}` tag, ISSUE-2 contains `{implement_close}` tag, ISSUE-3 has no workflow tag. Mock `io_ops.read_issue_notes` to return `IOSuccess("")` for all issues (no failure metadata). Verify it returns `IOSuccess(["ISSUE-1", "ISSUE-2"])` -- ISSUE-3 is excluded because it has no dispatchable workflow tag.
  - [ ] 5.2 GREEN: Create `adws/adw_trigger_cron.py`. Implement `poll_ready_issues() -> IOResult[list[str], PipelineError]`. Steps: (a) Call `io_ops.run_beads_list("open")` to get all open issues. (b) Parse the output with `parse_issue_list()`. (c) For each issue, read description via `io_ops.read_issue_description()`. (d) Attempt to extract workflow tag with `extract_workflow_tag()`. (e) Check tag matches a dispatchable workflow via `load_workflow()`. (f) Check dispatch guard via `check_dispatch_guard()`. (g) Return the list of issue IDs that pass all filters.
  - [ ] 5.3 RED: Write test for `poll_ready_issues` when one issue has `ADWS_FAILED` metadata. Mock `io_ops.run_beads_list` to return `"ISSUE-1\nISSUE-2\n"`. Both have valid workflow tags. Mock `io_ops.read_issue_notes` to return `IOSuccess("ADWS_FAILED|...")` for ISSUE-1 and `IOSuccess("")` for ISSUE-2. Verify it returns `IOSuccess(["ISSUE-2"])` -- ISSUE-1 is excluded by dispatch guard (FR47, NFR21).
  - [ ] 5.4 GREEN: Ensure dispatch guard filtering works correctly.
  - [ ] 5.5 RED: Write test for `poll_ready_issues` when one issue has `needs_human` metadata. Verify that issue is excluded.
  - [ ] 5.6 GREEN: Ensure `needs_human` filtering works.
  - [ ] 5.7 RED: Write test for `poll_ready_issues` when `io_ops.run_beads_list` returns `IOFailure`. Verify it returns `IOFailure(PipelineError)` propagated from io_ops.
  - [ ] 5.8 GREEN: Ensure list failure propagates.
  - [ ] 5.9 RED: Write test for `poll_ready_issues` when no open issues exist. Mock `io_ops.run_beads_list` to return `IOSuccess("")`. Verify it returns `IOSuccess([])`.
  - [ ] 5.10 GREEN: Ensure empty list is handled.
  - [ ] 5.11 RED: Write test for `poll_ready_issues` when an individual issue description read fails (e.g., `read_issue_description` returns `IOFailure` for ISSUE-2). The polling should skip that issue and continue with remaining issues. Given 3 issues where ISSUE-2 read fails, verify it returns `IOSuccess(["ISSUE-1", "ISSUE-3"])` (ISSUE-2 skipped, others processed).
  - [ ] 5.12 GREEN: Implement graceful per-issue error handling -- skip issues whose description cannot be read.
  - [ ] 5.13 RED: Write test for `poll_ready_issues` when an issue has a non-dispatchable workflow tag (e.g., `{convert_stories_to_beads}`). Verify it is excluded from the result.
  - [ ] 5.14 GREEN: Ensure non-dispatchable workflows are filtered.
  - [ ] 5.15 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 6: Create `run_poll_cycle` function (AC: #2, #4, #5)
  - [ ] 6.1 RED: Write test for `run_poll_cycle() -> CronCycleResult` in `adws/tests/test_adw_trigger_cron.py`. `CronCycleResult` is a frozen dataclass with fields: `issues_found` (int), `issues_dispatched` (int), `issues_succeeded` (int), `issues_failed` (int), `issues_skipped` (int), `errors` (list[str]). Mock `poll_ready_issues` to return `IOSuccess(["ISSUE-1", "ISSUE-2"])`. Mock `dispatch_and_execute` to return `IOSuccess(DispatchExecutionResult(success=True, ...))` for both. Verify `CronCycleResult` has `issues_found=2`, `issues_dispatched=2`, `issues_succeeded=2`, `issues_failed=0`.
  - [ ] 6.2 GREEN: Create `CronCycleResult` frozen dataclass in `adw_trigger_cron.py`. Implement `run_poll_cycle() -> CronCycleResult`. Call `poll_ready_issues()`. If it returns `IOFailure`, return `CronCycleResult(issues_found=0, ..., errors=[error_message])`. Otherwise, iterate through issue IDs sequentially, calling `dispatch_and_execute(issue_id)` for each. Accumulate results.
  - [ ] 6.3 RED: Write test for `run_poll_cycle` when one dispatch succeeds and one fails. Mock `poll_ready_issues` to return `IOSuccess(["ISSUE-1", "ISSUE-2"])`. Mock `dispatch_and_execute` to return `IOSuccess(DispatchExecutionResult(success=True, ...))` for ISSUE-1 and `IOSuccess(DispatchExecutionResult(success=False, ...))` for ISSUE-2. Verify `CronCycleResult` has `issues_succeeded=1`, `issues_failed=1`. Verify both issues were processed (failure on ISSUE-2 did not prevent ISSUE-1 from processing). (AC: #5)
  - [ ] 6.4 GREEN: Ensure sequential processing with failure isolation.
  - [ ] 6.5 RED: Write test for `run_poll_cycle` when `dispatch_and_execute` returns `IOFailure` for one issue (infrastructure error, not workflow failure). The cycle should catch this, record the error, and continue to the next issue. Verify `issues_skipped=1` and the error message is in `errors` list.
  - [ ] 6.6 GREEN: Implement error catching for `IOFailure` results from `dispatch_and_execute`.
  - [ ] 6.7 RED: Write test for `run_poll_cycle` when `poll_ready_issues` returns `IOFailure`. Verify `CronCycleResult` has `issues_found=0`, `issues_dispatched=0`, and `errors` contains the poll error message. The cycle does not crash. (AC: #4)
  - [ ] 6.8 GREEN: Ensure poll failure is handled gracefully.
  - [ ] 6.9 RED: Write test for `run_poll_cycle` when `poll_ready_issues` returns empty list. Verify `CronCycleResult` has `issues_found=0`, `issues_dispatched=0`, `issues_succeeded=0`, `issues_failed=0`, `errors=[]`. (AC: #3)
  - [ ] 6.10 GREEN: Ensure empty poll cycle works.
  - [ ] 6.11 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 7: Create `run_trigger_loop` function (AC: #3)
  - [ ] 7.1 RED: Write test for `run_trigger_loop(poll_interval_seconds: float, max_cycles: int | None = None) -> list[CronCycleResult]` in `adws/tests/test_adw_trigger_cron.py`. With `max_cycles=2`, mock `run_poll_cycle` to return a `CronCycleResult` with `issues_found=0` each time. Mock `io_ops.sleep_seconds` (used between cycles). Verify it returns a list of 2 `CronCycleResult` objects and `io_ops.sleep_seconds` was called once with the poll interval (sleep happens between cycles, not after the last one).
  - [ ] 7.2 GREEN: Implement `run_trigger_loop(poll_interval_seconds: float, max_cycles: int | None = None) -> list[CronCycleResult]`. Loop: call `run_poll_cycle()`, append result, if `max_cycles` reached break, else call `io_ops.sleep_seconds(poll_interval_seconds)`. The `max_cycles` parameter enables testing (avoids infinite loop). When `max_cycles=None`, loop indefinitely (production mode).
  - [ ] 7.3 RED: Write test for `run_trigger_loop` with `max_cycles=3` and varying results. First cycle: 2 issues found, both succeed. Second cycle: 1 issue found, it fails. Third cycle: 0 issues found. Verify list of 3 `CronCycleResult` objects with correct counts. Verify `io_ops.sleep_seconds` was called twice (between cycles 1-2 and 2-3).
  - [ ] 7.4 GREEN: Ensure multi-cycle behavior with varying results.
  - [ ] 7.5 RED: Write test for `run_trigger_loop` with `max_cycles=1`. Verify it returns 1 result and `io_ops.sleep_seconds` was NOT called (no sleep after the last/only cycle).
  - [ ] 7.6 GREEN: Ensure single cycle does not sleep.
  - [ ] 7.7 RED: Write test for `run_trigger_loop` when `run_poll_cycle` raises an unexpected exception (e.g., `RuntimeError`). The loop should catch this, create an error `CronCycleResult`, and continue to the next cycle. Verify the loop does not crash. (AC: #4)
  - [ ] 7.8 GREEN: Implement exception catching in the loop.
  - [ ] 7.9 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 8: Rich terminal output for cron trigger (AC: #2, #3)
  - [ ] 8.1 RED: Write test for `format_cycle_summary(result: CronCycleResult) -> str` in `adws/tests/test_adw_trigger_cron.py`. Given a `CronCycleResult(issues_found=3, issues_dispatched=2, issues_succeeded=1, issues_failed=1, issues_skipped=0, errors=[])`, verify the returned string contains key metrics: "3 found", "2 dispatched", "1 succeeded", "1 failed". This is a pure formatting function.
  - [ ] 8.2 GREEN: Implement `format_cycle_summary(result: CronCycleResult) -> str` in `adw_trigger_cron.py`. Format as: `"Cycle complete: {found} found, {dispatched} dispatched, {succeeded} succeeded, {failed} failed"`.
  - [ ] 8.3 RED: Write test for `format_cycle_summary` with errors. Given a `CronCycleResult` with `errors=["Poll failed: timeout"]`, verify the summary includes the error count.
  - [ ] 8.4 GREEN: Include error count in summary.
  - [ ] 8.5 RED: Write test for `log_cycle_result(result: CronCycleResult) -> None` in `adws/tests/test_adw_trigger_cron.py`. Mock `io_ops.write_stderr`. Verify it calls `write_stderr` with the formatted cycle summary. This is the actual logging function that writes to stderr.
  - [ ] 8.6 GREEN: Implement `log_cycle_result(result: CronCycleResult) -> None`. Call `format_cycle_summary(result)` then `io_ops.write_stderr(summary)`.
  - [ ] 8.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 9: Verify NFR19 compliance across cron trigger (AC: #1)
  - [ ] 9.1 RED: Write test confirming that `poll_ready_issues` never reads BMAD files (NFR19). Mock `io_ops.read_bmad_file` and verify it is NOT called during polling. The cron trigger only reads Beads issue data.
  - [ ] 9.2 GREEN: Confirm the implementation does not call any BMAD-related io_ops functions.
  - [ ] 9.3 RED: Write test confirming that `run_poll_cycle` never reads BMAD files through the full cycle flow.
  - [ ] 9.4 GREEN: Confirm NFR19 compliance in the full cycle.
  - [ ] 9.5 REFACTOR: Clean up.

- [ ] Task 10: Integration tests for full cron trigger flow (AC: #1, #2, #3, #4, #5, #6, #7)
  - [ ] 10.1 RED: Write integration test for successful poll-dispatch-execute cycle. Mock `io_ops.run_beads_list` to return 2 open issues with valid workflow tags. Mock `io_ops.read_issue_description` with descriptions containing `{implement_close}` tags. Mock `io_ops.read_issue_notes` to return `IOSuccess("")`. Mock `io_ops.execute_command_workflow` to succeed. Mock `io_ops.run_beads_close` to succeed. Call `run_poll_cycle()`. Verify `CronCycleResult` has `issues_found=2`, `issues_succeeded=2`. Verify `dispatch_and_execute` was called for each issue.
  - [ ] 10.2 GREEN: Ensure full success flow works end-to-end through the integration.
  - [ ] 10.3 RED: Write integration test for dispatch guard filtering. Mock `io_ops.run_beads_list` to return 3 issues. Issue 1 has `ADWS_FAILED` notes, Issue 2 has `needs_human` notes, Issue 3 has clean notes with valid tag. Verify only Issue 3 is dispatched. Verify `dispatch_and_execute` was called exactly once (for Issue 3 only).
  - [ ] 10.4 GREEN: Ensure dispatch guard filtering works in integration.
  - [ ] 10.5 RED: Write integration test for mixed success/failure cycle. Mock 3 ready issues: Issue 1 dispatches and succeeds, Issue 2 dispatches but workflow fails (IOSuccess with success=False), Issue 3 dispatch infrastructure fails (IOFailure). Verify `CronCycleResult` has `issues_succeeded=1`, `issues_failed=1`, `issues_skipped=1`. Verify all 3 issues were attempted (failure isolation).
  - [ ] 10.6 GREEN: Ensure failure isolation works in integration.
  - [ ] 10.7 RED: Write integration test for poll error recovery. Mock `io_ops.run_beads_list` to return `IOFailure`. Verify `CronCycleResult` has `issues_found=0` and `errors` contains error message. No dispatch calls made.
  - [ ] 10.8 GREEN: Ensure poll error recovery works in integration.
  - [ ] 10.9 RED: Write integration test for multi-cycle trigger loop. Use `max_cycles=2`. First cycle: 1 issue dispatched and succeeded. Second cycle: 0 issues found. Verify list of 2 results with correct counts. Verify `io_ops.sleep_seconds` was called once between cycles.
  - [ ] 10.10 GREEN: Ensure multi-cycle works in integration.
  - [ ] 10.11 RED: Write integration test verifying NFR19 across the full cron trigger flow: `io_ops.read_bmad_file` is never called.
  - [ ] 10.12 GREEN: Confirm NFR19 compliance in integration.
  - [ ] 10.13 REFACTOR: Clean up integration tests.

- [ ] Task 11: Verify full integration and quality gates (AC: #8)
  - [ ] 11.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 11.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 11.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 7.2)

**adw_dispatch.py** exists with three functions:
- `dispatch_workflow(issue_id: str) -> IOResult[WorkflowContext, PipelineError]` -- reads Beads issue, extracts workflow tag, validates, returns prepared WorkflowContext (Story 7.1)
- `execute_dispatched_workflow(ctx: WorkflowContext) -> IOResult[DispatchExecutionResult, PipelineError]` -- executes workflow, finalizes: close on success, tag failure on failure (Story 7.2)
- `dispatch_and_execute(issue_id: str) -> IOResult[DispatchExecutionResult, PipelineError]` -- full orchestrator: dispatch + execute + finalize (Story 7.2). This is the entry point the cron trigger calls.

**adw_trigger_cron.py** does NOT exist yet. This story creates it.

**io_ops.py** has ~26 public functions. Key functions for this story that already exist:
```python
def run_shell_command(cmd: str) -> IOResult[ShellResult, PipelineError]: ...
def read_issue_description(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_show(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[bool, PipelineError]: ...
def write_stderr(message: str) -> IOResult[bool, PipelineError]: ...
```

New io_ops functions needed:
```python
def run_beads_list(status: str) -> IOResult[str, PipelineError]: ...  # NEW: bd list --status={status}
def read_issue_notes(issue_id: str) -> IOResult[str, PipelineError]: ...  # NEW: bd show {issue_id} --notes
```

**_finalize.py** exists with shared finalize helpers (from Story 4.4). The cron trigger does NOT call finalize directly -- it delegates to `dispatch_and_execute()` which handles finalize internally.

**extract_workflow_tag.py** exists with `extract_workflow_tag(description: str) -> Result[str, PipelineError]` pure function that finds `{workflow_name}` patterns.

**workflows/__init__.py** has 5 registered workflows. Two are dispatchable: `implement_close` and `implement_verify_close`. Functions:
- `load_workflow(name: str) -> Workflow | None` -- pure lookup
- `list_workflows(dispatchable_only: bool = False) -> list[Workflow]` -- optionally filtered
- `list_dispatchable_workflows() -> list[str]` -- sorted names of dispatchable workflows

**Current test count**: 1109 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 120 files tracked by mypy.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: Story 7.3 Architecture

This story creates the cron trigger module (`adw_trigger_cron.py`) and supporting functions to enable fully autonomous execution:

```
Architecture: Cron Trigger Polling & Autonomous Execution

                        run_trigger_loop(interval, max_cycles)
                                    |
                                    | (repeating loop)
                                    v
                            run_poll_cycle()
                                    |
                        +-----------+-----------+
                        |                       |
                        v                       v
                poll_ready_issues()      log_cycle_result()
                        |                  (stderr output)
            +-----------+-----------+
            |           |           |
            v           v           v
    run_beads_list  read_issue_   check_dispatch_
    ("open")        description   guard(issue_id)
                    + extract_       |
                    workflow_tag  read_issue_notes
                    + load_         |
                    workflow      has_active_
                                 failure_metadata
                        |
                        v
            (filtered list of ready issue IDs)
                        |
                        v (sequential, one at a time)
            dispatch_and_execute(issue_id)
            (from Story 7.2 -- handles full
             dispatch + execute + finalize)
```

### Design: Separation of Concerns

The cron trigger module has clear responsibilities:

1. **Polling** (`poll_ready_issues`): Find issues that are ready for autonomous dispatch. Applies all filters: open status, valid workflow tag, dispatchable workflow, no failure metadata.

2. **Dispatch Guard** (`dispatch_guard.py`): Pure logic for checking whether an issue should be skipped based on its notes metadata. Extracted to a separate step module because it is independently testable and reusable by the triage workflow (Story 7.4).

3. **Cycle Execution** (`run_poll_cycle`): Orchestrates one poll-dispatch cycle. Handles sequential processing and failure isolation.

4. **Loop Management** (`run_trigger_loop`): Manages the repeating poll loop with configurable interval and optional cycle limit for testing.

5. **Execution** (delegated to `dispatch_and_execute`): The actual workflow dispatch, execution, and finalize are handled by Story 7.2's `dispatch_and_execute()` function. The cron trigger does NOT re-implement dispatch logic.

### Design: Dispatch Guard

The dispatch guard is the filter that prevents infinite retry loops (NFR21). It reads an issue's notes and checks for:

- `ADWS_FAILED` -- indicates the issue was previously dispatched and failed. The triage workflow (Story 7.4) must clear this before the issue re-enters the dispatch pool.
- `needs_human` -- indicates the issue requires human intervention. A human must resolve the issue and remove the tag before re-dispatch.

The guard is a separate step module (`dispatch_guard.py`) because:
1. It is pure logic that can be tested without mocking io_ops (the metadata check)
2. It will be reused by the triage workflow (Story 7.4) to identify issues needing triage
3. It follows the step creation checklist (errors -> io_ops -> step -> __init__ -> tests -> verify)

**Fail-open behavior**: If reading an issue's notes fails (bd show error), the guard assumes no failure metadata and allows dispatch. This is consistent with the fail-open pattern used throughout hooks (NFR4). The rationale: a temporary Beads CLI error should not permanently block an issue from dispatch.

### Design: Sequential Processing

Issues are processed one at a time (not in parallel) for several reasons:
1. Resource contention -- each `dispatch_and_execute` may spawn SDK calls
2. Simplicity -- sequential is easier to reason about, test, and debug
3. Isolation -- a failure on one issue does not affect others
4. The architecture document specifies sequential processing

### Design: CronCycleResult

```python
@dataclass(frozen=True)
class CronCycleResult:
    issues_found: int       # Number of ready issues found by poll
    issues_dispatched: int  # Number of issues sent to dispatch_and_execute
    issues_succeeded: int   # Number where dispatch_and_execute returned success=True
    issues_failed: int      # Number where dispatch_and_execute returned success=False
    issues_skipped: int     # Number where dispatch_and_execute returned IOFailure
    errors: list[str]       # Error messages from poll failures or unexpected exceptions
```

This result type enables monitoring and logging without side effects. The `run_trigger_loop` accumulates `CronCycleResult` objects for each cycle.

### Design: Testability

The `run_trigger_loop` function accepts `max_cycles: int | None = None` to enable testing without infinite loops. In production, `max_cycles=None` runs indefinitely. In tests, `max_cycles=N` runs exactly N cycles.

The `poll_interval_seconds` parameter enables fast testing (0.0 seconds) while allowing configurable production intervals.

`io_ops.sleep_seconds` (already exists) is the mock point for sleep between cycles.

### Design: Error Handling Tiers

1. **Poll failure** (`run_beads_list` fails): Entire cycle fails gracefully. `CronCycleResult` has `issues_found=0` and error in `errors` list. Next cycle tries again.

2. **Per-issue read failure** (`read_issue_description` fails for one issue): That issue is skipped. Other issues are still processed. No error in `CronCycleResult.errors` -- the issue simply does not appear in the ready list.

3. **Dispatch infrastructure failure** (`dispatch_and_execute` returns `IOFailure`): Counted as `issues_skipped`. Error message recorded. Other issues continue processing.

4. **Workflow execution failure** (`dispatch_and_execute` returns `IOSuccess(success=False)`): Counted as `issues_failed`. The finalize step (inside `dispatch_and_execute`) has already tagged the issue with `ADWS_FAILED` metadata. Next poll cycle's dispatch guard will skip this issue.

5. **Unexpected exception** (e.g., `RuntimeError` in `run_poll_cycle`): Caught by `run_trigger_loop`. Recorded as error. Next cycle tries again.

### Design: New io_ops Functions

Two new io_ops functions are needed:

**`run_beads_list(status: str)`**: Executes `bd list --status={status}` and returns raw stdout. Follows the same pattern as `run_beads_show` (shell command -> exit code check -> return stdout).

**`read_issue_notes(issue_id: str)`**: Executes `bd show {issue_id} --notes` and returns raw stdout. This is the mechanism for reading issue metadata to check for dispatch guard markers (`ADWS_FAILED`, `needs_human`). Follows the same pattern as `read_issue_description`.

NOTE: The exact `bd` CLI syntax for listing issues and reading notes fields may vary by Beads version. The io_ops functions abstract this away -- if the CLI syntax changes, only io_ops needs updating.

### Test Strategy

**New test files**:
- `adws/tests/test_adw_trigger_cron.py` -- poll_ready_issues, run_poll_cycle, run_trigger_loop, format_cycle_summary, log_cycle_result
- `adws/tests/adw_modules/steps/test_dispatch_guard.py` -- has_active_failure_metadata, check_dispatch_guard, parse_issue_list
- New tests in `adws/tests/adw_modules/test_io_ops.py` -- run_beads_list, read_issue_notes
- `adws/tests/integration/test_cron_trigger_flow.py` -- full cron trigger integration tests

**Mock targets**:
- `adws.adw_modules.io_ops.run_beads_list` -- mock in poll tests
- `adws.adw_modules.io_ops.read_issue_description` -- mock in poll tests (for tag extraction)
- `adws.adw_modules.io_ops.read_issue_notes` -- mock in dispatch guard tests
- `adws.adw_modules.io_ops.run_shell_command` -- mock in io_ops unit tests
- `adws.adw_modules.io_ops.sleep_seconds` -- mock in loop tests
- `adws.adw_modules.io_ops.write_stderr` -- mock in logging tests
- `adws.adw_modules.io_ops.read_bmad_file` -- mock to VERIFY IT IS NOT CALLED (NFR19)
- `adws.adw_modules.io_ops.execute_command_workflow` -- mock in integration tests
- `adws.adw_modules.io_ops.run_beads_close` -- mock in integration tests
- `adws.adw_modules.io_ops.run_beads_update_notes` -- mock in integration tests

**NOTE on dispatch_and_execute mocking**: In unit tests for `run_poll_cycle`, mock `dispatch_and_execute` directly (it lives in `adw_dispatch` module, not io_ops). In integration tests, mock the underlying io_ops functions to let the full dispatch_and_execute chain run.

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.
- Lazy imports (e.g., `from adws.workflows import load_workflow` inside function body) need `# noqa: PLC0415`.

### Architecture Compliance

- **FR21**: Cron trigger polls for open issues with workflow tags, excluding issues with active failure metadata.
- **FR22**: Execute dispatched workflows without manual intervention.
- **FR47**: Dispatch guard skips issues with `ADWS_FAILED` or `needs_human` metadata.
- **NFR1**: ROP error handling throughout. IOFailure for infrastructure errors, IOSuccess for results.
- **NFR2**: Failed workflows leave Beads issues open with structured failure metadata (handled by `dispatch_and_execute`).
- **NFR3**: Finalize runs regardless of success/failure (handled by `dispatch_and_execute`).
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Beads listing via `run_beads_list`. Notes reading via `read_issue_notes`. Sleep via `sleep_seconds`. Stderr via `write_stderr`.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads via bd CLI only. List, show, close, update all via io_ops functions.
- **NFR19**: ADWS never reads BMAD files during execution. The cron trigger reads only Beads issue data. Tests verify `io_ops.read_bmad_file` is not called.
- **NFR21**: Cron trigger never dispatches issues with active failure metadata. Dispatch guard enforces this.
- **NFR22**: Workflow agents operate autonomously -- no human input during execution.
- **Decision 5**: `load_workflow()` is pure lookup. Policy enforcement (dispatchable flag) checked during poll filtering.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT implement the triage workflow. That is Story 7.4.
- Do NOT change `dispatch_and_execute` from Story 7.2 -- only call it.
- Do NOT change `dispatch_workflow` from Story 7.1.
- Do NOT change `finalize_on_success` or `finalize_on_failure` in `_finalize.py`.
- Do NOT change `load_workflow()` or `list_workflows()` in `workflows/__init__.py`.
- Do NOT change the engine executor logic.
- Do NOT change existing io_ops functions -- add new ones (`run_beads_list`, `read_issue_notes`) and reuse existing.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in `adw_trigger_cron.py` or `dispatch_guard.py`.
- Do NOT read BMAD files from any code in this story (NFR19).
- Do NOT implement parallel issue processing -- issues must be processed sequentially.
- Do NOT implement scheduling (system cron, CI scheduled workflow) -- this story implements the polling logic. How the trigger is started is an operational concern, not a code concern.
- Do NOT create a `__main__.py` entry point -- the cron trigger is called by the system scheduler, not by `python -m`.

### Relationship to Adjacent Stories

- **Story 7.1** (predecessor): Issue Tag Extraction & Workflow Dispatch -- provides `dispatch_workflow()` that the cron trigger's polling logic reuses for tag extraction and validation.
- **Story 7.2** (predecessor): Workflow Execution & Issue Closure -- provides `dispatch_and_execute()` that the cron trigger calls for each ready issue. This is the sole entry point for autonomous execution.
- **Story 7.4** (successor): Triage Workflow - Self-Healing Failure Recovery -- processes issues tagged with `ADWS_FAILED` metadata by the finalize step. Reuses `dispatch_guard.py` to find failed issues needing triage. The triage workflow clears failure metadata to re-enable dispatch.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (Issue Integration section):**
> **Issue Integration (FR18-22)** | `adws/adw_dispatch.py`, `adw_trigger_cron.py` | `io_ops.py` (bd CLI calls), `workflows/__init__.py` (load_workflow)

**Architecture Integration Points:**
> Cron -> ADWS dispatch | `adw_trigger_cron.py` -> `adw_dispatch.py` | Inbound | `poll_ready_issues()`

**Architecture Gap Analysis (Minor Gap #4):**
> Cron trigger scheduling mechanism: `adw_trigger_cron.py` polls `bd ready`, but the architecture intentionally does not specify how the polling is scheduled (system cron, CI scheduled workflow, manual invocation). This is an implementation detail for the story that builds the cron trigger.

**FR21 (from epics):**
> Cron trigger can poll Beads for open issues with workflow tags ready for dispatch, excluding issues with active failure metadata

**FR22 (from epics):**
> Cron trigger can execute dispatched workflows without manual intervention

**FR47 (from epics):**
> Cron trigger dispatch guard skips issues with active failure metadata (structured `ADWS_FAILED` notes)

**NFR21 (from epics):**
> The cron trigger must never dispatch an issue with active failure metadata. A separate triage workflow governs retry eligibility, clearing failure metadata only after appropriate cooldown or AI triage analysis.

**Architecture One-Directional Flow:**
> BMAD -> Beads -> ADWS flow. Beads issues are the contract between planning and execution.

### Project Structure Notes

Files to create:
- `adws/adw_trigger_cron.py` -- cron trigger module (CronCycleResult, poll_ready_issues, run_poll_cycle, run_trigger_loop, format_cycle_summary, log_cycle_result)
- `adws/adw_modules/steps/dispatch_guard.py` -- dispatch guard step (has_active_failure_metadata, check_dispatch_guard, parse_issue_list)
- `adws/tests/test_adw_trigger_cron.py` -- cron trigger tests
- `adws/tests/adw_modules/steps/test_dispatch_guard.py` -- dispatch guard tests
- `adws/tests/integration/test_cron_trigger_flow.py` -- integration tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `run_beads_list()` and `read_issue_notes()`
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for new io_ops functions
- `adws/adw_modules/steps/__init__.py` -- export dispatch_guard functions

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.3] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7] -- Epic summary: "Automated Dispatch, Cron Trigger & Self-Healing Triage"
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry: dispatchable flag, load_workflow() pure lookup, policy in adw_dispatch.py
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- Cron -> ADWS dispatch via adw_trigger_cron.py
- [Source: _bmad-output/planning-artifacts/architecture.md#One-Directional System Flow] -- BMAD -> Beads -> ADWS
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR18-FR22, FR46-FR48 map to Epic 7
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap Analysis] -- Gap #4: Cron trigger scheduling mechanism deferred
- [Source: adws/adw_dispatch.py] -- dispatch_workflow(), execute_dispatched_workflow(), dispatch_and_execute()
- [Source: adws/adw_modules/commands/_finalize.py] -- build_failure_metadata format (ADWS_FAILED|attempt=N|...)
- [Source: adws/adw_modules/io_ops.py] -- run_beads_show, run_shell_command, sleep_seconds, write_stderr (patterns for new functions)
- [Source: adws/adw_modules/steps/extract_workflow_tag.py] -- extract_workflow_tag (reused for tag filtering)
- [Source: adws/adw_modules/engine/types.py] -- Workflow, Step, StepFunction
- [Source: adws/adw_modules/types.py] -- WorkflowContext frozen dataclass, ShellResult
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, load_workflow(), list_workflows(), list_dispatchable_workflows()
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/7-1-issue-tag-extraction-and-workflow-dispatch.md] -- Story 7.1 reference
- [Source: _bmad-output/implementation-artifacts/7-2-workflow-execution-and-issue-closure.md] -- Story 7.2 reference (predecessor)

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

From Story 7.2 learnings:
- **1109 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **120 source files**: Current file count tracked by mypy.
- **io_ops at ~26 public functions**: This story adds 2 new io_ops functions (`run_beads_list`, `read_issue_notes`).
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Frozen dataclasses**: All data models must be frozen.
- **Whitespace-only validation**: Issue IDs must be checked with `if not issue_id or not issue_id.strip():` per 7.1 code review finding.
- **Lazy imports**: When importing from `adws.workflows` inside function bodies (to avoid circular imports), use `# noqa: PLC0415`.
- **bind() and .lash() patterns**: Use for composing IOResult chains. The finalize helpers demonstrate this pattern.
- **Code review finding from 7.2**: Integration tests must verify specific arguments to io_ops calls, not just that they were called. Use `assert_called_once_with()` for argument verification.
- **Code review finding from 7.2**: Both issue_id AND method arguments must be verified in mock assertions to prevent regressions.
- **Semantic distinction**: `IOFailure` = infrastructure broke, `IOSuccess(success=False)` = workflow ran but failed.

## Code Review

**Reviewer**: Adversarial senior code reviewer
**Date**: 2026-02-02
**Result**: 4 issues found, all fixed. Quality gates green.

### Issue 1 (MEDIUM): run_trigger_loop tests leak I/O through unmocked write_stderr

**File**: `adws/tests/test_adw_trigger_cron.py` (TestRunTriggerLoop)
**Problem**: All 4 tests in TestRunTriggerLoop mock `run_poll_cycle` and `sleep_seconds` but do NOT mock `io_ops.write_stderr`. Since `run_trigger_loop` calls `log_cycle_result` which calls `io_ops.write_stderr`, the real `sys.stderr.write()` executes in unit tests. This is I/O leakage in unit tests and violates the NFR10 io_ops boundary principle.
**Fix**: Added `mocker.patch("adws.adw_trigger_cron.io_ops.write_stderr", return_value=IOSuccess(None))` to all 4 tests in TestRunTriggerLoop. The integration test in `test_cron_trigger_flow.py` already had this mock.
**Severity**: MEDIUM -- not a runtime bug but violates test isolation principles.

### Issue 2 (MEDIUM): has_active_failure_metadata uses substring matching without documenting behavior

**File**: `adws/adw_modules/steps/dispatch_guard.py`
**Problem**: `has_active_failure_metadata` uses plain `in` substring matching for `ADWS_FAILED` and `needs_human`. While this works for the ADWS-controlled metadata format (written by `build_failure_metadata`), the matching is case-sensitive and undocumented. If a future developer writes notes containing lowercase variants, the guard behavior would be unclear.
**Fix**: (a) Added docstring comment documenting the design decision -- substring matching is safe because notes are written by ADWS via `build_failure_metadata` with exact case. (b) Added 2 new tests (`test_case_sensitive_adws_failed`, `test_case_sensitive_needs_human`) that document and verify the case-sensitive behavior.
**Severity**: MEDIUM -- design documentation gap, not a runtime bug.

### Issue 3 (MEDIUM): _passes_dispatch_guard has redundant dead-code fail-open logic

**File**: `adws/adw_trigger_cron.py` line 95
**Problem**: `_passes_dispatch_guard` checked `isinstance(guard_result, IOFailure)` and returned `True`, but `check_dispatch_guard` already has `.lash(_fail_open)` that converts all IOFailure to IOSuccess(True). The isinstance check was unreachable dead code. The test `test_guard_io_failure_allows_dispatch` achieved coverage by mocking `check_dispatch_guard` directly to return IOFailure, bypassing the real `.lash()` behavior -- this is testing mock behavior rather than real code.
**Fix**: (a) Removed the dead `isinstance(guard_result, IOFailure)` branch from `_passes_dispatch_guard`. (b) Updated `test_guard_io_failure_allows_dispatch` to mock `io_ops.read_issue_notes` to return IOFailure instead -- testing the real check_dispatch_guard .lash() fail-open path end-to-end.
**Severity**: MEDIUM -- dead code and test that tests its own mock rather than real behavior.

### Issue 4 (MEDIUM): format_cycle_summary omits issues_skipped from output

**File**: `adws/adw_trigger_cron.py` (format_cycle_summary)
**Problem**: The summary string included found, dispatched, succeeded, failed, and error count -- but completely omitted `issues_skipped`. When `dispatch_and_execute` returns IOFailure (infrastructure error), the issue is counted as skipped but the cycle summary has no visibility into it. A cycle could report "3 dispatched, 1 succeeded, 0 failed" while silently dropping 2 issues to infrastructure errors.
**Fix**: (a) Added `f"{result.issues_skipped} skipped"` to the parts list in `format_cycle_summary`. (b) Updated `test_formats_key_metrics` to assert on "0 skipped". (c) Added new test `test_formats_with_skipped` to verify non-zero skipped count appears in summary along with error count.
**Severity**: MEDIUM -- monitoring gap that hides infrastructure failures from operators.

### Quality Gates (post-fix)

- **pytest**: 1161 passed, 5 skipped (enemy), 100% line+branch coverage
- **mypy**: Success, no issues found in 125 source files (strict mode)
- **ruff**: All checks passed, zero violations

### Learnings for Future Stories

- **Mock ALL io_ops calls in unit tests**: Even when the function under test is mocked at a higher level, if downstream code (like `log_cycle_result`) calls io_ops functions, those must be mocked too.
- **Avoid testing mock behavior**: When `.lash()` or `.bind()` makes certain IOResult branches unreachable, do not mock the intermediate function to force-return impossible states. Instead, test the real code path by mocking at the io_ops boundary.
- **Include all metrics in summaries**: Any field tracked in a result dataclass should be visible in its human-readable summary. Hidden metrics create operational blind spots.
- **Document case-sensitivity decisions**: When using substring matching for markers, document whether matching is case-sensitive and why.

# Story 7.4: Triage Workflow - Self-Healing Failure Recovery

Status: code-review-complete

## Code Review (Story 7.4)

**Reviewer**: Adversarial Senior Code Reviewer
**Date**: 2026-02-02

### Issues Found: 4

**ISSUE 1 (MEDIUM) -- FIXED: `format_triage_summary` double-reports error counts**
- File: `adws/adw_triage.py`, `format_triage_summary()`
- The summary always included `"{result.triage_errors} errors"` in the parts list, THEN conditionally appended `"{len(result.errors)} error(s)"` when the errors list was non-empty. This produced confusing output like `"1 errors, 1 error"` when both fields were populated. The `triage_errors` field tracks action-level errors (unknown/failed actions from `_count_action`) while `errors` is the list of error messages from IOFailure propagation -- they measure different things but were both labeled "errors".
- Fix: Combined into a single `total_errors = result.triage_errors + len(result.errors)` with one display line. Added test `test_format_triage_summary_combined_errors`.

**ISSUE 2 (MEDIUM) -- FIXED: `FailureMetadata` not exported from `steps/__init__.py`**
- File: `adws/adw_modules/steps/__init__.py`
- The three pure functions (`parse_failure_metadata`, `classify_failure_tier`, `check_cooldown_elapsed`) were all re-exported from the steps package, but the `FailureMetadata` dataclass they operate on was not. This breaks public API consistency -- downstream consumers of `adws.adw_modules.steps` can import the functions but not the type they return/accept.
- Fix: Added `FailureMetadata` to the import and `__all__` in `steps/__init__.py`.

**ISSUE 3 (MEDIUM) -- FIXED: Tier 2 `clear_failed` and `split_failed` not escalated to Tier 3**
- File: `adws/adw_triage.py`, `_TIER2_ESCALATION_ACTIONS` frozenset
- When a Tier 2 AI triage recommended `adjust_parameters` but `clear_failure_metadata` failed, or recommended `split` but `run_beads_create` failed, the result (`clear_failed` or `split_failed`) was NOT in `_TIER2_ESCALATION_ACTIONS`. This meant `triage_issue` returned the failed result without escalating to Tier 3. On the next triage cycle, the issue would still have ADWS_FAILED metadata, classify as Tier 2 again, make another expensive SDK call that would likely fail the same way -- creating a soft infinite retry loop at Tier 2 with repeated SDK costs.
- Fix: Added `"clear_failed"` and `"split_failed"` to `_TIER2_ESCALATION_ACTIONS`. Added tests `test_triage_issue_tier2_clear_failed_falls_to_tier3` and `test_triage_issue_tier2_split_failed_falls_to_tier3`.

**ISSUE 4 (LOW) -- FIXED: `_RETRYABLE_ERROR_CLASSES` is dead code**
- File: `adws/adw_modules/steps/triage.py`, line 32
- The `_RETRYABLE_ERROR_CLASSES` frozenset was defined with `{"SdkCallError", "TimeoutError", "TestFailureError"}` but never referenced anywhere in the codebase. The `classify_failure_tier` function uses a simpler `metadata.error_class == "unknown"` check instead. This dead constant is misleading -- it suggests the classification logic uses an explicit allowlist when it actually uses a denylist (`unknown` only).
- Fix: Removed the unused constant.

### Quality Gates (post-fix)

- **Tests**: 1271 passed, 5 skipped (enemy), 100% line + branch coverage
- **mypy**: Success, no issues found in 130 source files (strict mode)
- **ruff**: All checks passed (zero violations)

## Story

As an ADWS developer,
I want a triage workflow that automatically reviews failed issues and either retries them or escalates to human review,
so that the system self-heals from routine failures without human intervention (Zero Touch Engineering Principle).

## Acceptance Criteria

1. **Given** one or more open issues have `ADWS_FAILED` metadata in their notes, **When** the triage workflow runs, **Then** it parses the structured failure metadata: `ADWS_FAILED|attempt=N|last_failure=TIMESTAMP|error_class=CLASS|step=STEP|summary=TEXT` (FR48) **And** it classifies each failure into an escalation tier.

2. **Given** a failed issue classified as Tier 1 (transient/retryable: `sdk_error`, `timeout`, `test_failure` with attempt < 3), **When** the triage workflow evaluates it, **Then** it checks exponential backoff cooldown (30min, 2hr, 8hr based on attempt count) **And** if cooldown has elapsed, it clears the `ADWS_FAILED` metadata via `bd update --notes` **And** the issue re-enters the dispatch pool on the next cron poll cycle **And** no human involvement is required.

3. **Given** a failed issue classified as Tier 2 (repeated failure: attempt >= 3, error class is classifiable), **When** the triage workflow evaluates it, **Then** it invokes an AI triage agent via fresh SDK call to analyze the accumulated failure context **And** the triage agent can: adjust workflow parameters, simplify the task scope, or split the issue into smaller sub-issues via `bd create` **And** if the triage agent creates sub-issues, it closes the original with `bd close --reason "Split into sub-issues: <ids>"` **And** if the triage agent adjusts parameters, it clears the failure metadata and the issue re-enters dispatch **And** no human involvement is required.

4. **Given** a failed issue classified as Tier 3 (unresolvable: Tier 2 triage failed, or `unknown` error class), **When** the triage workflow evaluates it, **Then** it tags the issue with `needs_human` metadata via `bd update --notes` **And** this is the ONLY path that requires human attention **And** the issue remains open but is excluded from both dispatch and automated triage until a human intervenes.

5. **Given** the triage workflow runs periodically, **When** it processes the failed issue queue, **Then** issues are evaluated in order of oldest failure first **And** each issue is processed independently -- a triage failure on one issue does not affect others **And** triage workflow interacts with Beads exclusively via `bd` CLI (NFR17).

6. **Given** all triage workflow code, **When** I run tests, **Then** tests cover: Tier 1 cooldown retry, Tier 1 cooldown not yet elapsed, Tier 2 AI triage with adjustment, Tier 2 AI triage with split, Tier 3 human escalation, metadata parsing, multiple issues in queue **And** 100% coverage is maintained (NFR9).

7. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Create `parse_failure_metadata` pure function (AC: #1)
  - [ ] 1.1 RED: Write test for `parse_failure_metadata(notes: str) -> FailureMetadata | None` in `adws/tests/adw_modules/steps/test_triage.py`. Given `notes="ADWS_FAILED|attempt=2|last_failure=2026-02-01T12:00:00Z|error_class=SdkCallError|step=implement|summary=SDK timeout after 30s"`, verify it returns a `FailureMetadata` with `attempt=2`, `last_failure="2026-02-01T12:00:00Z"`, `error_class="SdkCallError"`, `step="implement"`, `summary="SDK timeout after 30s"`. `FailureMetadata` is a frozen dataclass with these fields.
  - [ ] 1.2 GREEN: Create `adws/adw_modules/steps/triage.py`. Define `FailureMetadata` frozen dataclass with fields: `attempt` (int), `last_failure` (str), `error_class` (str), `step` (str), `summary` (str). Implement `parse_failure_metadata(notes: str) -> FailureMetadata | None`. Find the `ADWS_FAILED` prefix in notes, split by `|`, parse each `key=value` pair. Return `None` if `ADWS_FAILED` is not found or parsing fails.
  - [ ] 1.3 RED: Write test for `parse_failure_metadata` with notes that do NOT contain `ADWS_FAILED`. Given `notes="Normal issue notes"`, verify it returns `None`.
  - [ ] 1.4 GREEN: Ensure non-matching notes return `None`.
  - [ ] 1.5 RED: Write test for `parse_failure_metadata` with empty notes. Given `notes=""`, verify it returns `None`.
  - [ ] 1.6 GREEN: Ensure empty string returns `None`.
  - [ ] 1.7 RED: Write test for `parse_failure_metadata` with malformed metadata (missing fields). Given `notes="ADWS_FAILED|attempt=1"`, verify it returns `None` (incomplete metadata is treated as unparseable).
  - [ ] 1.8 GREEN: Ensure malformed metadata returns `None`.
  - [ ] 1.9 RED: Write test for `parse_failure_metadata` with escaped pipe in summary. Given `notes="ADWS_FAILED|attempt=1|last_failure=2026-02-01T00:00:00Z|error_class=TestError|step=verify|summary=Error in step\\|detail"`, verify `summary="Error in step|detail"` (unescaped correctly).
  - [ ] 1.10 GREEN: Implement pipe unescaping in summary parsing.
  - [ ] 1.11 RED: Write test for `parse_failure_metadata` when notes contain `needs_human` instead of `ADWS_FAILED`. Given `notes="needs_human"`, verify it returns `None` (the function only parses `ADWS_FAILED` structured metadata).
  - [ ] 1.12 GREEN: Ensure `needs_human` notes return `None`.
  - [ ] 1.13 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 2: Create `classify_failure_tier` pure function (AC: #1, #2, #3, #4)
  - [ ] 2.1 RED: Write test for `classify_failure_tier(metadata: FailureMetadata) -> int` in `adws/tests/adw_modules/steps/test_triage.py`. Given `FailureMetadata(attempt=1, ..., error_class="SdkCallError", ...)`, verify it returns `1` (Tier 1: transient, retryable, attempt < 3).
  - [ ] 2.2 GREEN: Implement `classify_failure_tier(metadata: FailureMetadata) -> int` in `triage.py`. Tier 1 criteria: `error_class` in `{"SdkCallError", "TimeoutError", "TestFailureError"}` AND `attempt < 3`. Tier 2 criteria: `attempt >= 3` AND `error_class` NOT in `{"unknown"}`. Tier 3: everything else (unknown error class, or Tier 2 exhausted). Return the tier number (1, 2, or 3).
  - [ ] 2.3 RED: Write test for `classify_failure_tier` with `attempt=1` and `error_class="TimeoutError"`. Verify returns `1`.
  - [ ] 2.4 GREEN: Ensure TimeoutError at attempt 1 is Tier 1.
  - [ ] 2.5 RED: Write test for `classify_failure_tier` with `attempt=2` and `error_class="TestFailureError"`. Verify returns `1`.
  - [ ] 2.6 GREEN: Ensure TestFailureError at attempt 2 is Tier 1.
  - [ ] 2.7 RED: Write test for `classify_failure_tier` with `attempt=3` and `error_class="SdkCallError"`. Verify returns `2` (Tier 2: repeated failure, attempt >= 3, classifiable error).
  - [ ] 2.8 GREEN: Ensure attempt 3 with classifiable error is Tier 2.
  - [ ] 2.9 RED: Write test for `classify_failure_tier` with `attempt=5` and `error_class="TestFailureError"`. Verify returns `2`.
  - [ ] 2.10 GREEN: Ensure high attempt with classifiable error is Tier 2.
  - [ ] 2.11 RED: Write test for `classify_failure_tier` with `attempt=1` and `error_class="unknown"`. Verify returns `3` (Tier 3: unknown error class, immediate escalation).
  - [ ] 2.12 GREEN: Ensure unknown error class at any attempt is Tier 3.
  - [ ] 2.13 RED: Write test for `classify_failure_tier` with `attempt=3` and `error_class="unknown"`. Verify returns `3` (Tier 3: unknown error class, even at high attempt).
  - [ ] 2.14 GREEN: Ensure unknown error class at attempt >= 3 is still Tier 3, not Tier 2.
  - [ ] 2.15 RED: Write test for `classify_failure_tier` with non-standard error class (e.g., `error_class="BeadsCloseError"`, `attempt=1`). Verify returns `1` -- any error class other than `unknown` is considered retryable at low attempt counts.
  - [ ] 2.16 GREEN: Ensure non-standard classifiable errors are Tier 1 at low attempts.
  - [ ] 2.17 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 3: Create `check_cooldown_elapsed` pure function (AC: #2)
  - [ ] 3.1 RED: Write test for `check_cooldown_elapsed(metadata: FailureMetadata, now: datetime) -> bool` in `adws/tests/adw_modules/steps/test_triage.py`. Given `FailureMetadata(attempt=1, last_failure="2026-02-01T12:00:00Z", ...)` and `now=datetime(2026, 2, 1, 13, 0, 0, tzinfo=UTC)` (1 hour after failure), verify it returns `True` (30min cooldown for attempt 1 has elapsed).
  - [ ] 3.2 GREEN: Implement `check_cooldown_elapsed(metadata: FailureMetadata, now: datetime) -> bool` in `triage.py`. Cooldown schedule: attempt 1 = 30 minutes, attempt 2 = 2 hours, attempt >= 3 = 8 hours. Parse `metadata.last_failure` as ISO datetime, compute elapsed time, compare to cooldown threshold. Return `True` if cooldown has elapsed.
  - [ ] 3.3 RED: Write test for `check_cooldown_elapsed` when cooldown has NOT elapsed. Given attempt=1, last_failure=12:00:00Z, now=12:20:00Z (20 min, less than 30min). Verify returns `False`.
  - [ ] 3.4 GREEN: Ensure not-yet-elapsed returns `False`.
  - [ ] 3.5 RED: Write test for `check_cooldown_elapsed` with attempt=2. Given last_failure=12:00:00Z, now=14:30:00Z (2.5 hours after, exceeds 2hr). Verify returns `True`.
  - [ ] 3.6 GREEN: Ensure attempt 2 uses 2-hour cooldown.
  - [ ] 3.7 RED: Write test for `check_cooldown_elapsed` with attempt=2 when cooldown NOT elapsed. Given last_failure=12:00:00Z, now=13:30:00Z (1.5 hours, less than 2hr). Verify returns `False`.
  - [ ] 3.8 GREEN: Ensure attempt 2 cooldown is enforced.
  - [ ] 3.9 RED: Write test for `check_cooldown_elapsed` with attempt=3 (8hr cooldown). Given last_failure=12:00:00Z, now=21:00:00Z (9 hours after). Verify returns `True`.
  - [ ] 3.10 GREEN: Ensure attempt >= 3 uses 8-hour cooldown.
  - [ ] 3.11 RED: Write test for `check_cooldown_elapsed` with attempt=3 when cooldown NOT elapsed. Given last_failure=12:00:00Z, now=18:00:00Z (6 hours, less than 8hr). Verify returns `False`.
  - [ ] 3.12 GREEN: Ensure attempt 3 cooldown is enforced.
  - [ ] 3.13 RED: Write test for `check_cooldown_elapsed` with attempt=5 (high attempt). Verify it uses 8-hour cooldown (same as attempt >= 3).
  - [ ] 3.14 GREEN: Ensure high attempt numbers use 8-hour cooldown.
  - [ ] 3.15 RED: Write test for `check_cooldown_elapsed` with malformed `last_failure` timestamp. Given `last_failure="not-a-date"`, verify it returns `False` (conservative -- if we cannot parse, do not allow retry).
  - [ ] 3.16 GREEN: Implement safe datetime parsing with fallback to `False`.
  - [ ] 3.17 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 4: Create `clear_failure_metadata` io_ops function (AC: #2, #3)
  - [ ] 4.1 RED: Write test for `io_ops.clear_failure_metadata(issue_id: str) -> IOResult[ShellResult, PipelineError]` in `adws/tests/adw_modules/test_io_ops.py`. Mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=0, stdout="", stderr="", command="bd update ISSUE-42 --notes ''"))`. Verify it returns `IOSuccess(ShellResult(...))`. The function executes `bd update {issue_id} --notes ''` to clear notes (NFR17).
  - [ ] 4.2 GREEN: Implement `clear_failure_metadata(issue_id: str) -> IOResult[ShellResult, PipelineError]` in `adws/adw_modules/io_ops.py`. Validate non-empty `issue_id`. Execute `bd update {issue_id} --notes ''` via `run_shell_command`. On nonzero exit, return `IOFailure(PipelineError(step_name="io_ops.clear_failure_metadata", error_type="BeadsClearMetadataError", ...))`. On success, return `IOSuccess(sr)`.
  - [ ] 4.3 RED: Write test for `clear_failure_metadata` when `bd update` fails (nonzero exit). Mock `run_shell_command` to return nonzero exit. Verify `IOFailure` with `error_type="BeadsClearMetadataError"`.
  - [ ] 4.4 GREEN: Ensure error path returns correctly.
  - [ ] 4.5 RED: Write test for `clear_failure_metadata` when `issue_id` is empty. Verify `IOFailure` with `error_type="ValueError"`.
  - [ ] 4.6 GREEN: Implement empty issue_id validation.
  - [ ] 4.7 RED: Write test for `clear_failure_metadata` when `run_shell_command` itself returns `IOFailure`. Verify the `IOFailure` propagates via `.bind()`.
  - [ ] 4.8 GREEN: Ensure shell command failures propagate via bind.
  - [ ] 4.9 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 5: Create `tag_needs_human` io_ops function (AC: #4)
  - [ ] 5.1 RED: Write test for `io_ops.tag_needs_human(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]` in `adws/tests/adw_modules/test_io_ops.py`. Mock `run_shell_command` to return `IOSuccess(ShellResult(return_code=0, ...))`. Verify it calls `bd update {issue_id} --notes 'needs_human|reason=...'`.
  - [ ] 5.2 GREEN: Implement `tag_needs_human(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]` in `adws/adw_modules/io_ops.py`. Validate non-empty `issue_id`. Build notes string as `needs_human|reason={reason}`. Execute `bd update {issue_id} --notes {notes}` via `run_shell_command`. On nonzero exit, return `IOFailure(PipelineError(step_name="io_ops.tag_needs_human", error_type="BeadsTagHumanError", ...))`. On success, return `IOSuccess(sr)`.
  - [ ] 5.3 RED: Write test for `tag_needs_human` when `bd update` fails. Verify `IOFailure` with `error_type="BeadsTagHumanError"`.
  - [ ] 5.4 GREEN: Ensure error path returns correctly.
  - [ ] 5.5 RED: Write test for `tag_needs_human` when `issue_id` is empty. Verify `IOFailure` with `error_type="ValueError"`.
  - [ ] 5.6 GREEN: Implement empty issue_id validation.
  - [ ] 5.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 6: Create `poll_failed_issues` function (AC: #1, #5)
  - [ ] 6.1 RED: Write test for `poll_failed_issues() -> IOResult[list[TriageCandidate], PipelineError]` in `adws/tests/test_adw_triage.py`. `TriageCandidate` is a frozen dataclass with fields: `issue_id` (str), `metadata` (FailureMetadata). Mock `io_ops.run_beads_list("open")` to return `IOSuccess("ISSUE-1\nISSUE-2\nISSUE-3\n")`. Mock `io_ops.read_issue_notes`: ISSUE-1 has `ADWS_FAILED|attempt=1|last_failure=2026-02-01T12:00:00Z|error_class=SdkCallError|step=implement|summary=timeout`, ISSUE-2 has `needs_human|reason=unresolvable`, ISSUE-3 has no failure metadata (empty notes). Verify it returns `IOSuccess([TriageCandidate(issue_id="ISSUE-1", metadata=...)])` -- only ISSUE-1 has parseable `ADWS_FAILED` metadata (ISSUE-2 is `needs_human` not `ADWS_FAILED`, ISSUE-3 has no failure metadata).
  - [ ] 6.2 GREEN: Create `adws/adw_triage.py`. Define `TriageCandidate` frozen dataclass. Implement `poll_failed_issues() -> IOResult[list[TriageCandidate], PipelineError]`. Steps: (a) Call `io_ops.run_beads_list("open")`. (b) Parse with `parse_issue_list()`. (c) For each issue, call `io_ops.read_issue_notes()`. (d) Call `parse_failure_metadata()`. (e) Collect issues with valid `FailureMetadata` as `TriageCandidate`. (f) Sort by `last_failure` ascending (oldest first per AC #5).
  - [ ] 6.3 RED: Write test for `poll_failed_issues` when no issues have `ADWS_FAILED` metadata. Mock all notes as empty. Verify returns `IOSuccess([])`.
  - [ ] 6.4 GREEN: Ensure empty result when no failed issues.
  - [ ] 6.5 RED: Write test for `poll_failed_issues` when `run_beads_list` returns `IOFailure`. Verify propagation.
  - [ ] 6.6 GREEN: Ensure list failure propagates.
  - [ ] 6.7 RED: Write test for `poll_failed_issues` when one issue's `read_issue_notes` fails. The polling should skip that issue gracefully and continue. Given 3 issues where ISSUE-2 notes read fails, ISSUE-1 and ISSUE-3 have `ADWS_FAILED` metadata. Verify both ISSUE-1 and ISSUE-3 are returned (ISSUE-2 skipped).
  - [ ] 6.8 GREEN: Implement graceful per-issue error handling.
  - [ ] 6.9 RED: Write test for `poll_failed_issues` ordering -- oldest failure first. Given ISSUE-1 with `last_failure=2026-02-01T14:00:00Z` and ISSUE-2 with `last_failure=2026-02-01T12:00:00Z`. Verify ISSUE-2 appears before ISSUE-1 in the result list.
  - [ ] 6.10 GREEN: Ensure sorting by last_failure ascending.
  - [ ] 6.11 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 7: Create `handle_tier1` function (AC: #2)
  - [ ] 7.1 RED: Write test for `handle_tier1(candidate: TriageCandidate, now: datetime) -> IOResult[TriageResult, PipelineError]` in `adws/tests/test_adw_triage.py`. `TriageResult` is a frozen dataclass with fields: `issue_id` (str), `tier` (int), `action` (str), `detail` (str). Given a candidate with `attempt=1`, `last_failure=2026-02-01T12:00:00Z`, `error_class="SdkCallError"`, and `now=2026-02-01T13:00:00Z` (1 hour after, cooldown elapsed). Mock `io_ops.clear_failure_metadata` to return `IOSuccess(...)`. Verify it returns `IOSuccess(TriageResult(issue_id="ISSUE-1", tier=1, action="cleared_for_retry", detail="Cooldown elapsed, cleared ADWS_FAILED metadata"))`.
  - [ ] 7.2 GREEN: Define `TriageResult` frozen dataclass in `adw_triage.py`. Implement `handle_tier1(candidate: TriageCandidate, now: datetime) -> IOResult[TriageResult, PipelineError]`. Check cooldown via `check_cooldown_elapsed`. If elapsed, call `io_ops.clear_failure_metadata(candidate.issue_id)`. On success, return `IOSuccess(TriageResult(..., action="cleared_for_retry", ...))`.
  - [ ] 7.3 RED: Write test for `handle_tier1` when cooldown has NOT elapsed. Given attempt=1, last_failure=12:00:00Z, now=12:20:00Z. Verify returns `IOSuccess(TriageResult(..., action="cooldown_pending", detail="Cooldown not elapsed. Next eligible: ..."))`. No io_ops calls should be made (no metadata cleared).
  - [ ] 7.4 GREEN: Implement cooldown-pending path. Verify `io_ops.clear_failure_metadata` is NOT called.
  - [ ] 7.5 RED: Write test for `handle_tier1` when `clear_failure_metadata` fails. Mock it to return `IOFailure`. Verify returns `IOSuccess(TriageResult(..., action="clear_failed", detail="Failed to clear metadata: ..."))`. The triage should not crash on clear failure -- degrade gracefully.
  - [ ] 7.6 GREEN: Implement fail-safe clear path using `.lash()`.
  - [ ] 7.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 8: Create `handle_tier2` function (AC: #3)
  - [ ] 8.1 RED: Write test for `handle_tier2(candidate: TriageCandidate) -> IOResult[TriageResult, PipelineError]` in `adws/tests/test_adw_triage.py`. Given a candidate with `attempt=3`, `error_class="TestFailureError"`. Mock `io_ops.execute_sdk_call` to return `IOSuccess(AdwsResponse(result="ACTION: adjust_parameters|DETAIL: Simplified test scope", is_error=False))`. Verify returns `IOSuccess(TriageResult(..., tier=2, action="adjusted", detail="Simplified test scope"))`. Verify `io_ops.clear_failure_metadata` is called (metadata cleared for re-dispatch).
  - [ ] 8.2 GREEN: Implement `handle_tier2(candidate: TriageCandidate) -> IOResult[TriageResult, PipelineError]`. Build a triage agent prompt including failure context (attempt count, error class, step, summary). Call `io_ops.execute_sdk_call` with a triage system prompt. Parse the response for action directives: `ACTION: adjust_parameters|DETAIL: ...` or `ACTION: split|DETAIL: ...` or `ACTION: escalate|DETAIL: ...`. On `adjust_parameters`: call `io_ops.clear_failure_metadata` and return `adjusted`. On `split`: create sub-issues via `io_ops.run_beads_create`, close original via `io_ops.run_beads_close`. On `escalate`: fall through to Tier 3.
  - [ ] 8.3 RED: Write test for `handle_tier2` when triage agent recommends split. Mock `io_ops.execute_sdk_call` to return `IOSuccess(AdwsResponse(result="ACTION: split|DETAIL: Split into subtask A and subtask B"))`. Mock `io_ops.run_beads_create` to return `IOSuccess("ISSUE-10")` for first call, `IOSuccess("ISSUE-11")` for second call. Mock `io_ops.run_beads_close` to succeed. Verify returns `IOSuccess(TriageResult(..., action="split", detail="Split into sub-issues: ISSUE-10, ISSUE-11"))`. Verify `run_beads_create` was called twice and `run_beads_close` was called with reason containing sub-issue IDs.
  - [ ] 8.4 GREEN: Implement split path -- create sub-issues, close original.
  - [ ] 8.5 RED: Write test for `handle_tier2` when triage agent recommends escalation. Mock `io_ops.execute_sdk_call` to return `IOSuccess(AdwsResponse(result="ACTION: escalate|DETAIL: Cannot determine fix automatically"))`. Verify returns `IOSuccess(TriageResult(..., action="escalated_to_tier3", detail="Cannot determine fix automatically"))`. No metadata clearing, no sub-issues.
  - [ ] 8.6 GREEN: Implement escalation path.
  - [ ] 8.7 RED: Write test for `handle_tier2` when `execute_sdk_call` fails (SDK error). Verify returns `IOSuccess(TriageResult(..., action="triage_sdk_failed", detail="..."))`. Triage failures should not crash -- degrade to Tier 3 escalation.
  - [ ] 8.8 GREEN: Implement SDK failure handling with graceful degradation.
  - [ ] 8.9 RED: Write test for `handle_tier2` when `execute_sdk_call` returns unparseable response (no `ACTION:` directive). Verify returns `IOSuccess(TriageResult(..., action="triage_parse_failed", detail="..."))`. Degrades to Tier 3.
  - [ ] 8.10 GREEN: Implement response parsing failure handling.
  - [ ] 8.11 RED: Write test for `handle_tier2` when `run_beads_create` fails during split. Verify returns `IOSuccess(TriageResult(..., action="split_failed", detail="..."))`. The original issue remains open with existing metadata.
  - [ ] 8.12 GREEN: Implement split creation failure handling.
  - [ ] 8.13 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 9: Create `handle_tier3` function (AC: #4)
  - [ ] 9.1 RED: Write test for `handle_tier3(candidate: TriageCandidate) -> IOResult[TriageResult, PipelineError]` in `adws/tests/test_adw_triage.py`. Given a candidate with `error_class="unknown"`. Mock `io_ops.tag_needs_human` to return `IOSuccess(...)`. Verify returns `IOSuccess(TriageResult(..., tier=3, action="escalated_to_human", detail="Tagged needs_human..."))`.
  - [ ] 9.2 GREEN: Implement `handle_tier3(candidate: TriageCandidate) -> IOResult[TriageResult, PipelineError]`. Call `io_ops.tag_needs_human(candidate.issue_id, reason)` with reason including error context. Return `TriageResult` with `action="escalated_to_human"`.
  - [ ] 9.3 RED: Write test for `handle_tier3` when `tag_needs_human` fails. Verify returns `IOSuccess(TriageResult(..., action="escalation_failed", detail="..."))`. Even tagging failures must not crash triage.
  - [ ] 9.4 GREEN: Implement tag failure handling with `.lash()`.
  - [ ] 9.5 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 10: Create `triage_issue` orchestrator function (AC: #1, #2, #3, #4)
  - [ ] 10.1 RED: Write test for `triage_issue(candidate: TriageCandidate, now: datetime) -> IOResult[TriageResult, PipelineError]` in `adws/tests/test_adw_triage.py`. Given a Tier 1 candidate (attempt=1, SdkCallError, cooldown elapsed). Mock `io_ops.clear_failure_metadata`. Verify it classifies as Tier 1 and delegates to `handle_tier1`.
  - [ ] 10.2 GREEN: Implement `triage_issue(candidate: TriageCandidate, now: datetime) -> IOResult[TriageResult, PipelineError]`. Call `classify_failure_tier(candidate.metadata)`. Dispatch to `handle_tier1`, `handle_tier2`, or `handle_tier3` based on tier.
  - [ ] 10.3 RED: Write test for `triage_issue` with Tier 2 candidate (attempt=3, classifiable error). Mock SDK call for AI triage. Verify delegates to `handle_tier2`.
  - [ ] 10.4 GREEN: Ensure Tier 2 dispatch works.
  - [ ] 10.5 RED: Write test for `triage_issue` with Tier 3 candidate (unknown error class). Mock `io_ops.tag_needs_human`. Verify delegates to `handle_tier3`.
  - [ ] 10.6 GREEN: Ensure Tier 3 dispatch works.
  - [ ] 10.7 RED: Write test for `triage_issue` when Tier 2 handler returns `action="escalated_to_tier3"` (triage agent recommended escalation). Verify that `handle_tier3` is then called to tag `needs_human`.
  - [ ] 10.8 GREEN: Implement Tier 2 to Tier 3 escalation path.
  - [ ] 10.9 RED: Write test for `triage_issue` when Tier 2 handler returns `action="triage_sdk_failed"` or `action="triage_parse_failed"`. Verify that `handle_tier3` is called as fallback.
  - [ ] 10.10 GREEN: Implement Tier 2 failure to Tier 3 fallback.
  - [ ] 10.11 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 11: Create `run_triage_cycle` function (AC: #5)
  - [ ] 11.1 RED: Write test for `run_triage_cycle(now: datetime) -> TriageCycleResult` in `adws/tests/test_adw_triage.py`. `TriageCycleResult` is a frozen dataclass with fields: `issues_found` (int), `tier1_cleared` (int), `tier1_pending` (int), `tier2_adjusted` (int), `tier2_split` (int), `tier3_escalated` (int), `errors` (list[str]). Mock `poll_failed_issues` to return 2 candidates. Mock `triage_issue` to return Tier 1 cleared for first, Tier 3 escalated for second. Verify `TriageCycleResult(issues_found=2, tier1_cleared=1, tier3_escalated=1, ...)`.
  - [ ] 11.2 GREEN: Define `TriageCycleResult` frozen dataclass. Implement `run_triage_cycle(now: datetime) -> TriageCycleResult`. Call `poll_failed_issues()`. On failure, return result with `errors`. Otherwise, iterate candidates sequentially, calling `triage_issue(candidate, now)`. Accumulate results.
  - [ ] 11.3 RED: Write test for `run_triage_cycle` when `poll_failed_issues` returns `IOFailure`. Verify `TriageCycleResult(issues_found=0, ..., errors=["..."])`.
  - [ ] 11.4 GREEN: Ensure poll failure is handled gracefully.
  - [ ] 11.5 RED: Write test for `run_triage_cycle` when one `triage_issue` call returns `IOFailure`. Verify the error is recorded but processing continues for remaining issues.
  - [ ] 11.6 GREEN: Implement per-issue error isolation.
  - [ ] 11.7 RED: Write test for `run_triage_cycle` with mixed results. 4 candidates: Tier 1 cleared, Tier 1 pending, Tier 2 adjusted, Tier 3 escalated. Verify `TriageCycleResult(issues_found=4, tier1_cleared=1, tier1_pending=1, tier2_adjusted=1, tier3_escalated=1, ...)`.
  - [ ] 11.8 GREEN: Ensure all action types are counted correctly.
  - [ ] 11.9 RED: Write test for `run_triage_cycle` with empty failed issue queue. Verify `TriageCycleResult(issues_found=0, ...)` with all zeros.
  - [ ] 11.10 GREEN: Ensure empty queue returns zeros.
  - [ ] 11.11 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 12: Create `run_triage_loop` function (AC: #5)
  - [ ] 12.1 RED: Write test for `run_triage_loop(poll_interval_seconds: float, max_cycles: int | None = None) -> list[TriageCycleResult]` in `adws/tests/test_adw_triage.py`. With `max_cycles=2`, mock `run_triage_cycle` to return results. Mock `io_ops.sleep_seconds`. Mock `io_ops.write_stderr`. Verify it returns a list of 2 `TriageCycleResult` objects and `io_ops.sleep_seconds` was called once (between cycles, not after last).
  - [ ] 12.2 GREEN: Implement `run_triage_loop(poll_interval_seconds: float, max_cycles: int | None = None) -> list[TriageCycleResult]`. Same pattern as `run_trigger_loop` in `adw_trigger_cron.py`: loop, call `run_triage_cycle`, append result, log, sleep between cycles.
  - [ ] 12.3 RED: Write test for `run_triage_loop` with `max_cycles=1`. Verify it returns 1 result and `io_ops.sleep_seconds` was NOT called.
  - [ ] 12.4 GREEN: Ensure single cycle does not sleep.
  - [ ] 12.5 RED: Write test for `run_triage_loop` when `run_triage_cycle` raises an unexpected exception. Verify the loop catches this, creates an error `TriageCycleResult`, and continues.
  - [ ] 12.6 GREEN: Implement exception catching in the loop.
  - [ ] 12.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 13: Create triage cycle terminal output (AC: #5)
  - [ ] 13.1 RED: Write test for `format_triage_summary(result: TriageCycleResult) -> str` in `adws/tests/test_adw_triage.py`. Given a result with `issues_found=3, tier1_cleared=1, tier1_pending=1, tier3_escalated=1`, verify summary contains key metrics.
  - [ ] 13.2 GREEN: Implement `format_triage_summary(result: TriageCycleResult) -> str` in `adw_triage.py`.
  - [ ] 13.3 RED: Write test for `format_triage_summary` with errors. Given a result with `errors=["Poll failed"]`, verify error count appears.
  - [ ] 13.4 GREEN: Include error count in summary.
  - [ ] 13.5 RED: Write test for `log_triage_result(result: TriageCycleResult) -> None`. Mock `io_ops.write_stderr`. Verify it writes the formatted summary.
  - [ ] 13.6 GREEN: Implement `log_triage_result`.
  - [ ] 13.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 14: Register triage workflow in workflow registry (AC: #1)
  - [ ] 14.1 RED: Write test in `adws/tests/workflows/test_init.py` that `load_workflow("triage")` returns a `Workflow` with `name="triage"` and `dispatchable=False` (triage is invoked by its own loop, not by cron trigger dispatch).
  - [ ] 14.2 GREEN: Add `TRIAGE = "triage"` to `WorkflowName` in `adws/workflows/__init__.py`. Register the triage workflow in `_REGISTRY`. The triage workflow is `dispatchable=False` because it runs on its own schedule, not triggered by issue tags.
  - [ ] 14.3 RED: Write test that `list_workflows(dispatchable_only=True)` does NOT include the triage workflow.
  - [ ] 14.4 GREEN: Ensure triage workflow is excluded from dispatchable list.
  - [ ] 14.5 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 15: Verify NFR19 compliance across triage workflow (AC: #5)
  - [ ] 15.1 RED: Write test confirming that `poll_failed_issues` never reads BMAD files (NFR19). Mock `io_ops.read_bmad_file` and verify it is NOT called during polling.
  - [ ] 15.2 GREEN: Confirm the implementation does not call any BMAD-related io_ops functions.
  - [ ] 15.3 RED: Write test confirming that `run_triage_cycle` never reads BMAD files through the full cycle flow.
  - [ ] 15.4 GREEN: Confirm NFR19 compliance in the full cycle.
  - [ ] 15.5 REFACTOR: Clean up.

- [ ] Task 16: Integration tests for full triage flow (AC: #1, #2, #3, #4, #5, #6)
  - [ ] 16.1 RED: Write integration test for Tier 1 cooldown retry flow. Mock `io_ops.run_beads_list` to return 1 issue with `ADWS_FAILED` metadata (attempt=1, SdkCallError, old timestamp). Mock `io_ops.read_issue_notes` with the failure metadata. Mock `io_ops.clear_failure_metadata`. Verify `TriageCycleResult` has `tier1_cleared=1`.
  - [ ] 16.2 GREEN: Ensure Tier 1 retry flow works end-to-end through integration.
  - [ ] 16.3 RED: Write integration test for Tier 1 cooldown not elapsed. Same setup but with recent timestamp. Verify `tier1_pending=1` and `clear_failure_metadata` was NOT called.
  - [ ] 16.4 GREEN: Ensure cooldown enforcement works in integration.
  - [ ] 16.5 RED: Write integration test for Tier 2 AI triage with adjustment. Issue at attempt=3, classifiable error. Mock `io_ops.execute_sdk_call` returning adjust action. Mock `io_ops.clear_failure_metadata`. Verify `tier2_adjusted=1`.
  - [ ] 16.6 GREEN: Ensure Tier 2 adjustment flow works in integration.
  - [ ] 16.7 RED: Write integration test for Tier 2 AI triage with split. Mock `io_ops.execute_sdk_call` returning split action. Mock `io_ops.run_beads_create` twice. Mock `io_ops.run_beads_close`. Verify `tier2_split=1` and correct bd create/close calls.
  - [ ] 16.8 GREEN: Ensure Tier 2 split flow works in integration.
  - [ ] 16.9 RED: Write integration test for Tier 3 human escalation. Issue with `error_class="unknown"`. Mock `io_ops.tag_needs_human`. Verify `tier3_escalated=1`.
  - [ ] 16.10 GREEN: Ensure Tier 3 escalation works in integration.
  - [ ] 16.11 RED: Write integration test for mixed triage cycle. 4 issues: Tier 1 cleared, Tier 1 pending, Tier 2 adjusted, Tier 3 escalated. Verify all counts correct and all issues processed independently.
  - [ ] 16.12 GREEN: Ensure mixed cycle works in integration.
  - [ ] 16.13 RED: Write integration test verifying NFR19 across the full triage flow: `io_ops.read_bmad_file` is never called.
  - [ ] 16.14 GREEN: Confirm NFR19 compliance in integration.
  - [ ] 16.15 REFACTOR: Clean up integration tests.

- [ ] Task 17: Verify full integration and quality gates (AC: #7)
  - [ ] 17.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 17.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 17.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 7.3)

**adw_dispatch.py** exists with three functions:
- `dispatch_workflow(issue_id: str) -> IOResult[WorkflowContext, PipelineError]` -- reads Beads issue, extracts workflow tag, validates, returns prepared WorkflowContext (Story 7.1)
- `execute_dispatched_workflow(ctx: WorkflowContext) -> IOResult[DispatchExecutionResult, PipelineError]` -- executes workflow, finalizes: close on success, tag failure on failure (Story 7.2)
- `dispatch_and_execute(issue_id: str) -> IOResult[DispatchExecutionResult, PipelineError]` -- full orchestrator: dispatch + execute + finalize (Story 7.2). The cron trigger calls this.

**adw_trigger_cron.py** exists (from Story 7.3) with:
- `CronCycleResult` frozen dataclass
- `poll_ready_issues() -> IOResult[list[str], PipelineError]` -- polls for dispatch-ready issues
- `run_poll_cycle() -> CronCycleResult` -- one poll-dispatch cycle
- `run_trigger_loop(poll_interval_seconds, max_cycles)` -- repeating trigger loop
- `format_cycle_summary` and `log_cycle_result` -- terminal output

**adw_triage.py** does NOT exist yet. This story creates it.

**dispatch_guard.py** exists (from Story 7.3) with:
- `has_active_failure_metadata(notes: str) -> bool` -- checks for `ADWS_FAILED` or `needs_human`
- `check_dispatch_guard(issue_id: str) -> IOResult[bool, PipelineError]` -- full guard check with IO
- `parse_issue_list(raw_output: str) -> list[str]` -- parse bd list stdout

**_finalize.py** exists (from Story 4.4) with:
- `build_failure_metadata(error, attempt_count) -> str` -- builds `ADWS_FAILED|attempt=N|last_failure=ISO|error_class=X|step=Y|summary=Z` format
- `finalize_on_success(issue_id)` -- close on success
- `finalize_on_failure(issue_id, error, attempt_count)` -- tag failure metadata

**io_ops.py** has ~28 public functions. Key functions for this story that already exist:
```python
def run_shell_command(cmd, *, timeout=None, cwd=None) -> IOResult[ShellResult, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_beads_list(status: str) -> IOResult[str, PipelineError]: ...
def read_issue_notes(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_create(title: str, description: str) -> IOResult[str, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[None, PipelineError]: ...
def write_stderr(message: str) -> IOResult[None, PipelineError]: ...
```

New io_ops functions needed:
```python
def clear_failure_metadata(issue_id: str) -> IOResult[ShellResult, PipelineError]: ...  # NEW: bd update --notes '' to clear
def tag_needs_human(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...  # NEW: bd update --notes 'needs_human|...'
```

**workflows/__init__.py** has 5 registered workflows. Two are dispatchable: `implement_close` and `implement_verify_close`. The triage workflow will be added as `dispatchable=False`.

**Current test count**: 1161 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 125 files tracked by mypy.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: Story 7.4 Architecture

This story creates the triage module (`adw_triage.py`) and supporting pure functions in `triage.py` (step module) to implement the three-tier self-healing failure recovery:

```
Architecture: Triage Workflow - Self-Healing Failure Recovery

                       run_triage_loop(interval, max_cycles)
                                    |
                                    | (repeating loop)
                                    v
                           run_triage_cycle(now)
                                    |
                        +-----------+-----------+
                        |                       |
                        v                       v
                poll_failed_issues()    log_triage_result()
                        |                  (stderr output)
            +-----------+-----------+
            |           |           |
            v           v           v
    run_beads_list  read_issue_   parse_failure_
    ("open")        notes         metadata()
                                       |
                                       v
                            (list of TriageCandidate)
                                       |
                                       v (sequential, oldest first)
                            triage_issue(candidate, now)
                                       |
                        +--------------+--------------+
                        |              |              |
                        v              v              v
                  handle_tier1   handle_tier2   handle_tier3
                        |              |              |
                        v              v              v
              check_cooldown   execute_sdk_call  tag_needs_human
              clear_metadata   (AI triage agent)
                               run_beads_create
                               run_beads_close
                               clear_metadata
```

### Design: Three-Tier Escalation Model

**Tier 1 -- Automatic Retry with Exponential Backoff:**
- Criteria: `error_class` is retryable (`SdkCallError`, `TimeoutError`, `TestFailureError`, or any non-`unknown` class) AND `attempt < 3`
- Action: Check exponential backoff cooldown. If elapsed, clear `ADWS_FAILED` metadata. Issue re-enters dispatch pool on next cron cycle.
- Cooldown schedule: attempt 1 = 30 minutes, attempt 2 = 2 hours, attempt >= 3 = 8 hours
- No human involvement.

**Tier 2 -- AI Triage Agent:**
- Criteria: `attempt >= 3` AND `error_class` is NOT `unknown` (classifiable error that keeps failing)
- Action: Fresh SDK call with triage agent system prompt. Agent analyzes failure context and recommends one of:
  - `adjust_parameters`: Clear metadata, re-enter dispatch. No human.
  - `split`: Create sub-issues via `bd create`, close original. No human.
  - `escalate`: Fall through to Tier 3.
- On triage failure (SDK error, unparseable response): Escalate to Tier 3.
- No human involvement (unless agent recommends escalation).

**Tier 3 -- Human Escalation:**
- Criteria: `error_class` is `unknown`, or Tier 2 triage failed/recommended escalation
- Action: Tag issue with `needs_human` via `bd update --notes`. Issue is excluded from both dispatch AND automated triage.
- This is the ONLY path requiring human attention.

### Design: FailureMetadata Parsing

The `ADWS_FAILED` metadata format is written by `build_failure_metadata` in `_finalize.py`:
```
ADWS_FAILED|attempt=N|last_failure=ISO|error_class=X|step=Y|summary=Z
```

Parsing this format requires:
1. Find `ADWS_FAILED` prefix
2. Split by `|` (handling `\|` escapes in summary)
3. Parse `key=value` pairs
4. Return `FailureMetadata` dataclass or `None` on parse failure

The parser must be resilient -- malformed metadata should return `None`, not crash.

### Design: Triage Agent System Prompt

The Tier 2 triage agent receives a structured prompt with:
- Issue ID
- Failure metadata (attempt count, error class, step, summary)
- Historical context (accumulated from previous failures)

The agent's response must include a structured directive:
```
ACTION: adjust_parameters|DETAIL: <description of adjustment>
ACTION: split|DETAIL: <description of how to split>
ACTION: escalate|DETAIL: <reason for escalation>
```

The parsing is simple substring matching for the `ACTION:` prefix. Unparseable responses degrade to Tier 3 escalation.

### Design: Separation from Cron Trigger

The triage module (`adw_triage.py`) is separate from the cron trigger (`adw_trigger_cron.py`). They share:
- `dispatch_guard.py` -- `has_active_failure_metadata` (used by both)
- `parse_issue_list` -- shared utility
- `io_ops` functions -- `run_beads_list`, `read_issue_notes`, etc.

But they have distinct responsibilities:
- **Cron trigger**: Polls for READY issues (no failure metadata), dispatches workflows
- **Triage**: Polls for FAILED issues (has `ADWS_FAILED` metadata), evaluates recovery

### Design: TriageCandidate and TriageResult

```python
@dataclass(frozen=True)
class TriageCandidate:
    """A failed issue ready for triage evaluation."""
    issue_id: str
    metadata: FailureMetadata

@dataclass(frozen=True)
class TriageResult:
    """Result of triaging a single issue."""
    issue_id: str
    tier: int
    action: str  # "cleared_for_retry", "cooldown_pending", "adjusted", "split", "escalated_to_human", etc.
    detail: str

@dataclass(frozen=True)
class TriageCycleResult:
    """Result of a single triage cycle."""
    issues_found: int
    tier1_cleared: int
    tier1_pending: int
    tier2_adjusted: int
    tier2_split: int
    tier3_escalated: int
    triage_errors: int
    errors: list[str] = field(default_factory=list)
```

### Design: Testability

Same pattern as `adw_trigger_cron.py`:
- `run_triage_loop` accepts `max_cycles` for testing (avoids infinite loop)
- `run_triage_cycle` accepts `now: datetime` parameter for deterministic cooldown testing
- `check_cooldown_elapsed` accepts `now: datetime` parameter (no `datetime.now()` calls in pure functions)
- All io_ops behind mock boundary

### Design: Error Handling

Every tier handler returns `IOSuccess(TriageResult)` -- never `IOFailure`. Triage failures are recorded in the `TriageResult.action` field (e.g., `"clear_failed"`, `"triage_sdk_failed"`, `"split_failed"`, `"escalation_failed"`). This ensures:
1. One issue's triage failure does not prevent processing others
2. `run_triage_cycle` always gets a result to count
3. No infrastructure crashes from triage operations

`IOFailure` is reserved for infrastructure failures (e.g., `poll_failed_issues` fails to list issues).

### Design: Cooldown Schedule

```python
COOLDOWN_SCHEDULE: dict[int, timedelta] = {
    1: timedelta(minutes=30),   # 30 min after first failure
    2: timedelta(hours=2),      # 2 hours after second failure
}
DEFAULT_COOLDOWN = timedelta(hours=8)  # 8 hours for attempt >= 3
```

### Test Strategy

**New test files**:
- `adws/tests/adw_modules/steps/test_triage.py` -- parse_failure_metadata, classify_failure_tier, check_cooldown_elapsed, FailureMetadata dataclass tests
- `adws/tests/test_adw_triage.py` -- poll_failed_issues, handle_tier1/2/3, triage_issue, run_triage_cycle, run_triage_loop, format_triage_summary, log_triage_result, TriageCandidate, TriageResult, TriageCycleResult
- New tests in `adws/tests/adw_modules/test_io_ops.py` -- clear_failure_metadata, tag_needs_human
- `adws/tests/integration/test_triage_flow.py` -- full triage integration tests

**Mock targets**:
- `adws.adw_modules.io_ops.run_beads_list` -- mock in poll tests
- `adws.adw_modules.io_ops.read_issue_notes` -- mock in poll tests
- `adws.adw_modules.io_ops.clear_failure_metadata` -- mock in tier 1 tests
- `adws.adw_modules.io_ops.tag_needs_human` -- mock in tier 3 tests
- `adws.adw_modules.io_ops.execute_sdk_call` -- mock in tier 2 tests (AI triage)
- `adws.adw_modules.io_ops.run_beads_create` -- mock in tier 2 split tests
- `adws.adw_modules.io_ops.run_beads_close` -- mock in tier 2 split tests
- `adws.adw_modules.io_ops.run_shell_command` -- mock in io_ops unit tests
- `adws.adw_modules.io_ops.sleep_seconds` -- mock in loop tests
- `adws.adw_modules.io_ops.write_stderr` -- mock in logging tests
- `adws.adw_modules.io_ops.read_bmad_file` -- mock to VERIFY IT IS NOT CALLED (NFR19)

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.
- Lazy imports (e.g., `from adws.workflows import load_workflow` inside function body) need `# noqa: PLC0415`.
- `FBT003` (boolean positional argument) may be needed for `IOSuccess(True)` / `IOSuccess(False)` patterns.

### Architecture Compliance

- **FR48**: Triage workflow with tiered escalation (auto-retry, AI triage, human).
- **NFR1**: ROP error handling throughout. IOFailure for infrastructure errors, IOSuccess for results.
- **NFR2**: Failed workflows leave Beads issues open with structured failure metadata (handled by `_finalize.py`). Triage processes this metadata.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. New functions: `clear_failure_metadata`, `tag_needs_human`.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads via bd CLI only. All Beads operations via io_ops functions.
- **NFR19**: ADWS never reads BMAD files during execution. The triage workflow reads only Beads issue data. Tests verify `io_ops.read_bmad_file` is not called.
- **NFR21**: Cron trigger never dispatches issues with active failure metadata. Triage clears metadata to re-enable dispatch.
- **NFR22**: Workflow agents operate autonomously -- no human input during execution. Tier 3 escalation tags for human attention but does not block or prompt.
- **Decision 5**: `load_workflow()` is pure lookup. Triage workflow registered as `dispatchable=False`.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT change `dispatch_and_execute` from Story 7.2 -- triage is a separate workflow.
- Do NOT change `dispatch_workflow` from Story 7.1.
- Do NOT change `adw_trigger_cron.py` -- the cron trigger already skips `ADWS_FAILED` and `needs_human` issues.
- Do NOT change `finalize_on_success` or `finalize_on_failure` in `_finalize.py`.
- Do NOT change `has_active_failure_metadata` or `check_dispatch_guard` in `dispatch_guard.py`.
- Do NOT change the engine executor logic.
- Do NOT change existing io_ops functions -- add new ones (`clear_failure_metadata`, `tag_needs_human`) and reuse existing.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in `adw_triage.py` or `triage.py`.
- Do NOT read BMAD files from any code in this story (NFR19).
- Do NOT implement parallel issue processing -- issues must be processed sequentially (oldest first).
- Do NOT make triage workflow dispatchable -- it runs on its own loop, not triggered by issue tags.
- Do NOT change `WorkflowName` constants for existing workflows -- only add `TRIAGE`.

### Relationship to Adjacent Stories

- **Story 7.1** (predecessor): Issue Tag Extraction & Workflow Dispatch -- provides `dispatch_workflow()` for tag extraction. Not directly used by triage, but triage clears metadata so issues can re-enter dispatch.
- **Story 7.2** (predecessor): Workflow Execution & Issue Closure -- provides `dispatch_and_execute()` and finalize logic. The `build_failure_metadata` function in `_finalize.py` creates the format that triage parses.
- **Story 7.3** (predecessor): Cron Trigger Polling & Autonomous Execution -- provides `dispatch_guard.py` (reused for identifying failed issues), `parse_issue_list` (reused for parsing bd list output), and `CronCycleResult` (pattern for `TriageCycleResult`).
- **This is the FINAL story** in the project. No successor stories. Completing this story completes Epic 7 and the entire project.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (Issue Integration section):**
> **Issue Integration (FR18-22)** | `adws/adw_dispatch.py`, `adw_trigger_cron.py` | `io_ops.py` (bd CLI calls), `workflows/__init__.py` (load_workflow)

**FR48 (from epics):**
> Triage workflow reviews failed issues with tiered escalation: Tier 1 (automatic retry with exponential backoff), Tier 2 (AI triage agent analyzes and adjusts), Tier 3 (human escalation only after automated recovery is exhausted)

**NFR2 (from epics):**
> Failed workflows must leave Beads issues in a recoverable state: open with structured failure metadata (`ADWS_FAILED` notes including attempt count, error classification, and failure summary). Issues remain dispatchable only after automated triage clears them for retry.

**NFR21 (from epics):**
> The cron trigger must never dispatch an issue with active failure metadata. A separate triage workflow governs retry eligibility, clearing failure metadata only after appropriate cooldown or AI triage analysis.

**Epic 7 Description:**
> System autonomously polls Beads for open issues with workflow tags, dispatches the appropriate workflow, executes it, closes the issue on success, and handles failures through tiered automated triage -- zero manual intervention except for truly unresolvable problems (Zero Touch Engineering Principle).

### Project Structure Notes

Files to create:
- `adws/adw_triage.py` -- triage module (TriageCandidate, TriageResult, TriageCycleResult, poll_failed_issues, handle_tier1/2/3, triage_issue, run_triage_cycle, run_triage_loop, format_triage_summary, log_triage_result)
- `adws/adw_modules/steps/triage.py` -- triage pure functions (FailureMetadata, parse_failure_metadata, classify_failure_tier, check_cooldown_elapsed)
- `adws/tests/test_adw_triage.py` -- triage module tests
- `adws/tests/adw_modules/steps/test_triage.py` -- triage step tests
- `adws/tests/integration/test_triage_flow.py` -- integration tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `clear_failure_metadata()` and `tag_needs_human()`
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for new io_ops functions
- `adws/adw_modules/steps/__init__.py` -- export triage functions
- `adws/workflows/__init__.py` -- add `TRIAGE` to `WorkflowName`, register triage workflow
- `adws/tests/workflows/test_init.py` -- add tests for triage workflow registration

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.4] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7] -- Epic summary: "Automated Dispatch, Cron Trigger & Self-Healing Triage"
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry: dispatchable flag, load_workflow() pure lookup, policy in adw_dispatch.py
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK Integration Design: AdwsRequest/AdwsResponse at boundary, execute_sdk_call proxy
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- All integration points through io_ops.py
- [Source: _bmad-output/planning-artifacts/architecture.md#One-Directional System Flow] -- BMAD -> Beads -> ADWS
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR48 maps to Epic 7
- [Source: adws/adw_dispatch.py] -- dispatch_workflow(), execute_dispatched_workflow(), dispatch_and_execute(), DispatchExecutionResult
- [Source: adws/adw_trigger_cron.py] -- CronCycleResult, poll_ready_issues, run_poll_cycle, run_trigger_loop (patterns for triage equivalents)
- [Source: adws/adw_modules/commands/_finalize.py] -- build_failure_metadata format (ADWS_FAILED|attempt=N|...), finalize_on_success, finalize_on_failure
- [Source: adws/adw_modules/steps/dispatch_guard.py] -- has_active_failure_metadata, check_dispatch_guard, parse_issue_list (reused by triage)
- [Source: adws/adw_modules/io_ops.py] -- run_beads_list, read_issue_notes, run_beads_close, run_beads_create, run_beads_update_notes, execute_sdk_call, run_shell_command, sleep_seconds, write_stderr (patterns for new functions)
- [Source: adws/adw_modules/engine/types.py] -- Workflow, Step, StepFunction
- [Source: adws/adw_modules/types.py] -- WorkflowContext, ShellResult, AdwsRequest, AdwsResponse
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, load_workflow(), list_workflows(), list_dispatchable_workflows()
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/7-3-cron-trigger-polling-and-autonomous-execution.md] -- Story 7.3 reference (predecessor, format reference)
- [Source: _bmad-output/implementation-artifacts/7-2-workflow-execution-and-issue-closure.md] -- Story 7.2 reference (predecessor)
- [Source: _bmad-output/implementation-artifacts/7-1-issue-tag-extraction-and-workflow-dispatch.md] -- Story 7.1 reference (predecessor)

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

From Story 7.3 learnings:
- **1161 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **125 source files**: Current file count tracked by mypy.
- **io_ops at ~28 public functions**: This story adds 2 new io_ops functions (`clear_failure_metadata`, `tag_needs_human`).
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Frozen dataclasses**: All data models must be frozen.
- **Whitespace-only validation**: Issue IDs must be checked with `if not issue_id or not issue_id.strip():` per 7.1 code review finding.
- **Lazy imports**: When importing from `adws.workflows` inside function bodies (to avoid circular imports), use `# noqa: PLC0415`.
- **bind() and .lash() patterns**: Use for composing IOResult chains. The finalize helpers demonstrate this pattern.
- **Mock ALL io_ops calls in unit tests**: Even when the function under test is mocked at a higher level, if downstream code (like `log_triage_result`) calls io_ops functions, those must be mocked too.
- **Avoid testing mock behavior**: When `.lash()` or `.bind()` makes certain IOResult branches unreachable, do not mock the intermediate function to force-return impossible states. Instead, test the real code path by mocking at the io_ops boundary.
- **Include all metrics in summaries**: Any field tracked in a result dataclass should be visible in its human-readable summary.
- **Document case-sensitivity decisions**: When using substring matching for markers, document whether matching is case-sensitive and why.
- **Semantic distinction**: `IOFailure` = infrastructure broke, `IOSuccess(success=False)` = workflow ran but failed.
- **FBT003**: Boolean in `IOSuccess(True)` / `IOSuccess(False)` needs `# noqa: FBT003`.

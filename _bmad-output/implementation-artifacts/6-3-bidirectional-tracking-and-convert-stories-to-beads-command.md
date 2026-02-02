# Story 6.3: Bidirectional Tracking & /convert-stories-to-beads Command

Status: code-review-complete

## Code Review

**Reviewer**: Claude Opus 4.5 (adversarial review)
**Date**: 2026-02-02
**Verdict**: 4 issues found (1 HIGH, 2 MEDIUM, 1 LOW). HIGH and MEDIUM fixes applied.

### ISSUE 1 (HIGH) -- Multi-story file corruption via stale-read idempotency

**File**: `adws/adw_modules/steps/convert_stories_orchestrator.py`, lines 149-169 (original)
**Problem**: `_process_single_story` re-read the BMAD file for EACH story via `io_ops.read_bmad_file`. After story 1 wrote its beads_id into the file's front matter via `_inject_beads_id`, story 2's re-read would see `beads_id: ISSUE-1` in the front matter and `_has_beads_id` would return True, causing story 2 (and all subsequent stories) to be incorrectly SKIPPED. In production with real file I/O, only the first story would ever be converted per file. Tests masked this because mocks returned constant values for `read_bmad_file`.
**Fix**: Restructured the orchestrator to read the file ONCE before the loop. File-level idempotency (`_has_beads_id`) is checked once on the initial content. If the file already has a beads_id, ALL stories are skipped (correct batch-level idempotency). The pre-read content is passed to `_process_single_story` as a parameter, eliminating per-story re-reads.

### ISSUE 2 (MEDIUM) -- Orphaned Beads issues on write failure

**File**: `adws/adw_modules/steps/convert_stories_orchestrator.py`, lines 213-220 (original)
**Problem**: When `write_bmad_file` failed after `run_beads_create` succeeded, the result dict returned `"beads_issue_id": None` and `"status": "failed"`. The Beads issue was already created (step 4 succeeded) but its ID was silently lost. This created an orphaned issue in Beads with no record in the conversion results.
**Fix**: Changed the write-failure result to preserve the issue_id: `"beads_issue_id": issue_id` with an error message that includes both the created issue ID and the write failure details: `"Issue created (ISSUE-1) but writeback failed: ..."`.

### ISSUE 3 (MEDIUM) -- Test gap masking real-world behavior

**File**: `adws/tests/adw_modules/steps/test_convert_stories_orchestrator.py` and `adws/tests/integration/test_convert_stories_flow.py`
**Problem**: The `test_idempotent_skip` test used `side_effect` on `read_bmad_file` to return different values per call (first call with beads_id, second without). This masked the real-world bug (ISSUE 1) because in production, all reads of the same file would return the same content (which changes after each write). The `test_mixed_results` integration test had the same flaw -- it assumed per-story file reads with different content.
**Fix**: Rewrote `test_idempotent_skip` to test file-level batch idempotency (all stories skipped when file has beads_id). Rewrote `test_mixed_results` to test mixed create/fail outcomes without relying on per-story file reads. Added `test_read_failure_returns_iofailure` to test the new file-level read failure path.

### ISSUE 4 (LOW) -- Silent type coercion in dispatch

**File**: `adws/adw_modules/commands/dispatch.py`, lines 141-143
**Problem**: `str(bmad_file_path)` and `str(workflow_name)` silently coerce non-string values. If `bmad_file_path` is explicitly set to `None` in inputs, `ctx.inputs.get("bmad_file_path", "")` returns `None` (not the default `""`), and `str(None)` becomes the string `"None"`, which would be treated as a valid file path.
**Fix**: Not applied (LOW severity). Downstream validation catches this at the step level.

### Quality Gates (post-fix)

- `pytest`: 1044 passed, 5 skipped (enemy), 100% line+branch coverage
- `mypy --strict`: Success, no issues in 113 source files
- `ruff check`: All checks passed

## Story

As an ADWS developer,
I want beads_id written back into source BMAD files and a command to orchestrate the full conversion,
so that planning artifacts stay linked to execution issues and I can convert stories with a single command.

## Acceptance Criteria

1. **Given** a Beads issue is created from a BMAD story, **When** the tracker processes the result, **Then** `beads_id` is written back into the source BMAD story file (FR27) **And** the original story content is preserved -- only the beads_id field is added.

2. **Given** the /convert-stories-to-beads command is invoked, **When** it executes, **Then** the command .md entry point delegates to the Python module (FR23) **And** the full flow runs: parse BMAD markdown -> create Beads issues -> embed workflow tags -> write beads_id back **And** progress is reported for each story processed.

3. **Given** a story already has a beads_id, **When** conversion runs on it, **Then** it skips the story (idempotent -- no duplicate issues created).

4. **Given** conversion of multiple stories, **When** one story fails to convert, **Then** the failure is reported but remaining stories continue processing **And** successfully converted stories have their beads_id written back.

5. **Given** all conversion code, **When** I run tests, **Then** tests cover: full conversion flow, beads_id writeback, idempotent skip, partial failure handling **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Define `write_bmad_file` io_ops function (AC: #1)
  - [ ] 1.1 RED: Write test for `io_ops.write_bmad_file(path: str, content: str) -> IOResult[None, PipelineError]`. Given a valid relative path and content string, mock `Path.write_text` (or test against tmp_path). Verify it returns `IOSuccess(None)`. The function resolves the path relative to the project root (same pattern as `read_bmad_file`).
  - [ ] 1.2 GREEN: Implement `write_bmad_file` in `adws/adw_modules/io_ops.py`. Validate path is non-empty. Resolve relative to project root via `_find_project_root()`. Write content via `Path.write_text()`. Return `IOSuccess(None)`.
  - [ ] 1.3 RED: Write test for `write_bmad_file` when path is empty string. Verify it returns `IOFailure(PipelineError)` with `error_type="ValueError"` and `step_name="io_ops.write_bmad_file"`.
  - [ ] 1.4 GREEN: Implement empty path validation -- return `IOFailure` with ValueError.
  - [ ] 1.5 RED: Write test for `write_bmad_file` when `Path.write_text` raises `PermissionError`. Verify it returns `IOFailure(PipelineError)` with `error_type="PermissionError"`.
  - [ ] 1.6 GREEN: Implement PermissionError handling.
  - [ ] 1.7 RED: Write test for `write_bmad_file` when `Path.write_text` raises `OSError`. Verify it returns `IOFailure(PipelineError)` with the exception type name as error_type.
  - [ ] 1.8 GREEN: Implement OSError handling.
  - [ ] 1.9 REFACTOR: Clean up, verify consistent pattern with `read_bmad_file`, verify mypy/ruff.

- [ ] Task 2: Define `_inject_beads_id` private helper (AC: #1)
  - [ ] 2.1 RED: Write test for `_inject_beads_id(markdown: str, beads_id: str) -> str`. Given a BMAD story markdown file content (with `---` front matter delimited YAML at top), verify it adds `beads_id: <value>` into the existing front matter block before the closing `---`. If no front matter exists, it prepends one containing `beads_id: <value>`.
  - [ ] 2.2 GREEN: Implement `_inject_beads_id` in `adws/adw_modules/steps/write_beads_id.py`. Parse the front matter block (between opening `---` and closing `\n---`). Insert `beads_id: <value>` line. Reconstruct the full content.
  - [ ] 2.3 RED: Write test for `_inject_beads_id` when the markdown has no front matter (`---` block). Verify it prepends `---\nbeads_id: ISSUE-42\n---\n` before the content, preserving the original content below.
  - [ ] 2.4 GREEN: Implement no-front-matter handling -- prepend a new front matter block.
  - [ ] 2.5 RED: Write test for `_inject_beads_id` when the front matter already contains a `beads_id:` line. Verify it replaces the existing `beads_id:` value (not duplicates it). This supports re-runs where the beads_id changed.
  - [ ] 2.6 GREEN: Implement existing beads_id replacement logic.
  - [ ] 2.7 RED: Write test for `_inject_beads_id` with multi-line front matter containing other fields (`status:`, `stepsCompleted:`, etc.). Verify only `beads_id:` is added/updated and all other fields are preserved exactly.
  - [ ] 2.8 GREEN: Ensure other front matter fields are preserved.
  - [ ] 2.9 RED: Write test for `_inject_beads_id` with empty string content. Verify it returns `---\nbeads_id: ISSUE-42\n---\n`.
  - [ ] 2.10 GREEN: Handle empty content case.
  - [ ] 2.11 REFACTOR: Clean up.

- [ ] Task 3: Define `_has_beads_id` private helper (AC: #3)
  - [ ] 3.1 RED: Write test for `_has_beads_id(markdown: str) -> bool`. Given markdown with front matter containing `beads_id: ISSUE-42`, verify it returns `True`.
  - [ ] 3.2 GREEN: Implement `_has_beads_id` in `adws/adw_modules/steps/write_beads_id.py`. Parse front matter and check for `beads_id:` line.
  - [ ] 3.3 RED: Write test for `_has_beads_id` when markdown has front matter but no `beads_id:` line. Verify it returns `False`.
  - [ ] 3.4 GREEN: Implement missing beads_id detection.
  - [ ] 3.5 RED: Write test for `_has_beads_id` when markdown has no front matter at all. Verify it returns `False`.
  - [ ] 3.6 GREEN: Implement no-front-matter case.
  - [ ] 3.7 RED: Write test for `_has_beads_id` with empty string. Verify it returns `False`.
  - [ ] 3.8 GREEN: Handle empty string.
  - [ ] 3.9 REFACTOR: Clean up.

- [ ] Task 4: Create `write_beads_id` step function (AC: #1, #3)
  - [ ] 4.1 RED: Write test for `write_beads_id(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `ctx.inputs` contains `"beads_issue_id"` set to `"ISSUE-42"`, `"current_story"` (BmadStory with `slug="6-1-bmad-markdown-parser"`), and `"bmad_file_path"` set to a BMAD file path, mock `io_ops.read_bmad_file` to return file content without beads_id, and mock `io_ops.write_bmad_file` to return `IOSuccess(None)`. Verify it returns `IOSuccess(WorkflowContext)` with outputs containing `"beads_id_written": True` and `"story_slug"`.
  - [ ] 4.2 GREEN: Implement `write_beads_id` step. Extract `beads_issue_id`, `current_story`, and `bmad_file_path` from `ctx.inputs`. Read the BMAD file via `io_ops.read_bmad_file`. Locate the story section in the file content (matching by story header pattern from `BmadStory`). Inject beads_id via `_inject_beads_id`. Write back via `io_ops.write_bmad_file`. Return `IOSuccess` with write confirmation in outputs.
  - [ ] 4.3 RED: Write test for `write_beads_id` when `beads_issue_id` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="write_beads_id"`.
  - [ ] 4.4 GREEN: Implement missing input validation for `beads_issue_id`.
  - [ ] 4.5 RED: Write test for `write_beads_id` when `current_story` is missing or not a `BmadStory`. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"`.
  - [ ] 4.6 GREEN: Implement missing input validation for `current_story`.
  - [ ] 4.7 RED: Write test for `write_beads_id` when `bmad_file_path` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"`.
  - [ ] 4.8 GREEN: Implement missing input validation for `bmad_file_path`.
  - [ ] 4.9 RED: Write test for `write_beads_id` when `io_ops.read_bmad_file` returns `IOFailure`. Verify the failure propagates through.
  - [ ] 4.10 GREEN: Implement read failure propagation.
  - [ ] 4.11 RED: Write test for `write_beads_id` when `io_ops.write_bmad_file` returns `IOFailure`. Verify the failure propagates through.
  - [ ] 4.12 GREEN: Implement write failure propagation.
  - [ ] 4.13 RED: Write test for idempotency: when the file content already contains `beads_id: ISSUE-42` in its front matter for this story (detected via `_has_beads_id`), verify the step returns `IOSuccess` with `"beads_id_written": False` and `"skipped_reason": "already_has_beads_id"` in outputs, and `io_ops.write_bmad_file` is NOT called.
  - [ ] 4.14 GREEN: Implement idempotency check using `_has_beads_id`.
  - [ ] 4.15 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 5: Create `convert_stories_orchestrator` step function (AC: #2, #3, #4)
  - [ ] 5.1 RED: Write test for `convert_stories_orchestrator(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `ctx.inputs` contains `"parsed_stories"` (list of 2 BmadStory objects), `"workflow_name"`, and `"bmad_file_path"`, mock `io_ops.run_beads_create` to return `IOSuccess("ISSUE-1")` then `IOSuccess("ISSUE-2")`, mock `io_ops.read_bmad_file` and `io_ops.write_bmad_file` to succeed. Verify it returns `IOSuccess(WorkflowContext)` with outputs containing `"conversion_results"` -- a list of dicts with `{"story_slug": ..., "beads_issue_id": ..., "status": "created"}` for each story.
  - [ ] 5.2 GREEN: Implement `convert_stories_orchestrator` in `adws/adw_modules/steps/convert_stories_orchestrator.py`. This step iterates over `parsed_stories`, calling `create_beads_issue` logic and `write_beads_id` logic for each story. It collects results and reports progress. It does NOT halt on individual story failure -- it continues to the next story (AC: #4).
  - [ ] 5.3 RED: Write test for idempotent skip (AC: #3). Given 2 stories where the first already has a `beads_id` in the file content (mocked via `io_ops.read_bmad_file`). Verify the first story is skipped (status `"skipped"`) and the second is processed normally.
  - [ ] 5.4 GREEN: Implement idempotency check before creating each issue.
  - [ ] 5.5 RED: Write test for partial failure (AC: #4). Given 3 stories where `io_ops.run_beads_create` returns `IOFailure` for the second story. Verify: first story succeeds, second story has status `"failed"` with error details, third story still processes and succeeds. The step itself returns `IOSuccess` (not IOFailure) because it handles individual failures internally.
  - [ ] 5.6 GREEN: Implement per-story error isolation with continue-on-failure.
  - [ ] 5.7 RED: Write test for all stories failing. Verify the step returns `IOSuccess(WorkflowContext)` with all statuses `"failed"` and a summary in outputs indicating no stories were successfully converted.
  - [ ] 5.8 GREEN: Implement all-fail handling.
  - [ ] 5.9 RED: Write test for empty `parsed_stories` list. Verify the step returns `IOSuccess(WorkflowContext)` with empty `conversion_results` and no io_ops calls.
  - [ ] 5.10 GREEN: Handle empty story list.
  - [ ] 5.11 RED: Write test for missing `parsed_stories` input. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"`.
  - [ ] 5.12 GREEN: Implement missing input validation.
  - [ ] 5.13 RED: Write test for missing `workflow_name` input. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"`.
  - [ ] 5.14 GREEN: Implement missing workflow_name validation.
  - [ ] 5.15 RED: Write test for progress tracking. Verify that `conversion_results` includes a `"total"`, `"created"`, `"skipped"`, and `"failed"` summary count.
  - [ ] 5.16 GREEN: Implement summary counters in output.
  - [ ] 5.17 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 6: Register steps in steps/__init__.py and engine step registry (AC: #5)
  - [ ] 6.1 RED: Write test that `write_beads_id` is importable from `adws.adw_modules.steps`. Verify it appears in `__all__`.
  - [ ] 6.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py` in the "Bridge steps (BMAD-to-Beads)" section.
  - [ ] 6.3 RED: Write test that `convert_stories_orchestrator` is importable from `adws.adw_modules.steps`. Verify it appears in `__all__`.
  - [ ] 6.4 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [ ] 6.5 RED: Write test that `_STEP_REGISTRY` in `adws/adw_modules/engine/executor.py` contains entries for `"write_beads_id"` and `"convert_stories_orchestrator"`.
  - [ ] 6.6 GREEN: Add entries to `_STEP_REGISTRY` in executor.py with corresponding imports.
  - [ ] 6.7 REFACTOR: Verify imports are consistent with the rest of the module.

- [ ] Task 7: Update `convert_stories_to_beads` workflow definition (AC: #2)
  - [ ] 7.1 RED: Write test that the `convert_stories_to_beads` workflow in `adws/workflows/__init__.py` includes all three steps in order: `"parse_bmad_story"`, `"convert_stories_orchestrator"`. Verify the workflow has exactly 2 steps (the orchestrator replaces `create_beads_issue` as a direct step and handles both issue creation and beads_id writeback internally per-story).
  - [ ] 7.2 GREEN: Update `_CONVERT_STORIES_TO_BEADS` in `adws/workflows/__init__.py`. Replace the current 2-step workflow (`parse_bmad_story`, `create_beads_issue`) with `parse_bmad_story` followed by `convert_stories_orchestrator`. The orchestrator handles per-story iteration internally: for each story it validates, creates the beads issue, and writes the beads_id back.
  - [ ] 7.3 REFACTOR: Verify workflow definition consistency.

- [ ] Task 8: Create `/convert-stories-to-beads` command entry point (AC: #2)
  - [ ] 8.1 RED: Write test for `run_convert_stories_command(bmad_file_path: str, workflow_name: str) -> IOResult[WorkflowContext, PipelineError]` in `adws/adw_modules/commands/convert_stories.py`. Given valid arguments, mock `io_ops.load_command_workflow` to return the `convert_stories_to_beads` workflow, mock `io_ops.execute_command_workflow` to return `IOSuccess(WorkflowContext)`. Verify it calls load then execute with correct inputs (`bmad_file_path` and `workflow_name` in context inputs).
  - [ ] 8.2 GREEN: Implement `run_convert_stories_command` in `adws/adw_modules/commands/convert_stories.py`. Build `WorkflowContext` with `inputs={"bmad_file_path": bmad_file_path, "workflow_name": workflow_name}`. Load the `convert_stories_to_beads` workflow. Execute it.
  - [ ] 8.3 RED: Write test for `run_convert_stories_command` when workflow load fails. Verify the failure propagates.
  - [ ] 8.4 GREEN: Implement workflow load error handling.
  - [ ] 8.5 RED: Write test for `run_convert_stories_command` when workflow execution fails. Verify the failure propagates.
  - [ ] 8.6 GREEN: Implement execution error handling.
  - [ ] 8.7 Create `.claude/commands/adws-convert-stories-to-beads.md` command file following the pattern from `adws-build.md`. The command delegates to `uv run python -m adws.adw_modules.commands.dispatch convert-stories-to-beads`.
  - [ ] 8.8 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 9: Edge case and integration tests (AC: #1, #3, #4, #5)
  - [ ] 9.1 RED: Write test for `_inject_beads_id` with content containing `---` within the body (not front matter). Verify only the actual front matter is modified and in-body `---` separators are preserved.
  - [ ] 9.2 GREEN: Ensure front matter detection is robust (matches `_strip_front_matter` logic from `parse_bmad_story.py`).
  - [ ] 9.3 RED: Write test for `write_beads_id` when `BmadStory.slug` contains special characters. Verify the writeback still works correctly.
  - [ ] 9.4 GREEN: Verify slug handling is robust.
  - [ ] 9.5 RED: Write integration test for the full convert flow: parse BMAD file (mocked read) -> iterate stories -> create issues (mocked bd create) -> write back beads_ids (mocked write) -> verify final outputs have complete conversion results.
  - [ ] 9.6 GREEN: Ensure full flow integration works.
  - [ ] 9.7 RED: Write integration test for idempotent re-run: second execution with beads_ids already present skips all stories.
  - [ ] 9.8 GREEN: Ensure idempotency across full flow.
  - [ ] 9.9 RED: Write integration test for mixed results: 3 stories where 1 already has beads_id (skipped), 1 succeeds, 1 fails. Verify conversion_results accurately reflects all three statuses.
  - [ ] 9.10 GREEN: Ensure mixed result handling.
  - [ ] 9.11 REFACTOR: Clean up integration tests.

- [ ] Task 10: Verify full integration and quality gates (AC: #6)
  - [ ] 10.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 10.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 10.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 6.2)

**io_ops.py** has 27 public functions + 4 private helpers + 1 async helper + 1 internal exception + 1 sanitizer. Key functions already established:
```python
def read_bmad_file(path: str) -> IOResult[str, PipelineError]: ...
def run_beads_create(title: str, description: str) -> IOResult[str, PipelineError]: ...
def run_beads_show(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
def load_command_workflow(workflow_name: str) -> IOResult[Workflow, PipelineError]: ...
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
```

**Missing io_ops function**: `write_bmad_file` -- needed for writing beads_id back to BMAD story files. This is the counterpart to `read_bmad_file`. Pattern follows `read_bmad_file`: validate non-empty path, resolve relative to project root, write content, handle exceptions.

**types.py** has `BmadStory` and `BmadEpic` frozen dataclasses (from Story 6.1):
```python
@dataclass(frozen=True)
class BmadStory:
    epic_number: int
    story_number: int
    title: str
    slug: str
    user_story: str
    acceptance_criteria: str
    frs_covered: list[str] = field(default_factory=list)
    raw_content: str = ""

@dataclass(frozen=True)
class BmadEpic:
    epic_number: int
    title: str
    description: str
    frs_covered: list[str] = field(default_factory=list)
    stories: list[BmadStory] = field(default_factory=list)
```

**steps/__init__.py** exports 21 steps including `parse_bmad_story` and `create_beads_issue`.

**engine/executor.py** `_STEP_REGISTRY` has 18 entries including `parse_bmad_story` and `create_beads_issue`.

**workflows/__init__.py** has 5 registered workflows. `_CONVERT_STORIES_TO_BEADS` currently has 2 steps:
```python
_CONVERT_STORIES_TO_BEADS = Workflow(
    name=WorkflowName.CONVERT_STORIES_TO_BEADS,
    description="Convert BMAD stories to Beads issues with workflow tags",
    dispatchable=False,
    steps=[
        Step(name="parse_bmad_story", function="parse_bmad_story"),
        Step(name="create_beads_issue", function="create_beads_issue"),
    ],
)
```

**WorkflowName** registry constants:
```python
class WorkflowName:
    IMPLEMENT_CLOSE = "implement_close"
    IMPLEMENT_VERIFY_CLOSE = "implement_verify_close"
    CONVERT_STORIES_TO_BEADS = "convert_stories_to_beads"
    SAMPLE = "sample"
    VERIFY = "verify"
```

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 989 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 106 files tracked by mypy.

**Command pattern**: `.claude/commands/adws-<name>.md` delegates to `adws.adw_modules.commands.<name>`. See `adws-build.md` and `adws/adw_modules/commands/build.py` for the established pattern.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: Story 6.3 Architecture

This story completes Epic 6 by adding three capabilities:

1. **Bidirectional tracking**: `write_beads_id` step writes `beads_id` back into BMAD story files
2. **Multi-story orchestration**: `convert_stories_orchestrator` step iterates over parsed stories, creating issues and writing beads_ids with per-story error isolation
3. **Command entry point**: `/convert-stories-to-beads` command wires the full flow

```
Architecture: convert_stories_to_beads workflow

┌──────────────────────────────────────────────────────┐
│  /convert-stories-to-beads command                    │
│  .claude/commands/adws-convert-stories-to-beads.md   │
│  -> adws/adw_modules/commands/convert_stories.py     │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  convert_stories_to_beads workflow                    │
│  adws/workflows/__init__.py                          │
│  Steps: [parse_bmad_story, convert_stories_orch.]    │
└──────────────────┬───────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌────────────────┐   ┌─────────────────────────────────┐
│ parse_bmad_    │   │ convert_stories_orchestrator     │
│ story          │   │ (iterates parsed_stories)        │
│ (from 6.1)     │   │   For each story:                │
│                │   │     1. Check idempotency          │
│ Outputs:       │   │     2. Validate & embed tag       │
│  parsed_epics  │   │     3. run_beads_create           │
│  parsed_stories│   │     4. write beads_id back        │
└────────────────┘   │   Continue on individual failure  │
                     └─────────────────────────────────┘
```

### Design: Why an Orchestrator Step (not 3 workflow steps)

The engine's `promote_outputs_to_inputs` mechanism promotes ALL outputs from step N as inputs to step N+1. For multi-story conversion, this creates a problem: the workflow processes one story at a time through `create_beads_issue` -> `write_beads_id`, but the engine does not support per-item iteration within a workflow.

The solution: a single `convert_stories_orchestrator` step that internally iterates over the `parsed_stories` list, calling `create_beads_issue` logic and `write_beads_id` logic for each story. This step:

- Receives `parsed_stories` (from `parse_bmad_story` via promote_outputs_to_inputs)
- Iterates per-story, isolating failures (AC: #4)
- Checks idempotency per-story (AC: #3)
- Accumulates results into `conversion_results`
- Returns `IOSuccess` even when individual stories fail (continue-on-failure)

This is architecturally consistent: the orchestrator is a step that happens to call io_ops functions multiple times. It does NOT call other steps directly (steps never import steps). It uses the same io_ops functions (`run_beads_create`, `read_bmad_file`, `write_bmad_file`) and the same validation helpers (`_validate_workflow_name`, `_embed_workflow_tag` from `create_beads_issue`).

### Design: New io_ops Function

One new io_ops function is needed:

**`write_bmad_file(path: str, content: str) -> IOResult[None, PipelineError]`**
- Validates path is non-empty (follows `read_bmad_file` pattern)
- Resolves path relative to project root via `_find_project_root()`
- Writes content via `Path.write_text()`
- Returns `IOSuccess(None)` on success
- Returns `IOFailure(PipelineError)` with `error_type="ValueError"` for empty path
- Returns `IOFailure(PipelineError)` with appropriate error_type for `PermissionError`, `OSError`
- Step name: `"io_ops.write_bmad_file"`

This brings io_ops to ~28 public functions. Still under the split threshold.

### Design: beads_id Injection Format

The `_inject_beads_id` helper modifies BMAD story files to add/update a `beads_id` field in the YAML front matter:

**Before (no front matter):**
```markdown
#### Story 6.1: BMAD Markdown Parser
...story content...
```

**After:**
```markdown
---
beads_id: ISSUE-42
---

#### Story 6.1: BMAD Markdown Parser
...story content...
```

**Before (existing front matter without beads_id):**
```markdown
---
status: ready-for-dev
---

#### Story 6.1: BMAD Markdown Parser
...story content...
```

**After:**
```markdown
---
status: ready-for-dev
beads_id: ISSUE-42
---

#### Story 6.1: BMAD Markdown Parser
...story content...
```

**Before (existing front matter WITH beads_id):**
```markdown
---
status: ready-for-dev
beads_id: OLD-ID
---

#### Story 6.1: BMAD Markdown Parser
...story content...
```

**After (replaced):**
```markdown
---
status: ready-for-dev
beads_id: ISSUE-42
---

#### Story 6.1: BMAD Markdown Parser
...story content...
```

The implementation MUST be consistent with the `_strip_front_matter` logic in `parse_bmad_story.py`: front matter starts with `---` at position 0 and ends with `\n---` on its own line.

### Design: Idempotency Strategy

Idempotency (AC: #3) is checked at two levels:

1. **File level** (`_has_beads_id`): Checks if the BMAD story file already contains a `beads_id:` line in its front matter. If yes, the story is skipped entirely.
2. **Orchestrator level**: Before calling `run_beads_create`, the orchestrator reads the story's BMAD file content and checks `_has_beads_id`. If the story already has a beads_id, it records status `"skipped"` and moves to the next story.

Note: The `write_beads_id` step ALSO has idempotency checking (Task 4.13-4.14). This provides defense-in-depth if the step is ever called outside the orchestrator context.

### Design: Conversion Results Format

The `convert_stories_orchestrator` outputs structured results:

```python
{
    "conversion_results": [
        {
            "story_slug": "6-1-bmad-markdown-parser",
            "beads_issue_id": "ISSUE-1",
            "status": "created",
        },
        {
            "story_slug": "6-2-beads-issue-creator",
            "beads_issue_id": None,
            "status": "skipped",
            "reason": "already_has_beads_id",
        },
        {
            "story_slug": "6-3-bidirectional-tracking",
            "beads_issue_id": None,
            "status": "failed",
            "error": "bd create failed: ...",
        },
    ],
    "summary": {
        "total": 3,
        "created": 1,
        "skipped": 1,
        "failed": 1,
    },
}
```

### Design: Orchestrator Internal Logic

The `convert_stories_orchestrator` step calls io_ops functions directly (through the io_ops boundary) rather than calling other step functions. This preserves the architecture rule that steps never import other steps:

```python
# convert_stories_orchestrator.py (pseudocode)
# For each story in parsed_stories:
#   1. Read BMAD file content -> check _has_beads_id -> skip if present
#   2. Validate workflow name (from _validate_workflow_name logic)
#   3. Embed tag (from _embed_workflow_tag logic)
#   4. io_ops.run_beads_create(title, description) -> get issue_id
#   5. _inject_beads_id(file_content, issue_id)
#   6. io_ops.write_bmad_file(path, updated_content)
#   7. Record result (created/skipped/failed)
```

The helper functions `_validate_workflow_name` and `_embed_workflow_tag` from `create_beads_issue.py` should be either:
- Extracted to a shared private module if they are needed by both steps, OR
- Re-implemented as private helpers in the orchestrator (if minimal)

The recommended approach: the orchestrator imports and uses the `_embed_workflow_tag` and `_validate_workflow_name` from `create_beads_issue` as they are internal implementation details shared within the bridge steps. Alternatively, extract to `adws/adw_modules/steps/_beads_helpers.py` private module. The implementer should choose based on which results in cleaner imports and better testability.

### Design: Command Entry Point

The command follows the established pattern from Story 4.1:

```
.claude/commands/adws-convert-stories-to-beads.md
    -> delegates to Python module
adws/adw_modules/commands/convert_stories.py
    -> run_convert_stories_command(bmad_file_path, workflow_name)
        -> io_ops.load_command_workflow("convert_stories_to_beads")
        -> io_ops.execute_command_workflow(workflow, ctx)
```

The command accepts:
- `bmad_file_path`: Path to the BMAD epics markdown file (relative to project root)
- `workflow_name`: Default workflow to embed in tags (default: `"implement_verify_close"`)

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_write_beads_id.py` -- tests for `write_beads_id`, `_inject_beads_id`, `_has_beads_id`
- `adws/tests/adw_modules/steps/test_convert_stories_orchestrator.py` -- tests for orchestrator iteration, idempotency, partial failure
- `adws/tests/adw_modules/commands/test_convert_stories.py` -- tests for command entry point
- `adws/tests/integration/test_convert_stories_flow.py` -- full flow integration tests

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `write_bmad_file` tests
- `adws/tests/adw_modules/steps/test_steps_init.py` (if exists) -- verify new exports
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entries
- `adws/tests/workflows/test_workflows.py` (or equivalent) -- verify `convert_stories_to_beads` workflow update

**Mock targets**:
- `adws.adw_modules.io_ops.read_bmad_file` -- mock in step and orchestrator tests
- `adws.adw_modules.io_ops.write_bmad_file` -- mock in step and orchestrator tests
- `adws.adw_modules.io_ops.run_beads_create` -- mock in orchestrator tests
- `adws.adw_modules.io_ops.load_command_workflow` -- mock in command tests
- `adws.adw_modules.io_ops.execute_command_workflow` -- mock in command tests
- No SDK mocking needed -- this story is file I/O and Beads CLI only

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.

### Architecture Compliance

- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `write_bmad_file` is the new io_ops function; `read_bmad_file` and `run_beads_create` already exist. No direct file writes or subprocess calls in step logic.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads via bd CLI only. `run_beads_create` uses `bd create` through `run_shell_command`.
- **NFR19**: BMAD files are READ and WRITTEN in this story, but ONLY during the conversion workflow (not during execution workflows like `implement_verify_close`). This is explicitly allowed per architecture: "read_bmad_story() and write_beads_id_to_bmad() are called exclusively by steps in convert_stories_to_beads."
- **FR23**: `/convert-stories-to-beads` command entry point.
- **FR24**: Parse BMAD epic/story markdown (from Story 6.1, consumed here).
- **FR25**: Create Beads issues with story content (from Story 6.2, used by orchestrator).
- **FR26**: Embed workflow_name tag (from Story 6.2, used by orchestrator).
- **FR27**: Write beads_id back to BMAD story file -- NEW this story.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT interact with the Claude SDK -- this story is file I/O and Beads CLI only.
- Do NOT change `BmadStory` or `BmadEpic` dataclasses -- they are defined and complete from Story 6.1.
- Do NOT change the `parse_bmad_story` step -- it is complete from Story 6.1.
- Do NOT change the `create_beads_issue` step logic -- it is complete from Story 6.2. However, the orchestrator may import its private helpers (`_embed_workflow_tag`, `_validate_workflow_name`) or re-implement them.
- Do NOT create CLI hooks or SDK HookMatchers. This is not a hook -- these are pipeline steps.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in the step modules.
- Do NOT modify existing io_ops functions (only add the new `write_bmad_file`).
- Do NOT modify the engine executor logic. Only add new registry entries.
- Do NOT make the workflow dispatchable -- `convert_stories_to_beads` is manually invoked via command, not triggered by Beads issue tags (per architecture Decision 5).

### Relationship to Adjacent Stories

- **Story 6.1** (predecessor): BMAD markdown parser -- produces `BmadStory` and `BmadEpic` objects. The `parse_bmad_story` step is the first step in the workflow and its outputs (`parsed_stories`, `parsed_epics`) flow into the orchestrator.
- **Story 6.2** (predecessor): Beads issue creator -- the `create_beads_issue` step and its helpers (`_embed_workflow_tag`, `_validate_workflow_name`) provide the issue creation logic. The orchestrator reuses this logic (either by importing helpers or re-implementing).
- **Epic 7** (downstream): Story 7.1 (Issue Tag Extraction & Workflow Dispatch) will extract the `{workflow_name}` tag embedded by the conversion workflow from Beads issue descriptions to dispatch the correct workflow.
- **This story completes Epic 6**: After this story, all Epic 6 FRs (FR23-FR27) are satisfied.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (BMAD-to-Beads Bridge section):**
> **BMAD-to-Beads Bridge (FR23-27)** | `adws/adw_modules/steps/parse_bmad_story.py`, `create_beads_issue.py`, `write_beads_id.py` | `adws/workflows/convert_stories_to_beads.py`

**Architecture Step Naming:**
> `write_beads_id.py` (imperative form, function matches filename)

**Architecture Workflow Composition:**
> `convert_stories_to_beads.py` | `parse_bmad_story` -> `create_beads_issue` -> `write_beads_id` (all step modules)

Note: The architecture lists 3 separate step modules. The implementation adapts this by introducing a `convert_stories_orchestrator` that handles the per-story iteration (create_beads_issue + write_beads_id combined) because the engine does not support per-item iteration. The `write_beads_id` step module still exists for its core writeback logic and testability, but the orchestrator drives the multi-story loop.

**Architecture Integration Points:**
> ADWS -> BMAD files | File read/write | Bidirectional* | `read_bmad_story()`*, `write_beads_id_to_bmad()`*
> * Conversion workflow only.

**Architecture Command Inventory:**
> `/convert-stories-to-beads` | P2 | Bridge steps (parse/create/write) | Convert BMAD stories to Beads issues

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/write_beads_id.py` -- `write_beads_id()`, `_inject_beads_id()`, `_has_beads_id()`
- `adws/adw_modules/steps/convert_stories_orchestrator.py` -- `convert_stories_orchestrator()`
- `adws/adw_modules/commands/convert_stories.py` -- `run_convert_stories_command()`
- `.claude/commands/adws-convert-stories-to-beads.md` -- command entry point
- `adws/tests/adw_modules/steps/test_write_beads_id.py` -- write_beads_id tests
- `adws/tests/adw_modules/steps/test_convert_stories_orchestrator.py` -- orchestrator tests
- `adws/tests/adw_modules/commands/test_convert_stories.py` -- command tests
- `adws/tests/integration/test_convert_stories_flow.py` -- integration tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `write_bmad_file()` function in the "Prime command / BMAD" section
- `adws/adw_modules/steps/__init__.py` -- add `write_beads_id` and `convert_stories_orchestrator` imports/exports
- `adws/adw_modules/engine/executor.py` -- add `write_beads_id` and `convert_stories_orchestrator` to `_STEP_REGISTRY`
- `adws/workflows/__init__.py` -- update `_CONVERT_STORIES_TO_BEADS` workflow steps
- `adws/tests/adw_modules/test_io_ops.py` -- add `write_bmad_file` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entries

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 6] -- Epic summary: "BMAD-to-Beads Story Converter"
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `write_beads_id.py` in `adws/adw_modules/steps/`, workflow composition
- [Source: _bmad-output/planning-artifacts/architecture.md#Testing Strategy Notes] -- Step I/O density classification
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form, function matches filename
- [Source: _bmad-output/planning-artifacts/architecture.md#Step Internal Structure] -- Step pattern with one public function per module
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist (6 mandatory items)
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR23-FR27 map to Epic 6
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- ADWS -> BMAD files (bidirectional, conversion only)
- [Source: _bmad-output/planning-artifacts/architecture.md#One-Directional System Flow] -- BMAD -> Beads -> ADWS flow
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Discovery and Dispatch] -- convert_stories_to_beads is NOT a dispatch target
- [Source: adws/adw_modules/io_ops.py] -- 27 public functions, read_bmad_file pattern, run_beads_create, _find_project_root
- [Source: adws/adw_modules/types.py] -- BmadStory, BmadEpic, WorkflowContext frozen dataclasses
- [Source: adws/adw_modules/steps/create_beads_issue.py] -- _embed_workflow_tag, _validate_workflow_name (reusable helpers)
- [Source: adws/adw_modules/steps/parse_bmad_story.py] -- _strip_front_matter (reference for front matter handling)
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (18 entries to extend), promote_outputs_to_inputs flow
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, _CONVERT_STORIES_TO_BEADS (2 steps to update)
- [Source: adws/adw_modules/commands/build.py] -- command pattern reference
- [Source: .claude/commands/adws-build.md] -- command .md entry point reference
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/6-2-beads-issue-creator-with-workflow-tags.md] -- predecessor story, code review results

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

From Story 6.2 learnings:
- **989 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **106 source files**: Current file count tracked by mypy.
- **io_ops at 27 public functions**: This story adds 1 new io_ops function (`write_bmad_file`) bringing total to 28.
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Step creation checklist**: errors.py -> io_ops.py -> step -> __init__.py -> tests -> verify. This story does NOT add new error types to errors.py (it uses existing `PipelineError` with different `error_type` strings).
- **Frozen dataclasses**: All data models must be frozen. BmadStory, BmadEpic, WorkflowContext are already defined and frozen.
- **Code review finding from 6.2**: `current_story` re-output caused ContextCollisionError. This story's orchestrator MUST NOT re-output keys that already exist in inputs.
- **shlex.quote pattern**: All Beads CLI functions use `shlex.quote()` to escape user-provided arguments. The orchestrator delegates to existing io_ops functions that already handle this.
- **bind() pattern**: Existing io_ops functions use `.bind()` to chain operations. Follow this pattern for the new `write_bmad_file` function.
- **_has_beads_id front matter detection**: Must be consistent with `_strip_front_matter` in `parse_bmad_story.py` -- front matter starts with `---` at position 0 and closing `---` appears after `\n---` on its own line.

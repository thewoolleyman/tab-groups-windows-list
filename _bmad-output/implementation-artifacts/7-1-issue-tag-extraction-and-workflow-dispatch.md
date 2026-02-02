# Story 7.1: Issue Tag Extraction & Workflow Dispatch

Status: ready-for-dev

## Story

As an ADWS developer,
I want the engine to extract workflow tags from Beads issues and dispatch the correct workflow,
so that issues are automatically routed to the right execution pipeline.

## Acceptance Criteria

1. **Given** a Beads issue ID, **When** the engine receives it, **Then** it reads the issue description via `bd show` through io_ops (NFR17 -- Beads via bd CLI only) (FR18) **And** it extracts the `{workflow_name}` tag from the description.

2. **Given** an extracted workflow tag, **When** `load_workflow()` performs lookup, **Then** it returns the matching Workflow definition as pure data (Decision 5) **And** `adw_dispatch.py` enforces the `dispatchable` flag policy (FR19).

3. **Given** a non-dispatchable workflow tag, **When** dispatch policy is evaluated, **Then** the dispatch is rejected with a clear PipelineError explaining the workflow is not dispatchable.

4. **Given** a workflow tag that doesn't match any registered workflow, **When** lookup is performed, **Then** a PipelineError propagates with the unknown tag and available workflow names.

5. **Given** the engine processes a Beads issue, **When** executing the dispatch, **Then** it never reads BMAD files directly -- the Beads issue description is the only contract (NFR19).

6. **Given** all dispatch code, **When** I run tests, **Then** tests cover: successful extraction and dispatch, non-dispatchable rejection, unknown tag, missing tag in description **And** 100% coverage is maintained (NFR9).

7. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Create `extract_workflow_tag` pure function (AC: #1)
  - [ ] 1.1 RED: Write test for `extract_workflow_tag(description: str) -> Result[str, PipelineError]` in `adws/adw_modules/steps/extract_workflow_tag.py`. Given a Beads issue description containing `{implement_verify_close}` tag, verify it returns `Success("implement_verify_close")`. The function uses regex to find `{workflow_name}` patterns (matching the format embedded by `_embed_workflow_tag` in `create_beads_issue.py`).
  - [ ] 1.2 GREEN: Implement `extract_workflow_tag` as a pure function (returns `Result`, not `IOResult` -- no I/O). Use regex pattern `r"\{(\w+)\}"` to find the workflow tag. Return `Success(tag_name)` for the first match.
  - [ ] 1.3 RED: Write test for `extract_workflow_tag` when description contains no `{...}` tag. Verify it returns `Failure(PipelineError)` with `error_type="MissingWorkflowTagError"` and `step_name="extract_workflow_tag"`, with the description snippet in context.
  - [ ] 1.4 GREEN: Implement missing tag detection -- return `Failure` with clear error message including "No workflow tag found".
  - [ ] 1.5 RED: Write test for `extract_workflow_tag` when description contains multiple `{...}` tags (e.g., `{implement_verify_close}` and `{sample}`). Verify it returns `Success` with the FIRST tag found (consistent behavior).
  - [ ] 1.6 GREEN: Ensure regex returns first match only.
  - [ ] 1.7 RED: Write test for `extract_workflow_tag` with empty string description. Verify it returns `Failure(PipelineError)` with `error_type="MissingWorkflowTagError"`.
  - [ ] 1.8 GREEN: Handle empty description.
  - [ ] 1.9 RED: Write test for `extract_workflow_tag` when description contains `{...}` with non-word characters (e.g., `{invalid-name}` with hyphen, or `{has spaces}`). Verify these do NOT match (only `\w+` patterns match -- alphanumeric and underscore).
  - [ ] 1.10 GREEN: Ensure regex only matches valid workflow name characters (`\w+`).
  - [ ] 1.11 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 2: Create `extract_and_validate_tag` step function (AC: #1, #2, #4)
  - [ ] 2.1 RED: Write test for `extract_and_validate_tag(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `ctx.inputs` contains `"issue_description"` with a description containing `{implement_verify_close}` tag, verify it returns `IOSuccess(WorkflowContext)` with outputs containing `"workflow_tag": "implement_verify_close"` and `"workflow": <Workflow object>`. Mock nothing -- `load_workflow` is a pure lookup on the registry.
  - [ ] 2.2 GREEN: Implement `extract_and_validate_tag` step in `adws/adw_modules/steps/extract_workflow_tag.py`. Extract `issue_description` from `ctx.inputs`. Call `extract_workflow_tag()` on it. If successful, call `load_workflow(tag)` from `adws.workflows` to resolve the Workflow. Return `IOSuccess` with `workflow_tag` and `workflow` in outputs.
  - [ ] 2.3 RED: Write test for `extract_and_validate_tag` when `issue_description` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="extract_and_validate_tag"`.
  - [ ] 2.4 GREEN: Implement missing input validation.
  - [ ] 2.5 RED: Write test for `extract_and_validate_tag` when the extracted tag does not match any registered workflow (e.g., `{nonexistent_workflow}`). Verify it returns `IOFailure(PipelineError)` with `error_type="UnknownWorkflowTagError"` and context containing `"tag"` and `"available_workflows"` (list of registered workflow names).
  - [ ] 2.6 GREEN: Implement unknown workflow tag detection. When `load_workflow(tag)` returns `None`, build a `PipelineError` with available workflow names from `list_workflows()`.
  - [ ] 2.7 RED: Write test for `extract_and_validate_tag` when the description has no tag. Verify the `Failure` from `extract_workflow_tag()` is propagated as `IOFailure`.
  - [ ] 2.8 GREEN: Convert the `Result` failure from `extract_workflow_tag()` into an `IOFailure` for the step return.
  - [ ] 2.9 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 3: Create `read_issue_description` io_ops function (AC: #1, #5)
  - [ ] 3.1 RED: Write test for `io_ops.read_issue_description(issue_id: str) -> IOResult[str, PipelineError]`. Mock `io_ops.run_beads_show` to return `IOSuccess("issue description text")`. Verify it returns `IOSuccess("issue description text")`. This is a thin wrapper that delegates to `run_beads_show` and is the explicit entry point for reading issue descriptions in the dispatch flow.
  - [ ] 3.2 GREEN: Implement `read_issue_description` in `io_ops.py`. This function delegates to `run_beads_show(issue_id)` and returns the result directly. It exists to provide a semantically clear io_ops boundary function for the dispatch flow (vs. the generic `run_beads_show`).
  - [ ] 3.3 RED: Write test for `read_issue_description` when `issue_id` is empty string. Verify it returns `IOFailure(PipelineError)` with `error_type="ValueError"` and `step_name="io_ops.read_issue_description"`.
  - [ ] 3.4 GREEN: Implement empty issue_id validation.
  - [ ] 3.5 RED: Write test for `read_issue_description` when `run_beads_show` returns `IOFailure`. Verify the failure propagates through.
  - [ ] 3.6 GREEN: Ensure failure propagation via `.bind()` or direct delegation.
  - [ ] 3.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 4: Create `read_and_extract` step function (AC: #1, #5)
  - [ ] 4.1 RED: Write test for `read_and_extract(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `ctx.inputs` contains `"issue_id"` set to `"ISSUE-42"`, mock `io_ops.read_issue_description` to return `IOSuccess("Story content\n\n{implement_verify_close}")`. Verify it returns `IOSuccess(WorkflowContext)` with outputs containing `"issue_description"`, `"workflow_tag": "implement_verify_close"`, and `"workflow": <Workflow object>`.
  - [ ] 4.2 GREEN: Implement `read_and_extract` in `adws/adw_modules/steps/read_and_extract.py`. Extract `issue_id` from `ctx.inputs`. Call `io_ops.read_issue_description(issue_id)`. On success, call `extract_workflow_tag()` on the description. If tag extraction succeeds, call `load_workflow(tag)`. Return `IOSuccess` with `issue_description`, `workflow_tag`, and `workflow` in outputs.
  - [ ] 4.3 RED: Write test for `read_and_extract` when `issue_id` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="read_and_extract"`.
  - [ ] 4.4 GREEN: Implement missing input validation.
  - [ ] 4.5 RED: Write test for `read_and_extract` when `io_ops.read_issue_description` returns `IOFailure` (bd show fails). Verify the failure propagates through.
  - [ ] 4.6 GREEN: Implement io_ops failure propagation.
  - [ ] 4.7 RED: Write test for `read_and_extract` when the issue description has no workflow tag. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingWorkflowTagError"`.
  - [ ] 4.8 GREEN: Propagate the tag extraction failure.
  - [ ] 4.9 RED: Write test for `read_and_extract` when the extracted tag does not match any registered workflow. Verify it returns `IOFailure(PipelineError)` with `error_type="UnknownWorkflowTagError"`.
  - [ ] 4.10 GREEN: Propagate unknown workflow failure from validation.
  - [ ] 4.11 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 5: Create `adw_dispatch` module with policy enforcement (AC: #2, #3)
  - [ ] 5.1 RED: Write test for `dispatch_workflow(issue_id: str) -> IOResult[WorkflowContext, PipelineError]` in `adws/adw_dispatch.py`. Given `issue_id="ISSUE-42"`, mock `io_ops.read_issue_description` to return a description with `{implement_verify_close}` tag. Verify it returns `IOSuccess(WorkflowContext)` with `workflow_tag` and `issue_description` in the context. The function reads the issue, extracts the tag, validates the workflow exists AND is dispatchable (Decision 5), and returns the prepared context.
  - [ ] 5.2 GREEN: Implement `dispatch_workflow` in `adws/adw_dispatch.py`. Call `io_ops.read_issue_description(issue_id)`. Extract the workflow tag via `extract_workflow_tag()`. Look up the workflow via `load_workflow()`. Enforce `dispatchable` policy: if `workflow.dispatchable` is `False`, return `IOFailure`. Build and return `WorkflowContext` with `issue_id`, `issue_description`, `workflow_tag`, and `workflow` in inputs.
  - [ ] 5.3 RED: Write test for `dispatch_workflow` when the workflow tag matches a non-dispatchable workflow (e.g., `{convert_stories_to_beads}` which has `dispatchable=False`). Verify it returns `IOFailure(PipelineError)` with `error_type="NonDispatchableError"` and `step_name="adw_dispatch"`. The message should include the workflow name and explain that it is not dispatchable.
  - [ ] 5.4 GREEN: Implement `dispatchable` flag check after successful `load_workflow()`. Return clear `PipelineError` explaining the workflow is not dispatchable.
  - [ ] 5.5 RED: Write test for `dispatch_workflow` when the workflow tag does not match any registered workflow. Verify it returns `IOFailure(PipelineError)` with `error_type="UnknownWorkflowTagError"` and context containing `"tag"` and `"available_workflows"`.
  - [ ] 5.6 GREEN: Implement unknown workflow tag handling.
  - [ ] 5.7 RED: Write test for `dispatch_workflow` when the issue description has no workflow tag. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingWorkflowTagError"`.
  - [ ] 5.8 GREEN: Propagate missing tag failure.
  - [ ] 5.9 RED: Write test for `dispatch_workflow` when `io_ops.read_issue_description` fails (bd show fails). Verify the failure propagates.
  - [ ] 5.10 GREEN: Propagate io_ops failure.
  - [ ] 5.11 RED: Write test for `dispatch_workflow` with empty `issue_id`. Verify it returns `IOFailure(PipelineError)` with `error_type="ValueError"`.
  - [ ] 5.12 GREEN: Implement empty issue_id validation.
  - [ ] 5.13 RED: Write test confirming that `dispatch_workflow` never reads BMAD files (NFR19). Mock `io_ops.read_bmad_file` and verify it is NOT called during dispatch. The only data source is the Beads issue description.
  - [ ] 5.14 GREEN: Confirm the implementation does not import or call any BMAD-related io_ops functions.
  - [ ] 5.15 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 6: Register new steps in steps/__init__.py and engine step registry (AC: #6)
  - [ ] 6.1 RED: Write test that `extract_and_validate_tag` is importable from `adws.adw_modules.steps`. Verify it appears in `__all__`.
  - [ ] 6.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py` in a new "Dispatch steps" section.
  - [ ] 6.3 RED: Write test that `read_and_extract` is importable from `adws.adw_modules.steps`. Verify it appears in `__all__`.
  - [ ] 6.4 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py` in the "Dispatch steps" section.
  - [ ] 6.5 RED: Write test that `_STEP_REGISTRY` in `adws/adw_modules/engine/executor.py` contains entries for `"extract_and_validate_tag"` and `"read_and_extract"`.
  - [ ] 6.6 GREEN: Add entries to `_STEP_REGISTRY` in executor.py with corresponding imports.
  - [ ] 6.7 REFACTOR: Verify imports are consistent with the rest of the module.

- [ ] Task 7: Add `WorkflowName.DISPATCH` constant (if needed) and `list_dispatchable_workflows` helper
  - [ ] 7.1 RED: Write test for `list_dispatchable_workflows() -> list[str]` that returns only the names of dispatchable workflows. Verify that `implement_close` and `implement_verify_close` are included, but `convert_stories_to_beads`, `sample`, and `verify` are not.
  - [ ] 7.2 GREEN: Implement `list_dispatchable_workflows` in `adws/workflows/__init__.py`. Uses `list_workflows(dispatchable_only=True)` and returns a sorted list of workflow names. This provides a clean helper for error messages in the dispatch module.
  - [ ] 7.3 REFACTOR: Clean up.

- [ ] Task 8: Integration tests for full dispatch flow (AC: #1, #2, #3, #4, #5, #6)
  - [ ] 8.1 RED: Write integration test for successful dispatch: Given a Beads issue with `{implement_verify_close}` tag, mock `io_ops.read_issue_description` to return the description. Call `dispatch_workflow("ISSUE-42")`. Verify the returned `WorkflowContext` contains `issue_id`, `issue_description`, `workflow_tag`, and `workflow` with correct values.
  - [ ] 8.2 GREEN: Ensure full dispatch flow works end-to-end.
  - [ ] 8.3 RED: Write integration test for dispatch rejection of non-dispatchable workflow: Given a description with `{convert_stories_to_beads}` tag. Verify `dispatch_workflow` returns `IOFailure` with `NonDispatchableError`.
  - [ ] 8.4 GREEN: Ensure non-dispatchable rejection works.
  - [ ] 8.5 RED: Write integration test for dispatch with unknown tag: Given a description with `{totally_unknown}` tag. Verify `dispatch_workflow` returns `IOFailure` with `UnknownWorkflowTagError` and available workflow names in context.
  - [ ] 8.6 GREEN: Ensure unknown tag handling works.
  - [ ] 8.7 RED: Write integration test for dispatch with no tag: Given a description with no `{...}` tag at all. Verify `dispatch_workflow` returns `IOFailure` with `MissingWorkflowTagError`.
  - [ ] 8.8 GREEN: Ensure missing tag handling works.
  - [ ] 8.9 RED: Write integration test verifying NFR19 compliance: `dispatch_workflow` does NOT call `io_ops.read_bmad_file` at any point.
  - [ ] 8.10 GREEN: Confirm NFR19 compliance in integration.
  - [ ] 8.11 REFACTOR: Clean up integration tests.

- [ ] Task 9: Verify full integration and quality gates (AC: #7)
  - [ ] 9.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 9.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 9.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 6.3)

**io_ops.py** has 28 public functions + 4 private helpers + 1 async helper + 1 internal exception + 1 sanitizer. Key functions already established:
```python
def run_beads_show(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_create(title: str, description: str) -> IOResult[str, PipelineError]: ...
def load_command_workflow(workflow_name: str) -> IOResult[Workflow, PipelineError]: ...
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def read_bmad_file(path: str) -> IOResult[str, PipelineError]: ...
def write_bmad_file(path: str, content: str) -> IOResult[None, PipelineError]: ...
```

**workflows/__init__.py** has 5 registered workflows in `_REGISTRY`. `load_workflow()` is a pure lookup (returns `Workflow | None`). `list_workflows(dispatchable_only=False)` returns filtered lists. Two workflows are dispatchable: `implement_close` and `implement_verify_close`.

**WorkflowName** registry constants:
```python
class WorkflowName:
    IMPLEMENT_CLOSE = "implement_close"
    IMPLEMENT_VERIFY_CLOSE = "implement_verify_close"
    CONVERT_STORIES_TO_BEADS = "convert_stories_to_beads"
    SAMPLE = "sample"
    VERIFY = "verify"
```

**engine/executor.py** `_STEP_REGISTRY` has 21 entries. The registry maps string function names to step functions.

**errors.py** has a single `PipelineError` frozen dataclass with fields: `step_name`, `error_type`, `message`, `context` (dict).

**types.py** has `WorkflowContext` frozen dataclass with `inputs`, `outputs`, `feedback`, `with_updates()`, `promote_outputs_to_inputs()`, `merge_outputs()`, `add_feedback()`.

**Current test count**: 1044 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 113 files tracked by mypy.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: Story 7.1 Architecture

This story builds two capabilities:

1. **Tag extraction**: Pure function to extract `{workflow_name}` tags from Beads issue descriptions
2. **Dispatch policy**: `adw_dispatch.py` module that reads an issue, extracts its tag, validates the workflow exists and is dispatchable, and returns a prepared context for execution

This story does NOT execute the dispatched workflow. That is Story 7.2. This story ends with a validated, dispatchable `WorkflowContext` ready for execution.

```
Architecture: Issue Tag Extraction & Workflow Dispatch

┌──────────────────────────────────────────────────────┐
│  adw_dispatch.py (dispatch policy)                    │
│  dispatch_workflow(issue_id: str)                     │
│    -> IOResult[WorkflowContext, PipelineError]         │
└──────────────────┬───────────────────────────────────┘
                   │
        ┌──────────┴──────────────────────────┐
        ▼                                     ▼
┌────────────────────┐   ┌────────────────────────────────┐
│ io_ops             │   │ extract_workflow_tag            │
│ .read_issue_       │   │ (pure function, no I/O)        │
│  description()     │   │                                │
│ (delegates to      │   │ Input: description string      │
│  run_beads_show)   │   │ Output: Result[str, PipeErr]   │
│                    │   │                                │
│ Outputs:           │   │ Regex: r"\{(\w+)\}"            │
│  description text  │   │ Returns first match            │
└────────────────────┘   └────────────────────────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────────┐
                         │ load_workflow()                 │
                         │ (pure lookup, already exists)   │
                         │                                │
                         │ + dispatchable flag check       │
                         │ (policy enforcement)            │
                         └────────────────────────────────┘
```

### Design: Separation of Concerns

The architecture (Decision 5) specifies:

- **`load_workflow()`** in `workflows/__init__.py` is a **pure lookup** -- it finds a workflow by name and returns it (or `None`). It never checks `dispatchable`.
- **Policy enforcement** lives in `adw_dispatch.py` -- it checks `workflow.dispatchable` after lookup.

This separation is critical: `load_workflow()` is also called by command dispatch (`load_command_workflow` in io_ops), which intentionally invokes non-dispatchable workflows like `convert_stories_to_beads`. Only the cron trigger path (through `adw_dispatch.py`) enforces the dispatchable gate.

### Design: Tag Extraction Pattern

The `{workflow_name}` tags are embedded by `_embed_workflow_tag` in `create_beads_issue.py`:
```python
def _embed_workflow_tag(content: str, workflow_name: str) -> str:
    stripped = content.rstrip()
    return f"{stripped}\n\n{{{workflow_name}}}"
```

The extraction pattern must match this format:
- Tags are `{workflow_name}` where `workflow_name` is `\w+` (alphanumeric + underscore)
- Tags appear in the description body (typically at the end, per the embed function)
- Only the FIRST tag is extracted if multiple exist (deterministic behavior)
- Hyphens, spaces, and other non-word characters inside `{...}` are NOT valid tags

### Design: Dispatch Flow (Step by Step)

```
1. dispatch_workflow(issue_id) called
2. Validate issue_id is non-empty
3. io_ops.read_issue_description(issue_id)
   -> delegates to run_beads_show(issue_id) via bd show
   -> returns issue description text
4. extract_workflow_tag(description)
   -> regex extracts {workflow_name} tag
   -> returns tag name or PipelineError
5. load_workflow(tag_name)
   -> pure lookup in _REGISTRY
   -> returns Workflow or None
6. Check workflow.dispatchable
   -> if False, return PipelineError (NonDispatchableError)
7. Build WorkflowContext with:
   - inputs.issue_id = issue_id
   - inputs.issue_description = description
   - inputs.workflow_tag = tag_name
   - inputs.workflow = workflow
8. Return IOSuccess(context)
```

### Design: Why `read_issue_description` vs Reusing `run_beads_show`

The dispatch flow could call `run_beads_show` directly. We add `read_issue_description` as a semantic wrapper for two reasons:

1. **Mock clarity**: Tests mock `io_ops.read_issue_description` -- the intent is clear ("read the issue's description for dispatch") vs mocking `run_beads_show` which is a generic Beads command.
2. **Future-proofing**: If Beads issue reading needs pre-processing (e.g., stripping metadata headers, normalizing encoding), it lives in this one wrapper function.

The implementation is thin: validate input, delegate to `run_beads_show`, return result.

### Design: Why Two Step Functions

This story creates two step functions:

1. **`extract_and_validate_tag`**: Pure step that extracts a tag from a description already in context. Useful when the description is already available (e.g., from a previous step or command).
2. **`read_and_extract`**: Combined step that reads the issue description via io_ops AND extracts the tag. This is the primary step used in the dispatch flow.

Both follow the step signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.

The `adw_dispatch.py` module uses its OWN logic (not the step functions directly) because it is the dispatch entry point, not a workflow step. It calls io_ops and the pure `extract_workflow_tag()` function directly. The step functions exist for use in future workflows that need tag extraction as a pipeline step.

### Design: `adw_dispatch.py` Module Shape

Per architecture, `adw_dispatch.py` sits at the top level of `adws/` (same level as `adw_trigger_cron.py`). It is NOT a workflow step or a command -- it is the dispatch policy module. It:

- Is called by the cron trigger (Story 7.3)
- Enforces the `dispatchable` flag (Decision 5)
- Never reads BMAD files (NFR19)
- Interacts with Beads via io_ops only (NFR17)
- Returns a prepared `WorkflowContext` for execution (Story 7.2)

The existing `adws/adw_dispatch.py` file does NOT exist yet in the codebase. This story creates it. The architecture references it in Decision 5 and the project structure.

### Design: New io_ops Function

One new io_ops function is needed:

**`read_issue_description(issue_id: str) -> IOResult[str, PipelineError]`**
- Validates `issue_id` is non-empty (follows existing Beads function patterns)
- Delegates to `run_beads_show(issue_id)`
- Returns `IOSuccess(description)` on success
- Returns `IOFailure(PipelineError)` with `error_type="ValueError"` for empty issue_id
- Step name: `"io_ops.read_issue_description"`

This brings io_ops to ~29 public functions. Still under the split threshold.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_extract_workflow_tag.py` -- tests for `extract_workflow_tag`, `extract_and_validate_tag`
- `adws/tests/adw_modules/steps/test_read_and_extract.py` -- tests for `read_and_extract` step
- `adws/tests/test_adw_dispatch.py` -- tests for `dispatch_workflow` and dispatch policy
- `adws/tests/integration/test_dispatch_flow.py` -- full flow integration tests

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `read_issue_description` tests
- `adws/tests/adw_modules/steps/test_steps_init.py` (if exists) -- verify new exports
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entries
- `adws/tests/workflows/test_workflows.py` (or equivalent) -- verify `list_dispatchable_workflows` helper

**Mock targets**:
- `adws.adw_modules.io_ops.read_issue_description` -- mock in step and dispatch tests
- `adws.adw_modules.io_ops.run_beads_show` -- mock in io_ops unit tests for `read_issue_description`
- `adws.adw_modules.io_ops.read_bmad_file` -- mock to VERIFY IT IS NOT CALLED (NFR19 compliance)
- No SDK mocking needed -- this story is Beads CLI (via bd) and pure logic only

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.
- Lazy imports (e.g., `from adws.workflows import load_workflow` inside function body) need `# noqa: PLC0415`.

### Architecture Compliance

- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `read_issue_description` is the new io_ops function; `run_beads_show` already exists. No direct subprocess calls or bd CLI calls in step or dispatch logic.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads via bd CLI only. `read_issue_description` delegates to `run_beads_show` which uses `bd show` through `run_shell_command`.
- **NFR19**: ADWS never reads BMAD files during dispatch. The Beads issue description is the only contract. Tests verify `io_ops.read_bmad_file` is not called.
- **FR18**: Receive Beads issue ID, extract workflow tag from description.
- **FR19**: Dispatch appropriate workflow based on extracted tag.
- **Decision 5**: `load_workflow()` is pure lookup. Policy enforcement (dispatchable flag) in `adw_dispatch.py`.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT execute the dispatched workflow. That is Story 7.2 (Workflow Execution & Issue Closure).
- Do NOT implement the cron trigger. That is Story 7.3.
- Do NOT implement triage/failure recovery. That is Story 7.4.
- Do NOT implement the finalize step (close on success, tag on failure). That is Story 7.2.
- Do NOT interact with the Claude SDK -- this story is Beads CLI (via bd) and pure logic only.
- Do NOT change `load_workflow()` behavior -- it must remain a pure lookup that does NOT check `dispatchable`. Policy enforcement lives in `adw_dispatch.py`.
- Do NOT change `list_workflows()` behavior -- only add the new `list_dispatchable_workflows` helper.
- Do NOT change existing io_ops functions (only add the new `read_issue_description`).
- Do NOT change the engine executor logic. Only add new step registry entries.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in the step modules or `adw_dispatch.py`.
- Do NOT read BMAD files from any code in this story (NFR19).

### Relationship to Adjacent Stories

- **Story 6.2** (predecessor): Beads issue creator -- the `_embed_workflow_tag` function embeds `{workflow_name}` tags in issue descriptions. This story's `extract_workflow_tag` is the counterpart that READS those tags.
- **Story 6.3** (predecessor): Completes Epic 6, converting BMAD stories to Beads issues with embedded tags. Those issues are what this story dispatches.
- **Story 7.2** (successor): Workflow Execution & Issue Closure -- takes the dispatched workflow context from this story and executes it through the engine, then closes the issue or tags failure.
- **Story 7.3** (downstream): Cron Trigger -- calls `dispatch_workflow()` from this story during autonomous polling.
- **Story 7.4** (downstream): Triage Workflow -- handles issues that fail after dispatch.
- **This story starts Epic 7**: It provides the tag extraction and dispatch policy that all subsequent Epic 7 stories build upon.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (Issue Integration section):**
> **Issue Integration (FR18-22)** | `adws/adw_dispatch.py`, `adw_trigger_cron.py` | `io_ops.py` (bd CLI calls), `workflows/__init__.py` (load_workflow)

**Architecture Decision 5 (Dispatch Registry):**
> `load_workflow()` in `workflows/__init__.py` is a pure lookup -- it finds a workflow by name and returns it (or None). It never checks `dispatchable`. Policy enforcement lives in `adw_dispatch.py`.

**Architecture Project Structure:**
> `adws/adw_dispatch.py` -- Workflow dispatcher (uses load_workflow() to match tags)

**Architecture Integration Points:**
> ADWS -> Beads | `bd` CLI subprocess | Outbound | `run_beads_command()`

**Architecture One-Directional Flow:**
> BMAD -> Beads -> ADWS flow. Beads issues are the contract between planning and execution.

### Project Structure Notes

Files to create:
- `adws/adw_dispatch.py` -- `dispatch_workflow()`, dispatch policy enforcement
- `adws/adw_modules/steps/extract_workflow_tag.py` -- `extract_workflow_tag()` (pure), `extract_and_validate_tag()` (step)
- `adws/adw_modules/steps/read_and_extract.py` -- `read_and_extract()` (step)
- `adws/tests/test_adw_dispatch.py` -- dispatch policy tests
- `adws/tests/adw_modules/steps/test_extract_workflow_tag.py` -- tag extraction tests
- `adws/tests/adw_modules/steps/test_read_and_extract.py` -- read_and_extract step tests
- `adws/tests/integration/test_dispatch_flow.py` -- full flow integration tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `read_issue_description()` function in the "Beads CLI io_ops" section
- `adws/adw_modules/steps/__init__.py` -- add `extract_and_validate_tag` and `read_and_extract` imports/exports
- `adws/adw_modules/engine/executor.py` -- add `extract_and_validate_tag` and `read_and_extract` to `_STEP_REGISTRY`
- `adws/workflows/__init__.py` -- add `list_dispatchable_workflows` helper
- `adws/tests/adw_modules/test_io_ops.py` -- add `read_issue_description` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entries

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7] -- Epic summary: "Automated Dispatch, Cron Trigger & Self-Healing Triage"
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry: dispatchable flag, load_workflow() pure lookup, policy in adw_dispatch.py
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `adw_dispatch.py` in `adws/`
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Discovery and Dispatch] -- load_workflow(), list_workflows()
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- ADWS -> Beads via bd CLI
- [Source: _bmad-output/planning-artifacts/architecture.md#One-Directional System Flow] -- BMAD -> Beads -> ADWS
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form
- [Source: _bmad-output/planning-artifacts/architecture.md#Step Internal Structure] -- Step pattern with one public function per module
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist (6 mandatory items)
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR18-FR22, FR46-FR48 map to Epic 7
- [Source: adws/adw_modules/io_ops.py] -- 28 public functions, run_beads_show pattern, _find_project_root
- [Source: adws/adw_modules/types.py] -- WorkflowContext frozen dataclass
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/steps/create_beads_issue.py] -- _embed_workflow_tag (tag format reference), _validate_workflow_name
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, load_workflow(), list_workflows(), _REGISTRY
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (21 entries to extend)
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction types
- [Source: adws/adw_modules/commands/dispatch.py] -- command dispatch pattern (reference, NOT the same as workflow dispatch)
- [Source: adws/adw_modules/commands/build.py] -- command pattern reference with finalize
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/6-3-bidirectional-tracking-and-convert-stories-to-beads-command.md] -- predecessor story format reference

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

From Story 6.3 learnings:
- **1044 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **113 source files**: Current file count tracked by mypy.
- **io_ops at 28 public functions**: This story adds 1 new io_ops function (`read_issue_description`) bringing total to 29.
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Step creation checklist**: errors.py -> io_ops.py -> step -> __init__.py -> tests -> verify. This story does NOT add new error types to errors.py (it uses existing `PipelineError` with different `error_type` strings).
- **Frozen dataclasses**: All data models must be frozen. WorkflowContext is already defined and frozen.
- **Code review finding from 6.2**: `current_story` re-output caused ContextCollisionError. Steps in this story MUST NOT re-output keys that already exist in inputs.
- **shlex.quote pattern**: All Beads CLI functions use `shlex.quote()` to escape user-provided arguments. The `run_beads_show` function already handles this.
- **bind() pattern**: Existing io_ops functions use `.bind()` to chain operations. Follow this pattern for `read_issue_description`.
- **Lazy imports**: When importing from `adws.workflows` inside function bodies (to avoid circular imports), use `# noqa: PLC0415`.

## Code Review

### Review Date: 2026-02-02

### Issues Found: 4 (1 MEDIUM, 2 MEDIUM, 1 LOW)

#### Issue 1 (MEDIUM): Dispatch error shows non-dispatchable workflows in available list
- **Files**: `adws/adw_dispatch.py` line 76
- **Problem**: `dispatch_workflow` called `list_workflows()` without `dispatchable_only=True` when building the `UnknownWorkflowTagError`. This meant the `available_workflows` list in the error included non-dispatchable workflows (`convert_stories_to_beads`, `sample`, `verify`), misleading callers into thinking those workflows could be dispatched. The project specifically created `list_dispatchable_workflows()` in Task 7 for this purpose but never used it in the dispatch module.
- **Fix**: Changed `list_workflows()` to `list_dispatchable_workflows()` in `adw_dispatch.py`. Added test assertions in `test_adw_dispatch.py` and `test_dispatch_flow.py` verifying non-dispatchable workflows are excluded from the error context.

#### Issue 2 (MEDIUM): Whitespace-only issue_id bypasses validation
- **Files**: `adws/adw_dispatch.py` line 40, `adws/adw_modules/io_ops.py` line 786
- **Problem**: Both `dispatch_workflow` and `read_issue_description` used `if not issue_id:` to validate the issue ID. This check passes for whitespace-only strings like `"   "`, allowing a garbage shell command (`bd show '   '`) to execute. The issue ID should be stripped before the emptiness check.
- **Fix**: Changed validation to `if not issue_id or not issue_id.strip():` in both functions. Added whitespace-only test cases in `test_adw_dispatch.py` and `test_io_ops.py`.

#### Issue 3 (MEDIUM): Duplicated workflow validation logic across three modules
- **Files**: `adws/adw_dispatch.py` lines 67-90, `adws/adw_modules/steps/extract_workflow_tag.py` lines 79-103, `adws/adw_modules/steps/read_and_extract.py` lines 66-90
- **Problem**: The tag-lookup-then-build-error pattern is copy-pasted identically across three modules. If the error format or workflow list logic changes, all three must be updated. The story design doc explains why `adw_dispatch.py` doesn't reuse step functions, but the error construction is still duplicated.
- **Disposition**: Not fixed. The story design doc explicitly states `adw_dispatch.py` uses its own logic (not step functions) because it is the dispatch entry point. The step functions (`extract_and_validate_tag`, `read_and_extract`) are general-purpose and correctly use `list_workflows()` (all workflows). Extracting a shared helper would create coupling between dispatch-policy code and general step code. Left as a known code smell with this note.

#### Issue 4 (LOW): Step functions use `list_workflows()` instead of `list_dispatchable_workflows()` for error messages
- **Files**: `adws/adw_modules/steps/extract_workflow_tag.py` line 87, `adws/adw_modules/steps/read_and_extract.py` line 74
- **Problem**: The step functions list ALL workflows in `UnknownWorkflowTagError` context, not just dispatchable ones. However, unlike `adw_dispatch.py`, these steps are general-purpose (not dispatch-specific), so listing all workflows is arguably correct behavior -- a future command workflow might use these steps to extract tags for any workflow, including non-dispatchable ones.
- **Disposition**: Not fixed. By design -- these steps are reusable outside the dispatch path.

### Quality Gates After Fixes
- `pytest`: 1087 passed, 5 skipped, 100% line+branch coverage
- `mypy --strict`: no issues in 120 source files
- `ruff check`: all checks passed

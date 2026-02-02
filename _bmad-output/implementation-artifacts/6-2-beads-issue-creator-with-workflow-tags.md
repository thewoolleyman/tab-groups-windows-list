# Story 6.2: Beads Issue Creator with Workflow Tags

Status: review-complete

## Story

As an ADWS developer,
I want to create Beads issues from parsed story content with embedded workflow tags,
so that each issue is ready for automated dispatch.

## Acceptance Criteria

1. **Given** parsed story content from Story 6.1, **When** the creator generates a Beads issue, **Then** it calls `bd create` via io_ops shell function (NFR17 -- Beads via bd CLI only) **And** the entire story content is the issue description (FR25) **And** a `{workflow_name}` tag is embedded in the description using the workflow name registry from Epic 1 (FR26).

2. **Given** the workflow name registry, **When** the creator embeds a workflow tag, **Then** only valid workflow names from the registry are used **And** invalid or missing workflow names produce a clear PipelineError.

3. **Given** `bd create` succeeds, **When** the issue is created, **Then** the returned Beads issue ID is captured for bidirectional tracking.

4. **Given** `bd create` fails, **When** the creator processes the error, **Then** a PipelineError propagates with the bd CLI error details.

5. **Given** all creator code, **When** I run tests, **Then** tests cover: successful creation, workflow tag embedding, invalid workflow name, bd CLI failure **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Define `run_beads_create` io_ops function (AC: #1, #3, #4)
  - [ ] 1.1 RED: Write test for `io_ops.run_beads_create(title: str, description: str) -> IOResult[str, PipelineError]`. Given valid title and description, mock `run_shell_command` to return a `ShellResult` with `return_code=0` and `stdout="Created issue: ISSUE-123\n"`. Verify it returns `IOSuccess("ISSUE-123")` -- the parsed Beads issue ID from stdout.
  - [ ] 1.2 GREEN: Implement `run_beads_create` in `adws/adw_modules/io_ops.py`. Construct `bd create --title <title> --description <description>` command using `shlex.quote()` for safety (following the `run_beads_close` and `run_beads_update_notes` patterns). Delegate to `run_shell_command`. Parse the issue ID from stdout. Return `IOSuccess(issue_id)`.
  - [ ] 1.3 RED: Write test for `run_beads_create` when `bd create` returns nonzero exit code. Mock `run_shell_command` to return `ShellResult(return_code=1, stdout="", stderr="Error: failed to create", command="bd create ...")`. Verify it returns `IOFailure(PipelineError)` with `error_type="BeadsCreateError"`, `step_name="io_ops.run_beads_create"`, and stderr in context.
  - [ ] 1.4 GREEN: Implement nonzero exit handling -- return `IOFailure` with `BeadsCreateError`.
  - [ ] 1.5 RED: Write test for `run_beads_create` when stdout does not contain a parseable issue ID (e.g., `stdout="Unexpected output\n"`, `return_code=0`). Verify it returns `IOFailure(PipelineError)` with `error_type="BeadsCreateParseError"` and the raw stdout in context.
  - [ ] 1.6 GREEN: Implement stdout parsing validation -- if ID cannot be extracted from stdout, return `IOFailure`.
  - [ ] 1.7 RED: Write test for `run_beads_create` when `run_shell_command` itself returns `IOFailure` (e.g., command not found). Verify the failure propagates through.
  - [ ] 1.8 GREEN: Implement failure propagation -- `bind` on the `run_shell_command` result handles this naturally.
  - [ ] 1.9 REFACTOR: Clean up, verify consistent pattern with other `run_beads_*` functions, verify mypy/ruff.

- [ ] Task 2: Define `_embed_workflow_tag` private helper (AC: #1, #2)
  - [ ] 2.1 RED: Write test for `_embed_workflow_tag(story_content: str, workflow_name: str) -> str`. Given a story raw_content string and workflow_name `"implement_verify_close"`, verify it returns the story content with `{implement_verify_close}` tag appended on a new line at the end. The tag format is `{workflow_name}` (curly braces around the name).
  - [ ] 2.2 GREEN: Implement `_embed_workflow_tag` in `adws/adw_modules/steps/create_beads_issue.py`. Appends `\n\n{workflow_name}` to the end of the story content.
  - [ ] 2.3 RED: Write test for `_embed_workflow_tag` when story content already ends with whitespace/newlines. Verify the tag is still cleanly appended without excessive blank lines.
  - [ ] 2.4 GREEN: Implement content trimming before appending tag.
  - [ ] 2.5 REFACTOR: Clean up.

- [ ] Task 3: Define `_validate_workflow_name` private helper (AC: #2)
  - [ ] 3.1 RED: Write test for `_validate_workflow_name(workflow_name: str) -> Result[str, PipelineError]`. Given a valid workflow name from the registry (e.g., `"implement_verify_close"`), verify it returns `Success(workflow_name)`. Import `WorkflowName` from `adws.workflows` to check against the registry.
  - [ ] 3.2 GREEN: Implement `_validate_workflow_name` in `adws/adw_modules/steps/create_beads_issue.py`. Check if the name is in the set of valid `WorkflowName` constants. Return `Success(name)` if valid.
  - [ ] 3.3 RED: Write test for `_validate_workflow_name` with an invalid workflow name (e.g., `"nonexistent_workflow"`). Verify it returns `Failure(PipelineError)` with `error_type="InvalidWorkflowNameError"`, `step_name="create_beads_issue"`, and a message listing available workflow names.
  - [ ] 3.4 GREEN: Implement invalid name handling -- return `Failure(PipelineError)` with the list of valid names.
  - [ ] 3.5 RED: Write test for `_validate_workflow_name` with an empty string. Verify it returns `Failure(PipelineError)` with `error_type="InvalidWorkflowNameError"`.
  - [ ] 3.6 GREEN: Implement empty string handling.
  - [ ] 3.7 REFACTOR: Clean up.

- [ ] Task 4: Create `create_beads_issue` step function (AC: #1, #2, #3, #4)
  - [ ] 4.1 RED: Write test for `create_beads_issue(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `ctx.inputs` contains a `BmadStory` at key `"current_story"` and `"workflow_name"` set to `"implement_verify_close"`, mock `io_ops.run_beads_create` to return `IOSuccess("ISSUE-42")`. Verify it returns `IOSuccess(WorkflowContext)` with outputs containing `"beads_issue_id"` set to `"ISSUE-42"` and `"current_story"` preserved for downstream steps (Story 6.3).
  - [ ] 4.2 GREEN: Implement `create_beads_issue` step. Extract `current_story` (BmadStory) and `workflow_name` from `ctx.inputs`. Validate workflow name. Embed workflow tag in story raw_content. Call `io_ops.run_beads_create` with the story title as issue title and the tagged content as description. Return IOSuccess with `beads_issue_id` in outputs.
  - [ ] 4.3 RED: Write test for `create_beads_issue` when `current_story` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="create_beads_issue"`.
  - [ ] 4.4 GREEN: Implement missing input validation for `current_story`.
  - [ ] 4.5 RED: Write test for `create_beads_issue` when `workflow_name` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"`.
  - [ ] 4.6 GREEN: Implement missing input validation for `workflow_name`.
  - [ ] 4.7 RED: Write test for `create_beads_issue` when `workflow_name` is not a valid workflow name. Given `"bogus_workflow"` in inputs, verify it returns `IOFailure(PipelineError)` with `error_type="InvalidWorkflowNameError"`.
  - [ ] 4.8 GREEN: Implement workflow name validation by calling `_validate_workflow_name`.
  - [ ] 4.9 RED: Write test for `create_beads_issue` when `io_ops.run_beads_create` returns `IOFailure`. Mock it to return `IOFailure(PipelineError(step_name="io_ops.run_beads_create", error_type="BeadsCreateError", ...))`. Verify the failure propagates through.
  - [ ] 4.10 GREEN: Implement failure propagation from `run_beads_create`.
  - [ ] 4.11 RED: Write test for `create_beads_issue` when `current_story` is not a `BmadStory` instance (e.g., it is a plain dict or string). Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and a message indicating invalid type.
  - [ ] 4.12 GREEN: Implement type validation for `current_story`.
  - [ ] 4.13 RED: Write test verifying the issue description passed to `run_beads_create` contains both the full story raw_content AND the embedded `{workflow_name}` tag. Capture the call args on the mocked `io_ops.run_beads_create` and assert the description argument contains the tag.
  - [ ] 4.14 GREEN: Ensure the description construction is correct.
  - [ ] 4.15 RED: Write test verifying the issue title passed to `run_beads_create` uses a clear format including the story's epic and story number. For example, `"Story 6.2: Beads Issue Creator with Workflow Tags"`. Capture call args and verify title format.
  - [ ] 4.16 GREEN: Implement title formatting from BmadStory fields.
  - [ ] 4.17 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 5: Register step in steps/__init__.py and engine step registry (AC: #5)
  - [ ] 5.1 RED: Write test that `create_beads_issue` is importable from `adws.adw_modules.steps`. Verify it appears in `__all__`.
  - [ ] 5.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py` in the "Bridge steps (BMAD-to-Beads)" section alongside `parse_bmad_story`.
  - [ ] 5.3 RED: Write test that `_STEP_REGISTRY` in `adws/adw_modules/engine/executor.py` contains an entry for `"create_beads_issue"`.
  - [ ] 5.4 GREEN: Add entry `"create_beads_issue": create_beads_issue` to `_STEP_REGISTRY` in executor.py. Add the import to the imports from `adws.adw_modules.steps`.
  - [ ] 5.5 REFACTOR: Verify imports are consistent with the rest of the module.

- [ ] Task 6: Update `convert_stories_to_beads` workflow (AC: #1)
  - [ ] 6.1 RED: Write test that the `convert_stories_to_beads` workflow in `adws/workflows/__init__.py` now includes `"create_beads_issue"` as the second step (after `"parse_bmad_story"`). Verify the step is present in the workflow definition's steps list.
  - [ ] 6.2 GREEN: Update `_CONVERT_STORIES_TO_BEADS` in `adws/workflows/__init__.py` to include `create_beads_issue` as the second step. The step should have `name="create_beads_issue"` and `function="create_beads_issue"`.
  - [ ] 6.3 REFACTOR: Verify workflow definition consistency.

- [ ] Task 7: Edge case tests (AC: #2, #5)
  - [ ] 7.1 RED: Write test for `create_beads_issue` when the `BmadStory.raw_content` is empty. Verify the step still succeeds (creates an issue with just the workflow tag as description).
  - [ ] 7.2 GREEN: Ensure empty raw_content handling works.
  - [ ] 7.3 RED: Write test for `create_beads_issue` when the `BmadStory.title` contains special characters (quotes, ampersands, newlines). Verify the title is safely passed to `run_beads_create` (shlex quoting in io_ops handles this).
  - [ ] 7.4 GREEN: Verify special character handling (shlex.quote in io_ops covers this).
  - [ ] 7.5 RED: Write test for `_validate_workflow_name` with each valid workflow name in the registry (`implement_close`, `implement_verify_close`, `convert_stories_to_beads`, `sample`, `verify`). Verify all are accepted as valid.
  - [ ] 7.6 GREEN: Ensure all registry names pass validation.
  - [ ] 7.7 RED: Write test for `_embed_workflow_tag` with story content that already contains a `{workflow_name}` tag. Verify the function does NOT check for duplicates -- it always appends (idempotency is handled at the orchestration level in Story 6.3, not here).
  - [ ] 7.8 GREEN: Verify tag appending is unconditional.
  - [ ] 7.9 REFACTOR: Clean up edge case tests.

- [ ] Task 8: Integration tests (AC: #1, #3, #5)
  - [ ] 8.1 RED: Write integration test that constructs a realistic `BmadStory` (using data from Story 6.1's parser output) and runs `create_beads_issue` with mocked `io_ops.run_beads_create`. Verify the full flow: story content + tag embedding + bd create call + issue ID capture.
  - [ ] 8.2 GREEN: Ensure integration test passes.
  - [ ] 8.3 RED: Write integration test that exercises the `_validate_workflow_name` -> `_embed_workflow_tag` -> `io_ops.run_beads_create` chain end-to-end within the step function. Verify the mocked `run_beads_create` receives the correctly tagged description.
  - [ ] 8.4 GREEN: Ensure chain integration works.
  - [ ] 8.5 REFACTOR: Clean up integration tests.

- [ ] Task 9: Verify full integration and quality gates (AC: #6)
  - [ ] 9.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 9.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 9.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 6.1)

**io_ops.py** has 25 public functions + 4 private helpers + 1 async helper + 1 internal exception + 1 sanitizer. Key Beads CLI functions already established:
```python
def run_beads_show(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
```

**types.py** has `BmadStory` and `BmadEpic` frozen dataclasses (added by Story 6.1):
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

**steps/__init__.py** exports 21 steps including `parse_bmad_story`.

**engine/executor.py** `_STEP_REGISTRY` has 17 entries including `parse_bmad_story`.

**workflows/__init__.py** has 5 registered workflows. `_CONVERT_STORIES_TO_BEADS` currently has empty steps:
```python
_CONVERT_STORIES_TO_BEADS = Workflow(
    name=WorkflowName.CONVERT_STORIES_TO_BEADS,
    description="Convert BMAD stories to Beads issues with workflow tags",
    dispatchable=False,
    steps=[],  # Steps populated in Epic 6
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

**Current test count**: 935 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 103 files tracked by mypy.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: create_beads_issue Architecture

This story creates a **thin wrapper around I/O** step -- most of the work is validation (workflow name) and string composition (tag embedding), with the core action being a `bd create` CLI call through io_ops. The architecture document explicitly classifies `create_beads_issue.py` in this category:

> | Thin wrapper around I/O | `create_beads_issue.py` (shells out to `bd create`) | Mock-heavy; test error mapping and result handling |

```
Layer 1: Step Function (testable core)
  adws/adw_modules/steps/create_beads_issue.py
    create_beads_issue()             <-- public step function
    _validate_workflow_name()        <-- pure validation (no I/O)
    _embed_workflow_tag()            <-- pure string composition (no I/O)

Layer 2: I/O Boundary
  adws/adw_modules/io_ops.py
    run_beads_create()               <-- bd CLI call (new function this story)

Layer 3: Data Models
  adws/adw_modules/types.py
    BmadStory                        <-- frozen dataclass (from Story 6.1)
```

### Design: New io_ops Function

One new io_ops function is needed:

**`run_beads_create(title: str, description: str) -> IOResult[str, PipelineError]`**
- Constructs `bd create --title <title> --description <description>` command
- Uses `shlex.quote()` to safely escape both title and description (follows `run_beads_close` pattern)
- Delegates to `run_shell_command`
- Parses the issue ID from stdout (bd create outputs the created issue ID)
- Returns `IOSuccess(issue_id)` on success
- Returns `IOFailure(PipelineError)` with `error_type="BeadsCreateError"` on nonzero exit
- Returns `IOFailure(PipelineError)` with `error_type="BeadsCreateParseError"` if stdout cannot be parsed

This brings io_ops to ~26 public functions. Still under the split threshold.

**Pattern follows existing Beads CLI functions.** The `run_beads_show`, `run_beads_close`, and `run_beads_update_notes` functions establish the pattern:
1. Build command string with `shlex.quote()` for all user-provided arguments
2. Delegate to `run_shell_command`
3. Use `.bind()` with an inner `_check_exit` function to handle nonzero exit codes
4. Return domain-appropriate success type

**Stdout parsing note:** The `bd create` command outputs the created issue ID to stdout. The exact format may vary by Beads version. The implementation should use a regex to extract an ID pattern (e.g., alphanumeric with hyphens) from stdout. If no ID is found, return `IOFailure` with `BeadsCreateParseError`. The initial implementation should be flexible -- strip and return the first non-empty line, with a fallback regex match. This can be refined once the actual `bd create` output format is confirmed.

### Design: Workflow Tag Format

The architecture specifies workflow tags in the format `{workflow_name}`:

> **Given** parsed story content from Story 6.1, **When** the creator generates a Beads issue, **Then** a `{workflow_name}` tag is embedded in the description (FR26)

The tag is embedded at the end of the issue description, separated by a blank line:

```
[full story raw_content here]

{implement_verify_close}
```

This tag is what the dispatch mechanism in Epic 7 (Story 7.1) will extract to determine which workflow to run. The tag must exactly match a `WorkflowName` constant from `adws/workflows/__init__.py`.

### Design: Step Input/Output Contract

**Inputs expected in `ctx.inputs`:**
- `current_story` (BmadStory): The parsed story from `parse_bmad_story` step (Story 6.1 output promoted to inputs by engine)
- `workflow_name` (str): The workflow name to embed as a tag. This is provided by the orchestrating workflow or command

**Outputs produced in `ctx.outputs`:**
- `beads_issue_id` (str): The ID of the created Beads issue
- `current_story` (BmadStory): Passed through for downstream use by `write_beads_id` step (Story 6.3)

### Design: Issue Title Format

The issue title should clearly identify the story:

```
Story {epic_number}.{story_number}: {title}
```

For example: `Story 6.2: Beads Issue Creator with Workflow Tags`

This format is used by `bd create --title` and makes issues easily identifiable in `bd list` output.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_create_beads_issue.py` -- tests for `create_beads_issue`, `_validate_workflow_name`, `_embed_workflow_tag`
- `adws/tests/integration/test_beads_issue_creator.py` -- integration tests with realistic BmadStory data

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `run_beads_create` tests
- `adws/tests/adw_modules/steps/test_steps_init.py` (if exists) -- verify new export
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entry
- `adws/tests/workflows/test_workflows.py` (or equivalent) -- verify `convert_stories_to_beads` includes `create_beads_issue` step

**Mock targets**:
- `adws.adw_modules.io_ops.run_beads_create` -- mock in step tests
- `adws.adw_modules.io_ops.run_shell_command` -- mock in io_ops tests for `run_beads_create`
- No SDK mocking needed -- this story is Beads CLI integration, not SDK

**Recommended test fixtures** (in conftest.py or test file):
- `sample_bmad_story` -- minimal `BmadStory` instance for testing
- `sample_bmad_story_complex` -- `BmadStory` with special characters in title and long raw_content

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.

### Architecture Compliance

- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `run_beads_create` is the io_ops function; no direct subprocess or bd CLI calls in step logic.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: Beads via bd CLI only. `run_beads_create` uses `bd create` through `run_shell_command`.
- **NFR19**: BMAD files are NOT read in this story. The `BmadStory` data arrives via `WorkflowContext.inputs` from the upstream `parse_bmad_story` step. This step only interacts with Beads.
- **FR25**: Create Beads issues with story content as the issue description.
- **FR26**: Embed `{workflow_name}` tag in the Beads issue description.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT read BMAD files in this story -- the `BmadStory` data comes from Story 6.1's parser via context inputs.
- Do NOT write beads_id back to BMAD files -- that is Story 6.3.
- Do NOT orchestrate the full conversion flow (multi-story iteration, idempotency) -- that is Story 6.3.
- Do NOT interact with the Claude SDK -- this story is Beads CLI only (bd create).
- Do NOT create CLI hooks or SDK HookMatchers. This is not a hook -- it is a pipeline step.
- Do NOT create a fail-open wrapper for this step. Unlike hooks (which must fail-open per NFR4), this step is a pipeline step that SHOULD fail visibly if issue creation fails -- the error propagates through ROP.
- Do NOT change existing step functions, workflows, or engine logic (except adding step registry entries, __init__.py exports, and updating the convert_stories_to_beads workflow steps).
- Do NOT change the existing io_ops functions (only add the new `run_beads_create`).
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in the step module.
- Do NOT handle idempotency (skipping already-converted stories) -- that is Story 6.3's responsibility.
- Do NOT change `BmadStory` or `BmadEpic` dataclasses -- they are defined and complete from Story 6.1.

### Relationship to Adjacent Stories

- **Story 6.1** (predecessor): BMAD markdown parser -- produces `BmadStory` and `BmadEpic` objects that this story consumes. The `parse_bmad_story` step outputs `parsed_stories` (list of BmadStory) into context, which the orchestrating workflow (Story 6.3) iterates over and provides as `current_story` to this step.
- **Story 6.3** (successor): Bidirectional tracking -- consumes the `beads_issue_id` output from this step, writes it back to BMAD files, and orchestrates the full `/convert-stories-to-beads` command including multi-story iteration and idempotency.
- **Epic 7** (downstream): Story 7.1 (Issue Tag Extraction & Workflow Dispatch) will extract the `{workflow_name}` tag embedded by this story from Beads issue descriptions to dispatch the correct workflow.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (BMAD-to-Beads Bridge section):**
> **BMAD-to-Beads Bridge (FR23-27)** | `adws/adw_modules/steps/parse_bmad_story.py`, `create_beads_issue.py`, `write_beads_id.py` | `adws/workflows/convert_stories_to_beads.py`

**Architecture Step Naming:**
> `create_beads_issue.py` (not `beads_creator.py` or `issue_creation.py`)

**Architecture Testing Strategy:**
> | Thin wrapper around I/O | `create_beads_issue.py` (shells out to `bd create`) | Mock-heavy; test error mapping and result handling |

**Architecture Integration Points:**
> ADWS -> Beads | `bd` CLI subprocess | Outbound | `run_beads_command()`

**Architecture Workflow Composition:**
> `convert_stories_to_beads.py` | `parse_bmad_story` -> `create_beads_issue` -> `write_beads_id` (all step modules)

This story implements the second step (`create_beads_issue`) of this three-step workflow.

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/create_beads_issue.py` -- `create_beads_issue()`, `_validate_workflow_name()`, `_embed_workflow_tag()`
- `adws/tests/adw_modules/steps/test_create_beads_issue.py` -- step logic + private helper tests
- `adws/tests/integration/test_beads_issue_creator.py` -- integration tests with realistic content

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `run_beads_create()` function in the "Beads CLI io_ops" section
- `adws/adw_modules/steps/__init__.py` -- add `create_beads_issue` import and export in the "Bridge steps" section
- `adws/adw_modules/engine/executor.py` -- add `create_beads_issue` to `_STEP_REGISTRY` and import
- `adws/workflows/__init__.py` -- update `_CONVERT_STORIES_TO_BEADS` to include `create_beads_issue` as step 2
- `adws/tests/adw_modules/test_io_ops.py` -- add `run_beads_create` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entry

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 6] -- Epic summary: "BMAD-to-Beads Story Converter"
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `create_beads_issue.py` in `adws/adw_modules/steps/`, workflow composition
- [Source: _bmad-output/planning-artifacts/architecture.md#Testing Strategy Notes] -- `create_beads_issue.py` classified as "Thin wrapper around I/O"
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form, function matches filename
- [Source: _bmad-output/planning-artifacts/architecture.md#Step Internal Structure] -- Step pattern with one public function per module
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist (6 mandatory items)
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR25, FR26 map to Epic 6
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- ADWS -> Beads via bd CLI
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow Discovery and Dispatch] -- WorkflowName registry, {workflow_name} tag format
- [Source: adws/adw_modules/io_ops.py] -- 25 public functions, run_beads_close/update_notes (pattern for run_beads_create), shlex.quote pattern
- [Source: adws/adw_modules/types.py] -- BmadStory, BmadEpic frozen dataclasses (from Story 6.1)
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (17 entries to extend)
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, _CONVERT_STORIES_TO_BEADS (empty steps to be updated)
- [Source: adws/adw_modules/steps/parse_bmad_story.py] -- predecessor step, outputs parsed_stories
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/6-1-bmad-markdown-parser.md] -- reference story format, Story 6.1 code review results

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

From Story 6.1 learnings:
- **935 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **103 source files**: Current file count tracked by mypy.
- **io_ops at 25 public functions**: This story adds 1 new io_ops function (`run_beads_create`) bringing total to 26.
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Step creation checklist**: errors.py -> io_ops.py -> step -> __init__.py -> tests -> verify. This story does NOT add new error types to errors.py (it uses existing `PipelineError` with different `error_type` strings like `"BeadsCreateError"`, `"InvalidWorkflowNameError"`, `"MissingInputError"`).
- **Frozen dataclasses**: All data models must be frozen. BmadStory and BmadEpic are already defined and frozen from Story 6.1.
- **Code review findings from 6.1**: Front matter parsing fixed (newline-delimited `---`), story FR inheritance from epic added. These patterns are stable now.
- **shlex.quote pattern**: All Beads CLI functions use `shlex.quote()` to escape user-provided arguments. The new `run_beads_create` MUST follow this pattern for both title and description arguments.
- **bind() pattern**: Existing Beads io_ops functions use `result.bind(_check_exit)` to chain shell command execution with exit code checking. Follow this exact pattern.

## Code Review

### Review Date: 2026-02-02

### Issues Found: 4 (2 MEDIUM, 1 MEDIUM, 1 LOW)

#### Issue 1 (MEDIUM) -- FIXED: `current_story` re-output causes ContextCollisionError
- **File**: `adws/adw_modules/steps/create_beads_issue.py` line 152-153
- **Problem**: The step outputs `current_story` in `ctx.outputs`, but `current_story` already exists in `ctx.inputs`. The engine's `promote_outputs_to_inputs()` raises `ValueError` when output keys collide with input keys. Currently the step is the last in the workflow so the collision is not triggered, but Story 6.3 adds `write_beads_id` as a third step, at which point `promote_outputs_to_inputs` will be called after `create_beads_issue` and will fail with `ContextCollisionError`.
- **Fix**: Removed `current_story` from outputs. It remains available to downstream steps via the engine's existing `promote_outputs_to_inputs` mechanism. Updated docstring and tests accordingly.
- **Files changed**: `create_beads_issue.py`, `test_create_beads_issue.py`, `test_beads_issue_creator.py`

#### Issue 2 (MEDIUM) -- FIXED: `_get_valid_workflow_names()` hardcodes workflow names
- **File**: `adws/adw_modules/steps/create_beads_issue.py` lines 16-28
- **Problem**: The function manually enumerates all 5 `WorkflowName` constants. If a new workflow is added to the registry, someone must also remember to update this function -- a maintenance drift risk. The `_REGISTRY` dict in `adws/workflows/__init__.py` already contains the authoritative list of valid names.
- **Fix**: Changed to derive names dynamically from `list_workflows()` via `frozenset(w.name for w in list_workflows())`. This ensures the validation always reflects the actual registry.
- **Files changed**: `create_beads_issue.py`

#### Issue 3 (MEDIUM) -- NOT FIXED (by design): `_parse_beads_issue_id` accepts any non-empty stdout as valid ID
- **File**: `adws/adw_modules/io_ops.py` lines 656-669
- **Problem**: The parser returns the first non-empty line (or the part after `": "`) as the issue ID without any format validation. If `bd create` outputs `"ERROR: something went wrong\n"` with `return_code=0` (buggy CLI), the parsed ID would be `"something went wrong"`, which would be stored as the `beads_issue_id`. This is a silent data corruption risk.
- **Reason not fixed**: The story spec explicitly states "The initial implementation should be flexible -- strip and return the first non-empty line, with a fallback regex match. This can be refined once the actual bd create output format is confirmed." The spec anticipates this being refined later. Filing as a known risk.

#### Issue 4 (LOW) -- NOT FIXED: Missing test for `_parse_beads_issue_id` with empty result after colon
- **File**: `adws/tests/adw_modules/test_io_ops.py`
- **Problem**: No test covers `_parse_beads_issue_id("Created: \n")` where the part after `": "` is empty or whitespace-only. The function returns `""` (correct behavior), but no test verifies this edge case.
- **Reason not fixed**: The behavior is already correct (returns empty string which triggers `BeadsCreateParseError` in `run_beads_create`). This is a test gap, not a code bug. The existing `test_parse_beads_issue_id_empty` and `test_run_beads_create_unparseable_stdout` tests cover the empty-result path.

### Quality Gates (post-fix)
- **Tests**: 989 passed, 5 skipped, 100% line+branch coverage
- **mypy**: Success, 106 source files, strict mode
- **ruff**: All checks passed

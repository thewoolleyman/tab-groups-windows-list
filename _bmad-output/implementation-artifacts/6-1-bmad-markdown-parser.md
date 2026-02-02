# Story 6.1: BMAD Markdown Parser

Status: ready-for-dev

## Story

As an ADWS developer,
I want to parse BMAD epic/story markdown files and extract structured story content,
so that the converter can create Beads issues from planning artifacts.

## Acceptance Criteria

1. **Given** a BMAD epic markdown file with stories, **When** the parser processes it, **Then** it extracts each story's title, user story (As a/I want/So that), and acceptance criteria (FR24) **And** it extracts story metadata (epic number, story number, FRs covered).

2. **Given** a BMAD file with multiple epics and stories, **When** the parser processes it, **Then** all stories are extracted with correct epic-to-story relationships **And** no story content is lost or truncated.

3. **Given** a malformed or incomplete BMAD file, **When** the parser encounters an error, **Then** it returns a clear PipelineError identifying what was unparseable and where.

4. **Given** all parser code, **When** I run tests, **Then** tests cover: single story, multiple stories, multiple epics, malformed input, edge cases (empty AC, missing fields) **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Define `BmadStory` and `BmadEpic` data models (AC: #1, #2)
  - [ ] 1.1 RED: Write test for `BmadStory` frozen dataclass in `adws/adw_modules/types.py`. Verify it has fields: `epic_number` (int), `story_number` (int), `title` (str -- e.g., "BMAD Markdown Parser"), `slug` (str -- e.g., "6-1-bmad-markdown-parser"), `user_story` (str -- the full "As a/I want/So that" block), `acceptance_criteria` (str -- the full AC text block), `frs_covered` (list[str] -- e.g., ["FR24"]), `raw_content` (str -- the full story text as it appears in the markdown, suitable for Beads issue body). Verify it is immutable (frozen dataclass).
  - [ ] 1.2 GREEN: Implement `BmadStory` frozen dataclass in `adws/adw_modules/types.py` following the pattern of `HookEvent`, `FileTrackEntry`, `SecurityLogEntry`.
  - [ ] 1.3 RED: Write test for `BmadEpic` frozen dataclass in `adws/adw_modules/types.py`. Verify it has fields: `epic_number` (int), `title` (str -- e.g., "BMAD-to-Beads Story Converter"), `description` (str -- the epic summary paragraph), `frs_covered` (list[str] -- e.g., ["FR23", "FR24", "FR25", "FR26", "FR27"]), `stories` (list[BmadStory]).
  - [ ] 1.4 GREEN: Implement `BmadEpic` frozen dataclass.
  - [ ] 1.5 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 2: Define `read_bmad_file` io_ops function (AC: #1, #3)
  - [ ] 2.1 RED: Write test for `io_ops.read_bmad_file(path: str) -> IOResult[str, PipelineError]`. Given a valid BMAD markdown file path, verify it reads and returns the full file contents as a string. Verify it uses `_find_project_root()` to resolve relative paths (consistent with `read_prime_file` pattern).
  - [ ] 2.2 GREEN: Implement `read_bmad_file` in `adws/adw_modules/io_ops.py`. Follow the `read_prime_file` pattern: resolve path relative to project root, delegate to `read_file()`, returns `IOResult`.
  - [ ] 2.3 RED: Write test for `read_bmad_file` when the file does not exist. Verify it returns `IOFailure(PipelineError)` with `error_type="FileNotFoundError"` and `step_name="io_ops.read_bmad_file"`.
  - [ ] 2.4 GREEN: Implement error handling (delegates to `read_file` which already catches `FileNotFoundError` and `PermissionError`).
  - [ ] 2.5 RED: Write test for `read_bmad_file` when passed an empty string path. Verify it returns an appropriate `IOFailure`.
  - [ ] 2.6 GREEN: Implement empty path validation.
  - [ ] 2.7 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 3: Implement `_parse_epic_header` private helper (AC: #1, #2)
  - [ ] 3.1 RED: Write test for `_parse_epic_header(header_text: str) -> tuple[int, str, str, list[str]]`. Given a header block like `"### Epic 6: BMAD-to-Beads Story Converter\n\nDeveloper can convert...\n\n**FRs covered:** FR23, FR24, FR25, FR26, FR27"`, verify it extracts: epic_number=6, title="BMAD-to-Beads Story Converter", description="Developer can convert...", frs_covered=["FR23", "FR24", "FR25", "FR26", "FR27"].
  - [ ] 3.2 GREEN: Implement `_parse_epic_header` in `adws/adw_modules/steps/parse_bmad_story.py`. Use regex to match `### Epic N: Title` pattern. Extract the description paragraph(s) between the title and `**FRs covered:**`. Parse the FRs from the comma-separated list.
  - [ ] 3.3 RED: Write test for `_parse_epic_header` with an epic that has no FRs covered line. Verify it returns an empty list for frs_covered (graceful degradation, not an error).
  - [ ] 3.4 GREEN: Implement missing FRs handling.
  - [ ] 3.5 RED: Write test for `_parse_epic_header` with an epic that has **Notes:** section after FRs. Verify the notes are NOT included in the description (description is only the paragraph before FRs).
  - [ ] 3.6 GREEN: Implement notes exclusion.
  - [ ] 3.7 REFACTOR: Clean up regex patterns.

- [ ] Task 4: Implement `_parse_story_block` private helper (AC: #1, #2)
  - [ ] 4.1 RED: Write test for `_parse_story_block(story_text: str, epic_number: int) -> BmadStory`. Given a story block from the epics file (starting with `#### Story 6.1: BMAD Markdown Parser`), verify it extracts: story_number=1, title="BMAD Markdown Parser", user_story="As an ADWS developer,\nI want to parse BMAD epic/story markdown files...\nSo that the converter can create Beads issues from planning artifacts.", acceptance_criteria (the full Given/When/Then blocks), raw_content (the entire story text). Verify slug is correctly generated: "6-1-bmad-markdown-parser" (epic_number-story_number-slugified-title).
  - [ ] 4.2 GREEN: Implement `_parse_story_block`. Use regex to match `#### Story N.M: Title` pattern. Extract the user story by finding the "As a..." / "I want..." / "So that..." pattern. Extract acceptance criteria by finding the `**Acceptance Criteria:**` section. Capture raw_content as everything from the story header to the next story header or end of epic section.
  - [ ] 4.3 RED: Write test for `_parse_story_block` with a story that has no explicit user story (As a/I want/So that). Verify it returns an empty string for user_story without erroring.
  - [ ] 4.4 GREEN: Implement missing user story handling.
  - [ ] 4.5 RED: Write test for `_parse_story_block` with a story that has no acceptance criteria section. Verify it returns an empty string for acceptance_criteria without erroring.
  - [ ] 4.6 GREEN: Implement missing AC handling.
  - [ ] 4.7 RED: Write test for `_parse_story_block` with a story that has Given/When/Then in the acceptance criteria with multiple AC blocks (numbered or separated by blank lines). Verify all AC blocks are captured in the acceptance_criteria string.
  - [ ] 4.8 GREEN: Implement multi-AC extraction.
  - [ ] 4.9 RED: Write test for slug generation: `_generate_slug(epic_number: int, story_number: int, title: str) -> str`. Given epic_number=6, story_number=1, title="BMAD Markdown Parser", verify slug is "6-1-bmad-markdown-parser". Test with titles containing special characters, ampersands, and mixed case.
  - [ ] 4.10 GREEN: Implement `_generate_slug`.
  - [ ] 4.11 REFACTOR: Clean up regex patterns, verify mypy/ruff.

- [ ] Task 5: Implement `_split_into_epic_sections` private helper (AC: #2)
  - [ ] 5.1 RED: Write test for `_split_into_epic_sections(markdown: str) -> list[str]`. Given the full epics markdown content with multiple epics (each starting with `### Epic N:`), verify it splits the content into separate epic sections. Each section starts at `### Epic N:` and ends just before the next `### Epic N:` or `---` separator or end of file.
  - [ ] 5.2 GREEN: Implement `_split_into_epic_sections`. Use regex `re.split` on the `### Epic` boundary pattern.
  - [ ] 5.3 RED: Write test for `_split_into_epic_sections` with a file containing only one epic. Verify it returns a list with one element.
  - [ ] 5.4 GREEN: Implement single-epic handling.
  - [ ] 5.5 RED: Write test for `_split_into_epic_sections` with content that has sections after the epics (e.g., "### Dependency & Parallelism Map"). Verify non-epic sections are NOT included in the results.
  - [ ] 5.6 GREEN: Filter non-epic sections.
  - [ ] 5.7 REFACTOR: Clean up.

- [ ] Task 6: Implement `_split_into_story_blocks` private helper (AC: #2)
  - [ ] 6.1 RED: Write test for `_split_into_story_blocks(epic_section: str) -> list[str]`. Given an epic section containing multiple stories (each starting with `#### Story N.M:`), verify it splits into separate story blocks. Each block starts at `#### Story` and ends just before the next `#### Story` or end of section.
  - [ ] 6.2 GREEN: Implement `_split_into_story_blocks`. Use regex split on the `#### Story` boundary.
  - [ ] 6.3 RED: Write test with an epic that has no stories. Verify it returns an empty list.
  - [ ] 6.4 GREEN: Implement no-stories case.
  - [ ] 6.5 REFACTOR: Clean up.

- [ ] Task 7: Create `parse_bmad_story` step function (AC: #1, #2, #3)
  - [ ] 7.1 RED: Write test for `parse_bmad_story(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given `ctx.inputs` contains `bmad_file_path="path/to/epics.md"`, mock `io_ops.read_bmad_file` to return sample BMAD markdown with one epic containing one story. Verify it returns `IOSuccess(WorkflowContext)` with outputs containing `parsed_epics` (list of `BmadEpic`) and `parsed_stories` (list of `BmadStory`).
  - [ ] 7.2 GREEN: Implement `parse_bmad_story` step. Extracts `bmad_file_path` from `ctx.inputs`. Calls `io_ops.read_bmad_file`. Parses the markdown using the private helpers. Returns IOSuccess with parsed data in outputs.
  - [ ] 7.3 RED: Write test for `parse_bmad_story` with multiple epics and multiple stories. Mock `io_ops.read_bmad_file` to return a markdown string with 2 epics, each containing 2-3 stories. Verify all stories are parsed with correct epic-to-story relationships (correct epic_number on each story).
  - [ ] 7.4 GREEN: Implement multi-epic, multi-story parsing.
  - [ ] 7.5 RED: Write test for `parse_bmad_story` when `bmad_file_path` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="parse_bmad_story"`.
  - [ ] 7.6 GREEN: Implement missing input validation.
  - [ ] 7.7 RED: Write test for `parse_bmad_story` when `bmad_file_path` is not a string. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"`.
  - [ ] 7.8 GREEN: Implement non-string type validation.
  - [ ] 7.9 RED: Write test for `parse_bmad_story` when `io_ops.read_bmad_file` returns `IOFailure` (file not found). Verify the step returns `IOFailure` with appropriate PipelineError.
  - [ ] 7.10 GREEN: Implement file read failure propagation.
  - [ ] 7.11 RED: Write test for `parse_bmad_story` when the markdown contains no parseable epics. Verify it returns `IOFailure(PipelineError)` with `error_type="ParseError"` and message indicating no epics found.
  - [ ] 7.12 GREEN: Implement empty parse result handling.
  - [ ] 7.13 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 8: Register step in steps/__init__.py and engine step registry (AC: #4)
  - [ ] 8.1 RED: Write test that `parse_bmad_story` is importable from `adws.adw_modules.steps`. Verify it appears in `__all__`.
  - [ ] 8.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py` in a new "Bridge steps (BMAD-to-Beads)" section.
  - [ ] 8.3 RED: Write test that `_STEP_REGISTRY` in `adws/adw_modules/engine/executor.py` contains an entry for `"parse_bmad_story"`.
  - [ ] 8.4 GREEN: Add entry to `_STEP_REGISTRY` in executor.py.
  - [ ] 8.5 REFACTOR: Verify imports are consistent with the rest of the module.

- [ ] Task 9: Edge case and malformed input tests (AC: #3, #4)
  - [ ] 9.1 RED: Write test for `parse_bmad_story` with a BMAD file that has stories with empty acceptance criteria (the `**Acceptance Criteria:**` header exists but no content follows). Verify the story is parsed with `acceptance_criteria=""`.
  - [ ] 9.2 GREEN: Ensure empty AC extraction works.
  - [ ] 9.3 RED: Write test for `parse_bmad_story` with a BMAD file that has a story with missing "As a / I want / So that" user story but does have acceptance criteria. Verify the story is parsed with `user_story=""` and the AC is preserved.
  - [ ] 9.4 GREEN: Ensure missing user story handling works.
  - [ ] 9.5 RED: Write test for `parse_bmad_story` with a BMAD file that has malformed epic headers (e.g., `### Epic X: Missing Number`). Verify it returns `IOFailure(PipelineError)` with `error_type="ParseError"` identifying the malformed header.
  - [ ] 9.6 GREEN: Implement malformed header detection.
  - [ ] 9.7 RED: Write test for `parse_bmad_story` with a BMAD file that has malformed story headers (e.g., `#### Story X: Missing Numbers`). Verify it returns `IOFailure(PipelineError)` with `error_type="ParseError"`.
  - [ ] 9.8 GREEN: Implement malformed story header detection.
  - [ ] 9.9 RED: Write test for `parse_bmad_story` with a completely empty file. Verify it returns `IOFailure(PipelineError)` with `error_type="ParseError"` and message indicating the file is empty or has no content.
  - [ ] 9.10 GREEN: Implement empty content handling.
  - [ ] 9.11 RED: Write test for `parse_bmad_story` with a file that has YAML front matter (the `---` delimited block at the top of the epics file). Verify the front matter is skipped and parsing starts from the actual markdown content.
  - [ ] 9.12 GREEN: Implement front matter skipping.
  - [ ] 9.13 REFACTOR: Clean up edge case handling.

- [ ] Task 10: Integration tests with realistic BMAD content (AC: #2, #4)
  - [ ] 10.1 RED: Write integration test using a subset of the ACTUAL epics.md format. Include at least 2 epics with 2-3 stories each (copy realistic content from the real epics file). Verify all stories are extracted correctly with the right epic-to-story relationships, titles, user stories, acceptance criteria, and FR references.
  - [ ] 10.2 GREEN: Ensure integration with realistic content works.
  - [ ] 10.3 RED: Write integration test verifying `raw_content` preservation. For each parsed story, verify that the `raw_content` field contains the complete story text as it appeared in the original markdown -- suitable for use as a Beads issue body in Story 6.2.
  - [ ] 10.4 GREEN: Ensure raw content is preserved correctly.
  - [ ] 10.5 RED: Write integration test verifying slug generation for all parsed stories. Verify slugs follow the `{epic_number}-{story_number}-{slugified-title}` pattern and are URL-safe (lowercase, hyphens, no special characters).
  - [ ] 10.6 GREEN: Ensure slugs are correct.
  - [ ] 10.7 REFACTOR: Clean up integration tests.

- [ ] Task 11: Verify full integration and quality gates (AC: #5)
  - [ ] 11.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 11.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 11.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 5.4)

**io_ops.py** has 24 public functions + 4 private helpers + 1 async helper + 1 internal exception + 1 sanitizer:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_shell_command(command: str, *, timeout: int | None = None, cwd: str | None = None) -> IOResult[ShellResult, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[None, PipelineError]: ...
def run_jest_tests() -> IOResult[VerifyResult, PipelineError]: ...
def run_playwright_tests() -> IOResult[VerifyResult, PipelineError]: ...
def run_mypy_check() -> IOResult[VerifyResult, PipelineError]: ...
def run_ruff_check() -> IOResult[VerifyResult, PipelineError]: ...
def read_prime_file(path: str) -> IOResult[str, PipelineError]: ...
def get_directory_tree(root: str, *, max_depth: int = 3) -> IOResult[str, PipelineError]: ...
def load_command_workflow(workflow_name: str) -> IOResult[Workflow, PipelineError]: ...
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
def run_beads_show(issue_id: str) -> IOResult[str, PipelineError]: ...
def run_beads_close(issue_id: str, reason: str) -> IOResult[ShellResult, PipelineError]: ...
def run_beads_update_notes(issue_id: str, notes: str) -> IOResult[ShellResult, PipelineError]: ...
def write_hook_log(session_id: str, event_json: str) -> IOResult[None, PipelineError]: ...
def write_context_bundle(session_id: str, entry_json: str) -> IOResult[None, PipelineError]: ...
def read_context_bundle(session_id: str) -> IOResult[str, PipelineError]: ...
def list_context_bundles() -> IOResult[list[str], PipelineError]: ...
def write_security_log(session_id: str, entry_json: str) -> IOResult[None, PipelineError]: ...
def write_stderr(message: str) -> IOResult[None, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError, _find_project_root(), _build_verify_result(), _build_tree_lines(), _EXCLUDED_DIRS, _sanitize_session_id()
```

**types.py** has: `HookEvent` (with `to_jsonl()`), `FileTrackEntry` (with `to_jsonl()`), `SecurityLogEntry` (with `to_jsonl()`), `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports 19 steps: `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `block_dangerous_command`, `block_dangerous_command_safe`, `build_feedback_context`, `check_sdk_available`, `execute_shell_step`, `implement_step`, `log_hook_event`, `log_hook_event_safe`, `refactor_step`, `run_jest_step`, `run_mypy_step`, `run_playwright_step`, `run_ruff_step`, `track_file_operation`, `track_file_operation_safe`, `verify_tests_fail`, `write_failing_tests`.

**engine/executor.py** `_STEP_REGISTRY` has 16 entries.

**workflows/__init__.py** has 5 registered workflows: `implement_close`, `implement_verify_close`, `convert_stories_to_beads` (empty steps -- to be populated by Epic 6), `verify`, `sample`. Plus `WorkflowName` registry class with 5 names.

**commands/** has: `dispatch.py`, `registry.py` (6 registered commands), `types.py` (`CommandSpec`), `verify.py`, `prime.py`, `build.py`, `implement.py`, `_finalize.py`, `load_bundle.py`.

**hooks/** has: `__init__.py`, `event_logger.py`, `file_tracker.py`, `command_blocker.py`.

**.claude/hooks/** has: `hook_logger.sh`, `file_tracker.sh`, `command_blocker.sh`.

**.claude/commands/** has: `adws-verify.md`, `adws-prime.md`, `adws-build.md`, `adws-implement.md`, `adws-load-bundle.md`.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 867 tests (excluding 5 enemy tests), 100% line+branch coverage.

**Current source file count**: 99 files tracked by mypy.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: parse_bmad_story Architecture

This story creates a **pure logic heavy** step with a thin I/O tail -- most of the work is markdown parsing (regex, string splitting) with a single I/O call (`read_bmad_file`). The architecture document explicitly classifies `parse_bmad_story.py` in this category:

> | Balanced | `parse_bmad_story.py` (markdown parsing + file read) | Mix of logic tests and mocked I/O |

```
Layer 1: Step Function (testable core)
  adws/adw_modules/steps/parse_bmad_story.py
    parse_bmad_story()             <-- public step function
    _parse_epic_header()           <-- pure regex parsing (no I/O)
    _parse_story_block()           <-- pure regex parsing (no I/O)
    _split_into_epic_sections()    <-- pure string splitting (no I/O)
    _split_into_story_blocks()     <-- pure string splitting (no I/O)
    _generate_slug()               <-- pure string transformation (no I/O)

Layer 2: I/O Boundary
  adws/adw_modules/io_ops.py
    read_bmad_file()               <-- file read (new function this story)

Layer 3: Data Models
  adws/adw_modules/types.py
    BmadStory                      <-- frozen dataclass (new this story)
    BmadEpic                       <-- frozen dataclass (new this story)
```

### Design: BMAD Markdown Structure

The parser must handle the specific markdown format used in `_bmad-output/planning-artifacts/epics.md`. Key structural patterns:

**File structure:**
```markdown
---
YAML front matter (skip this)
---

# title

## Overview
(skip this section)

## Requirements Inventory
(skip this section)

## Epic List

### Epic N: Title

Description paragraph(s)...

**FRs covered:** FR1, FR2, FR3

**Notes:** Optional notes...

#### Story N.M: Title

As a [role],
I want [capability],
So that [benefit].

**Acceptance Criteria:**

**Given** condition
**When** action
**Then** result
**And** additional result

#### Story N.M+1: Title
(next story...)

---

### Epic N+1: Title
(next epic...)

---

### Dependency & Parallelism Map
(non-epic section -- skip)
```

**Key parsing rules:**
1. Skip YAML front matter (between `---` markers at top)
2. Skip sections before `## Epic List` (or first `### Epic`)
3. Split epics on `### Epic N:` boundaries
4. Within each epic, split stories on `#### Story N.M:` boundaries
5. Extract user story from "As a/I want/So that" pattern
6. Extract acceptance criteria from `**Acceptance Criteria:**` to next story or end of epic
7. Extract FRs from `**FRs covered:** FRx, FRy, FRz` line
8. Skip non-epic `###` sections (e.g., "### Dependency & Parallelism Map")
9. `raw_content` captures the entire story block as-is (preserving markdown formatting)

### Design: Slug Generation

Slugs are used for file naming and identification in downstream stories (6.2, 6.3). The slug format must match the existing BMAD story file naming convention visible in `sprint-status.yaml`:

```
6-1-bmad-markdown-parser
6-2-beads-issue-creator-with-workflow-tags
6-3-bidirectional-tracking-and-convert-stories-to-beads-command
```

Algorithm:
1. Start with `{epic_number}-{story_number}-{title}`
2. Convert to lowercase
3. Replace spaces and non-alphanumeric characters with hyphens
4. Collapse multiple hyphens to single hyphen
5. Strip leading/trailing hyphens

### Design: New io_ops Function

One new io_ops function is needed:

**`read_bmad_file(path: str) -> IOResult[str, PipelineError]`**
- Uses `_find_project_root()` (existing helper)
- Resolves path relative to project root
- Delegates to `read_file()` for actual I/O
- Returns `IOSuccess(contents)` on success
- Returns `IOFailure(PipelineError)` with `error_type="FileNotFoundError"` or `"PermissionError"` on failure
- Pattern follows `read_prime_file()` exactly

This brings io_ops to ~25 public functions. Still under the split threshold.

### Design: New Data Models in types.py

Two new frozen dataclasses:

```python
@dataclass(frozen=True)
class BmadStory:
    """Parsed BMAD story content (FR24)."""
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
    """Parsed BMAD epic with contained stories."""
    epic_number: int
    title: str
    description: str
    frs_covered: list[str] = field(default_factory=list)
    stories: list[BmadStory] = field(default_factory=list)
```

These follow the same pattern as `HookEvent`, `FileTrackEntry`, and `SecurityLogEntry` -- frozen dataclasses in `types.py`.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_parse_bmad_story.py` -- tests for `parse_bmad_story`, `_parse_epic_header`, `_parse_story_block`, `_split_into_epic_sections`, `_split_into_story_blocks`, `_generate_slug`
- `adws/tests/adw_modules/test_types_bmad.py` -- tests for `BmadStory` and `BmadEpic` dataclasses
- `adws/tests/integration/test_bmad_parser.py` -- integration tests with realistic BMAD content

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `read_bmad_file` tests
- `adws/tests/adw_modules/steps/test_steps_init.py` (if exists) -- verify new export
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entry

**Mock targets**:
- `adws.adw_modules.io_ops.read_bmad_file` -- mock in step tests
- No SDK mocking needed -- this story is pure markdown parsing + file read

**Recommended test fixtures** (in conftest.py or test file):
- `sample_bmad_single_story` -- minimal BMAD markdown with one epic, one story
- `sample_bmad_multi_epic` -- BMAD markdown with 2 epics, 2-3 stories each
- `sample_bmad_malformed` -- BMAD markdown with invalid headers
- `sample_bmad_with_front_matter` -- BMAD markdown with YAML front matter

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed.

### Architecture Compliance

- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `read_bmad_file` is the io_ops function; no direct file access in step logic.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR17**: This story does NOT interact with Beads. That is Story 6.2.
- **NFR19**: BMAD files are read during conversion only (not during execution workflows). The `read_bmad_file` io_ops function is called exclusively by the `parse_bmad_story` step which is part of the `convert_stories_to_beads` workflow (dispatchable=False, manually invoked).
- **FR24**: Parse BMAD epic/story markdown and extract full story content.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Immutability**: All dataclasses are frozen. `WorkflowContext` updated via `with_updates()`.

### What NOT to Do

- Do NOT create Beads issues in this story -- that is Story 6.2.
- Do NOT write beads_id back to BMAD files -- that is Story 6.3.
- Do NOT embed workflow tags -- that is Story 6.2.
- Do NOT create a fail-open wrapper for this step. Unlike hooks (which must fail-open per NFR4), this step is a pipeline step that SHOULD fail visibly if parsing fails -- the error propagates through ROP and the workflow handles it.
- Do NOT create CLI hooks or SDK HookMatchers. This is not a hook -- it is a pipeline step.
- Do NOT read BMAD files during execution workflows. The `parse_bmad_story` step exists only in the `convert_stories_to_beads` workflow.
- Do NOT change existing step functions, workflows, or engine logic (except adding step registry entries and __init__.py exports).
- Do NOT change the existing io_ops functions.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()`.
- Do NOT put step-internal types (`_parse_epic_header` etc.) in `types.py` -- only `BmadStory` and `BmadEpic` go in types.py because they are used by other steps (6.2, 6.3).
- Do NOT change the IOResult type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT import `claude-agent-sdk` or `subprocess` in the step module.

### Relationship to Adjacent Stories

- **Story 6.2** (successor): Beads issue creator -- consumes `BmadStory` objects produced by this parser, creates Beads issues via `bd create`, embeds workflow tags.
- **Story 6.3** (successor): Bidirectional tracking -- writes beads_id back to BMAD files, orchestrates the full `/convert-stories-to-beads` command.
- **Epic 6 completion**: This is the FIRST story in Epic 6. Stories 6.2 and 6.3 depend on the `BmadStory`/`BmadEpic` types and `parse_bmad_story` step defined here.

### Relationship to Architecture

From the architecture document:

**FR-to-Structure mapping (BMAD-to-Beads Bridge section):**
> **BMAD-to-Beads Bridge (FR23-27)** | `adws/adw_modules/steps/parse_bmad_story.py`, `create_beads_issue.py`, `write_beads_id.py` | `adws/workflows/convert_stories_to_beads.py`

**Architecture Step Naming:**
> `parse_bmad_story.py` (not `bmad_parser.py` or `story_parsing.py`)

**Architecture Testing Strategy:**
> | Balanced | `parse_bmad_story.py` (markdown parsing + file read) | Mix of logic tests and mocked I/O |

**Architecture Integration Points:**
> `read_bmad_story()` and `write_beads_id_to_bmad()` are called exclusively by steps in `convert_stories_to_beads`.

Note: The architecture uses `read_bmad_story()` as the io_ops function name. We use `read_bmad_file()` to follow the convention of the existing `read_file()` and `read_prime_file()` functions -- it reads a file, not a parsed story. The parsed story is the step's output.

**Architecture Workflow Composition:**
> `convert_stories_to_beads.py` | `parse_bmad_story` -> `create_beads_issue` -> `write_beads_id` (all step modules)

This story implements only the first step (`parse_bmad_story`) of this three-step workflow.

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/parse_bmad_story.py` -- `parse_bmad_story()`, `_parse_epic_header()`, `_parse_story_block()`, `_split_into_epic_sections()`, `_split_into_story_blocks()`, `_generate_slug()`
- `adws/tests/adw_modules/steps/test_parse_bmad_story.py` -- step logic + private helper tests
- `adws/tests/adw_modules/test_types_bmad.py` -- BmadStory and BmadEpic dataclass tests
- `adws/tests/integration/test_bmad_parser.py` -- integration tests with realistic content

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `read_bmad_file()` function
- `adws/adw_modules/types.py` -- add `BmadStory` and `BmadEpic` frozen dataclasses
- `adws/adw_modules/steps/__init__.py` -- add `parse_bmad_story` export in new "Bridge steps" section
- `adws/adw_modules/engine/executor.py` -- add `parse_bmad_story` to `_STEP_REGISTRY`
- `adws/tests/adw_modules/test_io_ops.py` -- add `read_bmad_file` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains new entry

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 6] -- Epic summary: "BMAD-to-Beads Story Converter"
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `parse_bmad_story.py` in `adws/adw_modules/steps/`, workflow composition
- [Source: _bmad-output/planning-artifacts/architecture.md#Testing Strategy Notes] -- `parse_bmad_story.py` classified as "Balanced" (markdown parsing + file read)
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form, function matches filename
- [Source: _bmad-output/planning-artifacts/architecture.md#Step Internal Structure] -- Step pattern with one public function per module
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step creation checklist (6 mandatory items)
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR24 maps to Epic 6
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- `read_bmad_story()` conversion-only scope
- [Source: adws/adw_modules/io_ops.py] -- 24 public functions, read_prime_file (pattern for read_bmad_file), _find_project_root()
- [Source: adws/adw_modules/types.py] -- HookEvent, FileTrackEntry, SecurityLogEntry (pattern for BmadStory/BmadEpic)
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (16 entries to extend)
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, _CONVERT_STORIES_TO_BEADS (empty steps to be populated by Epic 6)
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures

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

From Story 5.4 learnings:
- **867 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **99 source files**: Current file count tracked by mypy.
- **io_ops at 24 public functions**: This story adds 1 new io_ops function (`read_bmad_file`) bringing total to 25.
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals.
- **Step creation checklist**: errors.py -> io_ops.py -> step -> __init__.py -> tests -> verify. This story does NOT add new error types to errors.py (it uses existing `PipelineError` with different `error_type` strings).
- **Frozen dataclasses**: All new data models must be frozen. Use `field(default_factory=list)` for mutable defaults.

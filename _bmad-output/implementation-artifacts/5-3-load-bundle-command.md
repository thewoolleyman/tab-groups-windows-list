# Story 5.3: /load_bundle Command

Status: review-complete

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want to invoke `/load_bundle` to reload context from a previous session,
so that I can resume work with full awareness of what was done in a prior session.

## Acceptance Criteria

1. **Given** a context bundle exists from a previous session in `agents/context_bundles/`, **When** I invoke `/load_bundle`, **Then** the command reads the bundle and loads file context into the current session (FR35) **And** the command follows the .md entry point + Python module pattern from Epic 4 (FR28).

2. **Given** the specified bundle does not exist, **When** /load_bundle is invoked, **Then** a clear error message indicates the bundle was not found **And** available bundles are listed for the user to choose from.

3. **Given** /load_bundle command code, **When** I run tests, **Then** tests cover: successful load, missing bundle, bundle listing **And** 100% coverage is maintained (NFR9).

4. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [ ] Task 1: Define io_ops functions for reading context bundles (AC: #1, #2)
  - [ ] 1.1 RED: Write test for `io_ops.read_context_bundle(session_id: str) -> IOResult[str, PipelineError]`. Given a session-specific JSONL file exists at `agents/context_bundles/<session_id>.jsonl`, verify it reads the full file content and returns `IOSuccess(content)`. The content should be the raw JSONL string (each line is a JSON entry from `FileTrackEntry.to_jsonl()`).
  - [ ] 1.2 GREEN: Implement `read_context_bundle` in `adws/adw_modules/io_ops.py`. Uses `_find_project_root()` to locate project root. Uses `_sanitize_session_id()` for path traversal protection. Opens the file in read mode. Returns `IOSuccess(content)`.
  - [ ] 1.3 RED: Write test for `read_context_bundle` when the bundle file does not exist. Verify it returns `IOFailure(PipelineError)` with `error_type="ContextBundleNotFoundError"` and `step_name="io_ops.read_context_bundle"`. The error message should include the session_id.
  - [ ] 1.4 GREEN: Implement `FileNotFoundError` handling in `read_context_bundle`.
  - [ ] 1.5 RED: Write test for `read_context_bundle` when the file read fails (e.g., PermissionError). Verify it returns `IOFailure(PipelineError)` with `error_type="ContextBundleReadError"`.
  - [ ] 1.6 GREEN: Implement PermissionError and OSError handling in `read_context_bundle`.
  - [ ] 1.7 RED: Write test for `io_ops.list_context_bundles() -> IOResult[list[str], PipelineError]`. Given `agents/context_bundles/` contains files `session-abc.jsonl` and `session-def.jsonl`, verify it returns `IOSuccess(["session-abc", "session-def"])` (session IDs without the `.jsonl` extension). Verify the list is sorted alphabetically.
  - [ ] 1.8 GREEN: Implement `list_context_bundles` in `adws/adw_modules/io_ops.py`. Uses `_find_project_root()`. Lists all `.jsonl` files in `agents/context_bundles/`. Strips the `.jsonl` extension to return session IDs. Returns sorted list.
  - [ ] 1.9 RED: Write test for `list_context_bundles` when the `agents/context_bundles/` directory does not exist. Verify it returns `IOSuccess([])` (empty list, not an error -- there simply are no bundles yet).
  - [ ] 1.10 GREEN: Implement missing directory handling (return empty list).
  - [ ] 1.11 RED: Write test for `list_context_bundles` when `agents/context_bundles/` exists but is empty. Verify it returns `IOSuccess([])`.
  - [ ] 1.12 GREEN: Implement empty directory handling.
  - [ ] 1.13 RED: Write test for `list_context_bundles` when a read of the directory fails (PermissionError). Verify it returns `IOFailure(PipelineError)` with `error_type="ContextBundleListError"`.
  - [ ] 1.14 GREEN: Implement PermissionError handling.
  - [ ] 1.15 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 2: Create `LoadBundleResult` data model (AC: #1, #2)
  - [ ] 2.1 RED: Write test for `LoadBundleResult` frozen dataclass in `adws/adw_modules/commands/load_bundle.py`. Verify it has fields: `success` (bool), `session_id` (str), `file_entries` (list of dicts -- parsed JSONL entries), `summary` (str, human-readable description), `available_bundles` (list[str], populated when bundle not found).
  - [ ] 2.2 GREEN: Implement `LoadBundleResult` as a frozen dataclass.
  - [ ] 2.3 REFACTOR: Clean up.

- [ ] Task 3: Create `_parse_bundle_content` helper (AC: #1)
  - [ ] 3.1 RED: Write test for `_parse_bundle_content(content: str) -> list[dict[str, object]]`. Given valid JSONL content (multiple lines, each a JSON object from `FileTrackEntry.to_jsonl()`), verify it parses each line and returns a list of dicts. Each dict should have keys: `timestamp`, `file_path`, `operation`, `session_id`, `hook_name`.
  - [ ] 3.2 GREEN: Implement `_parse_bundle_content`. Uses `json.loads()` on each non-empty line. Collects parsed dicts into a list.
  - [ ] 3.3 RED: Write test for `_parse_bundle_content` when a line contains invalid JSON. Verify it skips the malformed line (graceful degradation) and continues parsing remaining lines. Does NOT fail the entire parse for one bad line.
  - [ ] 3.4 GREEN: Implement invalid-line-skip logic with try/except around `json.loads()`.
  - [ ] 3.5 RED: Write test for `_parse_bundle_content` when content is empty string. Verify it returns an empty list.
  - [ ] 3.6 GREEN: Implement empty content handling.
  - [ ] 3.7 RED: Write test for `_parse_bundle_content` when content has trailing newlines or blank lines. Verify blank lines are skipped and valid lines are parsed.
  - [ ] 3.8 GREEN: Implement blank line filtering.
  - [ ] 3.9 REFACTOR: Clean up.

- [ ] Task 4: Create `run_load_bundle_command` function (AC: #1, #2)
  - [ ] 4.1 RED: Write test for `run_load_bundle_command(ctx: WorkflowContext) -> IOResult[LoadBundleResult, PipelineError]`. Given `ctx.inputs` contains `session_id="session-abc123"` and `io_ops.read_context_bundle` returns `IOSuccess` with valid JSONL content, verify it returns `IOSuccess(LoadBundleResult)` with `success=True`, correct `session_id`, populated `file_entries`, a summary indicating how many file entries were loaded, and `available_bundles=[]`.
  - [ ] 4.2 GREEN: Implement `run_load_bundle_command`. Extracts `session_id` from `ctx.inputs`. Calls `io_ops.read_context_bundle(session_id)`. Parses content with `_parse_bundle_content`. Builds `LoadBundleResult`.
  - [ ] 4.3 RED: Write test for `run_load_bundle_command` when `session_id` is missing from inputs. Verify it calls `io_ops.list_context_bundles()` and returns `IOFailure(PipelineError)` with `error_type="MissingSessionIdError"` and the error context includes `available_bundles` from the listing.
  - [ ] 4.4 GREEN: Implement missing session_id handling with bundle listing.
  - [ ] 4.5 RED: Write test for `run_load_bundle_command` when `session_id` is provided but the bundle does not exist (io_ops returns ContextBundleNotFoundError). Verify it calls `io_ops.list_context_bundles()` and returns `IOFailure(PipelineError)` with `error_type="ContextBundleNotFoundError"` and the error context includes `available_bundles`.
  - [ ] 4.6 GREEN: Implement bundle-not-found handling with available bundle listing.
  - [ ] 4.7 RED: Write test for `run_load_bundle_command` when `io_ops.list_context_bundles()` itself fails (e.g., PermissionError). Verify the error from `read_context_bundle` is still returned, with `available_bundles` as `[]` (graceful degradation -- listing failure should not mask the primary error).
  - [ ] 4.8 GREEN: Implement list_context_bundles failure handling.
  - [ ] 4.9 RED: Write test for `run_load_bundle_command` when the bundle exists but is empty (zero file entries). Verify it returns `IOSuccess(LoadBundleResult)` with `success=True`, `file_entries=[]`, and summary indicating "0 file entries loaded".
  - [ ] 4.10 GREEN: Implement empty bundle handling.
  - [ ] 4.11 RED: Write test for `run_load_bundle_command` when `session_id` is empty string. Verify same behavior as missing session_id -- calls list_context_bundles and returns error.
  - [ ] 4.12 GREEN: Implement empty string validation.
  - [ ] 4.13 REFACTOR: Clean up, verify mypy/ruff.

- [ ] Task 5: Wire `load_bundle` into command dispatch (AC: #1)
  - [ ] 5.1 RED: Write test that `run_command("load_bundle", ctx)` routes to `run_load_bundle_command`. Given `ctx.inputs` has `session_id="session-abc"` and `io_ops.read_context_bundle` returns valid content, verify `run_command` returns `IOSuccess(WorkflowContext)` with `load_bundle_result` in outputs.
  - [ ] 5.2 GREEN: Add `load_bundle` specialized handler to `_dispatch_specialized` in `adws/adw_modules/commands/dispatch.py`. Import `LoadBundleResult` and `run_load_bundle_command` from `adws.adw_modules.commands.load_bundle`. The handler calls `run_load_bundle_command(ctx)` and wraps the result into `ctx.merge_outputs({"load_bundle_result": lr})`.
  - [ ] 5.3 RED: Write test that `run_command("load_bundle", ctx)` with missing session_id returns `IOFailure` with `MissingSessionIdError`.
  - [ ] 5.4 GREEN: Verify routing works for error path.
  - [ ] 5.5 REFACTOR: Clean up dispatch.py changes, verify mypy/ruff.

- [ ] Task 6: Create `.claude/commands/adws-load-bundle.md` entry point (AC: #1)
  - [ ] 6.1 RED: Write test that `.claude/commands/adws-load-bundle.md` exists and contains the expected content structure (command name, usage, implementation delegation to Python module).
  - [ ] 6.2 GREEN: Create `.claude/commands/adws-load-bundle.md` with: command description, usage instructions (how to specify session_id), explanation that it lists available bundles when session_id is missing, and delegation note to `uv run python -m adws.adw_modules.commands.dispatch load_bundle`.
  - [ ] 6.3 REFACTOR: Verify markdown structure matches other adws-*.md command files.

- [ ] Task 7: Integration tests -- end-to-end load_bundle scenarios (AC: #1, #2, #3)
  - [ ] 7.1 RED: Write integration test: full success path. Mock `io_ops.read_context_bundle` to return valid JSONL content with multiple FileTrackEntry records. Invoke `run_load_bundle_command` with session_id in context. Verify `LoadBundleResult` contains all parsed file entries with correct fields, summary is accurate, and success is True.
  - [ ] 7.2 GREEN: Ensure integration success path works.
  - [ ] 7.3 RED: Write integration test: bundle not found with available alternatives. Mock `io_ops.read_context_bundle` to return `IOFailure(ContextBundleNotFoundError)`. Mock `io_ops.list_context_bundles` to return `IOSuccess(["session-old", "session-recent"])`. Verify the error message mentions the requested session_id and the response includes available bundles.
  - [ ] 7.4 GREEN: Ensure not-found-with-listing integration path works.
  - [ ] 7.5 RED: Write integration test: no session_id provided. Invoke `run_load_bundle_command` with empty inputs. Mock `io_ops.list_context_bundles` to return available bundles. Verify error includes `MissingSessionIdError` and available_bundles.
  - [ ] 7.6 GREEN: Ensure missing-session integration path works.
  - [ ] 7.7 RED: Write integration test: dispatch routing. Call `run_command("load_bundle", ctx)` with mocked io_ops. Verify it routes correctly and returns WorkflowContext with `load_bundle_result` in outputs.
  - [ ] 7.8 GREEN: Ensure dispatch routing integration works.
  - [ ] 7.9 RED: Write integration test: bundle with malformed lines. Mock `io_ops.read_context_bundle` to return content with one valid JSONL line and one malformed line. Verify `LoadBundleResult` contains only the valid entry and summary reflects the actual count.
  - [ ] 7.10 GREEN: Ensure malformed line tolerance works.
  - [ ] 7.11 REFACTOR: Clean up integration tests.

- [ ] Task 8: Verify full integration and quality gates (AC: #4)
  - [ ] 8.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [ ] 8.2 Run `uv run mypy adws/` -- strict mode passes
  - [ ] 8.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 5.2)

**io_ops.py** has 21 public functions + 3 private helpers + 1 async helper + 1 internal exception + 1 sanitizer:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_shell_command(command: str, *, timeout: int | None = None, cwd: str | None = None) -> IOResult[ShellResult, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[None, PipelineError]: ...
def _build_verify_result(shell_result: ShellResult, tool_name: str, error_filter: Callable) -> VerifyResult: ...
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
def write_stderr(message: str) -> IOResult[None, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError, _find_project_root(), _build_tree_lines(), _EXCLUDED_DIRS, _sanitize_session_id()
```

**types.py** has: `HookEvent` (with `to_jsonl()`), `FileTrackEntry` (with `to_jsonl()`), `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports 17 steps: `check_sdk_available`, `execute_shell_step`, `implement_step`, `refactor_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`, `write_failing_tests`, `verify_tests_fail`, `log_hook_event`, `log_hook_event_safe`, `track_file_operation`, `track_file_operation_safe`.

**engine/executor.py** `_STEP_REGISTRY` has 14 entries.

**workflows/__init__.py** has 5 registered workflows.

**commands/** has: `dispatch.py` (routes verify, prime, build, implement), `registry.py` (6 registered commands including `load_bundle`), `types.py` (`CommandSpec`), `verify.py`, `prime.py`, `build.py`, `implement.py`, `_finalize.py`.

**hooks/** has: `__init__.py`, `event_logger.py`, `file_tracker.py`.

**.claude/hooks/** has: `hook_logger.sh`, `file_tracker.sh`.

**.claude/commands/** has: `adws-verify.md`, `adws-prime.md`, `adws-build.md`, `adws-implement.md`.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 683 tests (excluding 5 enemy tests), 100% line+branch coverage.

**`load_bundle` is already in the command registry** (`adws/adw_modules/commands/registry.py`) with `workflow_name=None` (non-workflow, specialized handler pattern like `prime`). The dispatch module does NOT yet have a specialized handler for it -- currently returns `NoWorkflowError` if invoked.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: /load_bundle Architecture

The /load_bundle command follows the **non-workflow specialized command** pattern established by `/prime` (Story 4.3):

```
Layer 1: Entry Point (.md command)
  .claude/commands/adws-load-bundle.md --> uv run python -m adws.adw_modules.commands.dispatch load_bundle
                                             |
Layer 2: Command Dispatch                    |
  adws/adw_modules/commands/dispatch.py
    _dispatch_specialized() routes "load_bundle" -> run_load_bundle_command()
                                             |
Layer 3: Command Logic (testable)            |
  adws/adw_modules/commands/load_bundle.py
    run_load_bundle_command()            <-- core logic
    _parse_bundle_content()              <-- JSONL parsing helper
    LoadBundleResult                     <-- result data model
                                             |
Layer 4: I/O Boundary                        |
  adws/adw_modules/io_ops.py
    read_context_bundle()                <-- file read from agents/context_bundles/
    list_context_bundles()               <-- directory listing for available bundles
```

**Key principle:** This is a **read** command. Story 5.2 wrote context bundles; this story reads them. The JSONL format established in Story 5.2 (`FileTrackEntry.to_jsonl()`) is the contract.

### Design: LoadBundleResult Data Model

```python
@dataclass(frozen=True)
class LoadBundleResult:
    """User-facing output of the /load_bundle command.

    success: True when bundle loaded successfully.
    session_id: The session ID whose bundle was loaded.
    file_entries: Parsed JSONL entries (list of dicts).
    summary: Human-readable description of what was loaded.
    available_bundles: Populated when bundle not found (AC #2).
    """

    success: bool
    session_id: str
    file_entries: list[dict[str, object]]
    summary: str
    available_bundles: list[str] = field(default_factory=list)
```

### Design: New io_ops Functions

Two new io_ops functions are needed:

1. **`read_context_bundle(session_id: str) -> IOResult[str, PipelineError]`**
   - Uses `_find_project_root()` (existing helper) to locate project root
   - Uses `_sanitize_session_id()` (existing from Story 5.1) to prevent path traversal
   - Reads `agents/context_bundles/<sanitized_session_id>.jsonl`
   - Returns `IOSuccess(content)` on success
   - Returns `IOFailure(PipelineError)` with `error_type="ContextBundleNotFoundError"` for `FileNotFoundError`
   - Returns `IOFailure(PipelineError)` with `error_type="ContextBundleReadError"` for `PermissionError`/`OSError`

2. **`list_context_bundles() -> IOResult[list[str], PipelineError]`**
   - Uses `_find_project_root()` (existing helper)
   - Lists all `.jsonl` files in `agents/context_bundles/`
   - Returns sorted list of session IDs (filename without `.jsonl` extension)
   - Returns `IOSuccess([])` if directory does not exist or is empty
   - Returns `IOFailure(PipelineError)` with `error_type="ContextBundleListError"` for `PermissionError`

This brings io_ops to ~23 public functions. Still under the 300-line split threshold.

### Design: JSONL Parsing

The bundle files contain lines produced by `FileTrackEntry.to_jsonl()`:
```json
{"timestamp":"2026-02-02T10:30:00+00:00","file_path":"/path/to/file.py","operation":"read","session_id":"session-abc123","hook_name":"file_tracker"}
{"timestamp":"2026-02-02T10:30:01+00:00","file_path":"/path/to/other.py","operation":"write","session_id":"session-abc123","hook_name":"file_tracker"}
```

The `_parse_bundle_content(content: str) -> list[dict[str, object]]` helper:
- Splits content by newline
- Filters blank lines
- Parses each line with `json.loads()`
- Skips malformed lines gracefully (does NOT fail the entire parse)
- Returns list of parsed dicts

This is a **pure function** (no I/O) that lives in `commands/load_bundle.py`. It does not go through io_ops because it operates on in-memory content, not files.

### Design: Command Dispatch Integration

The `load_bundle` command is already registered in `registry.py` with `workflow_name=None`. This means it requires a specialized handler in `dispatch.py`, following the same pattern as `prime`:

```python
# In _dispatch_specialized:
if spec.name == "load_bundle":

    def _wrap_lbr(
        lbr: LoadBundleResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs({"load_bundle_result": lbr}),
        )

    return run_load_bundle_command(ctx).bind(_wrap_lbr)
```

### Design: .md Entry Point

Following the pattern established by `adws-prime.md`:

```markdown
# /adws-load-bundle

Reload context from a previous session.

## Usage

Invoke this command to reload context from a previous session's context bundle.
Pass a session_id to load a specific bundle. If no session_id is provided,
available bundles will be listed.

## What it does

1. Reads session-specific JSONL bundle from agents/context_bundles/
2. Parses file tracking entries (file paths, operations, timestamps)
3. Returns structured LoadBundleResult with parsed entries
4. If bundle not found, lists available bundles for selection

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch load_bundle`

The dispatch routes to `run_load_bundle_command` in
`adws.adw_modules.commands.load_bundle`, which reads bundles via
`io_ops.read_context_bundle` and lists available bundles via
`io_ops.list_context_bundles` (FR28, FR35).

All testable logic lives in `adws/adw_modules/commands/load_bundle.py` --
the .md file is the natural language entry point only (FR28).
```

### Design: Error Handling Strategy

| Scenario | Behavior | Error Type |
|----------|----------|------------|
| Bundle found, valid JSONL | Return LoadBundleResult with parsed entries | N/A (success) |
| Bundle found, some malformed lines | Return LoadBundleResult with valid entries only (graceful) | N/A (success) |
| Bundle found, empty content | Return LoadBundleResult with empty file_entries | N/A (success) |
| Bundle not found | List available bundles, return PipelineError | ContextBundleNotFoundError |
| No session_id provided | List available bundles, return PipelineError | MissingSessionIdError |
| Empty string session_id | Same as missing session_id | MissingSessionIdError |
| Read permission error | Return PipelineError | ContextBundleReadError |
| List permission error | Return error from read, with available_bundles=[] | ContextBundleListError |

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/commands/test_load_bundle.py` -- tests for `run_load_bundle_command`, `_parse_bundle_content`, `LoadBundleResult`
- `adws/tests/integration/test_load_bundle.py` -- integration tests for end-to-end scenarios

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `read_context_bundle` and `list_context_bundles` tests
- `adws/tests/adw_modules/commands/test_dispatch.py` -- add `load_bundle` dispatch routing test

**Existing test file for .md validation**:
- `adws/tests/adw_modules/commands/test_command_md_files.py` (if it exists) or new test verifying the .md file exists

**Mock targets**:
- `adws.adw_modules.io_ops.read_context_bundle` -- mock file reads in command tests
- `adws.adw_modules.io_ops.list_context_bundles` -- mock directory listing in command tests
- No SDK mocking needed -- this story is filesystem-only

### Ruff Considerations

- `PLR2004` (magic numbers in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- `S101` (assert usage): Relaxed in test files per pyproject.toml per-file-ignores.
- `ANN` (annotations in tests): Relaxed in test files per pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed. The command module follows the same patterns as `prime.py`.

### Architecture Compliance

- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `read_context_bundle` and `list_context_bundles` are the io_ops functions; no direct file access in command logic.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **FR28**: Command follows .md entry point + Python module pattern.
- **FR35**: Developer can reload previous session context via /load_bundle.
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).
- **Step Signature**: Not applicable -- this is a command, not a step. Command signature: `(WorkflowContext) -> IOResult[LoadBundleResult, PipelineError]`.
- **Immutability**: `LoadBundleResult` is a frozen dataclass. `WorkflowContext` updated via `merge_outputs()`.

### What NOT to Do

- Do NOT create a step function for this -- it's a command with custom logic (like `/prime`), not a workflow step.
- Do NOT write to `agents/context_bundles/` -- this command only reads. Writing is done by Story 5.2's `track_file_operation`.
- Do NOT change the existing `write_context_bundle` io_ops function or `FileTrackEntry` data model.
- Do NOT change the `COMMAND_REGISTRY` in `registry.py` -- `load_bundle` is already registered.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `merge_outputs()`.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()` (lesson from Story 5.1 code review).
- Do NOT create Enemy Unit Tests for this story -- there are no io_ops SDK functions. Context bundle loading is filesystem-based, not SDK-based.
- Do NOT fail the entire bundle parse for one malformed JSONL line -- skip it gracefully.
- Do NOT change any existing step functions, workflows, or engine logic (except adding the dispatch handler).
- Do NOT read BMAD files during this command's execution.

### Security: Path Traversal Protection

The new `read_context_bundle` function MUST use `_sanitize_session_id()` (existing from Story 5.1) to sanitize the `session_id` parameter before constructing the file path. This prevents path traversal attacks where a malicious `session_id` like `../../etc/passwd` would read outside `agents/context_bundles/`. This was a HIGH severity issue caught in Story 5.1's code review (Issue 1) and the fix must be applied consistently.

### Relationship to Adjacent Stories

- **Story 5.2** (predecessor): File tracker & context bundles -- writes to `agents/context_bundles/` in JSONL format using `FileTrackEntry.to_jsonl()`. The JSONL format from Story 5.2 is the contract this story reads.
- **Story 5.4** (next): Dangerous command blocker -- independent from this story, different sub-track (safety vs observability).

### Architecture Output-Only Boundary Exception

Per the architecture document (Section: Integration Points, Output-only boundary):
> "The `agents/` directory (`hook_logs/`, `context_bundles/`, `security_logs/`) is written to during workflow execution but never read from. The sole exception is `/load_bundle`, which reads from `context_bundles/` for manual session reload -- this is human-initiated, never automated. No workflow step reads from `agents/`."

This story implements that documented exception.

### Project Structure Notes

Files to create:
- `adws/adw_modules/commands/load_bundle.py` -- `LoadBundleResult`, `_parse_bundle_content()`, `run_load_bundle_command()`
- `.claude/commands/adws-load-bundle.md` -- .md entry point
- `adws/tests/adw_modules/commands/test_load_bundle.py` -- command logic tests
- `adws/tests/integration/test_load_bundle.py` -- integration tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `read_context_bundle()` and `list_context_bundles()` functions
- `adws/adw_modules/commands/dispatch.py` -- add `load_bundle` specialized handler to `_dispatch_specialized()`
- `adws/tests/adw_modules/test_io_ops.py` -- add `read_context_bundle` and `list_context_bundles` tests
- `adws/tests/adw_modules/commands/test_dispatch.py` -- add dispatch routing test for `load_bundle`

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5] -- Epic summary: "Observability & Safety Hooks"
- [Source: _bmad-output/planning-artifacts/architecture.md#Command Inventory] -- `/load_bundle` backed by `adws/adw_modules/steps/build_context_bundle.py` (NOTE: architecture uses step name; we implement as command module `commands/load_bundle.py` per command pattern -- this is a command, not a pipeline step)
- [Source: _bmad-output/planning-artifacts/architecture.md#Output-only boundary] -- `agents/` directory is write-only except for /load_bundle (documented exception)
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `agents/context_bundles/` directory
- [Source: _bmad-output/planning-artifacts/architecture.md#.gitignore Additions] -- `agents/context_bundles/` is gitignored
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Module naming conventions
- [Source: _bmad-output/implementation-artifacts/5-2-file-tracker-and-context-bundles.md] -- Story 5.2: established JSONL bundle format, FileTrackEntry data model, write_context_bundle io_ops function, _sanitize_session_id() usage
- [Source: adws/adw_modules/commands/prime.py] -- Pattern to follow: non-workflow specialized command with custom logic
- [Source: adws/adw_modules/commands/dispatch.py] -- Dispatch routing pattern for specialized commands
- [Source: adws/adw_modules/commands/registry.py] -- load_bundle already registered with workflow_name=None
- [Source: adws/adw_modules/io_ops.py] -- 21 public functions, _find_project_root(), _sanitize_session_id() helpers, write_context_bundle (write counterpart)
- [Source: adws/adw_modules/types.py] -- FileTrackEntry with to_jsonl() (the format this story reads)
- [Source: .claude/commands/adws-prime.md] -- Pattern to follow for .md entry point
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

From Story 5.2 learnings:
- **683 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **91 source files**: Current file count tracked by mypy.
- **io_ops at 21 public functions**: This story adds 2 new io_ops functions (`read_context_bundle`, `list_context_bundles`) bringing total to 23.
- **_sanitize_session_id()**: MUST be reused for path traversal protection. HIGH severity finding from Story 5.1 code review.
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals. MEDIUM severity finding from Story 5.1 code review.
- **Command pattern**: Follow `prime.py` exactly -- non-workflow command with custom logic, specialized handler in dispatch.py, result dataclass.
- **FileTrackEntry JSONL format**: The contract between Story 5.2 (write) and Story 5.3 (read). Each line is: `{"timestamp":"...","file_path":"...","operation":"...","session_id":"...","hook_name":"..."}`.

From Story 5.2 code review issues to avoid:
1. **Path traversal (HIGH)**: Use `_sanitize_session_id()` -- already exists, just call it.
2. **Private `_inner_value` (MEDIUM)**: Use `unsafe_perform_io()` instead.
3. **Stale docstrings (LOW)**: Keep docstrings accurate when functions are shared.
4. **Type validation (MEDIUM)**: Validate parsed JSON is the expected type (dict) before processing.

## Code Review (Story 5.3)

**Reviewer**: Adversarial code reviewer (Claude Opus 4.5)
**Date**: 2026-02-02
**Quality Gates**: All passing (722 tests, 100% coverage, mypy strict clean, ruff clean)

### Issue 1 (MEDIUM): Non-string session_id silently coerced via str()

**File**: `adws/adw_modules/commands/load_bundle.py`, lines 96-99 (original)
**Problem**: The original validation logic `not session_id or (isinstance(session_id, str) and not session_id.strip())` had a logic hole. If `session_id` was a non-string truthy value (e.g., integer `123`, list `["x"]`), both `not session_id` and `isinstance(session_id, str)` would be `False`, so the condition was `False`. The code then fell through to `sid = str(session_id)`, silently coercing `123` to `"123"` and calling `io_ops.read_context_bundle("123")`. Since `WorkflowContext.inputs` is `dict[str, object]`, non-string values are structurally possible.
**Fix applied**: Changed guard to `not isinstance(session_id, str) or not session_id.strip()` -- rejects non-string values upfront as `MissingSessionIdError`.
**Test added**: `test_run_load_bundle_command_non_string_session_id` in `test_load_bundle.py`.

### Issue 2 (MEDIUM): Missing test for whitespace-only session_id

**File**: `adws/tests/adw_modules/commands/test_load_bundle.py`
**Problem**: The story spec (Task 4.11-4.12) requires testing empty string session_id behaves as missing. There was a test for `""` but none for whitespace-only `"   "`. The implementation explicitly handles this via `.strip()`, but without a dedicated test, the whitespace-strip branch exists without a test demanding it. This violates the TDD principle: "every line exists because a test demanded it."
**Fix applied**: Added `test_run_load_bundle_command_whitespace_session_id` test.

### Issue 3 (LOW): Summary uses awkward `entry(ies)` pluralization

**File**: `adws/adw_modules/commands/load_bundle.py`, line 151 (original)
**Problem**: The summary string `f"Loaded {count} file entry(ies) from session {sid}"` produces grammatically incorrect output: "1 file entry(ies)" or "2 file entry(ies)". The story spec says summary should indicate "how many file entries were loaded" and the empty case should say "0 file entries loaded".
**Fix applied**: Replaced with proper conditional pluralization: `noun = "entry" if count == 1 else "entries"` followed by `f"Loaded {count} file {noun} from session {sid}"`.

### Issue 4 (LOW): `_get_available_bundles` has no direct unit test

**File**: `adws/adw_modules/commands/load_bundle.py`, lines 65-80
**Problem**: The `_get_available_bundles()` helper is only tested indirectly through `run_load_bundle_command`. Its two branches (IOSuccess with data, IOFailure returning []) are exercised but only via integration through the parent function. While not a coverage gap (coverage is 100%), this is a test design concern -- direct tests for this helper would provide faster failure localization.
**No fix applied**: This is a LOW severity style concern. The function is covered indirectly. Adding a direct test would be ideal but is not required.

### Summary

| # | Severity | Issue | Fixed |
|---|----------|-------|-------|
| 1 | MEDIUM | Non-string session_id coerced silently | Yes -- type guard + test |
| 2 | MEDIUM | Missing whitespace-only session_id test | Yes -- test added |
| 3 | LOW | Awkward `entry(ies)` pluralization | Yes -- proper pluralization |
| 4 | LOW | No direct test for `_get_available_bundles` | No -- indirect coverage sufficient |

### Post-Review Quality Gate Results

- `uv run pytest adws/tests/ -m "not enemy"`: 722 passed, 5 skipped, 100% coverage
- `uv run mypy adws/ --strict`: Success, no issues in 94 source files
- `uv run ruff check adws/`: All checks passed

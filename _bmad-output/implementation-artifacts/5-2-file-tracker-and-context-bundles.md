# Story 5.2: File Tracker & Context Bundles

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want files read and written during sessions tracked to context bundles,
so that session activity can be replayed and context can be restored later.

## Acceptance Criteria

1. **Given** a file is read or written during a session, **When** the file tracker processes the event, **Then** the file path and operation type are recorded in a session-specific bundle in `agents/context_bundles/` (FR34).

2. **Given** the file tracker Python module, **When** used by CLI hooks and SDK HookMatchers, **Then** both entry points use the same underlying module with zero duplicated logic (FR36).

3. **Given** the file tracker encounters an error, **When** it fails to record a file operation, **Then** it logs to stderr and does NOT block the observed operation (NFR4).

4. **Given** all file tracker code, **When** I run tests, **Then** tests cover: read tracking, write tracking, session-specific bundling, fail-open behavior **And** 100% coverage is maintained (NFR9).

5. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Define `FileTrackEntry` data model and io_ops context bundle write function (AC: #1)
  - [x] 1.1 RED: Write test for `FileTrackEntry` frozen dataclass in `adws/adw_modules/types.py`. Verify it has fields: `timestamp` (str, ISO 8601 format), `file_path` (str, absolute path of tracked file), `operation` (str, one of "read" or "write"), `session_id` (str), `hook_name` (str, e.g. "file_tracker"). Verify it is immutable (frozen=True). Verify a `to_jsonl()` method returns a single-line JSON string with all fields.
  - [x] 1.2 GREEN: Implement `FileTrackEntry` as a frozen dataclass in `adws/adw_modules/types.py` with `to_jsonl()` method using `json.dumps()`. Follows the same pattern as `HookEvent.to_jsonl()`.
  - [x] 1.3 RED: Write test for `to_jsonl()` output format. Verify it produces valid JSON. Verify it is a single line (no embedded newlines). Verify all fields are present.
  - [x] 1.4 GREEN: Implement any remaining `to_jsonl()` logic.
  - [x] 1.5 RED: Write test for `io_ops.write_context_bundle(session_id: str, entry_json: str) -> IOResult[None, PipelineError]`. Given the target directory `agents/context_bundles/` exists, verify it appends the entry_json string plus newline to a file named `<session_id>.jsonl` within `agents/context_bundles/`. Verify it returns `IOSuccess(None)` on success.
  - [x] 1.6 GREEN: Implement `write_context_bundle` in `adws/adw_modules/io_ops.py`. Uses `_find_project_root()` to locate project root. Creates `agents/context_bundles/` directory if it does not exist (using `Path.mkdir(parents=True, exist_ok=True)`). Opens the file in append mode. Writes the entry_json line. Returns IOSuccess(None). Uses `_sanitize_session_id()` for path traversal protection (same helper from Story 5.1).
  - [x] 1.7 RED: Write test for `write_context_bundle` when the directory cannot be created (e.g., PermissionError). Verify it returns `IOFailure(PipelineError)` with `error_type="ContextBundleWriteError"` and `step_name="io_ops.write_context_bundle"`.
  - [x] 1.8 GREEN: Implement PermissionError and OSError handling in `write_context_bundle`.
  - [x] 1.9 RED: Write test for `write_context_bundle` when the file open/write fails. Verify `IOFailure(PipelineError)` with appropriate error details.
  - [x] 1.10 GREEN: Implement file write error handling.
  - [x] 1.11 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `track_file_operation` step function (AC: #1, #2)
  - [x] 2.1 RED: Write test for `track_file_operation(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` in `adws/adw_modules/steps/track_file_operation.py`. Given `ctx.inputs` contains `file_path="/some/file.py"`, `operation="read"`, `session_id="session-abc123"`, `hook_name="file_tracker"`, verify it constructs a `FileTrackEntry` with current timestamp, calls `io_ops.write_context_bundle(session_id, entry.to_jsonl())`, and returns `IOSuccess(WorkflowContext)` with outputs containing `{"file_tracked": True}`.
  - [x] 2.2 GREEN: Implement `track_file_operation` in `adws/adw_modules/steps/track_file_operation.py`. Constructs `FileTrackEntry` with `datetime.now(tz=UTC).isoformat()` for timestamp, extracts inputs from context, calls io_ops.
  - [x] 2.3 RED: Write test for `track_file_operation` when `file_path` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="track_file_operation"`.
  - [x] 2.4 GREEN: Implement missing file_path validation.
  - [x] 2.5 RED: Write test for `track_file_operation` when `operation` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="track_file_operation"`.
  - [x] 2.6 GREEN: Implement missing operation validation.
  - [x] 2.7 RED: Write test for `track_file_operation` when `operation` is not "read" or "write". Verify it returns `IOFailure(PipelineError)` with `error_type="InvalidInputError"` and `step_name="track_file_operation"`, message indicating valid operations are "read" and "write".
  - [x] 2.8 GREEN: Implement operation value validation.
  - [x] 2.9 RED: Write test for `track_file_operation` when `session_id` is missing from inputs. Verify it generates a fallback session_id (e.g., `"unknown-<timestamp>"`) and proceeds to track. This is graceful degradation -- do not fail just because session_id is missing.
  - [x] 2.10 GREEN: Implement fallback session_id logic.
  - [x] 2.11 RED: Write test for `track_file_operation` when `hook_name` is missing from inputs. Verify it defaults to `"file_tracker"` and proceeds to track.
  - [x] 2.12 GREEN: Implement default hook_name handling.
  - [x] 2.13 RED: Write test for `track_file_operation` when `io_ops.write_context_bundle` returns `IOFailure`. Verify the step returns `IOFailure(PipelineError)` with `step_name="track_file_operation"` and the original io_ops error preserved in context.
  - [x] 2.14 GREEN: Implement io_ops failure handling using `.lash()` for failure re-attribution.
  - [x] 2.15 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create fail-open wrapper for file tracking (AC: #3)
  - [x] 3.1 RED: Write test for `track_file_operation_safe(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` in `adws/adw_modules/steps/track_file_operation.py`. Given `track_file_operation` returns `IOFailure(PipelineError(...))`, verify `track_file_operation_safe` catches the failure, writes the error to stderr (via `io_ops.write_stderr`), and returns `IOSuccess(WorkflowContext)` with outputs containing `{"file_tracked": False, "file_track_error": "<error message>"}`. This is the fail-open behavior (NFR4).
  - [x] 3.2 GREEN: Implement `track_file_operation_safe`. Calls `track_file_operation(ctx)`, on IOFailure extracts the PipelineError, logs to stderr, and returns IOSuccess with failure info in outputs.
  - [x] 3.3 RED: Write test for `track_file_operation_safe` when `track_file_operation` returns `IOSuccess`. Verify it passes through the IOSuccess unchanged.
  - [x] 3.4 GREEN: Implement pass-through on success.
  - [x] 3.5 RED: Write test for `track_file_operation_safe` when both `track_file_operation` fails AND `write_stderr` fails (double failure). Verify it still returns `IOSuccess(WorkflowContext)` -- fail-open means NEVER blocking the observed operation.
  - [x] 3.6 GREEN: Implement double-failure handling (catch-all in `track_file_operation_safe`).
  - [x] 3.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create CLI hook shim script (AC: #2)
  - [x] 4.1 RED: Write test that `.claude/hooks/file_tracker.sh` exists and is executable.
  - [x] 4.2 GREEN: Create `.claude/hooks/file_tracker.sh` shell script. Contents: `#!/bin/bash` header, reads stdin JSON, passes it to `uv run python -m adws.hooks.file_tracker`. No standalone logic (NFR20). Includes `|| true` for fail-open (NFR4), same pattern as Story 5.1's `hook_logger.sh`.
  - [x] 4.3 RED: Write test for `adws/hooks/file_tracker.py` `main()` entry point. Given stdin provides JSON `{"file_path": "/some/file.py", "operation": "read", "session_id": "sess-1", "hook_name": "file_tracker"}`, verify it constructs a `WorkflowContext` from the JSON and calls `track_file_operation_safe`.
  - [x] 4.4 GREEN: Implement `adws/hooks/file_tracker.py` with a `main()` function that reads stdin JSON, builds `WorkflowContext`, calls `track_file_operation_safe`, and handles parse errors gracefully (print to stderr, exit 0 -- fail-open).
  - [x] 4.5 RED: Write test for `file_tracker.py` when stdin contains invalid JSON. Verify it writes error to stderr and exits with code 0 (fail-open, NFR4).
  - [x] 4.6 GREEN: Implement invalid JSON handling.
  - [x] 4.7 RED: Write test for `file_tracker.py` when stdin is empty. Verify it writes error to stderr and exits with code 0.
  - [x] 4.8 GREEN: Implement empty stdin handling.
  - [x] 4.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Create SDK HookMatcher wrapper (AC: #2)
  - [x] 5.1 RED: Write test for `create_file_tracker_hook_matcher() -> dict[str, object]` in `adws/hooks/file_tracker.py`. Verify it returns a dict with `hook_name="file_tracker"`, `hook_types=["PreToolUse", "PostToolUse"]`, and `handler` is a callable that invokes `track_file_operation_safe`.
  - [x] 5.2 GREEN: Implement `create_file_tracker_hook_matcher`. Returns a dict matching the HookMatcher structure expected by the SDK. The handler callable constructs a `WorkflowContext` from the hook event data and delegates to `track_file_operation_safe`.
  - [x] 5.3 RED: Write test that the HookMatcher handler callable, when given event data `{"file_path": "/some/file.py", "operation": "write"}` and `session_id="sess-1"`, constructs the correct WorkflowContext inputs and calls `track_file_operation_safe`.
  - [x] 5.4 GREEN: Implement the handler callable.
  - [x] 5.5 RED: Write test that the HookMatcher handler is fail-open. When `track_file_operation_safe` raises (shouldn't happen but defense-in-depth), verify the handler catches the exception, writes to stderr, and returns without blocking.
  - [x] 5.6 GREEN: Implement defense-in-depth exception handling in the handler.
  - [x] 5.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Register step in infrastructure (AC: #1, #2, #4)
  - [x] 6.1 RED: Write test that `track_file_operation` is importable from `adws.adw_modules.steps`.
  - [x] 6.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x] 6.3 RED: Write test that `track_file_operation_safe` is importable from `adws.adw_modules.steps`.
  - [x] 6.4 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x] 6.5 RED: Write test that `_STEP_REGISTRY` in `engine/executor.py` contains `"track_file_operation"` mapped to the correct function.
  - [x] 6.6 GREEN: Add `"track_file_operation"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x] 6.7 RED: Write test that `_STEP_REGISTRY` contains `"track_file_operation_safe"` mapped to the correct function.
  - [x] 6.8 GREEN: Add `"track_file_operation_safe"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x] 6.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 7: Integration tests -- end-to-end file tracking scenarios (AC: #1, #2, #3, #4)
  - [x] 7.1 RED: Write integration test: CLI path. Simulate reading stdin JSON with file read event, constructing context, calling `track_file_operation_safe` with mocked `io_ops.write_context_bundle` returning `IOSuccess(None)`. Verify the JSONL content written contains correct timestamp, file_path, operation, session_id, and hook_name.
  - [x] 7.2 GREEN: Ensure CLI integration path works.
  - [x] 7.3 RED: Write integration test: SDK HookMatcher path. Create the HookMatcher via `create_file_tracker_hook_matcher()`, invoke the handler with mock event data for a file write operation, verify `io_ops.write_context_bundle` was called with the correct session_id and JSONL content.
  - [x] 7.4 GREEN: Ensure SDK integration path works.
  - [x] 7.5 RED: Write integration test: fail-open end-to-end. Mock `io_ops.write_context_bundle` to return `IOFailure`. Verify `track_file_operation_safe` returns `IOSuccess` with failure info. Verify stderr received the error message.
  - [x] 7.6 GREEN: Ensure fail-open integration path works.
  - [x] 7.7 RED: Write integration test: session-specific bundle naming. Mock `io_ops.write_context_bundle` and verify it is called with the session_id from the input context. Test with two different session_ids and verify each produces a call with its respective session_id.
  - [x] 7.8 GREEN: Ensure session-specific routing works.
  - [x] 7.9 RED: Write integration test: mixed read and write operations. Process two events (one read, one write) for the same session. Verify `io_ops.write_context_bundle` is called twice with the same session_id but different entry content.
  - [x] 7.10 GREEN: Ensure mixed operation tracking works.
  - [x] 7.11 REFACTOR: Clean up integration tests.

- [x] Task 8: Verify full integration and quality gates (AC: #5)
  - [x] 8.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 8.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 8.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 5.1)

**io_ops.py** has 20 public functions + 3 private helpers + 1 async helper + 1 internal exception + 1 sanitizer:
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
def write_stderr(message: str) -> IOResult[None, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError, _find_project_root(), _build_tree_lines(), _EXCLUDED_DIRS, _sanitize_session_id()
```

**types.py** has: `HookEvent` (with `to_jsonl()`), `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports 15 steps: `check_sdk_available`, `execute_shell_step`, `implement_step`, `refactor_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`, `write_failing_tests`, `verify_tests_fail`, `log_hook_event`, `log_hook_event_safe`.

**engine/executor.py** `_STEP_REGISTRY` has 12 entries.

**workflows/__init__.py** has 5 registered workflows.

**commands/** has: `dispatch.py`, `registry.py`, `types.py`, `verify.py`, `prime.py`, `build.py`, `implement.py`, `_finalize.py`.

**hooks/** has: `__init__.py`, `event_logger.py` (CLI `main()` + SDK `create_event_logger_hook_matcher()`).

**.claude/hooks/** has: `hook_logger.sh`.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 638 tests (excluding 5 enemy tests), 100% line+branch coverage.

**`agents/hook_logs/` is created on demand at runtime and gitignored.** This story follows the same pattern for `agents/context_bundles/`.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: File Tracker Architecture

The file tracker mirrors the three-layer architecture established in Story 5.1 for the event logger:

```
Layer 1: Entry Points (CLI + SDK)
  .claude/hooks/file_tracker.sh  --> uv run python -m adws.hooks.file_tracker
  SDK HookMatcher                --> adws.hooks.file_tracker.create_file_tracker_hook_matcher()
                                     |
Layer 2: Step (shared logic)         |
  adws/adw_modules/steps/track_file_operation.py
    track_file_operation()       <-- core tracking logic
    track_file_operation_safe()  <-- fail-open wrapper (NFR4)
                                     |
Layer 3: I/O Boundary                |
  adws/adw_modules/io_ops.py
    write_context_bundle()       <-- file append to agents/context_bundles/
    write_stderr()               <-- stderr output for fail-open errors (EXISTING from 5.1)
```

**Key principle:** Both CLI hook entry and SDK HookMatcher call the same step function (`track_file_operation_safe`). Zero duplicated logic (FR36, NFR20).

### Design: FileTrackEntry Data Model

```python
@dataclass(frozen=True)
class FileTrackEntry:
    """Structured file tracking entry for context bundles (FR34)."""
    timestamp: str          # ISO 8601, e.g., "2026-02-02T10:30:00+00:00"
    file_path: str          # Absolute path of the tracked file
    operation: str          # "read" or "write"
    session_id: str         # Session-specific identifier for bundle routing
    hook_name: str          # e.g., "file_tracker"

    def to_jsonl(self) -> str:
        """Serialize to single-line JSON string for JSONL format."""
        ...
```

The `FileTrackEntry` goes into `adws/adw_modules/types.py` alongside `HookEvent` and the other data types. It follows the same frozen dataclass + `to_jsonl()` pattern as `HookEvent`.

### Design: Context Bundle File Structure

Session-specific files in `agents/context_bundles/`:
```
agents/context_bundles/
  session-abc123.jsonl
  session-def456.jsonl
```

Each line in a `.jsonl` file is a standalone JSON object:
```json
{"timestamp":"2026-02-02T10:30:00+00:00","file_path":"/path/to/file.py","operation":"read","session_id":"session-abc123","hook_name":"file_tracker"}
{"timestamp":"2026-02-02T10:30:01+00:00","file_path":"/path/to/other.py","operation":"write","session_id":"session-abc123","hook_name":"file_tracker"}
```

### Design: CLI Hook Shim

The `.claude/hooks/file_tracker.sh` script follows the exact pattern from Story 5.1's `hook_logger.sh`:

```bash
#!/bin/bash
# File tracker hook -- delegates to Python module (NFR20)
# All logic is in adws/hooks/file_tracker.py
# This shim contains no standalone logic.
# || true ensures fail-open behavior (NFR4)

uv run python -m adws.hooks.file_tracker || true
```

### Design: Python Entry Point Module

`adws/hooks/file_tracker.py` serves as the `__main__` entry point, following the exact pattern from `adws/hooks/event_logger.py`:

```python
"""CLI entry point for file tracking.

Invoked by .claude/hooks/file_tracker.sh via:
  uv run python -m adws.hooks.file_tracker

Reads file operation JSON from stdin, tracks it via the shared
track_file_operation_safe step function. Fail-open: any error
is printed to stderr and exits 0 (NFR4).
"""
import json
import sys

from adws.adw_modules.steps.track_file_operation import track_file_operation_safe
from adws.adw_modules.types import WorkflowContext


def main() -> None:
    """Read stdin JSON, track file operation, exit 0 always (fail-open)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.stderr.write("file_tracker: empty stdin\n")
            return
        data = json.loads(raw)
        ctx = WorkflowContext(inputs=data)
        track_file_operation_safe(ctx)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"file_tracker: invalid JSON: {exc}\n")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"file_tracker: unexpected error: {exc}\n")
```

### Design: SDK HookMatcher Integration

```python
def create_file_tracker_hook_matcher() -> dict[str, object]:
    """Create HookMatcher config for SDK integration (FR36).

    Returns a dict with hook configuration that the SDK engine
    can use to register this hook. The handler callable delegates
    to track_file_operation_safe -- same function as the CLI path.
    """
    ...
```

The HookMatcher handler receives event data from the SDK and constructs a `WorkflowContext` identical to what the CLI path would produce. The `hook_types` for file tracking are `["PreToolUse", "PostToolUse"]` since file operations are associated with tool use events (e.g., Read tool, Write tool, Edit tool).

### Design: Fail-Open Pattern (NFR4)

Same three-layer fail-open defense from Story 5.1:

1. **`track_file_operation_safe()`**: Wraps `track_file_operation()`. On failure, logs to stderr and returns `IOSuccess`.
2. **CLI entry point `main()`**: Wraps everything in try/except. On any error, prints to stderr and exits 0.
3. **SDK HookMatcher handler**: Wraps `track_file_operation_safe()` call in try/except. On any error, prints to stderr and returns without raising.
4. **Shell shim `file_tracker.sh`**: `|| true` ensures exit 0 regardless.

Four layers of fail-open defense. The operation being observed is NEVER blocked.

### Design: New io_ops Function

One new io_ops function is needed:

1. **`write_context_bundle(session_id: str, entry_json: str) -> IOResult[None, PipelineError]`**
   - Creates `agents/context_bundles/` directory if needed
   - Appends `entry_json + "\n"` to `agents/context_bundles/<session_id>.jsonl`
   - Returns `IOSuccess(None)` or `IOFailure(PipelineError)` on error
   - Uses `_find_project_root()` (existing helper) to locate project root
   - Uses `_sanitize_session_id()` (existing from Story 5.1) to prevent path traversal

**Note:** `write_stderr()` already exists from Story 5.1 and is reused as-is.

This brings io_ops to ~21 public functions. Still under the 300-line split threshold.

### Design: Step Functions

Two step functions in `adws/adw_modules/steps/track_file_operation.py`:

1. **`track_file_operation(ctx) -> IOResult[WorkflowContext, PipelineError]`**: Core tracking logic. Validates inputs (file_path, operation), constructs `FileTrackEntry`, calls `io_ops.write_context_bundle`. Returns IOSuccess with `{"file_tracked": True}` in outputs on success, IOFailure on any error.

2. **`track_file_operation_safe(ctx) -> IOResult[WorkflowContext, PipelineError]`**: Fail-open wrapper. Calls `track_file_operation`, on failure logs to stderr and returns IOSuccess with `{"file_tracked": False, "file_track_error": "<message>"}` in outputs. NEVER returns IOFailure.

Both follow the step signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.

### Design: Input Validation

The step validates these inputs from `ctx.inputs`:

| Input | Required | Validation | Fallback |
|-------|----------|------------|----------|
| `file_path` | Yes | Must be non-empty string | IOFailure (MissingInputError) |
| `operation` | Yes | Must be "read" or "write" | IOFailure (MissingInputError or InvalidInputError) |
| `session_id` | No | String | Generates `"unknown-<timestamp>"` |
| `hook_name` | No | String | Defaults to `"file_tracker"` |

### Design: Step Registration

Both step functions are registered in:
1. `steps/__init__.py` -- exported for import (17 exports total, up from 15)
2. `engine/executor.py` `_STEP_REGISTRY` -- registered for engine dispatch (14 entries total, up from 12)

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_track_file_operation.py` -- tests for `track_file_operation`, `track_file_operation_safe`, input validation, fail-open behavior
- `adws/tests/adw_modules/test_types_file_track_entry.py` -- tests for `FileTrackEntry` dataclass and `to_jsonl()` (separate test file, same pattern as `test_types_hook_event.py`)
- `adws/tests/hooks/test_file_tracker.py` -- tests for CLI `main()`, SDK `create_file_tracker_hook_matcher()`, stdin parsing, fail-open exit behavior

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `write_context_bundle` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains `"track_file_operation"` and `"track_file_operation_safe"`

**New integration test file**:
- `adws/tests/integration/test_file_tracking.py` -- end-to-end file tracking scenarios (CLI path, SDK path, fail-open, session-specific bundling, mixed operations)

**Mock targets**:
- `adws.adw_modules.io_ops.write_context_bundle` -- mock file writes in step tests
- `adws.adw_modules.io_ops.write_stderr` -- mock stderr in fail-open tests (existing from 5.1)
- `sys.stdin` -- mock in CLI entry point tests
- `adws.adw_modules.steps.track_file_operation.track_file_operation_safe` -- mock in integration tests

### Ruff Considerations

- `BLE001` (broad exception): Needed in fail-open handlers (`except Exception`). Already used in existing code. Suppress with `# noqa: BLE001`.
- `T201` (print usage): Use `sys.stderr.write()` instead of `print(..., file=sys.stderr)`.
- Test file relaxed rules (`S101`, `PLR2004`, `ANN`): Already configured in pyproject.toml per-file-ignores.
- No new ruff suppressions should be needed beyond `BLE001` for fail-open exception handlers.

### Architecture Compliance

- **NFR4**: Hook failures fail-open with stderr logging. Four-layer defense (shell shim, CLI entry, safe wrapper, io_ops).
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `write_context_bundle` is the io_ops function; `write_stderr` reused from 5.1.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR20**: CLI hook shim delegates to shared Python module. No standalone logic in shell script.
- **FR34**: File paths and operation types tracked to session-specific bundles in `agents/context_bundles/`.
- **FR36**: CLI hooks and SDK HookMatchers share the same underlying Python module (`track_file_operation_safe`).
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Step Naming**: `track_file_operation.py` contains `track_file_operation()` (core) and `track_file_operation_safe()` (fail-open wrapper).
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).

### What NOT to Do

- Do NOT make hook failures block the observed operation -- always fail-open (NFR4).
- Do NOT put logic in the `.claude/hooks/file_tracker.sh` shim -- it delegates to Python (NFR20).
- Do NOT duplicate logic between CLI and SDK entry points -- both call `track_file_operation_safe` (FR36).
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `print()` in step functions for logging -- use `io_ops.write_stderr()` for fail-open error output.
- Do NOT change any existing step functions, workflows, commands, or engine logic (except adding to `_STEP_REGISTRY` and `steps/__init__.py`).
- Do NOT read BMAD files during hook execution.
- Do NOT create `agents/context_bundles/` in the repo -- it is created on demand at runtime and gitignored.
- Do NOT create Enemy Unit Tests for this story -- there are no io_ops SDK functions (no `execute_sdk_call` usage). File tracking is filesystem-based, not SDK-based.
- Do NOT use `_inner_value` to access returns library internals -- use `unsafe_perform_io()` (lesson from Story 5.1 code review Issue 2).

### Security: Path Traversal Protection

The new `write_context_bundle` function MUST use `_sanitize_session_id()` (existing from Story 5.1) to sanitize the `session_id` parameter before constructing the file path. This prevents path traversal attacks where a malicious `session_id` like `../../etc/passwd` would write outside `agents/context_bundles/`. This was a HIGH severity issue caught in Story 5.1's code review (Issue 1) and the fix must be applied consistently.

### Relationship to Subsequent Stories

- **Story 5.2 (this)**: File tracker & context bundles -- writes to `agents/context_bundles/`
- **Story 5.3**: /load_bundle command -- READS from `agents/context_bundles/`. Story 5.3 depends on this story's bundle file format (session-specific JSONL with `FileTrackEntry` records). The JSONL format established here is the contract for Story 5.3.
- **Story 5.4**: Dangerous command blocker -- same dual-entry pattern, `agents/security_logs/`

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/track_file_operation.py` -- `track_file_operation()` + `track_file_operation_safe()` step functions
- `adws/hooks/file_tracker.py` -- CLI `main()` entry point + SDK `create_file_tracker_hook_matcher()`
- `.claude/hooks/file_tracker.sh` -- CLI hook shim script (thin, delegates to Python)
- `adws/tests/adw_modules/steps/test_track_file_operation.py` -- step tests
- `adws/tests/adw_modules/test_types_file_track_entry.py` -- FileTrackEntry dataclass tests
- `adws/tests/hooks/test_file_tracker.py` -- CLI/SDK entry point tests
- `adws/tests/integration/test_file_tracking.py` -- integration tests

Files to modify:
- `adws/adw_modules/types.py` -- add `FileTrackEntry` frozen dataclass
- `adws/adw_modules/io_ops.py` -- add `write_context_bundle()` function
- `adws/adw_modules/steps/__init__.py` -- add `track_file_operation` and `track_file_operation_safe` imports/exports
- `adws/adw_modules/engine/executor.py` -- add `"track_file_operation"` and `"track_file_operation_safe"` to `_STEP_REGISTRY`
- `adws/tests/adw_modules/test_io_ops.py` -- add `write_context_bundle` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- add registry tests for new steps

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5] -- Epic summary: "Observability & Safety Hooks"
- [Source: _bmad-output/planning-artifacts/architecture.md#Observability (FR33-36)] -- Event logging, file tracking, shared hook modules
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `agents/context_bundles/`, `.claude/hooks/`, `adws/adw_modules/steps/build_context_bundle.py` (NOTE: architecture uses `build_context_bundle.py` name but we name it `track_file_operation.py` per step naming convention -- imperative form matching the action)
- [Source: _bmad-output/planning-artifacts/architecture.md#Step Internal Structure] -- Step creation checklist, step signature pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Steps never import I/O directly, single mock point at io_ops
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- `write_context_bundle()` io_ops function
- [Source: _bmad-output/planning-artifacts/architecture.md#Output-only boundary] -- `agents/` directory is write-only during workflow execution (exception: /load_bundle in Story 5.3)
- [Source: _bmad-output/planning-artifacts/architecture.md#.gitignore Additions] -- `agents/context_bundles/` is gitignored
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] -- Step-to-step communication via WorkflowContext
- [Source: _bmad-output/implementation-artifacts/5-1-hook-event-logger-module-and-cli-sdk-wiring.md] -- Story 5.1 patterns: three-layer architecture, fail-open defense, HookEvent data model, hook_logger.sh shim, event_logger.py entry point, _sanitize_session_id(), path traversal fix
- [Source: adws/adw_modules/io_ops.py] -- 20 public functions, _find_project_root(), _sanitize_session_id() helpers
- [Source: adws/adw_modules/types.py] -- Existing data types (HookEvent, VerifyResult, ShellResult, WorkflowContext, etc.)
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (12 entries)
- [Source: adws/adw_modules/steps/__init__.py] -- current step exports (15 steps)
- [Source: adws/adw_modules/steps/log_hook_event.py] -- Pattern to follow: log_hook_event + log_hook_event_safe
- [Source: adws/hooks/event_logger.py] -- Pattern to follow: CLI main() + SDK create_event_logger_hook_matcher()
- [Source: .claude/hooks/hook_logger.sh] -- Pattern to follow: thin shim with || true
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

From Story 5.1 learnings:
- **638 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **85 source files**: Current file count tracked by mypy.
- **io_ops at 20 public functions**: This story adds 1 new io_ops function (`write_context_bundle`) bringing total to 21. Reuses existing `write_stderr`.
- **_sanitize_session_id()**: MUST be reused for path traversal protection. HIGH severity finding from Story 5.1 code review.
- **unsafe_perform_io()**: MUST be used instead of `_inner_value` for accessing returns library internals. MEDIUM severity finding from Story 5.1 code review.
- **Shell shim fail-open**: `|| true` MUST be included in `file_tracker.sh`. MEDIUM severity finding from Story 5.1 code review.
- **Three-layer fail-open defense**: Established pattern. This story extends it with the same pattern.
- **Structural symmetry with Story 5.1**: The file tracker follows the EXACT same three-layer architecture as the event logger. Story 5.1 is the blueprint.

From Story 5.1 code review issues to avoid:
1. **Path traversal (HIGH)**: Use `_sanitize_session_id()` -- already exists, just call it.
2. **Private `_inner_value` (MEDIUM)**: Use `unsafe_perform_io()` instead.
3. **Shell shim fail-open (MEDIUM)**: Include `|| true` in `file_tracker.sh`.
4. **Inconsistent try/except (LOW)**: Place `IOSuccess` return after except block (cosmetic, not critical).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- All 8 tasks completed via strict TDD (RED-GREEN-REFACTOR)
- 681 tests passing (up from 638 in Story 5.1), 100% line + branch coverage
- mypy strict: 0 issues across 91 source files (up from 85)
- ruff check: 0 violations
- FileTrackEntry frozen dataclass follows HookEvent pattern exactly
- write_context_bundle uses _sanitize_session_id() for path traversal protection (Story 5.1 code review fix)
- track_file_operation_safe uses unsafe_perform_io() (not _inner_value) per Story 5.1 code review
- file_tracker.sh includes || true for fail-open (Story 5.1 code review fix)
- Four-layer fail-open defense: shell shim, CLI entry, safe wrapper, io_ops
- Both CLI and SDK entry points delegate to track_file_operation_safe (FR36, zero duplicated logic)

### File List

**New files created:**
- `adws/adw_modules/steps/track_file_operation.py` -- track_file_operation() + track_file_operation_safe() step functions
- `adws/hooks/file_tracker.py` -- CLI main() entry point + SDK create_file_tracker_hook_matcher()
- `.claude/hooks/file_tracker.sh` -- CLI hook shim script (thin, delegates to Python)
- `adws/tests/adw_modules/steps/test_track_file_operation.py` -- step tests (11 tests)
- `adws/tests/adw_modules/test_types_file_track_entry.py` -- FileTrackEntry dataclass tests (5 tests)
- `adws/tests/hooks/test_file_tracker.py` -- CLI/SDK entry point tests (14 tests)
- `adws/tests/integration/test_file_tracking.py` -- integration tests (5 tests)

**Modified files:**
- `adws/adw_modules/types.py` -- added FileTrackEntry frozen dataclass
- `adws/adw_modules/io_ops.py` -- added write_context_bundle() function
- `adws/adw_modules/steps/__init__.py` -- added track_file_operation and track_file_operation_safe imports/exports (17 exports, up from 15)
- `adws/adw_modules/engine/executor.py` -- added track_file_operation and track_file_operation_safe to _STEP_REGISTRY (14 entries, up from 12)
- `adws/tests/adw_modules/test_io_ops.py` -- added write_context_bundle tests (6 tests)
- `adws/tests/adw_modules/engine/test_executor.py` -- added registry tests for new steps (2 tests)

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (claude-opus-4-5-20251101) -- adversarial code review mode
**Date**: 2026-02-02
**Verdict**: APPROVED with fixes applied

### Quality Gates (post-fix)

| Gate | Result |
|------|--------|
| pytest (not enemy) | 683 passed, 5 deselected |
| Coverage | 100% line + branch (6943 stmts, 318 branches) |
| mypy --strict | 0 issues, 91 source files |
| ruff check | All checks passed |

### Issues Found: 5

#### Issue 1 (LOW -- fixed): Stale `_sanitize_session_id` docstring
- **File**: `adws/adw_modules/io_ops.py` line 637
- **Problem**: Docstring said "stays within agents/hook_logs/" but the function is now shared with `write_context_bundle` (agents/context_bundles/). Misleading after Story 5.2 expanded its usage.
- **Fix**: Updated docstring to say "stays within its target directory (e.g., agents/hook_logs/ or agents/context_bundles/)".

#### Issue 2 (MEDIUM -- fixed): `track_file_operation_safe` not truly fail-open on catastrophic failure
- **File**: `adws/adw_modules/steps/track_file_operation.py` lines 144-158
- **Problem**: The failure-handling path called `unsafe_perform_io(result.failure())` and `str(error)` without a try/except. If either raised an unexpected exception, the function would propagate it instead of being fail-open. AC #3 says "does NOT block the observed operation" -- this was not bulletproof.
- **Fix**: Wrapped the failure extraction + stderr logging in a try/except with `error_msg = "unknown error (fail-open)"` fallback. Added `test_track_file_operation_safe_catastrophic_failure` test to exercise this path.

#### Issue 3 (MEDIUM -- fixed): `main()` does not validate `json.loads()` returns a dict
- **File**: `adws/hooks/file_tracker.py` line 31
- **Problem**: `json.loads(raw)` could return a list, int, string, etc. from valid JSON like `[1,2,3]` or `42`. Passing a non-dict to `WorkflowContext(inputs=data)` would silently create a broken context (frozen dataclasses don't validate types at runtime). The subsequent `.get()` call would raise `AttributeError`. While the outer `except Exception` would catch this (still fail-open), it's not clean -- the error message would be confusing ("AttributeError: 'list' object has no attribute 'get'" instead of "expected JSON object").
- **Fix**: Added `if not isinstance(data, dict)` guard with a clear stderr message before constructing WorkflowContext. Added `test_file_tracker_main_non_dict_json` test.

#### Issue 4 (LOW -- not fixed): `write_context_bundle` IOSuccess outside try/except
- **File**: `adws/adw_modules/io_ops.py` line 723
- **Problem**: `return IOSuccess(None)` is after the except block rather than in a `try/else` clause. Functionally correct (except does early return), but structurally misleading. Same pattern as Story 5.1's `write_hook_log` (Issue 4 from that review).
- **Action**: Not fixed. Pre-existing pattern from Story 5.1 that would require changing `write_hook_log` too for consistency. Cosmetic only.

#### Issue 5 (LOW -- not fixed): SDK handler does not explicitly inject `hook_name`
- **File**: `adws/hooks/file_tracker.py` line 60
- **Problem**: The `_handler` does not explicitly set `hook_name` in the inputs dict. It relies on `event_data` potentially containing it, or falling back to the step-level default "file_tracker".
- **Action**: Not fixed. Consistent with Story 5.1's `event_logger.py` pattern. The step-level default handles this gracefully.

### Summary

The implementation follows the Story 5.1 blueprint very closely. Three-layer architecture, four-layer fail-open defense, path traversal protection via `_sanitize_session_id()`, and `unsafe_perform_io()` (not `_inner_value`) are all correctly applied. The 2 MEDIUM issues were genuine defense gaps in the fail-open behavior -- both now have targeted fixes with tests. Story 5.1 code review lessons (Issues 1-4) were all respected. Test count: 683 (up from 638 baseline, +45 new tests including 2 review-added tests).

# Story 5.1: Hook Event Logger Module & CLI/SDK Wiring

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want all hook events logged to session-specific JSONL files via a shared module,
so that I have a complete audit trail of agent activity accessible from both CLI hooks and SDK engine.

## Acceptance Criteria

1. **Given** a hook event occurs (any hook type), **When** the event logger processes it, **Then** a JSONL entry is written to a session-specific file in `agents/hook_logs/` (FR33) **And** the entry includes timestamp, event type, hook name, and relevant payload data.

2. **Given** the event logger Python module in `adws/`, **When** I inspect the CLI hook wiring, **Then** `.claude/hooks/hook_logger.sh` delegates to the Python module via `uv run python -m adws.hooks.event_logger` **And** the shim contains no standalone logic -- all logic is in the Python module (NFR20).

3. **Given** the same event logger module, **When** used by the SDK engine via HookMatcher, **Then** the HookMatcher calls the same Python module with zero duplicated logic (FR36).

4. **Given** the event logger encounters an error, **When** it fails to write a log entry, **Then** it logs the error to stderr and does NOT block the operation being observed (NFR4).

5. **Given** all event logger code, **When** I run tests, **Then** tests cover: successful logging, session-specific file creation, fail-open behavior, CLI and SDK entry points **And** 100% coverage is maintained (NFR9).

6. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Define `HookEvent` data model and io_ops file write function (AC: #1)
  - [x]1.1 RED: Write test for `HookEvent` frozen dataclass in `adws/adw_modules/types.py`. Verify it has fields: `timestamp` (str, ISO 8601 format), `event_type` (str), `hook_name` (str), `session_id` (str), `payload` (dict[str, object]). Verify it is immutable (frozen=True). Verify a `to_jsonl()` method returns a single-line JSON string with all fields.
  - [x]1.2 GREEN: Implement `HookEvent` as a frozen dataclass in `adws/adw_modules/types.py` with `to_jsonl()` method using `json.dumps()`.
  - [x]1.3 RED: Write test for `to_jsonl()` output format. Verify it produces valid JSON. Verify it is a single line (no embedded newlines). Verify all fields are present. Verify `payload` dict values are JSON-serializable.
  - [x]1.4 GREEN: Implement any remaining `to_jsonl()` logic.
  - [x]1.5 RED: Write test for `io_ops.write_hook_log(session_id: str, event_json: str) -> IOResult[None, PipelineError]`. Given the target directory `agents/hook_logs/` exists, verify it appends the event_json string plus newline to a file named `<session_id>.jsonl` within `agents/hook_logs/`. Verify it returns `IOSuccess(None)` on success.
  - [x]1.6 GREEN: Implement `write_hook_log` in `adws/adw_modules/io_ops.py`. Uses `_find_project_root()` to locate project root. Creates `agents/hook_logs/` directory if it does not exist (using `mkdir -p` equivalent `Path.mkdir(parents=True, exist_ok=True)`). Opens the file in append mode. Writes the event_json line. Returns IOSuccess(None).
  - [x]1.7 RED: Write test for `write_hook_log` when the directory cannot be created (e.g., PermissionError). Verify it returns `IOFailure(PipelineError)` with `error_type="HookLogWriteError"` and `step_name="io_ops.write_hook_log"`.
  - [x]1.8 GREEN: Implement PermissionError and OSError handling in `write_hook_log`.
  - [x]1.9 RED: Write test for `write_hook_log` when the file open/write fails. Verify `IOFailure(PipelineError)` with appropriate error details.
  - [x]1.10 GREEN: Implement file write error handling.
  - [x]1.11 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `log_hook_event` step function (AC: #1, #3)
  - [x]2.1 RED: Write test for `log_hook_event(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` in `adws/adw_modules/steps/log_hook_event.py`. Given `ctx.inputs` contains `event_type="PreToolUse"`, `hook_name="tool_logger"`, `session_id="session-abc123"`, `payload={"tool_name": "Bash", "command": "ls"}`, verify it constructs a `HookEvent` with current timestamp, calls `io_ops.write_hook_log(session_id, event.to_jsonl())`, and returns `IOSuccess(WorkflowContext)` with outputs containing `{"hook_event_logged": True}`.
  - [x]2.2 GREEN: Implement `log_hook_event` in `adws/adw_modules/steps/log_hook_event.py`. Constructs `HookEvent` with `datetime.now(tz=UTC).isoformat()` for timestamp, extracts inputs from context, calls io_ops.
  - [x]2.3 RED: Write test for `log_hook_event` when `event_type` or `hook_name` is missing from inputs. Verify it returns `IOFailure(PipelineError)` with `error_type="MissingInputError"` and `step_name="log_hook_event"`.
  - [x]2.4 GREEN: Implement missing-input validation.
  - [x]2.5 RED: Write test for `log_hook_event` when `session_id` is missing from inputs. Verify it generates a fallback session_id (e.g., `"unknown-<timestamp>"`) and proceeds to log. This is graceful degradation -- do not fail just because session_id is missing.
  - [x]2.6 GREEN: Implement fallback session_id logic.
  - [x]2.7 RED: Write test for `log_hook_event` when `payload` is missing from inputs. Verify it defaults to an empty dict `{}` and proceeds to log.
  - [x]2.8 GREEN: Implement default payload handling.
  - [x]2.9 RED: Write test for `log_hook_event` when `io_ops.write_hook_log` returns `IOFailure`. Verify the step returns `IOFailure(PipelineError)` with `step_name="log_hook_event"` and the original io_ops error preserved in context.
  - [x]2.10 GREEN: Implement io_ops failure handling using `.lash()` for failure re-attribution.
  - [x]2.11 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create fail-open wrapper for event logging (AC: #4)
  - [x]3.1 RED: Write test for `log_hook_event_safe(ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]` in `adws/adw_modules/steps/log_hook_event.py`. Given `log_hook_event` returns `IOFailure(PipelineError(...))`, verify `log_hook_event_safe` catches the failure, writes the error to stderr (via `io_ops.write_stderr`), and returns `IOSuccess(WorkflowContext)` with outputs containing `{"hook_event_logged": False, "hook_event_error": "<error message>"}`. This is the fail-open behavior (NFR4).
  - [x]3.2 GREEN: Implement `log_hook_event_safe`. Calls `log_hook_event(ctx)`, on IOFailure extracts the PipelineError, logs to stderr, and returns IOSuccess with failure info in outputs.
  - [x]3.3 RED: Write test for `log_hook_event_safe` when `log_hook_event` returns `IOSuccess`. Verify it passes through the IOSuccess unchanged.
  - [x]3.4 GREEN: Implement pass-through on success.
  - [x]3.5 RED: Write test for `io_ops.write_stderr(message: str) -> IOResult[None, PipelineError]`. Verify it writes the message to `sys.stderr`. Verify it returns `IOSuccess(None)`.
  - [x]3.6 GREEN: Implement `write_stderr` in `adws/adw_modules/io_ops.py`. Uses `sys.stderr.write()`.
  - [x]3.7 RED: Write test for `write_stderr` when stderr.write raises an OSError. Verify it returns `IOFailure(PipelineError)` -- but this failure is itself swallowed in `log_hook_event_safe` (double fail-open).
  - [x]3.8 GREEN: Implement error handling.
  - [x]3.9 RED: Write test for `log_hook_event_safe` when both `log_hook_event` fails AND `write_stderr` fails (double failure). Verify it still returns `IOSuccess(WorkflowContext)` -- fail-open means NEVER blocking the observed operation.
  - [x]3.10 GREEN: Implement double-failure handling (catch-all in `log_hook_event_safe`).
  - [x]3.11 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create CLI hook shim script (AC: #2)
  - [x]4.1 RED: Write test that `.claude/hooks/hook_logger.sh` exists and is executable.
  - [x]4.2 GREEN: Create `.claude/hooks/hook_logger.sh` shell script. Contents: `#!/bin/bash` header, reads stdin JSON, passes it to `uv run python -m adws.hooks.event_logger`. No standalone logic (NFR20).
  - [x]4.3 RED: Write test for `adws/hooks/__init__.py` module existence (Python package for hook entry points).
  - [x]4.4 GREEN: Create `adws/hooks/__init__.py`.
  - [x]4.5 RED: Write test for `adws/hooks/event_logger.py` `__main__` entry point. Given stdin provides JSON `{"event_type": "PreToolUse", "hook_name": "tool_logger", "session_id": "sess-1", "payload": {"tool": "Bash"}}`, verify it constructs a `WorkflowContext` from the JSON and calls `log_hook_event_safe`.
  - [x]4.6 GREEN: Implement `adws/hooks/event_logger.py` with a `main()` function that reads stdin JSON, builds `WorkflowContext`, calls `log_hook_event_safe`, and handles parse errors gracefully (print to stderr, exit 0 -- fail-open).
  - [x]4.7 RED: Write test for `event_logger.py` when stdin contains invalid JSON. Verify it writes error to stderr and exits with code 0 (fail-open, NFR4).
  - [x]4.8 GREEN: Implement invalid JSON handling.
  - [x]4.9 RED: Write test for `event_logger.py` when stdin is empty. Verify it writes error to stderr and exits with code 0.
  - [x]4.10 GREEN: Implement empty stdin handling.
  - [x]4.11 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Create SDK HookMatcher wrapper (AC: #3)
  - [x]5.1 RED: Write test for `create_event_logger_hook_matcher() -> dict[str, object]` in `adws/hooks/event_logger.py`. Verify it returns a dict with `hook_name="event_logger"`, `hook_types=["PreToolUse", "PostToolUse", "Notification"]`, and `handler` is a callable that invokes `log_hook_event_safe`.
  - [x]5.2 GREEN: Implement `create_event_logger_hook_matcher`. Returns a dict matching the HookMatcher structure expected by the SDK. The handler callable constructs a `WorkflowContext` from the hook event data and delegates to `log_hook_event_safe`.
  - [x]5.3 RED: Write test that the HookMatcher handler callable, when given event data `{"event_type": "PreToolUse", "tool_name": "Bash"}` and `session_id="sess-1"`, constructs the correct WorkflowContext inputs and calls `log_hook_event_safe`.
  - [x]5.4 GREEN: Implement the handler callable.
  - [x]5.5 RED: Write test that the HookMatcher handler is fail-open. When `log_hook_event_safe` raises (shouldn't happen but defense-in-depth), verify the handler catches the exception, writes to stderr, and returns without blocking.
  - [x]5.6 GREEN: Implement defense-in-depth exception handling in the handler.
  - [x]5.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Register step in infrastructure (AC: #1, #3, #5)
  - [x]6.1 RED: Write test that `log_hook_event` is importable from `adws.adw_modules.steps`.
  - [x]6.2 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x]6.3 RED: Write test that `log_hook_event_safe` is importable from `adws.adw_modules.steps`.
  - [x]6.4 GREEN: Add import and export to `adws/adw_modules/steps/__init__.py`.
  - [x]6.5 RED: Write test that `_STEP_REGISTRY` in `engine/executor.py` contains `"log_hook_event"` mapped to the correct function.
  - [x]6.6 GREEN: Add `"log_hook_event"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x]6.7 RED: Write test that `_STEP_REGISTRY` contains `"log_hook_event_safe"` mapped to the correct function.
  - [x]6.8 GREEN: Add `"log_hook_event_safe"` to `_STEP_REGISTRY` in `engine/executor.py`.
  - [x]6.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 7: Integration tests -- end-to-end logging scenarios (AC: #1, #2, #3, #4, #5)
  - [x]7.1 RED: Write integration test: CLI path. Simulate reading stdin JSON, constructing context, calling `log_hook_event_safe` with mocked `io_ops.write_hook_log` returning `IOSuccess(None)`. Verify the JSONL content written contains correct timestamp, event_type, hook_name, session_id, and payload.
  - [x]7.2 GREEN: Ensure CLI integration path works.
  - [x]7.3 RED: Write integration test: SDK HookMatcher path. Create the HookMatcher via `create_event_logger_hook_matcher()`, invoke the handler with mock event data, verify `io_ops.write_hook_log` was called with the correct session_id and JSONL content.
  - [x]7.4 GREEN: Ensure SDK integration path works.
  - [x]7.5 RED: Write integration test: fail-open end-to-end. Mock `io_ops.write_hook_log` to return `IOFailure`. Verify `log_hook_event_safe` returns `IOSuccess` with failure info. Verify stderr received the error message.
  - [x]7.6 GREEN: Ensure fail-open integration path works.
  - [x]7.7 RED: Write integration test: session-specific file naming. Mock `io_ops.write_hook_log` and verify it is called with the session_id from the input context. Test with two different session_ids and verify each produces a call with its respective session_id.
  - [x]7.8 GREEN: Ensure session-specific routing works.
  - [x]7.9 REFACTOR: Clean up integration tests.

- [x] Task 8: Verify full integration and quality gates (AC: #6)
  - [x]8.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x]8.2 Run `uv run mypy adws/` -- strict mode passes
  - [x]8.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 4.8)

**io_ops.py** has 18 public functions + 3 private helpers + 1 async helper + 1 internal exception:
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
# Plus: async _execute_sdk_call_async(), _NoResultError, _find_project_root(), _build_tree_lines(), _EXCLUDED_DIRS
```

**types.py** has: `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports 13 steps: `check_sdk_available`, `execute_shell_step`, `implement_step`, `refactor_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`, `write_failing_tests`, `verify_tests_fail`.

**engine/executor.py** `_STEP_REGISTRY` has 10 entries.

**workflows/__init__.py** has 5 registered workflows.

**commands/** has: `dispatch.py`, `registry.py`, `types.py`, `verify.py`, `prime.py`, `build.py`, `implement.py`, `_finalize.py`.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 588 tests (excluding 5 enemy tests), 100% line+branch coverage.

**No `.claude/hooks/` directory exists yet.** This story creates it.
**No `agents/` directory exists yet.** This story's io_ops function creates `agents/hook_logs/` on demand.
**No `adws/hooks/` Python package exists yet.** This story creates it for CLI/SDK hook entry points.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order.

### Design: Event Logger Architecture

The event logger has three layers:

```
Layer 1: Entry Points (CLI + SDK)
  .claude/hooks/hook_logger.sh  --> uv run python -m adws.hooks.event_logger
  SDK HookMatcher                --> adws.hooks.event_logger.create_event_logger_hook_matcher()
                                     |
Layer 2: Step (shared logic)         |
  adws/adw_modules/steps/log_hook_event.py
    log_hook_event()              <-- core logging logic
    log_hook_event_safe()         <-- fail-open wrapper (NFR4)
                                     |
Layer 3: I/O Boundary                |
  adws/adw_modules/io_ops.py
    write_hook_log()              <-- file append to agents/hook_logs/
    write_stderr()                <-- stderr output for fail-open errors
```

**Key principle:** Both CLI hook entry and SDK HookMatcher call the same step function (`log_hook_event_safe`). Zero duplicated logic (FR36, NFR20).

### Design: HookEvent Data Model

```python
@dataclass(frozen=True)
class HookEvent:
    """Structured hook event for JSONL logging (FR33)."""
    timestamp: str          # ISO 8601, e.g., "2026-02-02T10:30:00+00:00"
    event_type: str         # e.g., "PreToolUse", "PostToolUse", "Notification"
    hook_name: str          # e.g., "event_logger", "file_tracker"
    session_id: str         # Session-specific identifier for file routing
    payload: dict[str, object]  # Event-specific data

    def to_jsonl(self) -> str:
        """Serialize to single-line JSON string for JSONL format."""
        ...
```

The `HookEvent` goes into `adws/adw_modules/types.py` alongside the other data types (`VerifyResult`, `ShellResult`, `WorkflowContext`, etc.). It follows the same frozen dataclass pattern.

### Design: JSONL File Structure

Session-specific files in `agents/hook_logs/`:
```
agents/hook_logs/
  session-abc123.jsonl
  session-def456.jsonl
```

Each line in a `.jsonl` file is a standalone JSON object:
```json
{"timestamp":"2026-02-02T10:30:00+00:00","event_type":"PreToolUse","hook_name":"event_logger","session_id":"session-abc123","payload":{"tool_name":"Bash","command":"ls"}}
{"timestamp":"2026-02-02T10:30:01+00:00","event_type":"PostToolUse","hook_name":"event_logger","session_id":"session-abc123","payload":{"tool_name":"Bash","exit_code":0}}
```

### Design: CLI Hook Shim

The `.claude/hooks/hook_logger.sh` script is a thin shim (NFR20):

```bash
#!/bin/bash
# Hook event logger -- delegates to Python module (NFR20)
# All logic is in adws/hooks/event_logger.py
# This shim contains no standalone logic.

uv run python -m adws.hooks.event_logger
```

The shim reads stdin (hook event JSON from Claude CLI) and pipes it to the Python entry point. The Python module handles parsing, validation, logging, and error handling. If the Python module fails for any reason, the shim should not block the hook operation (fail-open, NFR4). The `uv run` prefix ensures the correct Python environment is used.

### Design: Python Entry Point Module

`adws/hooks/event_logger.py` serves as the `__main__` entry point:

```python
"""CLI entry point for hook event logging.

Invoked by .claude/hooks/hook_logger.sh via:
  uv run python -m adws.hooks.event_logger

Reads hook event JSON from stdin, logs it via the shared
log_hook_event_safe step function. Fail-open: any error
is printed to stderr and exits 0 (NFR4).
"""
import json
import sys

from adws.adw_modules.steps.log_hook_event import log_hook_event_safe
from adws.adw_modules.types import WorkflowContext


def main() -> None:
    """Read stdin JSON, log event, exit 0 always (fail-open)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print("event_logger: empty stdin", file=sys.stderr)
            return
        data = json.loads(raw)
        ctx = WorkflowContext(inputs=data)
        log_hook_event_safe(ctx)
    except json.JSONDecodeError as exc:
        print(f"event_logger: invalid JSON: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"event_logger: unexpected error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

### Design: SDK HookMatcher Integration

The SDK HookMatcher is created via a factory function in the same module:

```python
def create_event_logger_hook_matcher() -> dict[str, object]:
    """Create HookMatcher config for SDK integration (FR36).

    Returns a dict with hook configuration that the SDK engine
    can use to register this hook. The handler callable delegates
    to log_hook_event_safe -- same function as the CLI path.
    """
    ...
```

The HookMatcher handler receives event data from the SDK and constructs a `WorkflowContext` identical to what the CLI path would produce. This ensures FR36 compliance (shared modules, zero duplicated logic).

### Design: Fail-Open Pattern (NFR4)

NFR4 states: "Hook failures must not block the operation they're observing -- fail-open with stderr logging."

This is implemented at two levels:

1. **`log_hook_event_safe()`**: Wraps `log_hook_event()`. On failure, logs to stderr and returns `IOSuccess`.
2. **CLI entry point `main()`**: Wraps everything in try/except. On any error, prints to stderr and exits 0.
3. **SDK HookMatcher handler**: Wraps `log_hook_event_safe()` call in try/except. On any error (shouldn't happen), prints to stderr and returns without raising.

Three layers of fail-open defense. The operation being observed is NEVER blocked.

### Design: New io_ops Functions

Two new io_ops functions are needed:

1. **`write_hook_log(session_id: str, event_json: str) -> IOResult[None, PipelineError]`**
   - Creates `agents/hook_logs/` directory if needed
   - Appends `event_json + "\n"` to `agents/hook_logs/<session_id>.jsonl`
   - Returns `IOSuccess(None)` or `IOFailure(PipelineError)` on error
   - Uses `_find_project_root()` (existing helper) to locate project root

2. **`write_stderr(message: str) -> IOResult[None, PipelineError]`**
   - Writes message to `sys.stderr`
   - Returns `IOSuccess(None)` or `IOFailure(PipelineError)` on error
   - Used by `log_hook_event_safe` for fail-open error reporting

These bring io_ops to ~20 public functions. Still under the 300-line split threshold but monitor.

### Design: Step Functions

Two step functions in `adws/adw_modules/steps/log_hook_event.py`:

1. **`log_hook_event(ctx) -> IOResult[WorkflowContext, PipelineError]`**: Core logging logic. Validates inputs, constructs `HookEvent`, calls `io_ops.write_hook_log`. Returns IOSuccess with `{"hook_event_logged": True}` in outputs on success, IOFailure on any error.

2. **`log_hook_event_safe(ctx) -> IOResult[WorkflowContext, PipelineError]`**: Fail-open wrapper. Calls `log_hook_event`, on failure logs to stderr and returns IOSuccess with `{"hook_event_logged": False, "hook_event_error": "<message>"}` in outputs. NEVER returns IOFailure.

Both follow the step signature: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.

### Design: Step Registration

Both step functions are registered in:
1. `steps/__init__.py` -- exported for import (15 exports total, up from 13)
2. `engine/executor.py` `_STEP_REGISTRY` -- registered for engine dispatch (12 entries total, up from 10)

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/steps/test_log_hook_event.py` -- tests for `log_hook_event`, `log_hook_event_safe`, input validation, fail-open behavior
- `adws/tests/adw_modules/test_types_hook_event.py` -- tests for `HookEvent` dataclass and `to_jsonl()` (or add to existing `test_types.py`)
- `adws/tests/hooks/__init__.py` -- test package
- `adws/tests/hooks/test_event_logger.py` -- tests for CLI `main()`, SDK `create_event_logger_hook_matcher()`, stdin parsing, fail-open exit behavior

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add `write_hook_log` and `write_stderr` tests
- `adws/tests/adw_modules/engine/test_executor.py` -- verify `_STEP_REGISTRY` contains `"log_hook_event"` and `"log_hook_event_safe"`

**Mock targets**:
- `adws.adw_modules.io_ops.write_hook_log` -- mock file writes in step tests
- `adws.adw_modules.io_ops.write_stderr` -- mock stderr in fail-open tests
- `sys.stdin` -- mock in CLI entry point tests
- `adws.adw_modules.steps.log_hook_event.log_hook_event_safe` -- mock in integration tests

### Ruff Considerations

- `S602` (subprocess shell=True): Not applicable -- no subprocess calls in this story.
- `BLE001` (broad exception): Needed in fail-open handlers (`except Exception`). Already used in executor.py and event_logger CLI entry point. Suppress with `# noqa: BLE001`.
- `S604` (possible shell step): Not applicable -- no new shell steps added.
- `E501` (line too long): Keep all lines under 88 characters.
- `T201` (print usage): The CLI entry point uses `print(..., file=sys.stderr)` for fail-open error output. If ruff flags this, use `sys.stderr.write()` instead.
- Test file relaxed rules (`S101`, `PLR2004`, `ANN`): Already configured in pyproject.toml per-file-ignores.

### Architecture Compliance

- **NFR4**: Hook failures fail-open with stderr logging. Three-layer defense.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. `write_hook_log` and `write_stderr` are the io_ops functions.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR20**: CLI hook shim delegates to shared Python module. No standalone logic in shell script.
- **FR33**: JSONL entries written to session-specific files in `agents/hook_logs/`.
- **FR36**: CLI hooks and SDK HookMatchers share the same underlying Python module (log_hook_event_safe).
- **Step Signature**: `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`.
- **Step Naming**: `log_hook_event.py` contains `log_hook_event()` (core) and `log_hook_event_safe()` (fail-open wrapper).
- **Import Pattern**: Absolute imports only (`from adws.adw_modules.X import Y`).

### What NOT to Do

- Do NOT make hook failures block the observed operation -- always fail-open (NFR4).
- Do NOT put logic in the `.claude/hooks/hook_logger.sh` shim -- it delegates to Python (NFR20).
- Do NOT duplicate logic between CLI and SDK entry points -- both call `log_hook_event_safe` (FR36).
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `print()` in step functions for logging -- use `io_ops.write_stderr()` for fail-open error output.
- Do NOT change any existing step functions, workflows, commands, or engine logic (except adding to `_STEP_REGISTRY` and `steps/__init__.py`).
- Do NOT read BMAD files during hook execution.
- Do NOT create `agents/hook_logs/` in the repo -- it is created on demand at runtime and gitignored.
- Do NOT create Enemy Unit Tests for this story -- there are no io_ops SDK functions (no `execute_sdk_call` usage). Hook logging is filesystem-based, not SDK-based.

### Epic 5 Context

This is the first story of Epic 5 (Observability & Safety Hooks). Epic 5 is on Track B -- it depends only on Epic 1 (foundation) and is implementable alongside the Track A epics. This story establishes:

1. The `agents/hook_logs/` output directory pattern
2. The `adws/hooks/` Python package for CLI/SDK hook entry points
3. The `.claude/hooks/` directory for CLI hook shim scripts
4. The fail-open design pattern (NFR4)
5. The shared module pattern (FR36, NFR20)

These patterns are reused by subsequent Epic 5 stories:
- **Story 5.2** (File Tracker): Same dual-entry pattern, `agents/context_bundles/`
- **Story 5.3** (/load_bundle Command): Reads from `agents/context_bundles/`
- **Story 5.4** (Dangerous Command Blocker): Same dual-entry pattern, `agents/security_logs/`

### Project Structure Notes

Files to create:
- `adws/adw_modules/steps/log_hook_event.py` -- `log_hook_event()`, `log_hook_event_safe()`
- `adws/hooks/__init__.py` -- Python package for hook entry points
- `adws/hooks/event_logger.py` -- CLI `main()` entry point + SDK `create_event_logger_hook_matcher()`
- `.claude/hooks/hook_logger.sh` -- CLI hook shim script (thin, delegates to Python)
- `adws/tests/adw_modules/steps/test_log_hook_event.py` -- step tests
- `adws/tests/hooks/__init__.py` -- test package
- `adws/tests/hooks/test_event_logger.py` -- CLI/SDK entry point tests

Files to modify:
- `adws/adw_modules/types.py` -- add `HookEvent` frozen dataclass
- `adws/adw_modules/io_ops.py` -- add `write_hook_log()` and `write_stderr()` functions
- `adws/adw_modules/steps/__init__.py` -- add `log_hook_event` and `log_hook_event_safe` imports/exports
- `adws/adw_modules/engine/executor.py` -- add `"log_hook_event"` and `"log_hook_event_safe"` to `_STEP_REGISTRY`
- `adws/tests/adw_modules/test_io_ops.py` -- add `write_hook_log` and `write_stderr` tests
- `adws/tests/adw_modules/test_types.py` -- add `HookEvent` tests (or create separate test file)

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1] -- AC and story definition
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5] -- Epic summary: "Observability & Safety Hooks"
- [Source: _bmad-output/planning-artifacts/architecture.md#Observability (FR33-36)] -- Event logging, file tracking, shared hook modules
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `agents/hook_logs/`, `.claude/hooks/`, `adws/adw_modules/steps/log_hook_event.py`
- [Source: _bmad-output/planning-artifacts/architecture.md#Step Internal Structure] -- Step creation checklist, step signature pattern
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Steps never import I/O directly, single mock point at io_ops
- [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points] -- `write_hook_log()` io_ops function
- [Source: _bmad-output/planning-artifacts/architecture.md#Output-only boundary] -- `agents/` directory is write-only during workflow execution
- [Source: _bmad-output/planning-artifacts/architecture.md#.gitignore Additions] -- `agents/hook_logs/` is gitignored
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] -- Step module naming: imperative form
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] -- Step-to-step communication via WorkflowContext
- [Source: adws/adw_modules/io_ops.py] -- 18 public functions, _find_project_root() helper
- [Source: adws/adw_modules/types.py] -- Existing data types (VerifyResult, ShellResult, WorkflowContext, etc.)
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/types.py] -- Step, Workflow, StepFunction
- [Source: adws/adw_modules/engine/executor.py] -- _STEP_REGISTRY (10 entries)
- [Source: adws/adw_modules/steps/__init__.py] -- current step exports (13 steps)
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: _bmad-output/implementation-artifacts/4-7-implement-and-refactor-steps-green-and-refactor-phases.md] -- Previous story patterns: step creation, ROP composition, registry registration
- [Source: _bmad-output/implementation-artifacts/4-8-implement-verify-close-workflow-and-implement-command.md] -- Previous story: 588 tests, 77 source files, io_ops function patterns

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

From Story 4.8 learnings:
- **588 tests**: Current test count (excluding 5 enemy tests), 100% line+branch coverage.
- **77 source files**: Current file count tracked by mypy.
- **io_ops at 18 public functions**: This story adds 2 new io_ops functions (write_hook_log, write_stderr) bringing total to 20.
- **Shared finalize extraction**: Task 3.9 in Story 4.8 extracted `_build_failure_metadata`, `finalize_on_success`, `finalize_on_failure` to `commands/_finalize.py`. Pattern: when logic is needed by multiple modules, extract to a shared module.
- **Dispatch handler pattern**: `_dispatch_specialized` helper separates routing concerns. The event logger follows a similar separation: entry points (CLI/SDK) route to shared step logic.

From Story 4.7 learnings:
- **Pre-compiled regex patterns**: All regex patterns should be module-level compiled constants. May be relevant if JSONL validation uses regex.
- **Structural symmetry**: The three SDK steps follow identical structure. The hook steps follow a different pattern (fail-open wrapper) but should be internally consistent.
- **No new io_ops for SDK steps**: Stories 4.5-4.7 reused existing `execute_sdk_call`. This story adds new io_ops functions because hooks require new I/O operations (file append, stderr write).

### Relationship to Subsequent Stories

This is the first story of Epic 5:

1. **Story 5.1 (this)**: Hook event logger -- establishes `.claude/hooks/`, `agents/hook_logs/`, `adws/hooks/` package, fail-open pattern, shared module pattern
2. **Story 5.2**: File tracker & context bundles -- same dual-entry pattern, `agents/context_bundles/`
3. **Story 5.3**: /load_bundle command -- reads from `agents/context_bundles/`
4. **Story 5.4**: Dangerous command blocker -- same dual-entry pattern, `agents/security_logs/`

Stories 5.2 and 5.4 will follow the EXACT patterns established here (CLI shim + Python module + fail-open + io_ops boundary). This story sets the blueprint.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- 632 tests pass (44 new), 5 enemy deselected, 100% line+branch coverage
- mypy strict: 0 errors across 85 source files
- ruff: 0 violations
- All 8 tasks completed via strict TDD (RED-GREEN-REFACTOR)
- Three-layer fail-open defense pattern established (NFR4)
- Zero duplicated logic between CLI and SDK paths (FR36, NFR20)
- HookEvent frozen dataclass with to_jsonl() for JSONL format (FR33)
- Session-specific file routing via agents/hook_logs/<session_id>.jsonl
- io_ops boundary maintained: write_hook_log + write_stderr (NFR10)
- Step registry updated: 12 entries (up from 10)
- Steps __init__.py exports: 15 steps (up from 13)

### File List

Files created:
- adws/adw_modules/steps/log_hook_event.py -- log_hook_event() + log_hook_event_safe() step functions
- adws/hooks/__init__.py -- Python package for hook entry points
- adws/hooks/event_logger.py -- CLI main() entry point + SDK create_event_logger_hook_matcher()
- .claude/hooks/hook_logger.sh -- CLI hook shim script (thin, delegates to Python)
- adws/tests/adw_modules/steps/test_log_hook_event.py -- step tests (9 tests)
- adws/tests/adw_modules/test_types_hook_event.py -- HookEvent dataclass tests (7 tests)
- adws/tests/hooks/__init__.py -- test package
- adws/tests/hooks/test_event_logger.py -- CLI/SDK entry point tests (15 tests)
- adws/tests/integration/test_hook_event_logging.py -- integration tests (4 tests)

Files modified:
- adws/adw_modules/types.py -- added HookEvent frozen dataclass
- adws/adw_modules/io_ops.py -- added write_hook_log() and write_stderr()
- adws/adw_modules/steps/__init__.py -- added log_hook_event and log_hook_event_safe exports
- adws/adw_modules/engine/executor.py -- added log_hook_event and log_hook_event_safe to _STEP_REGISTRY
- adws/tests/adw_modules/test_io_ops.py -- added write_hook_log and write_stderr tests (7 tests), plus 6 sanitization tests (review fix)
- adws/tests/adw_modules/engine/test_executor.py -- added registry tests for new steps (2 tests)

## Senior Developer Review

**Reviewer**: Claude Opus 4.5 (adversarial code review mode)
**Date**: 2026-02-02
**Verdict**: APPROVED with 3 fixes applied (all resolved)

### Issues Found: 5 (3 fixed, 2 noted)

#### Issue 1: Path Traversal Vulnerability in `write_hook_log` -- HIGH -- FIXED

**File**: `adws/adw_modules/io_ops.py` (write_hook_log)
**Problem**: The `session_id` parameter was directly interpolated into a file path (`log_dir / f"{session_id}.jsonl"`) with zero sanitization. A malicious `session_id` like `../../etc/passwd` would write to an arbitrary filesystem location outside `agents/hook_logs/`. This is a real security vulnerability -- session_id originates from external input (hook event JSON from Claude CLI or SDK).
**Fix**: Added `_sanitize_session_id()` helper that uses `PurePosixPath.name` to strip directory traversal, with fallback for empty/dot-only names. Added 6 new tests covering normal, traversal, absolute path, empty, and dot-only cases, plus an end-to-end test verifying the file stays within `agents/hook_logs/`.

#### Issue 2: Private `_inner_value` Access in `log_hook_event_safe` -- MEDIUM -- FIXED

**File**: `adws/adw_modules/steps/log_hook_event.py` line 127
**Problem**: Used `result.failure()._inner_value` with a `noqa: SLF001` suppression to access a private attribute of the `returns` library. The entire rest of the codebase (80+ call sites in production and test code) uses `unsafe_perform_io(result.failure())` which is the official public API. Using `_inner_value` directly couples to the library's internal implementation and could break on library upgrades.
**Fix**: Replaced with `unsafe_perform_io(result.failure())` and added the `from returns.unsafe import unsafe_perform_io` import. Removed the `noqa: SLF001` suppression.

#### Issue 3: Shell Shim Lacks Fail-Open Protection -- MEDIUM -- FIXED

**File**: `.claude/hooks/hook_logger.sh`
**Problem**: NFR4 states "Hook failures must not block the operation they're observing -- fail-open with stderr logging." The Python layer has three-layer fail-open defense. But the bash shim had no protection. If `uv` is not in PATH (exits 127), if the Python module segfaults, or if any unexpected shell error occurs, the shim would exit nonzero, potentially blocking the hook operation. The fail-open defense had a gap at the outermost layer.
**Fix**: Added `|| true` to the `uv run` invocation so the script always exits 0 regardless of what happens. Added a comment documenting the NFR4 rationale.

#### Issue 4: Inconsistent try/except Pattern -- LOW -- NOTED

**File**: `adws/adw_modules/io_ops.py` (write_hook_log, write_stderr)
**Problem**: Other io_ops functions use `try/except/else` with `return IOSuccess(...)` in the `else` block. The new `write_hook_log` and `write_stderr` functions place `return IOSuccess(None)` after the except block (outside the try/except). Functionally equivalent but stylistically inconsistent.
**Decision**: Not fixed. The behavior is correct and the inconsistency is cosmetic. Not worth a change given all gates pass.

#### Issue 5: Missing Test for Path Traversal -- LOW -- ADDRESSED BY FIX 1

Added as part of Issue 1 fix. Six new tests verify sanitization behavior plus one integration test confirming traversal is blocked end-to-end.

### Quality Gate Results (Post-Fix)

- **Tests**: 638 passed, 5 enemy deselected (6 new tests from review fixes)
- **Coverage**: 100% line + 100% branch (298 branches, 0 missing)
- **mypy**: 0 errors across 85 source files (strict mode)
- **ruff**: 0 violations (ALL rules)

### AC Verification Summary

| AC | Status | Notes |
|----|--------|-------|
| AC1: JSONL to session-specific file | PASS | HookEvent.to_jsonl(), write_hook_log(), session routing tested |
| AC2: CLI shim delegates to Python | PASS | hook_logger.sh is thin shim, now with fail-open || true |
| AC3: SDK HookMatcher uses same module | PASS | create_event_logger_hook_matcher() delegates to log_hook_event_safe |
| AC4: Fail-open on errors | PASS | Three-layer defense + shell-level fail-open (fixed) |
| AC5: Test coverage | PASS | 638 tests, 100% coverage, all scenarios covered |
| AC6: All quality gates pass | PASS | pytest, mypy strict, ruff all clean |

### Architecture Compliance

- NFR4 (fail-open): Now complete at all four layers -- shell shim, CLI entry, safe wrapper, io_ops
- NFR9 (100% coverage): Maintained at 100% line + branch
- NFR10 (io_ops boundary): write_hook_log + write_stderr behind boundary, all mocked in tests
- NFR11 (mypy strict): 0 errors, 85 files
- NFR12 (ruff ALL): 0 violations
- NFR20 (no standalone logic in shim): hook_logger.sh contains only delegation
- FR33 (JSONL logging): Session-specific files in agents/hook_logs/
- FR36 (shared modules): CLI and SDK both call log_hook_event_safe, zero duplication

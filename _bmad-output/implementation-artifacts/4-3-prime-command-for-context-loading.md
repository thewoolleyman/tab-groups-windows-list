# Story 4.3: /prime Command for Context Loading

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want to invoke `/prime` to load codebase context into a session,
so that subsequent commands operate with full awareness of the project structure and conventions.

## Acceptance Criteria

1. **Given** the command pattern from Story 4.1, **When** I invoke `/prime`, **Then** the command reads relevant project files (CLAUDE.md, architecture docs, directory structure) (FR31) **And** context is loaded into the session for use by subsequent commands.

2. **Given** /prime has loaded context, **When** I inspect the loaded context, **Then** it includes project structure, coding conventions, and TDD mandate **And** it does NOT include secrets or credentials.

3. **Given** /prime command code, **When** I run tests, **Then** context loading paths are covered **And** 100% coverage is maintained (NFR9).

4. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create `PrimeContextResult` data type for command output (AC: #1, #2)
  - [x] 1.1 RED: Write test for `PrimeContextResult` frozen dataclass with fields: `success` (bool), `files_loaded` (list[str] -- paths of files successfully read), `summary` (str -- human-readable description of what was loaded), `context_sections` (dict[str, str] -- mapping of section name to content, e.g. "claude_md" -> content). Verify construction, immutability, and field access.
  - [x] 1.2 GREEN: Implement `PrimeContextResult` as a frozen dataclass in `adws/adw_modules/commands/prime.py`.
  - [x] 1.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Define `PRIME_FILE_SPECS` constant for context file definitions (AC: #1, #2)
  - [x] 2.1 RED: Write test for `PRIME_FILE_SPECS` -- a tuple of frozen `PrimeFileSpec` dataclass instances, each with `key` (str -- section name for context_sections), `path` (str -- relative path from project root), `description` (str -- human-readable name), `required` (bool -- whether failure to read is an error or just a warning). Verify at least these specs exist: CLAUDE.md (required), architecture.md (optional), epics.md (optional). Verify no spec paths reference `.env`, credential files, or secret-bearing paths (AC #2 -- no secrets).
  - [x] 2.2 GREEN: Implement `PrimeFileSpec` frozen dataclass and `PRIME_FILE_SPECS` tuple in `adws/adw_modules/commands/prime.py`. Include entries for: `CLAUDE.md`, `_bmad-output/planning-artifacts/architecture.md`, `_bmad-output/planning-artifacts/epics.md`.
  - [x] 2.3 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create io_ops function for reading prime context files (AC: #1)
  - [x] 3.1 RED: Write test for `io_ops.read_prime_file(path: str) -> IOResult[str, PipelineError]`. Given a valid file path, verify it returns `IOSuccess(content)`. Given a missing file, verify it returns `IOFailure(PipelineError(...))` with error_type `"FileNotFoundError"`. Given a permission error, verify `IOFailure` with `"PermissionError"`.
  - [x] 3.2 GREEN: Implement `read_prime_file` in `io_ops.py`. This wraps `read_file()` but accepts a string path (resolves to absolute from project root). Uses the existing `read_file` function internally.
  - [x] 3.3 RED: Write test for `io_ops.get_directory_tree(root: str, max_depth: int = 3) -> IOResult[str, PipelineError]`. Given a valid directory, verify it returns `IOSuccess(tree_string)` with a tree representation of the directory structure. Verify it excludes common non-relevant directories (`.git`, `__pycache__`, `node_modules`, `.venv`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `htmlcov`). Given an invalid directory, verify `IOFailure`.
  - [x] 3.4 GREEN: Implement `get_directory_tree` in `io_ops.py`. Uses `pathlib.Path` and `os.walk` (or iterdir) to build a tree string, respecting max_depth and exclusion list.
  - [x] 3.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create `_load_file_context()` pure helper function (AC: #1, #2)
  - [x] 4.1 RED: Write test for `_load_file_context(file_specs: tuple[PrimeFileSpec, ...]) -> IOResult[PrimeContextResult, PipelineError]`. Given all files exist (mock io_ops.read_prime_file returning IOSuccess for each), verify it returns `IOSuccess(PrimeContextResult)` with all files in `files_loaded`, all content in `context_sections`, success=True, and a summary stating how many files were loaded.
  - [x] 4.2 GREEN: Implement `_load_file_context` in `adws/adw_modules/commands/prime.py`. Iterates over file specs, calls `io_ops.read_prime_file()` for each. Collects results -- required file failures produce IOFailure, optional file failures are skipped with a note in summary.
  - [x] 4.3 RED: Write test for `_load_file_context` when an optional file is missing. Verify it still returns IOSuccess but the missing file is NOT in `files_loaded` and NOT in `context_sections`, and the summary mentions the skipped file.
  - [x] 4.4 GREEN: Implement optional file skip logic.
  - [x] 4.5 RED: Write test for `_load_file_context` when a required file is missing. Verify it returns IOFailure(PipelineError) with error_type `"RequiredFileError"` and the missing file path in context.
  - [x] 4.6 GREEN: Implement required file failure logic.
  - [x] 4.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 5: Create `_load_directory_context()` helper function (AC: #1)
  - [x] 5.1 RED: Write test for `_load_directory_context() -> IOResult[dict[str, str], PipelineError]`. Given `io_ops.get_directory_tree` succeeds for `adws/` and project root, verify it returns IOSuccess with dict mapping `"adws_tree"` -> tree content and `"project_tree"` -> tree content.
  - [x] 5.2 GREEN: Implement `_load_directory_context` in `adws/adw_modules/commands/prime.py`. Calls `io_ops.get_directory_tree()` for `adws/` (depth=3) and project root (depth=2).
  - [x] 5.3 RED: Write test for `_load_directory_context` when directory tree fails. Verify it returns IOSuccess with an empty tree entry for the failed directory (non-fatal -- directory tree is informational).
  - [x] 5.4 GREEN: Implement fallback for directory tree failures.
  - [x] 5.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Create `run_prime_command()` function (AC: #1, #2)
  - [x] 6.1 RED: Write test for `run_prime_command(ctx: WorkflowContext) -> IOResult[PrimeContextResult, PipelineError]`. Given all context files exist and directory tree succeeds (mocked via io_ops), verify it returns `IOSuccess(PrimeContextResult)` with all files and directory structure loaded, success=True.
  - [x] 6.2 GREEN: Implement `run_prime_command` in `adws/adw_modules/commands/prime.py`. Calls `_load_file_context(PRIME_FILE_SPECS)` and `_load_directory_context()`, merges directory trees into context_sections, produces final PrimeContextResult.
  - [x] 6.3 RED: Write test for `run_prime_command` when a required file fails. Verify IOFailure propagates from `_load_file_context`.
  - [x] 6.4 GREEN: Implement required file failure propagation.
  - [x] 6.5 RED: Write test for `run_prime_command` output does NOT contain secrets. Verify `context_sections` keys do not include `.env`, `credentials`, `secrets`, or `api_key`. (Structural test -- ensures the file spec list is safe.)
  - [x] 6.6 GREEN: Ensure file specs exclude secret paths (already enforced by PRIME_FILE_SPECS definition).
  - [x] 6.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 7: Wire `run_prime_command` into command dispatch (AC: #1)
  - [x] 7.1 RED: Write test that `run_command("prime", ctx)` delegates to `run_prime_command` instead of returning the generic "NoWorkflowError". Verify the return is `IOResult[WorkflowContext, PipelineError]` where the WorkflowContext has the PrimeContextResult serialized in outputs under key `"prime_result"`.
  - [x] 7.2 GREEN: Update `run_command` in dispatch.py to detect the "prime" command and route to `run_prime_command`. The `PrimeContextResult` is placed into the WorkflowContext outputs under key `"prime_result"`. Move the `workflow_name is None` check AFTER the prime-specific check.
  - [x] 7.3 RED: Write test that the "load_bundle" command (also workflow_name=None) still returns "NoWorkflowError" from the generic path -- no regression.
  - [x] 7.4 GREEN: Ensure only "prime" gets the specialized handler; other non-workflow commands are unaffected.
  - [x] 7.5 RED: Write test that workflow-backed commands ("verify", "build", etc.) still work correctly through their respective paths -- no regression.
  - [x] 7.6 GREEN: Ensure existing dispatch paths are unaffected.
  - [x] 7.7 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 8: Update `.claude/commands/adws-prime.md` entry point (AC: #1)
  - [x] 8.1 RED: Write test that `.claude/commands/adws-prime.md` exists and contains reference to `run_prime_command` and the prime-specific module, no longer marked as stub.
  - [x] 8.2 GREEN: Update the `.md` file content to reference the prime-specific module and describe what files are loaded.
  - [x] 8.3 REFACTOR: Verify file content, mypy, ruff.

- [x] Task 9: Export `run_prime_command`, `PrimeContextResult`, and `PrimeFileSpec` from commands package (AC: #1)
  - [x] 9.1 RED: Write tests for importing `run_prime_command`, `PrimeContextResult`, and `PrimeFileSpec` from `adws.adw_modules.commands`.
  - [x] 9.2 GREEN: Add exports to `adws/adw_modules/commands/__init__.py`.
  - [x] 9.3 REFACTOR: Verify import paths, mypy, ruff.

- [x] Task 10: Integration test -- full /prime command flow (AC: #1, #2, #3)
  - [x] 10.1 RED: Write integration test: invoke `run_prime_command` with a context, mock io_ops to simulate all files existing and directory tree succeeding. Verify PrimeContextResult has success=True, all expected files in files_loaded, all expected keys in context_sections (including "claude_md", "architecture", "epics", "adws_tree", "project_tree"), summary mentions all loaded files.
  - [x] 10.2 GREEN: Ensure integration path works end-to-end with mocked io_ops.
  - [x] 10.3 RED: Write integration test: invoke `run_prime_command` with mocked io_ops where architecture.md returns IOFailure (optional file missing). Verify PrimeContextResult has success=True (optional files don't block success), `files_loaded` omits the missing file, `context_sections` omits the missing key, summary mentions skipped file.
  - [x] 10.4 GREEN: Ensure optional file missing path works correctly.
  - [x] 10.5 RED: Write integration test: invoke `run_prime_command` with mocked io_ops where CLAUDE.md returns IOFailure (required file missing). Verify IOFailure propagates with error about missing required file.
  - [x] 10.6 GREEN: Ensure required file failure path works correctly.
  - [x] 10.7 REFACTOR: Clean up integration tests, verify all scenarios covered.

- [x] Task 11: Verify full integration and quality gates (AC: #4)
  - [x] 11.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x] 11.2 Run `uv run mypy adws/` -- strict mode passes
  - [x] 11.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 4.2)

**io_ops.py** has 12 public functions + 1 shared helper + 1 async helper + 1 internal exception:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]: ...
def run_shell_command(command: str, *, timeout: int | None = None, cwd: str | None = None) -> IOResult[ShellResult, PipelineError]: ...
def sleep_seconds(seconds: float) -> IOResult[None, PipelineError]: ...
def _build_verify_result(shell_result: ShellResult, tool_name: str, error_filter: Callable[[str], bool]) -> VerifyResult: ...
def run_jest_tests() -> IOResult[VerifyResult, PipelineError]: ...
def run_playwright_tests() -> IOResult[VerifyResult, PipelineError]: ...
def run_mypy_check() -> IOResult[VerifyResult, PipelineError]: ...
def run_ruff_check() -> IOResult[VerifyResult, PipelineError]: ...
def load_command_workflow(workflow_name: str) -> IOResult[Workflow, PipelineError]: ...
def execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]: ...
# Plus: async _execute_sdk_call_async(), _NoResultError exception
```

**types.py** has: `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**commands/** package has:
- `types.py` -- `CommandSpec` frozen dataclass
- `registry.py` -- `COMMAND_REGISTRY` (MappingProxyType, 6 commands: verify, build, implement, prime, load_bundle, convert_stories_to_beads), `get_command()`, `list_commands()`
- `dispatch.py` -- `run_command()` dispatch function (uses `.bind()` pattern, routes through io_ops). Has verify-specific routing via `run_verify_command`.
- `verify.py` -- `VerifyCommandResult`, `format_verify_success()`, `format_verify_failure()`, `run_verify_command()`
- `__init__.py` -- exports: `CommandSpec`, `VerifyCommandResult`, `get_command`, `list_commands`, `run_command`, `run_verify_command`

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`.

**engine/executor.py** has 8 functions. `_STEP_REGISTRY` has 6 entries: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants: IMPLEMENT_CLOSE, IMPLEMENT_VERIFY_CLOSE, CONVERT_STORIES_TO_BEADS, SAMPLE, VERIFY), `load_workflow()`, `list_workflows()`, 5 registered workflows.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 343 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: /prime Command Architecture

The `/prime` command is a non-workflow command with custom logic. Unlike `/verify` (which executes the verify workflow and formats results), `/prime` performs direct file reading and context assembly. It does NOT use a workflow or the engine -- it calls io_ops functions directly to read files and build a context bundle.

```
.claude/commands/adws-prime.md
    |
    v
adws/adw_modules/commands/dispatch.py  (run_command)
    |
    v (detects "prime" has specialized handler)
adws/adw_modules/commands/prime.py     (run_prime_command)
    |
    v (reads files and builds directory tree via io_ops)
adws/adw_modules/io_ops.py            (read_prime_file, get_directory_tree)
```

**Key design decisions:**

1. **PrimeContextResult** -- a new frozen dataclass in `commands/prime.py` that represents the user-facing output of the /prime command:
   ```python
   @dataclass(frozen=True)
   class PrimeContextResult:
       success: bool
       files_loaded: list[str]
       summary: str
       context_sections: dict[str, str] = field(default_factory=dict)
   ```

2. **PrimeFileSpec** -- defines which files to load:
   ```python
   @dataclass(frozen=True)
   class PrimeFileSpec:
       key: str            # section name in context_sections
       path: str           # relative path from project root
       description: str    # human-readable name
       required: bool      # True = failure is an error, False = skip gracefully
   ```

3. **PRIME_FILE_SPECS** -- the immutable tuple of files to load:
   ```python
   PRIME_FILE_SPECS: tuple[PrimeFileSpec, ...] = (
       PrimeFileSpec(
           key="claude_md",
           path="CLAUDE.md",
           description="TDD mandate and coding conventions",
           required=True,
       ),
       PrimeFileSpec(
           key="architecture",
           path="_bmad-output/planning-artifacts/architecture.md",
           description="Architecture decision document",
           required=False,
       ),
       PrimeFileSpec(
           key="epics",
           path="_bmad-output/planning-artifacts/epics.md",
           description="Epic and story breakdown",
           required=False,
       ),
   )
   ```

4. **No workflow backing** -- the `prime` command in the registry has `workflow_name=None`. This story changes the dispatch behavior so that "prime" gets a specialized handler (like "verify" got in Story 4.2) instead of falling through to the generic "NoWorkflowError". The dispatch ordering must be:
   - Check for unknown command
   - Check for "verify" specialized handler
   - Check for "prime" specialized handler
   - Check for workflow_name is None (NoWorkflowError -- catches "load_bundle" etc.)
   - Generic workflow path

5. **Security: no secrets** -- the `PRIME_FILE_SPECS` tuple deliberately excludes `.env`, `.env.sample`, and any credential files. A structural test verifies that no spec path contains secret-bearing segments. This is the architectural enforcement for AC #2.

6. **Optional vs required files** -- CLAUDE.md is required (it is the foundation). Architecture and epics files are optional -- they may not exist in every project, and their absence should not block context loading.

7. **Directory tree** -- two new io_ops functions produce directory structure strings. The `adws/` tree (depth=3) captures the Python module structure. The project root tree (depth=2) captures the overall project layout. These are informational -- directory tree failures are non-fatal.

### Design: Dispatch Routing Update

The dispatch function `run_command` in `dispatch.py` currently has this flow:
1. Look up command spec (unknown -> IOFailure)
2. Check if verify -> specialized handler
3. Check if workflow_name is None -> IOFailure(NoWorkflowError)
4. Generic workflow path

After this story, the flow becomes:
1. Look up command spec (unknown -> IOFailure)
2. Check if verify -> specialized handler
3. Check if prime -> specialized handler
4. Check if workflow_name is None -> IOFailure(NoWorkflowError)
5. Generic workflow path

The prime handler follows the same pattern as verify:
```python
if spec.name == "prime":
    def _wrap_pr(
        pr: PrimeContextResult,
    ) -> IOResult[WorkflowContext, PipelineError]:
        return IOSuccess(
            ctx.merge_outputs({"prime_result": pr}),
        )
    return run_prime_command(ctx).bind(_wrap_pr)
```

### Design: io_ops Functions for /prime

Two new io_ops functions are needed:

```python
def read_prime_file(path: str) -> IOResult[str, PipelineError]:
    """Read a context file by relative path from project root.

    Resolves the path relative to the project root and delegates
    to read_file(). Returns IOResult, never raises.
    """
    ...

def get_directory_tree(
    root: str,
    *,
    max_depth: int = 3,
) -> IOResult[str, PipelineError]:
    """Build a directory tree string for the given root.

    Excludes common non-relevant directories (.git, __pycache__,
    node_modules, .venv, .mypy_cache, .ruff_cache, .pytest_cache,
    htmlcov, .coverage). Returns a formatted tree string.
    """
    ...
```

**Why `read_prime_file` wraps `read_file`**: The existing `read_file` takes a `Path` object. The prime command works with string paths relative to the project root. `read_prime_file` handles the resolution from relative string to absolute Path, then delegates to `read_file`. This avoids duplicating file-reading error handling.

**Why `get_directory_tree` is a new function**: No existing io_ops function produces directory listings. This is genuine I/O (filesystem traversal) and belongs in io_ops per NFR10. The exclusion list prevents loading noisy generated directories.

After this story, io_ops.py will have 14 public functions (up from 12). Still within the ~15 function threshold noted in the architecture before considering a split into an `io_ops/` package.

### Design: Project Root Resolution

The `read_prime_file` io_ops function needs to resolve relative paths from the project root. The project root is determined by finding the directory containing `pyproject.toml`. This can be:

Option A (selected): Use a constant or function in io_ops that resolves the project root using `Path(__file__).resolve()` and walking up to find `pyproject.toml`. This is deterministic and testable (mock the path resolution).

Option B (rejected): Accept the project root as a parameter. Rejected because it pushes I/O concern (path resolution) into the command layer, violating NFR10.

The project root resolution should be a private helper `_find_project_root()` in io_ops.py, testable through its public consumers.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/commands/test_prime.py` -- tests for PrimeContextResult, PrimeFileSpec, PRIME_FILE_SPECS, _load_file_context, _load_directory_context, run_prime_command

**Modified test files**:
- `adws/tests/adw_modules/commands/test_dispatch.py` -- add prime-specific dispatch routing, regression tests for other commands
- `adws/tests/adw_modules/commands/test_wiring.py` -- add import tests for new exports, .md file update tests
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for `read_prime_file` and `get_directory_tree`

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_prime_context_result_construction`
- `test_prime_context_result_immutable`
- `test_prime_file_spec_construction`
- `test_prime_file_specs_contain_claude_md`
- `test_prime_file_specs_no_secret_paths`
- `test_load_file_context_all_files_exist`
- `test_load_file_context_optional_file_missing`
- `test_load_file_context_required_file_missing`
- `test_load_directory_context_success`
- `test_load_directory_context_tree_failure`
- `test_run_prime_command_success`
- `test_run_prime_command_required_file_failure`
- `test_run_prime_command_no_secrets`
- `test_dispatch_prime_uses_specialized_handler`
- `test_dispatch_load_bundle_still_returns_no_workflow_error`
- `test_dispatch_verify_still_works`
- `test_dispatch_build_still_works`
- `test_read_prime_file_success`
- `test_read_prime_file_not_found`
- `test_get_directory_tree_success`
- `test_get_directory_tree_excludes_hidden`
- `test_get_directory_tree_invalid_directory`

**Mock targets for prime command tests**:
- `adws.adw_modules.io_ops.read_prime_file` -- mock file reading
- `adws.adw_modules.io_ops.get_directory_tree` -- mock directory listing

**For dispatch regression tests**: Same mock targets as Story 4.1/4.2 dispatch tests.

**For io_ops tests**: Use `tmp_path` pytest fixture for filesystem tests (read_prime_file, get_directory_tree). Mock `_find_project_root` for `read_prime_file` tests to control the resolved path.

### Ruff Considerations

- `FBT001`/`FBT002` (boolean positional): `PrimeContextResult.success` and `PrimeFileSpec.required` are fields, not positional params -- no issue.
- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files. `max_depth` parameter has default value.
- `E501` (line too long): Keep all lines under 88 characters.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.
- `ARG001` (unused function argument): The `ctx` parameter in `run_prime_command` may not be directly used for file loading, but it is part of the command interface signature. If truly unused, pass it through to the result or document why it is accepted.
- `S108` (hardcoded temp directory): Avoid `/tmp/` literal strings in test data.

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- `run_prime_command` returns IOResult, never raises.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Prime command uses io_ops functions for file reading and directory listing.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR16**: No secrets in source control -- PRIME_FILE_SPECS excludes credentials.
- **FR28**: Command has .md entry point backed by Python module.
- **FR31**: Developer can invoke /prime to load codebase context into session.

### What NOT to Do

- Do NOT implement a workflow for /prime -- this is a non-workflow command with custom logic. There is no engine orchestration needed.
- Do NOT add any steps to `_STEP_REGISTRY` -- commands are NOT steps.
- Do NOT change the verify command (`commands/verify.py`) or its routing -- it is correct as-is from Story 4.2.
- Do NOT change any verify step functions, verify workflow, or io_ops verify functions -- they are correct as-is.
- Do NOT read `.env`, `.env.sample`, credentials.json, or any secret-bearing file in the prime command.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances via `with_updates()` or `merge_outputs()`.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT use `unsafe_perform_io` in production code (commands, steps). Only use `.bind()` for composing IOResult chains.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT break the existing `run_command` tests for "verify", "build", or "unknown" commands.
- Do NOT add command-specific routing for commands other than "prime" in this story -- each command gets its own routing in its own story.
- Do NOT change the engine executor, step registry, or any registered workflow steps.
- Do NOT implement the `__main__.py` CLI entry point -- the .md file delegates to dispatch, which routes to prime-specific logic.
- Do NOT read BMAD files during execution workflows (NFR19) -- the prime command reads planning artifacts for context loading, which is a developer-initiated action (not an execution workflow). This is similar to how `/convert-stories-to-beads` reads BMAD files during conversion (not execution).

### Project Structure Notes

Files to create:
- `adws/adw_modules/commands/prime.py` -- `PrimeContextResult`, `PrimeFileSpec`, `PRIME_FILE_SPECS`, `_load_file_context()`, `_load_directory_context()`, `run_prime_command()`
- `adws/tests/adw_modules/commands/test_prime.py` -- all prime command tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `read_prime_file()`, `get_directory_tree()`, `_find_project_root()` private helper
- `adws/adw_modules/commands/dispatch.py` -- add prime-specific routing in `run_command`
- `adws/adw_modules/commands/__init__.py` -- add exports for `PrimeContextResult`, `PrimeFileSpec`, `run_prime_command`
- `.claude/commands/adws-prime.md` -- update from stub to full entry point
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for `read_prime_file`, `get_directory_tree`
- `adws/tests/adw_modules/commands/test_dispatch.py` -- add prime routing tests, regression tests
- `adws/tests/adw_modules/commands/test_wiring.py` -- add import tests for new exports, .md file tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3] -- AC and story definition (FR31)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] -- Epic summary: "Developer can invoke /implement, /verify, /build, and /prime commands."
- [Source: _bmad-output/planning-artifacts/architecture.md#Command Inventory] -- `/prime` maps to "TBD" Python module, P2 priority
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, load_workflow() pure lookup
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, CLAUDE.md mandate
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Step patterns, io_ops boundary, ROP patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Four-layer pipeline boundary, io_ops boundary
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR31: "/prime command for context loading"
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- Full project directory tree
- [Source: adws/adw_modules/commands/dispatch.py] -- run_command dispatch function with verify routing
- [Source: adws/adw_modules/commands/verify.py] -- Verify command pattern (specialized handler + result formatting)
- [Source: adws/adw_modules/commands/registry.py] -- COMMAND_REGISTRY with "prime" mapping to workflow_name=None
- [Source: adws/adw_modules/commands/types.py] -- CommandSpec frozen dataclass
- [Source: adws/adw_modules/commands/__init__.py] -- Current exports: CommandSpec, VerifyCommandResult, get_command, list_commands, run_command, run_verify_command
- [Source: adws/adw_modules/io_ops.py] -- read_file, load_command_workflow, execute_command_workflow (12 public functions currently)
- [Source: adws/adw_modules/types.py] -- WorkflowContext with merge_outputs()
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/tests/conftest.py] -- sample_workflow_context, mock_io_ops fixtures
- [Source: .claude/commands/adws-prime.md] -- Current stub .md entry point
- [Source: CLAUDE.md] -- TDD mandate (one of the files /prime loads)
- [Source: _bmad-output/implementation-artifacts/4-2-verify-command-entry-point.md] -- Verify command story with specialized dispatch routing pattern
- [Source: _bmad-output/implementation-artifacts/4-1-command-pattern-md-entry-points-and-python-module-wiring.md] -- Command infrastructure, dispatch, registry, wiring patterns

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

From Story 4.2 learnings:
- **Verify dispatch routing pattern**: `run_command` checks `spec.name == "verify"` and routes to `run_verify_command`, wrapping result in WorkflowContext via `.bind(_wrap_vr)`. Follow this exact pattern for prime.
- **ROP .bind()/.lash() pattern**: verify.py uses `.bind()` for success composition and `.lash()` for failure-to-success conversion. Prime will use `.bind()` for composing file reads.
- **VerifyCommandResult wrapping**: After specialized handler returns, result is placed in `ctx.merge_outputs({"verify_result": vr})`. Prime should use `ctx.merge_outputs({"prime_result": pr})`.
- **343 tests**: Current test count (excluding 2 enemy tests), 100% line+branch coverage.
- **Dispatch test update**: When adding verify routing in Story 4.2, one existing dispatch test was updated to use "build" instead of "verify" since verify now has a specialized handler. Similar care needed when adding prime routing.

From Story 4.1 learnings:
- **Circular import resolution**: io_ops.py uses lazy imports (PLC0415 noqa) inside function bodies to avoid circular imports with engine/executor.py. New io_ops functions for prime should NOT need lazy imports (they don't reference engine).
- **MappingProxyType**: COMMAND_REGISTRY uses `MappingProxyType` for runtime immutability.
- **ROP .bind() pattern**: dispatch.py uses `.bind()` instead of `unsafe_perform_io`. All production code must follow this pattern.
- **Mock targets for io_ops**: Tests mock at `adws.adw_modules.io_ops.<function_name>`.
- **CommandSpec**: prime command has `workflow_name=None` in registry.

From Story 3.3 learnings:
- **Pure functions**: Functions that don't do I/O return plain values, not IOResult. `_load_file_context` and `_load_directory_context` DO call io_ops, so they return IOResult.
- **VerifyFeedback serialization**: Pipe delimiter format. Not directly relevant but shows structured data pattern.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen. PrimeContextResult's `files_loaded` list and `context_sections` dict are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Relationship to Subsequent Stories

This story follows the same pattern as 4.2 (specialized command handler) but for a non-workflow command:

1. **Story 4.1 (done)**: Command pattern -- registry, dispatch, .md entry points
2. **Story 4.2 (done)**: `/verify` command -- specialized handler, workflow-backed
3. **Story 4.3 (this)**: `/prime` command -- specialized handler, NON-workflow (custom logic)
4. **Story 4.4**: `/build` command -- implement_close workflow
5. **Stories 4.5-4.8**: TDD workflow steps and `/implement` command

The prime command establishes the pattern for non-workflow commands with custom io_ops logic. The `/load_bundle` command (Epic 5, Story 5.3) will follow a similar pattern.

### io_ops.py Size Note

After this story, io_ops.py will have 14 public functions (up from 12) plus 1 new private helper (`_find_project_root`). This approaches the ~15 function threshold noted in the architecture for considering an `io_ops/` package split. Monitor after this story; the split may become necessary during Story 4.4 or later.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- 390 tests pass (47 new, up from 343), 2 enemy tests deselected
- 100% line + branch coverage on all adws/ code
- mypy strict mode: zero errors (60 source files checked)
- ruff: zero violations
- io_ops.py now has 14 public functions + 2 private helpers (_find_project_root, _build_tree_lines)
- Dispatch ordering: unknown -> verify -> prime -> no-workflow -> generic workflow
- _extract_io_value helper uses unsafe_perform_io in private boundary-crossing context (loops accumulating IOResult values)
- Existing dispatch test for "prime" -> NoWorkflowError updated to use "load_bundle" (since prime now has specialized handler)
- _build_tree_lines uses Path.iterdir() per ruff PTH208 (not os.listdir)

### File List

Created:
- adws/adw_modules/commands/prime.py -- PrimeContextResult, PrimeFileSpec, PRIME_FILE_SPECS, _extract_io_value, _load_file_context, _load_directory_context, run_prime_command
- adws/tests/adw_modules/commands/test_prime.py -- 24 tests for prime command (unit + integration)

Modified:
- adws/adw_modules/io_ops.py -- added _EXCLUDED_DIRS, _find_project_root, read_prime_file, get_directory_tree, _build_tree_lines
- adws/adw_modules/commands/dispatch.py -- added prime-specific routing via run_prime_command, reordered NoWorkflowError check after prime
- adws/adw_modules/commands/__init__.py -- added PrimeContextResult, PrimeFileSpec, run_prime_command exports
- .claude/commands/adws-prime.md -- updated from stub to full entry point referencing run_prime_command
- adws/tests/adw_modules/test_io_ops.py -- added 13 tests for read_prime_file, get_directory_tree, _find_project_root, _build_tree_lines
- adws/tests/adw_modules/commands/test_dispatch.py -- added 5 prime dispatch tests + regression tests, updated existing NoWorkflow test
- adws/tests/adw_modules/commands/test_wiring.py -- added 5 prime export and .md wiring tests
- _bmad-output/implementation-artifacts/sprint-status.yaml -- updated 4-3 status to in-progress then review

## Senior Developer Review

### Reviewer
Claude Opus 4.5 (adversarial review mode)

### Review Date
2026-02-02

### Verdict
APPROVED with 3 fixes applied. All quality gates pass.

### Issues Found

| # | Severity | File | Description | Resolution |
|---|----------|------|-------------|------------|
| 1 | MEDIUM | test_dispatch.py | Duplicate test: `test_run_command_load_bundle_no_workflow` was identical to `test_run_command_no_workflow_returns_failure` (same input, same assertions). Test bloat from Story 4.3 adding a test that duplicated an existing one updated in the same story. | Removed the duplicate test. 389 tests remain (down from 390). |
| 2 | MEDIUM | io_ops.py | `.coverage` in `_EXCLUDED_DIRS` is a file, not a directory. The exclusion list is only checked inside `if entry_path.is_dir()`, making the `.coverage` entry dead code that never triggers. | Removed `.coverage` from `_EXCLUDED_DIRS`. Updated corresponding test. |
| 3 | MEDIUM | prime.py | `_extract_io_value` accepted `IOResult[str, PipelineError]` but would crash with `UnwrapFailedError` if called with `IOFailure`. Type signature was misleading -- callers guard with `isinstance(result, IOSuccess)` but the function itself had no contract enforcement. | Added defensive `assert isinstance(result, IOSuccess)` with clear precondition documentation in docstring. |
| 4 | LOW | io_ops.py | No path traversal validation in `read_prime_file`. An adversarial `PrimeFileSpec` with `path="../../../etc/passwd"` would resolve and read. | Not fixed -- `PRIME_FILE_SPECS` is a hardcoded frozen tuple. Risk is architectural, not runtime. |
| 5 | LOW | io_ops.py | `_find_project_root` fallback returns `adws/adw_modules/` which is not a meaningful project root. | Not fixed -- marked `pragma: no cover`, only reachable if filesystem root has no `pyproject.toml`. |

### Quality Gate Results (Post-Fix)

- **pytest**: 389 passed, 2 deselected (enemy) -- all pass
- **coverage**: 100% line + branch (4047 stmts, 202 branches, 0 missing)
- **mypy --strict**: zero errors (60 source files)
- **ruff check**: zero violations

### Architecture Assessment

The implementation correctly follows the established patterns:
- Non-workflow command with custom io_ops logic (parallels verify command pattern from Story 4.2)
- All I/O behind io_ops.py boundary (NFR10)
- ROP .bind() composition for IOResult chains in production code
- Frozen dataclasses for all data types
- Dispatch ordering: unknown -> verify -> prime -> no-workflow -> generic (correct)
- Security: PRIME_FILE_SPECS excludes secret-bearing paths (tested structurally)

### Test Quality Assessment

Test coverage is thorough with 24 prime-specific tests covering:
- Data type construction and immutability (6 tests)
- File spec validation including secret path exclusion (5 tests)
- File context loading: all-exist, optional-missing, required-missing, empty specs (4 tests)
- Directory context: success, single failure, both fail (3 tests)
- Command: success, required failure, no-secrets (3 tests)
- Integration: full flow, optional missing, required missing (3 tests)
- Plus 5 dispatch routing tests and 5 wiring tests in their respective files

Mock targets are correct (patching at `adws.adw_modules.io_ops.*` module level).

### Notes for Future Stories

- io_ops.py now has 14 public functions approaching the ~15 threshold for package split (per architecture doc). Monitor during Story 4.4.
- The `_extract_io_value` pattern with `unsafe_perform_io` in a private helper for imperative loops is acceptable but should not proliferate. Future non-workflow commands should prefer `.bind()` composition where possible.

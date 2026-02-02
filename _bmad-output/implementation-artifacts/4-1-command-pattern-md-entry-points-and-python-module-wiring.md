# Story 4.1: Command Pattern - .md Entry Points & Python Module Wiring

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want a consistent pattern for defining commands as Claude command .md files backed by Python modules,
so that every command has a natural language entry point and testable logic separated cleanly.

## Acceptance Criteria

1. **Given** the adws project structure from Epic 1, **When** I inspect the command pattern, **Then** each command has a `.md` file in the Claude commands directory (`.claude/commands/`) as its natural language entry point **And** each `.md` file delegates to a Python module in `adws/` for testable logic (FR28) **And** the Python module follows the io_ops boundary pattern for any external I/O.

2. **Given** the command pattern is established, **When** I create a new command, **Then** I follow the pattern: `.md` entry point + Python module + tests **And** the template/pattern is documented for consistency across all commands.

3. **Given** the command pattern, **When** I run tests, **Then** the wiring between .md entry point and Python module is verified **And** 100% coverage is maintained (NFR9).

4. **Given** all code, **When** I run `uv run pytest adws/tests/ -m "not enemy"`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Create the command module infrastructure in `adws/adw_modules/commands/` (AC: #1, #2)
  - [x]1.1 RED: Write test for `CommandSpec` frozen dataclass with fields: `name` (str), `description` (str), `python_module` (str), `workflow_name` (str | None). Verify construction, immutability, and field access.
  - [x]1.2 GREEN: Implement `CommandSpec` as a frozen dataclass in `adws/adw_modules/commands/types.py`.
  - [x]1.3 RED: Write test for `COMMAND_REGISTRY` dict mapping command names to `CommandSpec` instances. Verify registry contains entries for all planned commands: `verify`, `prime`, `build`, `implement`, `load_bundle`, `convert_stories_to_beads`. Verify each has `name`, `description`, `python_module`, and correct `workflow_name` (or None for non-workflow commands).
  - [x]1.4 GREEN: Implement `COMMAND_REGISTRY` in `adws/adw_modules/commands/registry.py` with all 6 command specs.
  - [x]1.5 RED: Write test for `get_command(name: str) -> CommandSpec | None` that performs registry lookup.
  - [x]1.6 GREEN: Implement `get_command` in registry module.
  - [x]1.7 RED: Write test for `list_commands() -> list[CommandSpec]` that returns all registered commands.
  - [x]1.8 GREEN: Implement `list_commands` in registry module.
  - [x]1.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 2: Create `run_command` dispatch function (AC: #1, #3)
  - [x]2.1 RED: Write test for `run_command(name: str, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. Given a valid command name that maps to a workflow, verify it loads the workflow via `load_workflow()` and executes it via `run_workflow()`. Mock both `load_workflow` and `run_workflow` through io_ops boundary.
  - [x]2.2 GREEN: Implement `run_command` in `adws/adw_modules/commands/dispatch.py`. Uses `get_command()` to find the spec, then delegates to `load_workflow()` + `run_workflow()` for workflow-backed commands.
  - [x]2.3 RED: Write test for `run_command` with unknown command name. Verify returns `IOFailure(PipelineError(...))` with error_type `"UnknownCommandError"` and available commands listed in context.
  - [x]2.4 GREEN: Implement unknown command error handling.
  - [x]2.5 RED: Write test for `run_command` when `load_workflow` returns None (workflow not registered). Verify returns `IOFailure(PipelineError(...))` with error_type `"WorkflowNotFoundError"`.
  - [x]2.6 GREEN: Implement workflow-not-found error handling.
  - [x]2.7 RED: Write test for `run_command` with a non-workflow command (workflow_name is None). Verify it returns `IOFailure(PipelineError(...))` with error_type `"NoWorkflowError"` indicating the command does not have an associated workflow. (Non-workflow commands like `/prime` have custom logic added in their own stories.)
  - [x]2.8 GREEN: Implement non-workflow command handling.
  - [x]2.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 3: Create io_ops functions for command infrastructure (AC: #1)
  - [x]3.1 RED: Write test for `io_ops.load_command_workflow(workflow_name: str) -> IOResult[Workflow, PipelineError]`. This wraps `load_workflow()` in the io_ops pattern -- returns `IOSuccess(workflow)` or `IOFailure(PipelineError(...))`.
  - [x]3.2 GREEN: Implement `load_command_workflow` in io_ops.py.
  - [x]3.3 RED: Write test for `io_ops.execute_command_workflow(workflow: Workflow, ctx: WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`. This wraps `run_workflow()` in the io_ops pattern.
  - [x]3.4 GREEN: Implement `execute_command_workflow` in io_ops.py.
  - [x]3.5 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 4: Create `.md` command entry point files (AC: #1, #2)
  - [x]4.1 Create `.claude/commands/adws-verify.md` -- natural language entry point for `/verify`. Includes description, delegates to `uv run python -m adws.adw_modules.commands.dispatch verify`.
  - [x]4.2 Create `.claude/commands/adws-prime.md` -- entry point for `/prime`. Stub noting implementation in Story 4.3.
  - [x]4.3 Create `.claude/commands/adws-build.md` -- entry point for `/build`. Stub noting implementation in Story 4.4.
  - [x]4.4 Create `.claude/commands/adws-implement.md` -- entry point for `/implement`. Stub noting implementation in Story 4.8.
  - [x]4.5 Verify all `.md` files follow the same template structure.

- [x] Task 5: Create command wiring verification tests (AC: #3)
  - [x]5.1 RED: Write test that verifies every command in `COMMAND_REGISTRY` maps to a real Python module path that exists as an importable module.
  - [x]5.2 GREEN: Ensure all Python modules referenced by command specs exist and are importable.
  - [x]5.3 RED: Write test that verifies every command with a `workflow_name` maps to a registered workflow via `load_workflow()`.
  - [x]5.4 GREEN: Ensure all workflow names in command specs match registered workflows.
  - [x]5.5 RED: Write test that `.claude/commands/adws-verify.md` file exists and contains the expected delegation instructions.
  - [x]5.6 GREEN: Verify file exists and content is correct.
  - [x]5.7 RED: Write tests for `.claude/commands/adws-build.md`, `.claude/commands/adws-prime.md`, `.claude/commands/adws-implement.md` existence.
  - [x]5.8 GREEN: Verify all command .md files exist.
  - [x]5.9 REFACTOR: Clean up, verify mypy/ruff.

- [x] Task 6: Export command modules from package __init__.py (AC: #1, #2)
  - [x]6.1 RED: Write tests for importing `CommandSpec`, `get_command`, `list_commands`, `run_command` from `adws.adw_modules.commands`.
  - [x]6.2 GREEN: Create `adws/adw_modules/commands/__init__.py` with exports.
  - [x]6.3 REFACTOR: Verify import paths, mypy, ruff.

- [x] Task 7: Verify full integration and quality gates (AC: #4)
  - [x]7.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all tests pass, 100% coverage
  - [x]7.2 Run `uv run mypy adws/` -- strict mode passes
  - [x]7.3 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 3.3)

**io_ops.py** has 10 public functions + 1 shared helper + 1 async helper + 1 internal exception:
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
# Plus: async _execute_sdk_call_async(), _NoResultError exception
```

**types.py** has: `VerifyResult`, `VerifyFeedback`, `ShellResult`, `WorkflowContext` (with `with_updates()`, `add_feedback()`, `promote_outputs_to_inputs()`, `merge_outputs()`), `AdwsRequest`, `AdwsResponse`, `DEFAULT_CLAUDE_MODEL`, `PermissionMode`.

**errors.py** has: `PipelineError(step_name, error_type, message, context)` frozen dataclass with `to_dict()` and `__str__()`.

**steps/__init__.py** exports: `check_sdk_available`, `execute_shell_step`, `run_jest_step`, `run_playwright_step`, `run_mypy_step`, `run_ruff_step`, `accumulate_verify_feedback`, `add_verify_feedback_to_context`, `build_feedback_context`.

**engine/executor.py** has 8 functions: `_resolve_step_function`, `run_step`, `_run_step_with_retry`, `_resolve_input_from`, `_should_skip_step`, `_record_failure`, `_finalize_workflow`, `run_workflow`. `_STEP_REGISTRY` has 6 entries.

**engine/types.py** has: `Step` (with `always_run`, `max_attempts`, `retry_delay_seconds`, `shell`, `command`, `output`, `input_from`, `condition`), `Workflow` (with `dispatchable`), `StepFunction`.

**engine/combinators.py** has: `with_verification`, `sequence`.

**workflows/__init__.py** has: `WorkflowName` (5 constants: IMPLEMENT_CLOSE, IMPLEMENT_VERIFY_CLOSE, CONVERT_STORIES_TO_BEADS, SAMPLE, VERIFY), `load_workflow()`, `list_workflows()`, 5 registered workflows. `_REGISTRY` dict maps names to workflows.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**Current test count**: 283 tests (excluding 2 enemy tests), 100% line+branch coverage.

### IOResult Type Order Convention

**CRITICAL**: This project uses `IOResult[SuccessType, ErrorType]` -- success first, error second. This is the `returns` library v0.26.0 convention. All existing code follows this order. Do NOT reverse it.

Examples from codebase:
- `IOResult[WorkflowContext, PipelineError]` -- success is `WorkflowContext`
- `IOResult[VerifyResult, PipelineError]` -- success is `VerifyResult`
- `IOResult[ShellResult, PipelineError]` -- success is `ShellResult`

### Design: Command Architecture Pattern

Epic 4 introduces the "dual-layer command pattern" (FR28): each developer command exists as both a Claude command `.md` file (natural language entry point) and a Python module (testable logic). This story establishes the foundational pattern that all subsequent command stories (4.2 through 4.8) build upon.

```
.claude/commands/adws-verify.md    -->    adws/adw_modules/commands/dispatch.py
.claude/commands/adws-build.md     -->    adws/adw_modules/commands/dispatch.py
.claude/commands/adws-prime.md     -->    adws/adw_modules/commands/dispatch.py
.claude/commands/adws-implement.md -->    adws/adw_modules/commands/dispatch.py
```

**Key design decisions:**

1. **Commands package** -- `adws/adw_modules/commands/` is a new package containing:
   - `types.py` -- `CommandSpec` frozen dataclass (command metadata)
   - `registry.py` -- `COMMAND_REGISTRY`, `get_command()`, `list_commands()`
   - `dispatch.py` -- `run_command()` dispatch function
   - `__init__.py` -- public exports

2. **CommandSpec dataclass** -- describes a command's metadata without executing it:
   ```python
   @dataclass(frozen=True)
   class CommandSpec:
       """Metadata for a registered command."""
       name: str                      # e.g., "verify"
       description: str               # Human-readable description
       python_module: str             # e.g., "adws.adw_modules.commands.dispatch"
       workflow_name: str | None = None  # Workflow to execute, or None for custom logic
   ```

3. **Registry pattern** -- all commands registered in a single dict, consistent with the workflow registry pattern in `workflows/__init__.py`:
   ```python
   COMMAND_REGISTRY: dict[str, CommandSpec] = {
       "verify": CommandSpec(
           name="verify",
           description="Run full local quality gate",
           python_module="adws.adw_modules.commands.dispatch",
           workflow_name="verify",  # Maps to WorkflowName.VERIFY
       ),
       "build": CommandSpec(
           name="build",
           description="Fast-track trivial changes",
           python_module="adws.adw_modules.commands.dispatch",
           workflow_name="implement_close",  # Maps to WorkflowName.IMPLEMENT_CLOSE
       ),
       "implement": CommandSpec(
           name="implement",
           description="Execute full TDD-enforced implementation workflow",
           python_module="adws.adw_modules.commands.dispatch",
           workflow_name="implement_verify_close",  # Maps to WorkflowName.IMPLEMENT_VERIFY_CLOSE
       ),
       "prime": CommandSpec(
           name="prime",
           description="Load codebase context into session",
           python_module="adws.adw_modules.commands.dispatch",
           workflow_name=None,  # Custom logic, no workflow
       ),
       "load_bundle": CommandSpec(
           name="load_bundle",
           description="Reload previous session context",
           python_module="adws.adw_modules.commands.dispatch",
           workflow_name=None,  # Custom logic, no workflow (Epic 5)
       ),
       "convert_stories_to_beads": CommandSpec(
           name="convert_stories_to_beads",
           description="Convert BMAD stories to Beads issues",
           python_module="adws.adw_modules.commands.dispatch",
           workflow_name="convert_stories_to_beads",  # Maps to WorkflowName.CONVERT_STORIES_TO_BEADS
       ),
   }
   ```

4. **run_command dispatch function** -- the central dispatch point for all commands:
   ```python
   def run_command(
       name: str,
       ctx: WorkflowContext,
   ) -> IOResult[WorkflowContext, PipelineError]:
       """Dispatch a command by name. Workflow-backed commands execute the associated workflow."""
   ```

5. **io_ops wiring** -- `run_command` uses io_ops functions to load and execute workflows, maintaining the I/O boundary (NFR10). The io_ops functions `load_command_workflow` and `execute_command_workflow` wrap the existing `load_workflow()` and `run_workflow()` functions behind the io_ops boundary.

### Design: .md Entry Point Template

Each command `.md` file in `.claude/commands/` follows this template:

```markdown
# /adws-<command>

<One-line description of what the command does.>

## Usage

Invoke this command to <action description>.

## What it does

<Numbered list of what the command executes.>

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch <command_name>`

All testable logic lives in `adws/adw_modules/commands/` -- the .md file
is the natural language entry point only (FR28).
```

**Naming convention for .md files**: `adws-<command>.md` prefix to avoid collisions with existing BMAD commands in `.claude/commands/`. The prefix groups all ADWS commands together alphabetically.

### Design: io_ops Boundary for Commands

Two new io_ops functions wrap workflow loading and execution for the command layer:

```python
def load_command_workflow(
    workflow_name: str,
) -> IOResult[Workflow, PipelineError]:
    """Load a workflow by name for command execution."""
    ...

def execute_command_workflow(
    workflow: Workflow,
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Execute a workflow through the engine."""
    ...
```

These functions do NOT perform actual I/O themselves (they call `load_workflow()` and `run_workflow()` which are already in-process). However, wrapping them in io_ops is important because:
1. `run_workflow()` ultimately calls step functions which call io_ops for real I/O
2. Tests need to mock at the io_ops boundary to isolate command dispatch logic
3. It maintains the established pattern: steps/commands never call engine functions directly

**Alternative considered and rejected**: Having `run_command` call `load_workflow` and `run_workflow` directly (not through io_ops). Rejected because it breaks the io_ops boundary pattern -- command dispatch code should be testable by mocking io_ops, just like step code.

### Design: Why a Commands Package (Not a Single File)

The architecture specifies that commands follow the `.md` + Python module pattern (FR28). A commands package provides:

1. **Separation of concerns** -- type definitions, registry, and dispatch logic in separate files
2. **Extensibility** -- Stories 4.2-4.8 add command-specific logic without bloating a single file
3. **Testability** -- each module can be tested independently
4. **Consistency** -- mirrors the `engine/` package structure (types.py, executor.py, etc.)

The package lives under `adws/adw_modules/commands/` because:
- Commands are part of the ADWS module infrastructure
- They use engine and workflow types (same level as engine/ and steps/)
- They follow the same patterns (io_ops boundary, frozen dataclasses, etc.)

### Design: Command .md Files Are Stubs Until Their Stories

Only the `/verify` command `.md` file will have full delegation instructions in this story. The other `.md` files (`adws-build.md`, `adws-prime.md`, `adws-implement.md`) are created as stubs that document:
- What the command will do
- Which story implements the full logic
- That the command pattern is established and ready for wiring

This matches the workflow registry pattern where `_IMPLEMENT_VERIFY_CLOSE` has `steps=[]` until Epic 4 stories populate it.

### Test Strategy

**New test files** (one per module):
- `adws/tests/adw_modules/commands/__init__.py` -- test package init
- `adws/tests/adw_modules/commands/test_types.py` -- CommandSpec tests
- `adws/tests/adw_modules/commands/test_registry.py` -- registry, get_command, list_commands tests
- `adws/tests/adw_modules/commands/test_dispatch.py` -- run_command tests
- `adws/tests/adw_modules/commands/test_wiring.py` -- end-to-end wiring verification tests

**Modified test files**:
- `adws/tests/adw_modules/test_io_ops.py` -- add tests for `load_command_workflow` and `execute_command_workflow`

**Test naming convention**: `test_<function>_<scenario>`, e.g.:
- `test_command_spec_construction`
- `test_command_spec_immutable`
- `test_get_command_verify_returns_spec`
- `test_get_command_unknown_returns_none`
- `test_list_commands_returns_all`
- `test_run_command_verify_executes_workflow`
- `test_run_command_unknown_returns_failure`
- `test_run_command_workflow_not_found`
- `test_run_command_no_workflow_returns_failure`
- `test_wiring_all_commands_have_importable_modules`
- `test_wiring_workflow_commands_map_to_registered_workflows`
- `test_wiring_verify_md_exists`

**Mock targets for dispatch tests**:
- `adws.adw_modules.io_ops.load_command_workflow` -- mock workflow loading
- `adws.adw_modules.io_ops.execute_command_workflow` -- mock workflow execution

**For wiring verification tests**: No mocks needed -- these verify real module imports and file existence.

### Ruff Considerations

- `FBT001`/`FBT002` (boolean positional): Not applicable -- no boolean params in command functions.
- `S101` (assert): Suppressed in test files per pyproject.toml.
- `PLR2004` (magic numbers): Suppressed in test files.
- `E501` (line too long): Keep all lines under 88 characters.
- `TCH001`/`TCH002` (TYPE_CHECKING imports): Use TYPE_CHECKING guard for types used only in annotations.
- `ARG001` (unused function argument): The `ctx` parameter in `run_command` is always used (passed to workflow execution).

### Architecture Compliance

- **NFR1**: No uncaught exceptions -- `run_command` returns IOResult, never raises.
- **NFR9**: 100% line + branch coverage on all adws/ code.
- **NFR10**: All I/O behind io_ops.py boundary. Command dispatch uses io_ops functions for workflow loading and execution.
- **NFR11**: mypy strict mode -- all function signatures fully typed.
- **NFR12**: ruff ALL rules -- zero lint violations.
- **NFR13**: Workflow definitions (Tier 1) testable without mocking ROP internals.
- **FR28**: Each command has a `.md` entry point backed by a Python module in `adws/`.

### What NOT to Do

- Do NOT implement full command logic for `/verify`, `/build`, `/prime`, or `/implement` -- those are Stories 4.2, 4.3, 4.4, and 4.8 respectively. This story establishes the PATTERN only.
- Do NOT create step functions for commands -- commands are NOT steps. They are a separate layer that uses workflows, which use steps.
- Do NOT add command functions to `_STEP_REGISTRY` in executor.py -- commands are not steps.
- Do NOT put command code in `adws/adw_modules/steps/` -- create a new `adws/adw_modules/commands/` package.
- Do NOT change any existing steps, workflows, engine code, or io_ops functions from Epic 2/3 -- build ON TOP of them.
- Do NOT change the `IOResult` type parameter order -- success first, error second: `IOResult[SuccessType, ErrorType]`.
- Do NOT mutate `WorkflowContext` -- always return new instances.
- Do NOT use `_inner_value` -- use `unsafe_perform_io()` from `returns.unsafe` when unwrapping IOResults in tests.
- Do NOT change existing test assertions or existing function signatures.
- Do NOT prefix .md files with just the command name (e.g., `verify.md`) -- use `adws-` prefix to avoid collisions with existing BMAD commands.
- Do NOT make command dispatch depend on the engine directly -- use io_ops wrappers to maintain the boundary.
- Do NOT implement the `__main__.py` CLI entry point -- the `.md` files delegate to `uv run python -m adws.adw_modules.commands.dispatch <name>`, but the actual CLI invocation mechanism is a future concern. Focus on the Python module wiring and the `.md` entry points.
- Do NOT create command logic that reads BMAD files during execution (NFR19) -- commands receive their context from Beads issue descriptions (via the workflow).
- Do NOT change the verify workflow, implement_verify_close workflow, or any registered workflow steps -- they remain as-is from previous stories.

### Project Structure Notes

Files to create:
- `adws/adw_modules/commands/__init__.py` -- package init with exports
- `adws/adw_modules/commands/types.py` -- `CommandSpec` frozen dataclass
- `adws/adw_modules/commands/registry.py` -- `COMMAND_REGISTRY`, `get_command()`, `list_commands()`
- `adws/adw_modules/commands/dispatch.py` -- `run_command()` dispatch function
- `.claude/commands/adws-verify.md` -- verify command entry point
- `.claude/commands/adws-build.md` -- build command entry point (stub)
- `.claude/commands/adws-prime.md` -- prime command entry point (stub)
- `.claude/commands/adws-implement.md` -- implement command entry point (stub)
- `adws/tests/adw_modules/commands/__init__.py` -- test package init
- `adws/tests/adw_modules/commands/test_types.py` -- CommandSpec tests
- `adws/tests/adw_modules/commands/test_registry.py` -- registry tests
- `adws/tests/adw_modules/commands/test_dispatch.py` -- dispatch tests
- `adws/tests/adw_modules/commands/test_wiring.py` -- wiring verification tests

Files to modify:
- `adws/adw_modules/io_ops.py` -- add `load_command_workflow` and `execute_command_workflow` functions
- `adws/tests/adw_modules/test_io_ops.py` -- add io_ops command function tests

No files to delete.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1] -- AC and story definition (FR28)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] -- Epic summary: "Developer can invoke /implement, /verify, /build, and /prime commands. Each command has a .md entry point backed by a Python module."
- [Source: _bmad-output/planning-artifacts/architecture.md#Command Inventory] -- Table of all commands with Python module mappings
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure] -- `.claude/commands/` directory, `adws/adw_modules/` structure
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] -- Dispatch registry, dispatchable flag, `load_workflow()` pure lookup
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6] -- TDD enforcement, command entry points delegate to Python modules
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] -- Dual-layer command pattern: `.md` + Python module
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] -- Four-layer pipeline boundary, io_ops boundary
- [Source: _bmad-output/planning-artifacts/architecture.md#FR Coverage Map] -- FR28: "Command .md entry point + Python module pattern"
- [Source: adws/adw_modules/io_ops.py] -- io_ops boundary with 10 public functions
- [Source: adws/adw_modules/types.py] -- WorkflowContext, AdwsRequest, AdwsResponse
- [Source: adws/adw_modules/errors.py] -- PipelineError frozen dataclass
- [Source: adws/adw_modules/engine/types.py] -- Workflow, Step, StepFunction
- [Source: adws/adw_modules/engine/executor.py] -- run_step, run_workflow, _STEP_REGISTRY
- [Source: adws/workflows/__init__.py] -- WorkflowName registry, load_workflow(), list_workflows(), 5 registered workflows
- [Source: adws/adw_modules/steps/__init__.py] -- 9 exported step functions (verify steps, feedback functions, etc.)
- [Source: adws/tests/conftest.py] -- Shared fixtures (sample_workflow_context, mock_io_ops)
- [Source: _bmad-output/implementation-artifacts/3-3-feedback-accumulation-and-retry-context.md] -- Previous story: VerifyFeedback, feedback accumulation utilities, 283 test count
- [Source: _bmad-output/implementation-artifacts/3-2-verify-pipeline-steps-and-quality-gate-workflow.md] -- Verify steps, verify workflow, always_run pattern, _STEP_REGISTRY mocking

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

From Story 3.3 learnings:
- **VerifyFeedback**: Added to types.py as a frozen dataclass. Serialized as structured strings in ctx.feedback.
- **Pure functions**: Feedback accumulation functions are pure (no I/O, no IOResult return). NOT standard step functions.
- **283 tests**: Current test count (excluding 2 enemy tests), 100% line+branch coverage.
- **Pipe delimiter injection fix**: Serialization must handle special characters in field values.
- **TC001 import guard**: Applied where appropriate for annotation-only usage.

From Story 3.2 learnings:
- **Verify step pattern**: 4 steps (jest, playwright, mypy, ruff) each follow identical pattern: call io_ops, bind _handle_result, IOFailure propagation via bind.
- **_STEP_REGISTRY mocking**: `mocker.patch("adws.adw_modules.engine.executor._STEP_REGISTRY", {...})`.
- **always_run failure tracking**: Engine tracks always_run step failures without losing original pipeline error.
- **251 tests at Story 3.2 completion**: Test count before Story 3.3 additions.

From Story 2.7 learnings:
- **_STEP_REGISTRY mocking**: Tests mock `adws.adw_modules.engine.executor._STEP_REGISTRY` directly.
- **Sample workflow integration tests**: Helper functions `_make_success_step`, `_make_failure_step`, `_make_flaky_step`.

From Story 2.5 learnings:
- **unsafe_perform_io()**: `from returns.unsafe import unsafe_perform_io` to unwrap IOResult containers.
- **pipeline_failure tracking**: `run_workflow` tracks via `pipeline_failure: PipelineError | None`.

From Story 2.1 learnings:
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; containers are shallow-frozen.
- **ruff S108**: Avoid `/tmp/` literal strings in test data.
- **ruff E501**: Keep docstrings under 88 chars.

### Relationship to Epic 4 Stories

This story is the **foundation** for all Epic 4 stories. The progression is:

1. **Story 4.1 (this)**: Command pattern -- registry, dispatch, .md entry points, wiring tests
2. **Story 4.2**: `/verify` command -- full implementation using verify workflow from Epic 3
3. **Story 4.3**: `/prime` command -- context loading (custom logic, no workflow)
4. **Story 4.4**: `/build` command -- implement_close workflow
5. **Stories 4.5-4.7**: TDD step implementations (write_failing_tests, verify_tests_fail, implement, refactor)
6. **Story 4.8**: `/implement` command -- full TDD-enforced implement_verify_close workflow

Each subsequent story adds its command-specific logic to the pattern established here.

### io_ops.py Size Note

After this story, io_ops.py will have 12 public functions (up from 10). This is still well within the single-file threshold (~300 lines / ~15 functions noted in architecture). Monitor but no split needed yet.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

- Circular import between io_ops.py and engine/executor.py resolved using lazy imports (PLC0415 noqa) inside load_command_workflow and execute_command_workflow function bodies
- Mock targets for io_ops tests use source module paths (adws.workflows.load_workflow, adws.adw_modules.engine.executor.run_workflow) instead of io_ops module paths due to lazy imports
- 39 new tests added (283 -> 322 total, excluding 2 enemy tests)
- io_ops.py now has 12 public functions (up from 10)
- All 4 .md entry points created following consistent template pattern
- Commands package exports 4 public symbols: CommandSpec, get_command, list_commands, run_command

### File List

Files created:
- `adws/adw_modules/commands/__init__.py` -- package init with 4 exports
- `adws/adw_modules/commands/types.py` -- CommandSpec frozen dataclass
- `adws/adw_modules/commands/registry.py` -- COMMAND_REGISTRY (6 commands), get_command(), list_commands()
- `adws/adw_modules/commands/dispatch.py` -- run_command() dispatch function
- `.claude/commands/adws-verify.md` -- verify command entry point (full)
- `.claude/commands/adws-build.md` -- build command entry point (stub)
- `.claude/commands/adws-prime.md` -- prime command entry point (stub)
- `.claude/commands/adws-implement.md` -- implement command entry point (stub)
- `adws/tests/adw_modules/commands/__init__.py` -- test package init
- `adws/tests/adw_modules/commands/test_types.py` -- 3 CommandSpec tests
- `adws/tests/adw_modules/commands/test_registry.py` -- 14 registry tests
- `adws/tests/adw_modules/commands/test_dispatch.py` -- 7 dispatch tests
- `adws/tests/adw_modules/commands/test_wiring.py` -- 11 wiring tests (4 import + 7 structural)

Files modified:
- `adws/adw_modules/io_ops.py` -- added load_command_workflow(), execute_command_workflow() (4 new tests in test_io_ops.py)
- `adws/tests/adw_modules/test_io_ops.py` -- added 4 tests for new io_ops functions

## Senior Developer Review

### Reviewer

Claude Opus 4.5 (claude-opus-4-5-20251101) -- Adversarial review mode

### Review Date

2026-02-02

### Issues Found

| # | Severity | File | Issue | Fix Applied |
|---|----------|------|-------|-------------|
| 1 | MEDIUM | `adws/adw_modules/commands/registry.py` | `COMMAND_REGISTRY` was a mutable `dict[str, CommandSpec]` exposed publicly. Any caller could mutate it at runtime (`COMMAND_REGISTRY["evil"] = ...`), violating the immutability pattern used throughout the project (frozen dataclasses, shallow-frozen WorkflowContext). The workflow registry `_REGISTRY` in `workflows/__init__.py` avoids this by being prefixed with `_` (private), but the command registry was public. | Changed to `MappingProxyType[str, CommandSpec]` wrapping a frozen dict. Added `test_command_registry_is_immutable` test verifying mutation raises `TypeError`. |
| 2 | MEDIUM | `adws/adw_modules/commands/dispatch.py` | `dispatch.py` imported `COMMAND_REGISTRY` directly from `registry.py` and used `sorted(COMMAND_REGISTRY.keys())` to build the available commands list. This bypasses the registry's public API (`get_command()`, `list_commands()`) and creates unnecessary coupling to the registry data structure. | Replaced `COMMAND_REGISTRY` import with `list_commands()` import. Changed to `sorted(cmd.name for cmd in list_commands())`. |
| 3 | MEDIUM | `adws/adw_modules/commands/dispatch.py` | `dispatch.py` used `unsafe_perform_io` (via lazy import) to unwrap the `IOResult` from `load_command_workflow`, then passed the unwrapped `Workflow` to `execute_command_workflow`. This is inconsistent with the project's established ROP pattern: all non-engine code (steps, io_ops) uses `.bind()` for composing IOResult operations. Only the engine executor (Tier 2) uses `unsafe_perform_io` because it IS the orchestration layer. Command dispatch sits above the engine and should follow the `.bind()` pattern. | Replaced `unsafe_perform_io` unwrapping with `.bind(_execute_workflow)` pattern using a local closure function, consistent with the io_ops and step patterns (e.g., `run_jest_tests`, `run_jest_step`). |
| 4 | LOW | `.claude/commands/adws-*.md` | All `.md` files reference `uv run python -m adws.adw_modules.commands.dispatch <cmd>` but no `__main__.py` exists in the dispatch package. The story explicitly says NOT to implement the CLI entry point, and the `.md` files serve as natural language entry points (FR28), so this is by design. Noted for future stories. | No fix needed -- documented as by-design per story instructions. |

### Quality Gates (Post-Fix)

| Gate | Result |
|------|--------|
| `uv run pytest adws/tests/ -m "not enemy"` | 323 passed, 2 deselected |
| Coverage (line + branch) | 100.00% |
| `uv run ruff check adws/` | All checks passed |
| `uv run mypy adws/ --strict` | No issues found in 56 source files |

### Summary

The Story 4.1 implementation is solid and well-structured. The command pattern architecture (CommandSpec, registry, dispatch, io_ops boundary) is clean and follows established project conventions. Three MEDIUM-severity issues were found and fixed:

1. **Registry immutability** -- The most important fix. A public mutable dict holding the command registry is a correctness risk in a codebase that enforces frozen dataclasses everywhere. Now uses `MappingProxyType` to make it truly immutable at runtime, with a test to enforce this invariant.

2. **API encapsulation** -- Dispatch was reaching past the registry's public API to access the raw dict. Now uses `list_commands()` exclusively, making the dispatch module immune to future registry implementation changes.

3. **ROP consistency** -- Replacing `unsafe_perform_io` with `.bind()` in dispatch code aligns with the project's established pattern: steps and io_ops compose with `.bind()`, only the engine unwraps. This makes dispatch code more composable and consistent.

Test count after review: 323 (was 322, +1 immutability test). All ACs verified, all task checkboxes confirmed.

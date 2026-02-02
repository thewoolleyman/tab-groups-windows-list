# Story 1.2: Skeleton Layer Implementations & TDD Foundation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want skeleton implementations across all four pipeline layers with passing tests,
so that subsequent stories have established patterns to follow and quality gates are enforced from the start.

## Acceptance Criteria

1. **Given** the scaffold from Story 1.1 **When** I inspect `adws/adw_modules/errors.py` **Then** `PipelineError` dataclass is defined with structured error fields (step_name, error_type, message, context)

2. **Given** the scaffold from Story 1.1 **When** I inspect `adws/adw_modules/io_ops.py` **Then** at least one real function exists following the io_ops pattern (returns `IOResult`, catches specific exceptions) **And** the module establishes the I/O boundary pattern — all external I/O goes through this module (NFR10)

3. **Given** the scaffold from Story 1.1 **When** I inspect the `adws/adw_modules/` directory **Then** a skeleton step function exists with correct signature: `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]` **And** a skeleton engine module exists **And** a skeleton workflow definition exists as declarative data (not imperative code) **And** a workflow name registry (constants/enum) exists with valid workflow names for downstream epics

4. **Given** all skeleton modules exist **When** I run `uv run pytest adws/tests/` **Then** at least one test per layer passes (step, engine, workflow structure) **And** 100% line and branch coverage is maintained (NFR9)

5. **Given** the git history **When** I inspect commits for this story **Then** at least one test was committed RED-first in a separate commit from its implementation **And** the RED commit has `"""RED: <expected failure reason>"""` annotation

6. **Given** all skeleton modules exist **When** I run `uv run mypy adws/` **Then** type checking passes with strict mode (NFR11)

7. **Given** all skeleton modules exist **When** I run `uv run ruff check adws/` **Then** linting passes with zero violations (NFR12)

## Tasks / Subtasks

- [x] Task 1: Implement `PipelineError` and error types in `errors.py` (AC: #1)
  - [x] Define `PipelineError` as a frozen dataclass with fields: `step_name` (str), `error_type` (str), `message` (str), `context` (dict[str, object])
  - [x] Ensure immutability (frozen=True) and serializability
  - [x] Write RED test first: `adws/tests/adw_modules/test_errors.py`

- [x] Task 2: Implement `WorkflowContext` in `types.py` (AC: #3)
  - [x] Define `WorkflowContext` frozen dataclass with fields: `inputs` (dict), `outputs` (dict), `feedback` (list)
  - [x] Implement `with_updates()` method returning new context with replaced fields
  - [x] Write RED test first: `adws/tests/adw_modules/test_types.py`

- [x] Task 3: Implement `io_ops.py` with at least one real function (AC: #2)
  - [x] Create `read_file(path: Path) -> IOResult[str, PipelineError]` as the initial io_ops function
  - [x] Follow the io_ops pattern: returns IOResult, catches specific exceptions, transforms types
  - [x] Write RED test first: `adws/tests/adw_modules/test_io_ops.py`

- [x] Task 4: Implement skeleton step function (AC: #3)
  - [x] Create `adws/adw_modules/steps/check_sdk_available.py` with signature `(WorkflowContext) -> IOResult[WorkflowContext, PipelineError]`
  - [x] One public function matching filename
  - [x] Uses io_ops for any I/O operations
  - [x] Write RED test first: `adws/tests/adw_modules/steps/test_check_sdk_available.py`

- [x] Task 5: Implement skeleton engine types (AC: #3)
  - [x] Create `adws/adw_modules/engine/types.py` with `Workflow` and `Step` dataclasses
  - [x] `Workflow`: name, description, steps list, dispatchable boolean flag
  - [x] `Step`: name, function reference, always_run, max_attempts
  - [x] Write RED test first: `adws/tests/adw_modules/engine/test_types.py`

- [x] Task 6: Implement skeleton workflow definition and name registry (AC: #3)
  - [x] Create workflow name registry (constants/enum) in `adws/workflows/__init__.py`
  - [x] Define skeleton `implement_close` workflow as declarative data
  - [x] Implement `load_workflow()` and `list_workflows(dispatchable_only=False)` functions
  - [x] Write RED test first: `adws/tests/workflows/test_workflows.py`

- [x] Task 7: Add shared test fixtures to `conftest.py` (AC: #4)
  - [x] `sample_workflow_context()` fixture returning WorkflowContext with test data
  - [x] `mock_io_ops` fixture for mocked io_ops boundary
  - [x] Ensure all fixtures are typed

- [x] Task 8: Verify all quality gates pass (AC: #4, #6, #7)
  - [x] `uv run pytest adws/tests/` — 28 tests passing, 100% line+branch coverage
  - [x] `uv run mypy adws/` — strict mode passes (22 source files, no errors)
  - [x] `uv run ruff check adws/` — all checks passed, zero violations

- [x] Task 9: Verify TDD compliance in git history (AC: #5)
  - [x] RED commit `a5e6fde` — test only, failing with expected ImportError
  - [x] RED commit test has `"""RED: <expected failure reason>"""` annotation

## Dev Notes

### Architecture & Patterns

**Four-Layer Pipeline (all layers get skeleton implementations in this story):**

```
┌─────────────────────────────────────────────────────┐
│  Tier 1: Workflows (declarative, no ROP)            │
│  adws/workflows/*.py                                │
│  Workflow, Step dataclasses → engine                 │
├─────────────────────────────────────────────────────┤
│  Tier 2: Engine (ROP internals, hidden from Tier 1) │
│  adws/adw_modules/engine/types.py                   │
│  Public API types used by workflows                  │
├─────────────────────────────────────────────────────┤
│  Steps (pure logic + io_ops calls)                   │
│  adws/adw_modules/steps/*.py                         │
│  (WorkflowContext) → IOResult[PipelineError, ...]    │
├─────────────────────────────────────────────────────┤
│  I/O Boundary (single mock point)                    │
│  adws/adw_modules/io_ops.py                          │
│  File ops, subprocess, SDK calls, bd CLI             │
└─────────────────────────────────────────────────────┘
```

[Source: architecture.md#Architectural-Boundaries]

**Step Creation Checklist (mandatory for every new step):**
1. Add error type(s) to `errors.py` and update `PipelineError` union
2. Add I/O function(s) to `io_ops.py`
3. Create step module in `steps/` following the internal structure pattern
4. Export from `steps/__init__.py` in the correct conceptual group
5. Write tests: mock io_ops, test pure logic, test error paths
6. Verify: `uv run pytest`, `uv run mypy`, `uv run ruff check`

[Source: architecture.md#Process-Patterns]

### Critical Constraints

- **NFR9**: 100% line and branch coverage — `--cov-fail-under=100 --cov-branch` in pytest config
- **NFR10**: All I/O behind `io_ops.py` — single mock point for all tests
- **NFR11**: mypy strict mode — `strict = true` with `returns.contrib.mypy.returns_plugin`
- **NFR12**: ruff ALL rules — `select = ["ALL"]` with justified ignores only (D, COM812, ISC001)
- **NFR16**: No secrets committed — `.env` in `.gitignore`

### Library-Specific Implementation Notes

**`returns` library (0.26.0) — IOResult usage:**

```python
from returns.io import IOResult, IOSuccess, IOFailure

# io_ops function pattern
def read_file(path: Path) -> IOResult[PipelineError, str]:
    try:
        content = path.read_text()
        return IOSuccess(content)
    except FileNotFoundError:
        return IOFailure(PipelineError(
            step_name="io_ops.read_file",
            error_type="FileNotFoundError",
            message=f"File not found: {path}",
            context={},
        ))
```

Type parameter order: `IOResult[FailureType, SuccessType]` — error first, success second. This follows the Haskell Either convention.

**mypy returns plugin**: Already configured in pyproject.toml (`returns.contrib.mypy.returns_plugin`). Required for type inference through `flow()` and `bind()` chains.

**v0.26.0 notes**: Non-breaking release (Nov 2025). Added mypy 1.16-1.18 support. No API changes from 0.25.x.

[Source: returns.readthedocs.io, architecture.md#Decision-1-SDK-Integration-Design]

**`pydantic` (2.12.5) — NOT used in this story:**

Pydantic models (`AdwsRequest`, `AdwsResponse`) are part of the SDK boundary in Story 2.2. This story uses only frozen dataclasses for `PipelineError` and `WorkflowContext`. Do NOT import pydantic in this story's code.

### Code Patterns — What to Build

**`errors.py` — PipelineError:**

```python
"""Pipeline error types for ADWS workflow engine."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PipelineError:
    """Structured error for pipeline step failures."""
    step_name: str
    error_type: str
    message: str
    context: dict[str, object] = field(default_factory=dict)
```

Note: In Epic 2 (Story 2.1), `PipelineError` will evolve into a union type of specific error dataclasses (`SdkNotAvailableError`, `SdkCallError`, `BeadsCommandError`, etc.). For this story, a single concrete dataclass is sufficient — it establishes the pattern. The union refactoring happens when specific error types are needed.

[Source: architecture.md#Naming-Patterns, epics.md#Story-2.1]

**`types.py` — WorkflowContext:**

```python
"""Shared type definitions for ADWS pipeline."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkflowContext:
    """Immutable context flowing through pipeline steps."""
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)

    def with_updates(self, **kwargs: object) -> "WorkflowContext":
        """Return new context with specified fields replaced."""
        ...
```

WorkflowContext is IMMUTABLE. Steps return a NEW context via `with_updates()`. Never mutate.

[Source: architecture.md#Format-Patterns, architecture.md#Communication-Patterns]

**`io_ops.py` — I/O boundary:**

```python
"""I/O boundary module — ALL external I/O goes through here (NFR10)."""
from pathlib import Path
from returns.io import IOResult, IOSuccess, IOFailure

from adws.adw_modules.errors import PipelineError


def read_file(path: Path) -> IOResult[PipelineError, str]:
    """Read file contents. Returns IOResult, never raises."""
    ...
```

Rules:
- Always returns `IOResult`, never raises
- Catches specific exceptions, never bare `except Exception`
- Transforms external types into domain types before returning
- Never contains domain logic — that belongs in steps

[Source: architecture.md#io_ops-Function-Pattern]

**`steps/check_sdk_available.py` — skeleton step:**

```python
"""Check that the Claude SDK is importable and available."""
from returns.io import IOResult

from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import WorkflowContext
from adws.adw_modules.io_ops import check_sdk_import


def check_sdk_available(ctx: WorkflowContext) -> IOResult[PipelineError, WorkflowContext]:
    """Verify Claude SDK is available. Pure logic calls io_ops for impure operations."""
    ...
```

One public function per step, matching the filename. Uses absolute imports only.

[Source: architecture.md#Structure-Patterns]

**`engine/types.py` — Workflow and Step types:**

```python
"""Public API types for workflow definitions (Tier 1)."""
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class Step:
    """A single step in a workflow pipeline."""
    name: str
    function: str  # Reference to step function name
    always_run: bool = False
    max_attempts: int = 1
    ...

@dataclass(frozen=True)
class Workflow:
    """Declarative workflow definition."""
    name: str
    description: str
    steps: list[Step] = field(default_factory=list)
    dispatchable: bool = True
```

Workflow definitions are declarative DATA, not imperative code.

[Source: architecture.md#Decision-5-Workflow-Dispatch-Registry, architecture.md#Workflow-Definition-Pattern]

**`workflows/__init__.py` — Registry and discovery:**

```python
"""Workflow registry and discovery (Tier 1 API)."""
from adws.adw_modules.engine.types import Workflow


class WorkflowName:
    """Registry of valid workflow names (constants for downstream epics)."""
    IMPLEMENT_CLOSE = "implement_close"
    IMPLEMENT_VERIFY_CLOSE = "implement_verify_close"
    CONVERT_STORIES_TO_BEADS = "convert_stories_to_beads"


def load_workflow(name: str) -> Workflow | None:
    """Pure lookup — find workflow by name. No policy enforcement."""
    ...

def list_workflows(*, dispatchable_only: bool = False) -> list[Workflow]:
    """Return registered workflows, optionally filtered to dispatchable."""
    ...
```

[Source: architecture.md#Decision-5-Workflow-Dispatch-Registry, epics.md#Epic-1]

### Test Patterns — What to Test

**Test structure (mirrors source, one file per module):**

```
adws/tests/
├── conftest.py                        # Shared fixtures
├── adw_modules/
│   ├── __init__.py
│   ├── test_errors.py                 # PipelineError construction, immutability
│   ├── test_types.py                  # WorkflowContext creation, with_updates
│   ├── test_io_ops.py                 # io_ops functions with mocked I/O
│   ├── engine/
│   │   ├── __init__.py
│   │   └── test_types.py             # Workflow, Step dataclass construction
│   └── steps/
│       ├── __init__.py
│       └── test_check_sdk_available.py # Step with mocked io_ops
└── workflows/
    ├── __init__.py
    └── test_workflows.py             # Registry, load_workflow, list_workflows
```

**RED phase annotation pattern:**

```python
def test_pipeline_error_construction():
    """RED: Will fail with ImportError because PipelineError is not yet defined in errors.py."""
    from adws.adw_modules.errors import PipelineError
    error = PipelineError(
        step_name="test_step",
        error_type="TestError",
        message="test message",
        context={"key": "value"},
    )
    assert error.step_name == "test_step"
```

Every RED-phase test MUST have a docstring starting with `RED:` explaining the expected failure reason.

[Source: architecture.md#TDD-RED-Phase-Annotation-Pattern]

**Mock boundary is always `io_ops`:**

```python
def test_check_sdk_available_success(mocker):
    """Test that check_sdk_available returns success when SDK is importable."""
    mocker.patch("adws.adw_modules.io_ops.check_sdk_import", return_value=IOSuccess(True))
    ctx = WorkflowContext()
    result = check_sdk_available(ctx)
    assert isinstance(result, IOSuccess)
```

[Source: architecture.md#Test-Boundary]

### Previous Story Intelligence (1.1)

**Learnings to apply:**
- ANN101/ANN102 ruff rules are DEPRECATED in ruff 0.14.x — do not add them to ignores
- Use `[dependency-groups]` (PEP 735), not `[project.optional-dependencies]` — already configured
- `conftest.py` currently has fixture roadmap docstring only — this story adds real fixtures
- All `__init__.py` files are currently empty — this story adds exports/registry to relevant ones
- Quality gates verified passing on empty scaffold — new code must maintain 100% coverage

**Files from Story 1.1 (DO NOT MODIFY unless necessary):**
- `.mise.toml` — runtime version pins (Python 3.11.12, Node 20.19.5, uv 0.9.28)
- `pyproject.toml` — tool configs and dependency versions
- `uv.lock` — locked dependency versions
- `CLAUDE.md` — TDD mandate
- `.env.sample` — credential template
- `.gitignore` — Python artifact exclusions

**Files this story CREATES (new):**
- `adws/adw_modules/errors.py` — PipelineError dataclass
- `adws/adw_modules/types.py` — WorkflowContext dataclass
- `adws/adw_modules/io_ops.py` — I/O boundary with read_file
- `adws/adw_modules/steps/check_sdk_available.py` — skeleton step
- `adws/adw_modules/engine/types.py` — Workflow, Step dataclasses
- `adws/tests/adw_modules/__init__.py` — test package
- `adws/tests/adw_modules/test_errors.py` — error type tests
- `adws/tests/adw_modules/test_types.py` — WorkflowContext tests
- `adws/tests/adw_modules/test_io_ops.py` — io_ops tests
- `adws/tests/adw_modules/engine/__init__.py` — test package
- `adws/tests/adw_modules/engine/test_types.py` — engine type tests
- `adws/tests/adw_modules/steps/__init__.py` — test package
- `adws/tests/adw_modules/steps/test_check_sdk_available.py` — step tests
- `adws/tests/workflows/__init__.py` — test package
- `adws/tests/workflows/test_workflows.py` — workflow registry tests

**Files this story MODIFIES:**
- `adws/adw_modules/steps/__init__.py` — add step exports
- `adws/workflows/__init__.py` — add registry, load_workflow, list_workflows
- `adws/tests/conftest.py` — add real fixtures (sample_workflow_context, mock_io_ops)

### What This Story Does NOT Include

- No engine executor (`executor.py`) — that's Story 2.4
- No engine combinators (`combinators.py`) — that's Story 2.7
- No SDK client (`ClaudeSDKClient`) — that's Story 2.2
- No Pydantic models (`AdwsRequest`, `AdwsResponse`) — that's Story 2.2
- No CI pipeline changes — that's Story 1.3
- No Enemy Unit Tests — that's Story 2.2 (requires real SDK)

### Project Structure Notes

- All new files align with architecture.md project tree
- `adws/adw_modules/types.py` houses WorkflowContext (shared types), NOT `engine/types.py` which houses Workflow/Step (engine public API)
- `errors.py` at `adws/adw_modules/errors.py` (infrastructure level), not nested under engine/
- Step function `check_sdk_available` chosen as skeleton because it's referenced in the architecture as the first step in the pipeline and has clear io_ops dependency

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural-Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Format-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-1-SDK-Integration-Design]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-3-Tool-Configuration]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-5-Workflow-Dispatch-Registry]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-6-TDD-Pair-Programming-Enforcement]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#io_ops-Function-Pattern]
- [Source: _bmad-output/planning-artifacts/architecture.md#TDD-RED-Phase-Annotation-Pattern]
- [Source: _bmad-output/planning-artifacts/architecture.md#Workflow-Definition-Pattern]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1-Story-1.2]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1]
- [Source: _bmad-output/implementation-artifacts/1-1-project-scaffold-and-dual-toolchain-setup.md]
- [Source: returns.readthedocs.io — IOResult API, v0.26.0]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- IOResult type parameter order: Architecture doc says `IOResult[Error, Success]` but actual `returns` 0.26.0 uses `IOResult[Success, Error]` — code uses correct order
- `IOSuccess(value=True)` TypeError — positional args only, no keyword args
- `result.unwrap()` returns `IO[value]` not raw value — use `unsafe_perform_io()` from `returns.unsafe`
- Mock path must be where imported (`adws.adw_modules.steps.check_sdk_available.check_sdk_import`) not where defined

### Completion Notes List

- All 9 tasks completed across 4 pipeline layers
- 28 tests passing with 100% line + branch coverage
- mypy strict mode clean (22 files)
- ruff ALL rules clean
- TDD RED commit verified: `a5e6fde`
- `with_updates()` uses explicit parameters (not `**kwargs`) for mypy strict compatibility
- conftest.py excluded from coverage (test infrastructure, not production code)
- `check_sdk_import` failure test uses `sys.modules` patching + `importlib.reload` pattern

### Change Log

- Created `adws/adw_modules/errors.py` — PipelineError frozen dataclass
- Created `adws/adw_modules/types.py` — WorkflowContext frozen dataclass with `with_updates()`
- Created `adws/adw_modules/io_ops.py` — `read_file()`, `check_sdk_import()` I/O boundary
- Created `adws/adw_modules/steps/check_sdk_available.py` — skeleton step using `.map()`
- Created `adws/adw_modules/engine/types.py` — `Step`, `Workflow` frozen dataclasses
- Modified `adws/adw_modules/steps/__init__.py` — added `check_sdk_available` export
- Modified `adws/workflows/__init__.py` — WorkflowName registry, `load_workflow()`, `list_workflows()`
- Modified `adws/tests/conftest.py` — `sample_workflow_context`, `mock_io_ops` fixtures
- Modified `pyproject.toml` — added `[tool.coverage.run]` omit for conftest.py
- Created test files: `test_errors.py` (3), `test_types.py` (6), `test_io_ops.py` (5), `test_check_sdk_available.py` (2), `engine/test_types.py` (6), `test_workflows.py` (6)
- Created `__init__.py` for test packages: `adw_modules/`, `engine/`, `steps/`, `workflows/`

### File List

**Created:**
- `adws/adw_modules/errors.py`
- `adws/adw_modules/types.py`
- `adws/adw_modules/io_ops.py`
- `adws/adw_modules/steps/check_sdk_available.py`
- `adws/adw_modules/engine/types.py`
- `adws/tests/adw_modules/__init__.py`
- `adws/tests/adw_modules/test_errors.py`
- `adws/tests/adw_modules/test_types.py`
- `adws/tests/adw_modules/test_io_ops.py`
- `adws/tests/adw_modules/engine/__init__.py`
- `adws/tests/adw_modules/engine/test_types.py`
- `adws/tests/adw_modules/steps/__init__.py`
- `adws/tests/adw_modules/steps/test_check_sdk_available.py`
- `adws/tests/workflows/__init__.py`
- `adws/tests/workflows/test_workflows.py`

**Modified:**
- `adws/adw_modules/steps/__init__.py`
- `adws/workflows/__init__.py`
- `adws/tests/conftest.py`
- `pyproject.toml`

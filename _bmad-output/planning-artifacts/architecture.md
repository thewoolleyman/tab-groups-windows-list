---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-02-01'
inputDocuments: ['_bmad-output/planning-artifacts/prd.md', '_bmad-output/brainstorming/brainstorming-session-2026-01-31.md', 'README.md', 'HANDOVER.md', 'AGENTS.md']
workflowType: 'architecture'
project_name: 'tab-groups-windows-list'
user_name: 'Chad'
date: '2026-01-31'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

45 FRs organized across 9 capability areas, analyzed for architectural implications:

| Capability Area | FR Count | Architectural Implication |
|---|---|---|
| Workflow Execution (FR1-FR6) | 6 | Core engine with ROP pipeline, step executor, error propagation |
| Workflow Definition (FR7-FR11) | 5 | Two-tier type system: public Tier 1 API (Workflow/Step/WorkflowContext) wrapping Tier 2 ROP internals |
| Quality Verification (FR12-FR17) | 6 | Shell subprocess runner for npm/pytest + feedback accumulation in WorkflowContext |
| Issue Integration (FR18-FR22) | 5 | Beads CLI integration layer (`bd` commands), cron polling, workflow tag parsing |
| BMAD-to-Beads Bridge (FR23-FR27) | 5 | Markdown parser, Beads CLI wrapper, bidirectional file I/O (read BMAD, write beads_id back) |
| Commands (FR28-FR32) | 5 | Dual-layer pattern: `.md` command + Python module for each entry point |
| Observability (FR33-FR36) | 4 | Shared modules serving two entry points: CLI hook shims + SDK HookMatchers |
| Safety (FR37-FR40) | 4 | Regex-based command blocker with audit logging, same dual-entry pattern |
| Dev Environment (FR41-FR45) | 5 | Toolchain config: uv/pyproject.toml/uv.lock + mise.toml + CI pipeline extension |

**Non-Functional Requirements:**

20 NFRs across 5 areas driving architectural constraints:

- **Reliability (NFR1-4):** ROP-based error handling throughout engine; fail-open hooks; always_run step guarantee
- **Reproducibility (NFR5-8):** Pinned versions everywhere; `uv sync --frozen` and `npm ci` in CI; `mise.toml` as runtime source of truth
- **Testability (NFR9-13):** 100% coverage; single I/O boundary (`io_ops.py`); strict mypy + ruff; Tier 1 testable without ROP mocking
- **Security (NFR14-16):** Zero false negatives on known destructive patterns; audit logging; no secrets in source
- **Integration (NFR17-20):** Beads via `bd` CLI only; Claude via SDK only; no direct BMAD reads; shared modules for all hooks

### Scale & Complexity

- **Primary domain:** Developer Tool (SDK-based agentic workflow engine)
- **Complexity level:** Medium
- **Estimated architectural components:** ~8 (engine, steps, workflows, observability, safety, commands, bridge, CI)
- **Integration points:** 3 external systems (claude-agent-sdk, Beads/bd CLI, BMAD markdown files)
- **Language boundary:** Python (ADWS) + JavaScript (Application) -- two toolchains in one repo

### Technical Constraints & Dependencies

| Dependency | Role | Constraint |
|---|---|---|
| `claude-agent-sdk` | SDK for Claude API calls | Relatively new; mock at SDK boundary for all tests |
| `returns` (dry-python) | ROP monadic types (IOResult, etc.) | Core engine dependency; never exposed to Tier 1 API |
| `uv` | Python package manager | Must produce deterministic installs via `uv.lock` |
| `mise.toml` | Runtime version manager | Single source of truth for Python/Node.js versions |
| `bd` CLI (Beads) | Issue tracking commands | ADWS interacts with Beads exclusively via `bd` commands |
| Existing JS toolchain | Jest, Playwright, npm | Must coexist; CI runs both Python and JS pipelines |

### Cross-Cutting Concerns Identified

1. **Reproducibility:** Pervasive across all components -- every dependency, runtime, and toolchain config must be pinned and deterministic
2. **Dual-Layer Pattern:** Every command, hook, and entry point follows `.md` + Python module convention -- affects all component boundaries
3. **Shared Module Reuse:** Observability and safety modules serve both CLI hooks and SDK HookMatchers -- zero duplicated logic enforced architecturally
4. **ROP Boundary:** Engine internals use ROP (`IOResult`, `PipelineError`); workflow authors see only domain types -- strict two-tier separation
5. **I/O Boundary:** All impure operations through `io_ops.py` -- single mock point for entire test suite
6. **One-Directional Flow:** BMAD → Beads → ADWS -- no component may create a reverse dependency

## Starter Template Evaluation

### Primary Technology Domain

**Developer Tool (Python package within existing JS project)** -- brownfield addition of a Python-based agentic layer to an existing Chrome extension. Not a greenfield project requiring a framework starter.

### Starter Options Considered

**Option A: Cookiecutter/Copier Python Package Template**
Rejected. These generate opinionated structures (src layout, tox, sphinx docs) that conflict with the established flat-layout architecture from the source project.

**Option B: `uv init --lib`**
Rejected. Generates a `src/` layout package, which contradicts the source project's flat layout where `adws/` sits at project root as a direct subpackage.

**Option C: Manual Scaffold Mirroring Source (Selected)**
Port the exact directory structure from `agentic-ai-cli-example/adws/`, using the same flat layout, same `adw_modules/` infrastructure organization, and same four-layer ROP pipeline. New functionality (observability, safety, bridge) implemented as steps and workflows within the existing architecture -- not as separate module trees.

### Selected Approach: Manual Scaffold Mirroring Source

**Rationale:** The source project has a proven, well-documented architecture with a composable four-layer pipeline (Workflows -> Engine -> Steps -> I/O Boundary). All new functionality follows the same pattern: I/O ops in `io_ops.py`, domain errors in `errors.py`, steps in `steps/`, workflows in `workflows/`. No structural innovation needed -- the architecture is the architecture.

### Dual-Toolchain Contract

This project has two co-existing toolchains at the project root. This contract must be understood explicitly:

| Toolchain | Scope | Config | Lockfile | Install Command |
|---|---|---|---|---|
| `uv` | `adws/` (agentic layer) | `pyproject.toml` | `uv.lock` | `uv sync --frozen` (CI) |
| `npm` | Extension (application layer) | `package.json` | `package-lock.json` | `npm ci` (CI) |
| `mise` | Both (runtime versions) | `.mise.toml` | N/A | `mise install` |

Running `npm install` alone does **not** set up the agentic layer. Running `uv sync` alone does **not** set up the application layer. Both must be run. `mise install` must be run first to ensure correct runtime versions.

### Architectural Decisions Established by Scaffold

**Language & Runtime (all pinned exactly in `.mise.toml`):**

| Tool | Version | Role |
|---|---|---|
| Python | 3.11.x | ADWS engine runtime |
| Node.js | 20.x.x | Application layer runtime (existing) |
| uv | 0.9.28 | Python package manager (pinned, NOT "latest") |

Note: The source project uses `>=3.12` and `uv = "latest"`. We use `>=3.11` (verified: `claude-agent-sdk` requires `>=3.10`, `returns` is compatible). We pin `uv` to exact version to satisfy reproducibility NFR (NFR5-8). No floating versions anywhere.

**Core Dependencies (pinned in `pyproject.toml` + `uv.lock` at project root):**

| Package | Version | Role | Status |
|---|---|---|---|
| `claude-agent-sdk` | 0.1.27 | Native SDK for Claude API calls | Confirmed (requires Python >=3.10) |
| `returns` | 0.26.0 | ROP monadic types (IOResult, Result, flow) | Confirmed |
| `pydantic` | TBD | Request/response model validation | TBD -- see Deferred to Step 4 |
| `rich` | TBD | Terminal UI for dispatch/trigger scripts | TBD -- see Deferred to Step 4 |
| `dotenv` | TBD | Environment configuration | TBD -- see Deferred to Step 4 |

`click` is **dropped**: the source uses it for CLI entry points, which are replaced by SDK-native execution.

**Dev Dependencies (pinned in `pyproject.toml` + `uv.lock` at project root):**

| Package | Version | Role |
|---|---|---|
| `pytest` | 9.0.2 | Test framework |
| `pytest-cov` | 7.0.0 | Coverage reporting (100% target) |
| `pytest-mock` | 3.12.0 | Mock utilities (`mocker` fixture for `io_ops` boundary mocking) |
| `mypy` | 1.19.1 | Static type checking (strict mode) |
| `ruff` | 0.14.14 | Linting + formatting (zero suppressions) |

**`pyproject.toml` Metadata:**

```toml
[project]
name = "tab-groups-windows-list"
version = "0.0.1"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
include = ["adws*"]  # adws/ only -- agents/ is output dir, not distributable
```

Tool configuration sections (`[tool.mypy]`, `[tool.ruff]`, `[tool.pytest.ini_options]`) to be specified in step 4 (Architectural Decisions).

**Project Structure:**

```
tab-groups-windows-list/
├── pyproject.toml              # NEW at root (adws/ is a subpackage, not standalone)
├── uv.lock                     # NEW at root
├── .mise.toml                  # NEW at root (pins Python, Node.js, uv exactly)
├── adws/                       # NEW subpackage (flat layout, mirrors source)
│   ├── __init__.py
│   ├── adw_dispatch.py         # Workflow dispatcher (uses load_workflow() to match tags)
│   ├── adw_trigger_cron.py     # Beads cron trigger
│   ├── adw_modules/            # Infrastructure layer (four-layer pipeline)
│   │   ├── __init__.py
│   │   ├── engine/             # Executor, combinators, types (Tier 2)
│   │   │   ├── __init__.py
│   │   │   ├── types.py        # Public API: Workflow, Step, WorkflowContext
│   │   │   ├── executor.py     # ROP execution logic
│   │   │   └── combinators.py  # with_verification, sequence, etc.
│   │   ├── steps/              # ALL steps -- flat list, no subdirectories (see note)
│   │   │   ├── __init__.py     # Grouped exports (see Module Organization note)
│   │   │   ├── check_sdk_available.py  # Replaces check_claude.py
│   │   │   ├── execute.py              # Replaces subprocess: SDK-native
│   │   │   ├── parse_output.py         # Adapted: SDK ResultMessage, not JSONL
│   │   │   ├── convert_output.py       # Adapted: structured data, not JSONL
│   │   │   ├── output_dir.py           # Ported
│   │   │   ├── save_prompt.py          # Ported
│   │   │   ├── save_final.py           # Adapted: ResultMessage, not parsed JSON
│   │   │   ├── process_result.py       # Adapted: SDK response, not subprocess
│   │   │   ├── parse_bmad_story.py     # NEW: parse BMAD markdown
│   │   │   ├── create_beads_issue.py   # NEW: call bd create
│   │   │   ├── write_beads_id.py       # NEW: write beads_id back to BMAD
│   │   │   ├── log_hook_event.py       # NEW: hook event logging
│   │   │   ├── build_context_bundle.py # NEW: context bundle builder
│   │   │   └── block_dangerous_command.py # NEW: regex patterns + security log
│   │   ├── io_ops.py           # ALL I/O operations (single boundary -- see scaling note)
│   │   ├── errors.py           # ALL domain error types (frozen dataclasses)
│   │   ├── types.py            # Shared type definitions
│   │   ├── config.py           # Configuration & paths
│   │   ├── lift.py             # ROP lifting utilities
│   │   ├── retry.py            # Retry logic & decorators
│   │   └── utils.py            # Utility functions
│   ├── workflows/              # ALL workflow definitions (Tier 1)
│   │   ├── __init__.py         # load_workflow() & list_workflows() (discovery)
│   │   ├── implement_close.py
│   │   ├── implement_verify_close.py
│   │   └── convert_stories_to_beads.py
│   └── tests/                  # Mirrors source structure
│       ├── __init__.py
│       ├── conftest.py         # CRITICAL: shared fixtures (see Testing notes)
│       ├── adw_modules/
│       ├── engine/
│       ├── steps/
│       ├── integration/
│       └── workflows/
├── .claude/commands/           # Dual-layer command .md files (see Command Inventory)
├── .claude/hooks/              # CLI hook shims (thin, delegate to adws steps)
├── agents/                     # Output directory ONLY (not in setuptools include)
│   ├── hook_logs/
│   ├── context_bundles/
│   └── security_logs/
├── manifest.json               # EXISTING
├── popup.js                    # EXISTING
├── package.json                # EXISTING
├── package-lock.json           # EXISTING
├── tests/                      # EXISTING: JS tests
└── .github/workflows/ci-cd.yml # EXISTING: Extended for Python pipeline
```

**Module Organization Note -- `steps/` stays flat:**

The `steps/` directory holds 15+ files but must remain a flat list with no subdirectories. Every step is equal, discoverable, and follows the same pattern. The step creation checklist (`io_ops.py` -> `errors.py` -> `steps/` -> `__init__.py` -> tests) assumes a flat list. Nesting creates hierarchy where none should exist.

To aid navigation, `steps/__init__.py` should group exports with conceptual comments:

```python
# --- Ported from source (adapted for SDK) ---
from .check_sdk_available import check_sdk_available
from .execute import execute_sdk_call
# ...

# --- Bridge steps (BMAD-to-Beads) ---
from .parse_bmad_story import parse_bmad_story
from .create_beads_issue import create_beads_issue
from .write_beads_id import write_beads_id

# --- Observability steps ---
from .log_hook_event import log_hook_event
from .build_context_bundle import build_context_bundle

# --- Safety steps ---
from .block_dangerous_command import block_dangerous_command
```

This is documentation, not structure. Zero architectural weight.

### Command Inventory

These Claude commands will exist in `.claude/commands/`, each following the dual-layer pattern (`.md` entry point + Python module in `adws/`):

| Command | Phase | Python Module | Purpose |
|---|---|---|---|
| `/implement` | P1 (MVP) | `adws/adw_modules/steps/execute.py` | Execute implementation from Beads issue description |
| `/verify` | P1 (MVP) | Inline shell steps in workflow | Run full local quality gate (npm test, e2e, pytest, ruff) |
| `/build` | P2 | `adws/adw_modules/steps/execute.py` | Fast-track trivial changes |
| `/prime` | P2 | TBD | Load codebase context into session |
| `/load_bundle` | P3 | `adws/adw_modules/steps/build_context_bundle.py` | Reload previous session context (manual) |
| `/convert-stories-to-beads` | P2 | Bridge steps (parse/create/write) | Convert BMAD stories to Beads issues |

Note: `/verify` is not a standalone Python step -- it composes shell commands (`npm test`, `npm run test:e2e`, `uv run pytest`, `uv run ruff check`) within the `implement_verify_close` workflow via `with_verification`. The `.md` command provides the natural-language entry point for interactive use.

### Workflow Discovery and Dispatch

`workflows/__init__.py` provides `load_workflow(name)` and `list_workflows()`. When a Beads issue contains a `{workflow_name}` tag, `adw_dispatch.py` calls `load_workflow(name)` to match the tag string to a workflow's `.name` attribute. This is the glue binding Beads issues to ADWS execution.

`convert_stories_to_beads` is **not a dispatch target** -- it is invoked manually via Claude command, not triggered by a Beads issue tag (it *creates* Beads issues). Whether `list_workflows()` should distinguish dispatchable from manually-invoked workflows (e.g., a `dispatchable` flag or separate registry) is deferred to step 4.

### Workflow Composition Notes

| Workflow | Composition |
|---|---|
| `implement_close.py` | `/implement` (SDK step) -> `bd close` (shell step, `always_run=True`) |
| `implement_verify_close.py` | `/implement` (SDK step) -> verification shell steps (`npm test`, `npm run test:e2e`, `uv run pytest`, `uv run ruff check`) composed inline via `with_verification` combinator -> `bd close` (shell step, `always_run=True`) |
| `convert_stories_to_beads.py` | `parse_bmad_story` -> `create_beads_issue` -> `write_beads_id` (all step modules) |

Verification logic (FR12-FR17) is **not** a dedicated step module. It is composed from inline shell `Step` definitions within the `implement_verify_close` workflow. The `with_verification` combinator handles the implement/verify retry loop with accumulated feedback.

### Scaffold Story Definition of Done

The first implementation story (project initialization) must end with proof of life across the full pipeline:

1. `mise install` succeeds and pins correct runtime versions
2. `uv sync` installs all dependencies from `uv.lock`
3. `bd doctor` runs clean (Beads initialized)
4. `uv run pytest adws/tests/ -v` passes with at least **one test per layer**:
   - One step test (e.g., `check_sdk_available` returns proper `IOResult`)
   - One engine test (e.g., `WorkflowContext` creation and immutability)
   - One workflow structure test (e.g., `implement_close` has correct steps)
5. `uv run mypy adws/` passes
6. `uv run ruff check adws/` passes
7. CI pipeline extended: Python validation (`uv run pytest`, `uv run mypy`, `uv run ruff check`) runs on every PR alongside existing JS pipeline. **Verified by pushing a deliberately failing Python test and confirming the PR check fails.** The pipeline must gate merges, not just run.

Coverage can be skeletal at this point, but the test infrastructure and four-layer pipeline must be proven to work in this project.

**Mise bootstrapping:** The scaffold story must address how developers get `mise` itself. Either the README documents "Prerequisites: install mise" with a link, or the CI workflow uses `jdx/mise-action` (or both). A fresh clone where `mise install` is the first DoD item must not fail because mise isn't installed. The CI bootstrapping approach (`mise-action` vs `actions/setup-python` + manual `uv` install) is deferred to step 4.

### Changed or Dropped from Source

| Component | Change Type | Detail |
|---|---|---|
| `check_claude.py` | Replaced | -> `check_sdk_available.py` (SDK import + auth check) |
| `execute.py` | Replaced | Subprocess CLI -> SDK-native `ClaudeSDKClient` calls |
| `parse_output.py` | Adapted | JSONL stream parsing -> SDK `ResultMessage` processing |
| `convert_output.py` | Adapted | JSONL-to-JSON conversion -> structured data transformation |
| `save_final.py` | Adapted | JSON array extraction -> `ResultMessage` persistence |
| `process_result.py` | Adapted | Subprocess exit code analysis -> SDK response processing |
| `agent.py` | Removed | Replaced by SDK-native execution in `steps/execute.py` |
| `adw_prompt.py` | Removed | SDK handles direct prompts |
| `click` dependency | Removed | CLI entry points replaced by SDK-native execution |
| `plan_implement_close.py` | Removed | BMAD handles planning |
| `chore_implement.py` | Removed | BMAD handles lightweight planning |

Note: "Adapted" steps retain their architectural role in the pipeline but their input/output types change fundamentally. The source steps process JSONL subprocess output; the adapted steps process structured `ResultMessage` objects from the SDK. An implementing agent should not copy source verbatim -- the function signatures and internal logic will differ.

### Testing Strategy Notes

**I/O Density Variation:**

Steps vary in their ratio of pure logic to I/O operations. The test strategy should reflect this:

| Step Type | Example | Test Approach |
|---|---|---|
| Pure logic with thin I/O tail | `block_dangerous_command.py` (regex matching) | Mostly direct unit tests on logic; mock only `write_security_log_io()` |
| Balanced | `parse_bmad_story.py` (markdown parsing + file read) | Mix of logic tests and mocked I/O |
| Thin wrapper around I/O | `create_beads_issue.py` (shells out to `bd create`) | Mock-heavy; test error mapping and result handling |

All steps use `io_ops.py` as the mock boundary regardless. The difference is how much of the test exercises real logic vs mocked boundaries.

**`conftest.py` Shared Fixtures (porting requirement):**

The scaffold's `conftest.py` must provide shared fixtures from day one:
- Mocked `io_ops` module (common mock patterns for file ops, subprocess, SDK calls)
- Sample `WorkflowContext` instances (with and without issue IDs, feedback history)
- Sample `ResultMessage` objects (realistic SDK responses for adapted step tests -- prevents 4+ test files from inventing different mock formats)
- Sample Beads issue data (for bridge step tests)
- Sample BMAD story markdown (for parse step tests)

### `io_ops.py` Scaling Consideration

The source project's `io_ops.py` handles file ops, subprocess execution, JSON parsing, and CLI checks. Our version adds: SDK calls, Beads CLI calls (`bd create`, `bd close`), BMAD file reads/writes, security log writes, hook log writes, and context bundle writes -- roughly doubling the surface area.

The single-file pattern still works at our initial scale. However, if `io_ops.py` crosses ~300 lines or ~15 functions, the escape hatch is splitting it into an `io_ops/` **package** with submodules:

```
io_ops/
├── __init__.py      # Re-exports everything (mock point unchanged)
├── filesystem.py    # File read/write/directory ops
├── sdk.py           # ClaudeSDKClient calls
├── beads.py         # bd CLI calls
└── logging.py       # Hook logs, security logs, context bundles
```

The mock point stays `adws.adw_modules.io_ops.some_function` regardless -- consumers import from `io_ops` and never know whether it's a file or a package. This is a zero-cost refactor when needed, not an upfront decision. Flag it for review after Phase 1 MVP when the actual function count is known.

### Deferred to Step 4 (Architectural Decisions) -- CHECKLIST

Step 4 **must** explicitly resolve each item below with a decision or a justified further deferral. Do not silently drop items.

- [ ] TBD dependency: `pydantic` -- do SDK types replace source Pydantic models at API boundary?
- [ ] TBD dependency: `rich` -- do dispatch/trigger scripts need interactive terminal output?
- [ ] TBD dependency: `dotenv` -- what's the config approach for SDK credentials?
- [ ] `[tool.mypy]` strict mode configuration keys
- [ ] `[tool.ruff]` rule configuration
- [ ] `[tool.pytest.ini_options]` configuration
- [ ] CI job structure: parallel vs sequential Python/JS jobs
- [ ] CI bootstrapping: `jdx/mise-action` vs `actions/setup-python` + manual `uv` install
- [ ] Workflow dispatch registry: `dispatchable` flag or separate registry for manually-invoked vs auto-dispatched workflows

### .gitignore Additions

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/

# ADWS output (transient)
agents/hook_logs/
agents/context_bundles/
agents/security_logs/
```

## Core Architectural Decisions

### Deferred Checklist Resolution

All items deferred from Step 3 are resolved below with cross-references:

- [x] TBD dependency: `pydantic` → **Decision 2** (confirmed, 2.12.5)
- [x] TBD dependency: `rich` → **Decision 2** (confirmed, 14.3.1)
- [x] TBD dependency: `dotenv` → **Decision 2** (dropped, mise handles env)
- [x] `[tool.mypy]` strict mode configuration → **Decision 3**
- [x] `[tool.ruff]` rule configuration → **Decision 3**
- [x] `[tool.pytest.ini_options]` configuration → **Decision 3**
- [x] CI job structure → **Decision 4** (parallel Python/JS jobs)
- [x] CI bootstrapping → **Decision 4** (jdx/mise-action)
- [x] Workflow dispatch registry → **Decision 5** (dispatchable flag)

### Decision 1: SDK Integration Design

**Decision:** Thin Pydantic wrapper at the SDK boundary.

`AdwsRequest` and `AdwsResponse` are Pydantic models defined in `adws/adw_modules/types.py`. They represent what OUR pipeline needs -- not what the SDK exposes. `io_ops.py` translates between our types and SDK types (`ClaudeAgentOptions`, `ResultMessage`).

```python
# adws/adw_modules/types.py
from pydantic import BaseModel

class AdwsRequest(BaseModel):
    """What our pipeline sends to the SDK boundary."""
    model: str
    system_prompt: str
    prompt: str
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    max_turns: int | None = None

class AdwsResponse(BaseModel):
    """What our pipeline gets back from the SDK boundary."""
    result: str | None
    cost: float | None
    duration_seconds: float | None
    session_id: str | None
    is_error: bool = False
    error_message: str | None = None
```

```python
# adws/adw_modules/io_ops.py (SDK boundary)
def execute_sdk_call(request: AdwsRequest) -> AdwsResponse:
    """Translate AdwsRequest -> SDK types, call SDK, translate ResultMessage -> AdwsResponse.

    This is the ONLY function that imports claude-agent-sdk.
    Pipeline code never sees SDK types directly.
    """
    ...
```

**Why a wrapper and not direct SDK types?**
- SDK is relatively new; its types may change between versions
- Our pipeline only needs a subset of SDK capabilities
- Single translation point in io_ops.py means SDK upgrades touch one file
- Mocking is clean: mock `execute_sdk_call`, never mock SDK internals

#### Enemy Unit Tests (EUT)

**Enemy Unit Tests test the REAL SDK through our proxy with REAL API calls. NOTHING IS MOCKED. NOTHING IS INTROSPECTED. The entire point is to detect when the real third-party dependency changes behavior after a version bump.**

EUTs verify that our thin `AdwsRequest`/`AdwsResponse` proxy works correctly against the actual `claude-agent-sdk`. If Anthropic changes `ResultMessage` fields, renames parameters, or alters behavior in a new SDK version, EUTs fail. That's how we know.

**What EUTs are:**
- Integration tests that make REAL API calls using REAL credentials (ANTHROPIC_API_KEY)
- Tests that go through our `execute_sdk_call()` proxy with a real `AdwsRequest`
- Tests that verify the REAL `AdwsResponse` comes back with expected fields populated
- The safety net that catches SDK contract changes after `uv lock --upgrade-package claude-agent-sdk`

**What EUTs are NOT:**
- They are NOT unit tests with mocks
- They are NOT introspection tests checking SDK field names via `inspect`
- They are NOT tests that can run without credentials
- They are NOT tests where ANY part of the call chain is faked

**EUT execution:**
- Run with: `uv run pytest adws/tests/ -m enemy`
- Marked with: `@pytest.mark.enemy`
- Credentials: `ANTHROPIC_API_KEY` available locally (mise `.env`) and in CI (GitHub Actions secrets)
- Run everywhere: locally during development AND in CI. No "skip locally" behavior.
- Transient API failures: Investigate, don't suppress. If the API is flaky, that's information. If our proxy is wrong, that's a bug. Either way, suppressing the failure hides the signal.

**EUT example:**

```python
"""Enemy Unit Tests: Full round-trip through our proxy against the real SDK.

NOTHING IS MOCKED. These tests make REAL API calls using REAL credentials.
If the SDK changed after a version bump, these tests fail.
"""
import pytest

@pytest.mark.enemy
def test_proxy_full_round_trip():
    """Our proxy makes a real API call and parses the real response."""
    request = AdwsRequest(
        model="claude-sonnet-4-20250514",
        system_prompt="Respond with exactly: hello",
        prompt="Say hello",
    )
    response = execute_sdk_call(request)  # REAL proxy → REAL SDK → REAL API
    assert isinstance(response, AdwsResponse)
    assert response.result is not None
    assert response.cost is not None

@pytest.mark.enemy
def test_proxy_error_handling():
    """Our proxy correctly maps SDK errors to AdwsResponse."""
    request = AdwsRequest(
        model="nonexistent-model-12345",
        system_prompt="This should fail",
        prompt="Hello",
    )
    response = execute_sdk_call(request)  # REAL proxy → REAL SDK → REAL error
    assert response.is_error is True
    assert response.error_message is not None
```

### Decision 2: TBD Dependency Resolution

All TBD dependencies from Step 3 resolved:

| Dependency | Decision | Version | Rationale |
|---|---|---|---|
| `pydantic` | **Confirmed** | 2.12.5 | Required for `AdwsRequest`/`AdwsResponse` wrapper types (Decision 1). Provides validation, serialization, and type safety at the SDK boundary. |
| `rich` | **Confirmed** | 14.3.1 | Required for interactive terminal output in `adw_dispatch.py` and `adw_trigger_cron.py`. These are developer-facing scripts that benefit from formatted output, progress indicators, and error display. |
| `dotenv` | **Dropped** | N/A | Replaced by mise environment management. `.mise.toml` supports `env_file = '.env'` which loads environment variables at runtime. No Python dependency needed. |

Updated core dependencies table (supersedes Step 3 TBD entries):

| Package | Version | Role |
|---|---|---|
| `claude-agent-sdk` | 0.1.27 | Native SDK for Claude API calls |
| `returns` | 0.26.0 | ROP monadic types (IOResult, Result, flow) |
| `pydantic` | 2.12.5 | Request/response model validation at SDK boundary |
| `rich` | 14.3.1 | Terminal UI for dispatch/trigger scripts |

### Decision 3: Tool Configuration

All tool configurations specified with inline comments for developer clarity.

**`pyproject.toml` tool sections:**

```toml
[tool.mypy]
# Strict mode: catch type errors before they become runtime errors
strict = true
# Flag functions that return Any (often hides type information loss)
warn_return_any = true
# Flag [mypy] config entries that don't match any files (catches typos)
warn_unused_configs = true
# Required: makes mypy understand returns library's monadic types (IOResult, Result, etc.)
# Without this plugin, mypy can't track types through flow() and bind() chains
plugins = ["returns.contrib.mypy.returns_plugin"]

[tool.ruff]
# Match our Python version requirement
target-version = "py311"
# Industry standard line length (Black default)
line-length = 88

[tool.ruff.lint]
# Start with ALL rules enabled, then explicitly disable what we don't need.
# This is safer than starting permissive and missing things.
select = ["ALL"]
# D: docstring rules -- we use inline comments, not docstrings for everything
# ANN101/ANN102: self/cls type annotations -- redundant, Python knows these
# COM812: trailing comma -- conflicts with ruff formatter
# ISC001: implicit string concatenation -- conflicts with ruff formatter
ignore = ["D", "ANN101", "ANN102", "COM812", "ISC001"]

[tool.ruff.lint.per-file-ignores]
# Test files get relaxed rules:
# S101: assert usage (pytest requires assert)
# PLR2004: magic numbers in tests (test values like 42, 100 are fine)
# ANN: type annotations in tests (test functions don't need return types)
"adws/tests/**/*.py" = ["S101", "PLR2004", "ANN"]

[tool.pytest.ini_options]
# Where pytest looks for tests
testpaths = ["adws/tests"]
# Combined options:
# --cov=adws: measure coverage of the adws package
# --cov-report=term-missing: show which lines are NOT covered in terminal output
# --cov-fail-under=100: fail if coverage drops below 100% (enforced from day one)
# --cov-branch: require branch coverage (both if/else paths), not just line coverage
# --strict-markers: fail if a test uses an unregistered marker (catches typos like @pytest.mark.enmey)
addopts = "--cov=adws --cov-report=term-missing --cov-fail-under=100 --cov-branch --strict-markers"
# Register custom markers so --strict-markers knows about them
markers = [
    "enemy: Enemy Unit Tests - REAL API calls through REAL SDK (require ANTHROPIC_API_KEY)",
]
```

### Decision 4: CI Pipeline Design

**Decision:** Parallel Python and JavaScript jobs with mise-action bootstrapping.

```yaml
# .github/workflows/ci-cd.yml (extended)
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jdx/mise-action@v2  # Installs mise, reads .mise.toml, installs Python + uv
      - run: uv sync --frozen       # Install from uv.lock exactly
      - run: uv run ruff check adws/
      - run: uv run mypy adws/
      - run: uv run pytest adws/tests/
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}  # For Enemy Unit Tests

  javascript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jdx/mise-action@v2  # Reads .mise.toml, installs Node.js
      - run: npm ci
      - run: npm test
      - run: npm run test:e2e
```

Python and JavaScript jobs run in parallel -- neither depends on the other. Both use `jdx/mise-action` to read `.mise.toml` for runtime versions, ensuring CI matches local development exactly. `ANTHROPIC_API_KEY` is a GitHub Actions secret available to the Python job for EUTs.

### Decision 5: Workflow Dispatch Registry

**Decision:** `dispatchable` boolean flag on the `Workflow` dataclass with policy enforcement in `adw_dispatch.py`.

```python
@dataclass(frozen=True)
class Workflow:
    name: str
    description: str
    steps: list[Step]
    dispatchable: bool = True  # Can this workflow be triggered by a Beads issue tag?
```

**Dispatch policy separation:**

`load_workflow()` in `workflows/__init__.py` is a pure lookup -- it finds a workflow by name and returns it (or None). It never checks `dispatchable`. Policy enforcement lives in `adw_dispatch.py`:

```python
# adw_dispatch.py -- dispatch policy
workflow = load_workflow(tag_name)
if workflow is None:
    log_error(f"No workflow found for tag '{tag_name}'")
    return
if not workflow.dispatchable:
    log_error(f"Workflow '{tag_name}' is not dispatchable")
    return
execute_workflow(workflow, context)
```

**`list_workflows()` with optional filter:**

```python
def list_workflows(dispatchable_only: bool = False) -> list[Workflow]:
    """Return all registered workflows, optionally filtered to dispatchable only.

    Args:
        dispatchable_only: If True, return only workflows where dispatchable=True.
                          Cron/dispatch callers pass True; debugging callers pass False.
    """
```

**Workflow dispatch values:**

| Workflow | `dispatchable` | Reason |
|---|---|---|
| `implement_verify_close` | `True` | Triggered by Beads issue `{implement_verify_close}` tag |
| `implement_close` | `True` | Triggered by Beads issue `{implement_close}` tag |
| `convert_stories_to_beads` | `False` | Manually invoked via Claude command, not triggered by Beads |

### Decision 6: TDD & Pair Programming Enforcement

**Mandate: All code MUST be developed using strict TDD (Red-Green-Refactor). No code exists without a test that demanded it. TDD phases are enforced architecturally through separate agent roles in the workflow engine.**

#### Agent-to-Agent Pair Programming via Workflow Steps

Claude Flow implements pairing as separate agents with distinct roles coordinated through shared state. Our ADWS engine achieves the same pattern naturally -- each workflow step is a fresh SDK call with its own system prompt (brainstorming Decision #9: fresh SDK calls with accumulated feedback). The "pair" is:

- **Test Agent** (RED phase): System prompt focused exclusively on writing failing tests from story acceptance criteria. This agent writes tests and NOTHING ELSE.
- **Implementation Agent** (GREEN phase): System prompt focused exclusively on writing minimum code to make the failing tests pass. Receives the test files as context.
- **Refactor Agent** (REFACTOR phase): System prompt focused on cleanup and improvement with all tests still passing.

Shell verification steps between each agent call enforce the phase gates -- tests MUST fail after RED, tests MUST pass after GREEN and REFACTOR.

#### TDD Workflow Composition

The `implement_verify_close` workflow enforces TDD phases:

```
implement_verify_close (TDD-enforced):
  1. write_failing_tests    (SDK step — test agent, RED)
  2. verify_tests_fail      (shell step — confirms RED)
  3. implement              (SDK step — implementation agent, GREEN)
  4. verify_tests_pass      (shell step — confirms GREEN)
  5. refactor               (SDK step — refactor agent, REFACTOR)
  6. verify_tests_pass      (shell step — confirms still GREEN)
  7. bd close               (shell step, always_run=True)
```

Steps 1-2 are the RED phase. Steps 3-4 are GREEN. Steps 5-6 are REFACTOR. Each SDK step is a separate agent with a focused system prompt. The shell verification steps are the objective arbiter -- no agent self-reports success, the test runner proves it.

If `verify_tests_fail` (step 2) passes (meaning tests DON'T fail), the workflow errors -- tests must actually be failing before implementation begins. If `verify_tests_pass` (step 4) fails, the `with_verification` retry loop kicks in with accumulated feedback, same as the existing design.

#### New Steps Required

| Step | Type | Role |
|---|---|---|
| `write_failing_tests.py` | SDK step | Generates failing tests from story AC. System prompt: "Write tests only. Do not implement." After writing each test, annotates with expected failure reason (e.g., `"""RED: Will fail with ImportError because module does not exist yet."""`). Every test MUST state why it fails. |
| `verify_tests_fail.py` | Shell step | Runs `uv run pytest --tb=short` on newly written test files only (not full suite). Asserts non-zero exit and validates failure types. **Valid RED failures**: `AssertionError`, `AttributeError`, `ImportError`, `NotImplementedError` (missing implementation). **Invalid failures**: `SyntaxError`, `IndentationError`, `NameError` in test files (broken test code). **The RED phase is not "tests fail." The RED phase is "tests fail for the RIGHT EXPECTED REASON."** If failures are test-internal errors or unexpected types, the step fails and feeds back to the test agent for correction. |
| `refactor.py` | SDK step | Cleans up implementation with tests passing. System prompt: "Refactor only. All tests must still pass." |

Existing steps `execute.py` (implement) and verify shell steps handle the GREEN phase.

#### ATDD Integration with BMAD TEA

Before the TDD workflow runs, the `/bmad-tea-testarch-atdd` skill can optionally generate acceptance-level test scaffolds from story acceptance criteria. These become the starting point for the test agent's RED phase. The test agent then fills in unit and integration tests following the testing pyramid:

1. Unit tests first (fast, isolated, mock io_ops)
2. Integration/acceptance tests for user-facing behavior
3. Enemy Unit Tests for SDK boundary verification

#### CLAUDE.md Enforcement

The scaffold story creates `CLAUDE.md` at project root:

```markdown
## MANDATORY: TDD (Red-Green-Refactor)

ALL code in this project MUST be developed using strict TDD:
1. Write a failing test FIRST (RED) — the test MUST fail for the expected reason, not any reason
2. Write minimum code to pass (GREEN)
3. Refactor with tests passing (REFACTOR)
4. No code without a test. No exceptions.

### How TDD is enforced:
- The ADWS workflow engine runs separate agents for each TDD phase
- Test agent writes tests. Implementation agent writes code. Refactor agent cleans up.
- Shell verification steps between phases prove compliance — not self-reported
- Tests MUST fail after RED phase for the EXPECTED REASON (verified by runner)
- Tests MUST pass after GREEN and REFACTOR phases (verified by runner)

Python testing conventions:
- Tests in adws/tests/ mirroring source structure
- All external dependencies behind io_ops.py boundary (mockable)
- 100% line and branch coverage on all code — every line exists because a test demanded it
- Enemy Unit Tests (@pytest.mark.enemy) test REAL SDK with REAL API calls
- Never mock in EUTs — the whole point is testing the real dependency
- All I/O behind io_ops.py — mock in tests, real in production

Testing stack:
- pytest — test framework (primary)
- pytest-mock — mock utilities (mocker fixture)
- pytest-cov — coverage tracking (100% enforced)
- mypy — static type checking (strict mode)
- ruff — linting + formatting

### Testing Pyramid:
- Unit tests (bottom — many, fast, isolated): mock io_ops boundary
- Enemy Unit Tests (integration — fewer, test real SDK): NOTHING mocked, REAL API calls
- Acceptance tests (top — fewest, user perspective): from story AC via /bmad-tea-testarch-atdd

### THE RULE:
If a story's acceptance criteria can fail, a test MUST catch it.
```

#### Pre-Merge Enforcement

CI gates that block merge if any of these fail:
- `uv run pytest adws/tests/ --cov-fail-under=100` (all tests pass, 100% coverage)
- `uv run mypy adws/` (strict type checking)
- `uv run ruff check adws/` (zero lint violations)

No `--no-verify`, no skipping hooks, no exceptions.

#### Environment: `.env.sample`

The scaffold story creates `.env.sample` at project root:

```
# Required for ADWS engine and Enemy Unit Tests
ANTHROPIC_API_KEY=your-key-here
```

This documents the required credentials. Developers copy to `.env`, mise loads it via `env_file = '.env'` in `.mise.toml`.

#### Scaffold Story DoD Updates (from Step 4)

Added to existing DoD from Step 3:

- `CLAUDE.md` exists at project root with TDD mandate
- `.env.sample` exists at project root with `ANTHROPIC_API_KEY`
- `write_failing_tests` step exists and is wired into `implement_verify_close` workflow
- `verify_tests_fail` step exists and correctly validates failure types (expected vs broken)
- At least one test committed RED-first in a separate commit from its implementation (proves TDD workflow phases actually execute in order)

**Deferred to Step 5 (Implementation Patterns):** If the GREEN phase fails repeatedly despite accumulated feedback, the retry strategy should consider splitting the failing tests into smaller batches and implementing each batch separately. This is a combinator-level pattern for `with_verification` and belongs in implementation patterns, not architectural decisions.

## Implementation Patterns & Consistency Rules

_Status: Draft -- presented but not yet reviewed via Party Mode. Resume review from A/P/C menu._

### Critical Conflict Points Identified

8 areas where AI agents could make different choices when implementing ADWS.

### Naming Patterns

**Python Naming (PEP 8 + project conventions):**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Modules | `snake_case.py` | `check_sdk_available.py` | `checkSdkAvailable.py` |
| Functions | `snake_case` | `execute_sdk_call()` | `executeSdkCall()` |
| Classes | `PascalCase` | `AdwsRequest`, `PipelineError` | `adws_request`, `pipeline_error` |
| Constants | `UPPER_SNAKE_CASE` | `DANGEROUS_PATTERNS` | `dangerousPatterns` |
| Type aliases | `PascalCase` | `StepResult = IOResult[PipelineError, WorkflowContext]` | `step_result` |
| Private helpers | `_leading_underscore` | `_parse_failure_type()` | `parsefailuretype()` |
| Test functions | `test_<unit>_<scenario>` | `test_check_sdk_available_returns_success()` | `test_1()`, `test_it_works()` |
| Test files | `test_<module>.py` | `test_check_sdk_available.py` | `check_sdk_available_test.py` |
| Fixtures | Descriptive nouns | `mock_io_ops`, `sample_workflow_context` | `fixture1`, `ctx` |

**Step Module Naming:**

Every step file is named after the action it performs, in imperative form:
- `check_sdk_available.py` (not `sdk_checker.py` or `is_sdk_available.py`)
- `execute_sdk_call.py` (not `sdk_executor.py` or `run_sdk.py`)
- `parse_bmad_story.py` (not `bmad_parser.py` or `story_parsing.py`)
- `block_dangerous_command.py` (not `command_blocker.py` or `safety_check.py`)

The function exported from each step module matches the filename:
```python
# check_sdk_available.py
def check_sdk_available(ctx: WorkflowContext) -> IOResult[PipelineError, WorkflowContext]:
    ...
```

**Error Class Naming:**

All errors are frozen dataclasses in `errors.py` with a descriptive `Error` suffix:
```python
@dataclass(frozen=True)
class SdkNotAvailableError:
    message: str = "claude-agent-sdk is not importable"

@dataclass(frozen=True)
class SdkCallError:
    message: str
    request: AdwsRequest

@dataclass(frozen=True)
class BeadsCommandError:
    message: str
    command: str
    exit_code: int
```

The union type `PipelineError` aggregates all error types:
```python
PipelineError = SdkNotAvailableError | SdkCallError | BeadsCommandError | ...
```

### Structure Patterns

**Step Internal Structure (every step follows this pattern):**

```python
"""One-line description of what this step does."""
from returns.io import IOResult, IOSuccess, IOFailure

from adws.adw_modules.errors import PipelineError, SpecificError
from adws.adw_modules.io_ops import some_io_function
from adws.adw_modules.engine.types import WorkflowContext


def step_name(ctx: WorkflowContext) -> IOResult[PipelineError, WorkflowContext]:
    """Execute the step. Pure logic calls io_ops for impure operations."""
    # 1. Extract what we need from context
    # 2. Call io_ops for any I/O
    # 3. Process the result (pure logic)
    # 4. Return updated context or error
```

Rules enforced:
- ONE public function per step, matching the filename
- Signature is ALWAYS `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`
- Steps NEVER import `claude-agent-sdk`, `subprocess`, `pathlib`, `open()`, or any I/O directly
- Steps NEVER call other steps -- composition happens in workflows
- Private helpers `_prefixed()` are allowed for pure logic within the step

**Import Ordering (ruff enforced, but document the convention):**

```python
# 1. Standard library
import json
from pathlib import Path

# 2. Third-party
from returns.io import IOResult, IOSuccess, IOFailure
from pydantic import BaseModel

# 3. Local -- always absolute imports from adws
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.io_ops import execute_sdk_call
from adws.adw_modules.engine.types import WorkflowContext
```

Never use relative imports. Always `from adws.adw_modules.X import Y`.

**Test Structure (mirrors source):**

```
adws/tests/
├── conftest.py                    # Shared fixtures
├── adw_modules/
│   ├── test_io_ops.py             # I/O boundary tests
│   ├── test_errors.py             # Error type tests
│   ├── engine/
│   │   ├── test_types.py          # Tier 1 public types
│   │   ├── test_executor.py       # Tier 2 ROP internals
│   │   └── test_combinators.py    # Tier 2 combinators
│   └── steps/
│       ├── test_check_sdk_available.py
│       ├── test_execute.py
│       └── ...                    # One test file per step
├── workflows/
│   ├── test_implement_close.py
│   └── test_implement_verify_close.py
├── enemy/
│   └── test_sdk_proxy.py          # Enemy Unit Tests
└── integration/
    └── ...                        # Cross-component tests
```

Every test file tests exactly one module. No multi-module test files.

### Format Patterns

**ROP Return Type Usage:**

| Situation | Return Type | Rationale |
|---|---|---|
| Step functions | `IOResult[PipelineError, WorkflowContext]` | Steps do I/O (through io_ops) |
| io_ops functions | `IOResult[PipelineError, T]` | Direct I/O operations |
| Pure domain logic | `Result[PipelineError, T]` | No I/O involved |
| Engine combinators | `IOResult[PipelineError, WorkflowContext]` | Compose I/O-performing steps |
| Workflow definitions | Return `Workflow` dataclass | Declarative, no ROP needed |

An agent should NEVER use `IOResult` for pure logic or `Result` for I/O operations.

**WorkflowContext Update Pattern:**

`WorkflowContext` is immutable. Steps return a NEW context with updated fields:
```python
# CORRECT: Create new context with updated fields
return IOSuccess(ctx.with_updates(
    sdk_response=response,
    feedback=ctx.feedback + [new_feedback],
))

# WRONG: Mutate existing context
ctx.sdk_response = response  # This must not work (frozen dataclass)
```

**Logging Format:**

```python
# Use structured logging through io_ops, never print() or logging directly
from adws.adw_modules.io_ops import log_step_start, log_step_end, log_error

log_step_start("check_sdk_available")
# ... step logic ...
log_step_end("check_sdk_available", success=True)
```

Log messages are structured (JSON-compatible), not free-text. The io_ops functions handle formatting.

### Communication Patterns

**Step-to-Step Communication:**

Steps communicate exclusively through `WorkflowContext`. No global state, no module-level variables, no side-channel files.

```python
# Step 1 produces data
def write_failing_tests(ctx: WorkflowContext) -> IOResult[PipelineError, WorkflowContext]:
    ...
    return IOSuccess(ctx.with_updates(test_files=new_test_files))

# Step 2 consumes it
def verify_tests_fail(ctx: WorkflowContext) -> IOResult[PipelineError, WorkflowContext]:
    test_files = ctx.test_files  # Set by previous step
    ...
```

**Error Propagation:**

Errors short-circuit the pipeline via ROP. Steps never catch and swallow errors:
```python
# CORRECT: Let errors propagate
result = some_io_function(args)
# If result is IOFailure, the flow() chain stops here automatically

# WRONG: Catching and hiding errors
try:
    result = some_io_function(args)
except Exception:
    pass  # NEVER do this
```

The ONLY place errors are caught and handled is in the engine's executor, which maps them to workflow-level outcomes.

**`always_run` Steps:**

Steps marked `always_run=True` (like `bd close`) execute regardless of previous step failures. They receive the WorkflowContext in whatever state it was when the failure occurred. These steps MUST handle partial context gracefully.

### Process Patterns

**Step Creation Checklist (from source, mandatory for every new step):**

1. Add error type(s) to `errors.py` and update `PipelineError` union
2. Add I/O function(s) to `io_ops.py`
3. Create step module in `steps/` following the internal structure pattern
4. Export from `steps/__init__.py` in the correct conceptual group
5. Write tests: mock io_ops, test pure logic, test error paths
6. Verify: `uv run pytest`, `uv run mypy`, `uv run ruff check`

No step is complete until all 6 items are done. An agent that creates a step without updating `errors.py` or `io_ops.py` has created an incomplete step.

**io_ops Function Pattern:**

```python
# Every io_ops function follows this pattern:
def some_io_operation(args: SomeType) -> IOResult[SpecificError, ReturnType]:
    """One-line description. This function performs actual I/O."""
    try:
        # Actual I/O here (SDK call, file write, subprocess, etc.)
        result = actual_io_operation()
        return IOSuccess(transform(result))
    except SpecificException as e:
        return IOFailure(SpecificError(message=str(e), ...))
```

Rules:
- Always returns `IOResult`, never raises
- Catches specific exceptions, never bare `except Exception`
- Transforms external types into domain types before returning
- Never contains domain logic -- that belongs in steps

**Workflow Definition Pattern:**

```python
"""One-line description of what this workflow does."""
from adws.adw_modules.engine.types import Workflow, Step

implement_close = Workflow(
    name="implement_close",
    description="Fast-track for trivial changes: implement then close",
    dispatchable=True,
    steps=[
        Step(name="implement", function="execute_sdk_call", sdk=True),
        Step(name="close", function="bd_close", always_run=True),
    ],
)
```

Workflows are declarative data, not imperative code. They define WHAT steps run in WHAT order. The engine handles HOW.

**TDD RED Phase Annotation Pattern:**

```python
def test_check_sdk_available_returns_success():
    """RED: Will fail with ImportError because check_sdk_available does not exist yet.

    Once implemented, verifies that check_sdk_available returns IOSuccess
    when the SDK is importable and authenticated.
    """
    from adws.adw_modules.steps.check_sdk_available import check_sdk_available
    ctx = sample_workflow_context()
    result = check_sdk_available(ctx)
    assert isinstance(result, IOSuccess)
```

Every test written in the RED phase MUST have a docstring starting with `RED:` explaining the expected failure reason. This is auditable in code review and by the `verify_tests_fail` step.

**GREEN Phase Retry-and-Split Pattern:**

If the GREEN phase fails repeatedly (N retries with accumulated feedback), the `with_verification` combinator should consider splitting: break the failing tests into smaller batches and GREEN each batch separately. This prevents a single ambitious RED batch from blocking the entire workflow. The combinator tracks retry count and, after a configurable threshold, emits a split recommendation in the feedback. The implementation agent receives this recommendation and can choose to implement a subset of the failing tests.

### Enforcement Guidelines

**All AI Agents MUST:**

1. Follow the step creation checklist for every new step -- no partial steps
2. Use absolute imports from `adws.adw_modules` -- no relative imports
3. Route ALL I/O through `io_ops.py` -- no direct `open()`, `subprocess`, or SDK imports in steps
4. Return `IOResult`/`Result` -- never raise exceptions from steps
5. Update `WorkflowContext` immutably -- never mutate
6. Write one test file per source module -- no multi-module test files
7. Annotate RED phase tests with `RED:` docstring prefix
8. Follow the step signature: `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`

**Pattern Verification:**

- `ruff check` catches import ordering, naming violations
- `mypy --strict` catches type signature violations, return type mismatches
- `pytest --cov-fail-under=100` catches missing tests
- Code review catches structural violations (step creation checklist)

## Project Structure & Boundaries

### Requirements to Structure Mapping

Mapping the 9 FR capability areas from the PRD to specific files and directories:

| FR Category | Primary Location | Supporting Files |
|---|---|---|
| **Workflow Execution (FR1-6)** | `adws/adw_modules/engine/executor.py`, `combinators.py` | `engine/types.py` (WorkflowContext, Step, Workflow) |
| **Workflow Definition (FR7-11)** | `adws/workflows/*.py` | `engine/types.py` (Tier 1 public API) |
| **Quality Verification (FR12-17)** | Inline shell steps in `implement_verify_close.py` | `verify_tests_fail.py`, `verify_tests_pass` (shell steps) |
| **Issue Integration (FR18-22)** | `adws/adw_dispatch.py`, `adw_trigger_cron.py` | `io_ops.py` (bd CLI calls), `workflows/__init__.py` (load_workflow) |
| **BMAD-to-Beads Bridge (FR23-27)** | `adws/adw_modules/steps/parse_bmad_story.py`, `create_beads_issue.py`, `write_beads_id.py` | `adws/workflows/convert_stories_to_beads.py` |
| **Commands (FR28-32)** | `.claude/commands/*.md` | Corresponding Python modules in `adws/` |
| **Observability (FR33-36)** | `adws/adw_modules/steps/log_hook_event.py`, `build_context_bundle.py` | `.claude/hooks/` (CLI shims), `io_ops.py` (file writes) |
| **Safety (FR37-40)** | `adws/adw_modules/steps/block_dangerous_command.py` | `.claude/hooks/` (CLI shim), `io_ops.py` (security log writes) |
| **Dev Environment (FR41-45)** | `pyproject.toml`, `.mise.toml`, `uv.lock` | `.github/workflows/ci-cd.yml`, `CLAUDE.md` |

### Architectural Boundaries

**Four-Layer Pipeline Boundary (internal to ADWS):**

```
┌─────────────────────────────────────────────────────┐
│  Tier 1: Workflows (declarative, no ROP)            │
│  adws/workflows/*.py                                │
│  Workflow, Step dataclasses → engine                 │
├─────────────────────────────────────────────────────┤
│  Tier 2: Engine (ROP internals, hidden from Tier 1) │
│  adws/adw_modules/engine/executor.py, combinators.py│
│  flow(), bind(), IOResult chains                     │
├─────────────────────────────────────────────────────┤
│  Steps (pure logic + io_ops calls)                   │
│  adws/adw_modules/steps/*.py                         │
│  (WorkflowContext) → IOResult[PipelineError, ...]    │
├─────────────────────────────────────────────────────┤
│  I/O Boundary (single mock point)                    │
│  adws/adw_modules/io_ops.py                          │
│  SDK calls, file ops, subprocess, bd CLI             │
└─────────────────────────────────────────────────────┘
```

Rules:
- Tier 1 imports from `engine/types.py` only -- never sees `IOResult`, `flow`, or ROP internals
- Steps import from `io_ops.py` only for I/O -- never `subprocess`, `open()`, `claude-agent-sdk`
- `io_ops.py` is the ONLY file that imports `claude-agent-sdk` and `subprocess`
- Engine imports steps but steps never import engine -- no circular dependencies

**External System Boundaries (all through io_ops.py):**

```
                          ┌──────────────┐
                          │  io_ops.py   │
                          │  (boundary)  │
                          └──────┬───────┘
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
        ┌────────────┐  ┌────────────┐  ┌────────────┐
        │ claude-     │  │ bd CLI     │  │ filesystem │
        │ agent-sdk   │  │ (Beads)    │  │ (logs,     │
        │             │  │            │  │  bundles,  │
        │ AdwsRequest │  │ bd create  │  │  BMAD .md) │
        │ → SDK types │  │ bd close   │  │            │
        │ → AdwsResp  │  │ bd update  │  │            │
        └────────────┘  └────────────┘  └────────────┘
```

Each external system has dedicated functions in `io_ops.py`. Steps never know which external system they're talking to -- they call an io_ops function and get back a domain type.

**Test Boundary:**

All tests mock at `adws.adw_modules.io_ops` -- this is the single mock point for the entire test suite. Enemy Unit Tests are the exception: they call io_ops functions for real, hitting the actual SDK. This boundary is enforced architecturally by the step pattern (steps never import I/O directly, so there is nothing else to mock).

**One-Directional System Flow (BMAD → Beads → ADWS):**

```
BMAD (.md files)                    Beads (bd CLI)                     ADWS (engine)
┌──────────────┐                    ┌──────────────┐                   ┌──────────────┐
│ Epic/Story   │ /convert-stories   │ Beads Issue  │  adw_dispatch     │ Workflow     │
│ markdown     │ ──────────────►    │ {workflow}   │  ──────────►      │ Execution    │
│              │  to-beads          │ tag          │                   │              │
└──────────────┘                    └──────┬───────┘                   └──────────────┘
     ▲ beads_id                            │ ▲                              │
     │ written back                        │ │ bd ready                     │
     └─────────────────────────────────────┘ │ (polling)                    │
                                             │                              │
                                      ┌──────┴────────┐                    │
                                      │ adw_trigger_   │                    │
                                      │ cron.py        │                    │
                                      │ (polls ready   │                    │
                                      │  issues)       │                    │
                                      └────────────────┘                    │
                                             │ bd close                     │
                                             └◄─────────────────────────────┘
```

- BMAD files are READ by `parse_bmad_story` step, WRITTEN by `write_beads_id` step
- ADWS never reads BMAD files during workflow execution -- only during conversion
- Beads issues are the contract between planning and execution
- No reverse flow: ADWS never writes to BMAD (except beads_id tracking), Beads never triggers BMAD

**Dual-Toolchain Boundary:**

```
┌───────────────────────────────────────────────┐
│                 .mise.toml                     │
│          (pins Python, Node.js, uv)            │
├───────────────────┬───────────────────────────┤
│  Python (uv)      │  JavaScript (npm)          │
│  pyproject.toml   │  package.json              │
│  uv.lock          │  package-lock.json         │
│  adws/            │  popup.js, manifest.json   │
│  CLAUDE.md        │  tests/ (Jest, Playwright) │
│  .claude/hooks/   │                            │
│  .claude/commands/ │                            │
│  agents/          │                            │
└───────────────────┴───────────────────────────┘
```

The two toolchains share: `.mise.toml` (runtime versions), `.github/workflows/ci-cd.yml` (CI), and `.gitignore`. Nothing else crosses the boundary.

### Integration Points

| Integration | Mechanism | Direction | io_ops Function |
|---|---|---|---|
| ADWS → Claude API | `claude-agent-sdk` `ClaudeSDKClient` | Outbound | `execute_sdk_call()` |
| ADWS → Beads | `bd` CLI subprocess | Outbound | `run_beads_command()` |
| ADWS → BMAD files | File read/write | Bidirectional* | `read_bmad_story()`*, `write_beads_id_to_bmad()`* |
| ADWS → agents/ output | File append/write | **Write-only** | `write_hook_log()`, `write_security_log()`, `write_context_bundle()` |
| CLI hooks → ADWS steps | stdin JSON → Python function | Inbound | Hook shims in `.claude/hooks/` |
| SDK HookMatcher → ADWS steps | Callback → Python function | Inbound | HookMatcher registration in engine |
| Cron → ADWS dispatch | `adw_trigger_cron.py` → `adw_dispatch.py` | Inbound | `poll_ready_issues()` |

\* **Conversion workflow only.** `read_bmad_story()` and `write_beads_id_to_bmad()` are called exclusively by steps in `convert_stories_to_beads`. They are not available to execution workflows (`implement_verify_close`, `implement_close`). An agent implementing execution workflows should never call these functions.

**Output-only boundary:** The `agents/` directory (`hook_logs/`, `context_bundles/`, `security_logs/`) is written to during workflow execution but never read from. The sole exception is `/load_bundle`, which reads from `context_bundles/` for manual session reload -- this is human-initiated, never automated. No workflow step reads from `agents/`.

### Data Flow Through TDD Workflow

```
Story AC (from Beads issue description)
    │
    ▼
[1] write_failing_tests (SDK step — test agent)
    │ ctx.test_files = [new test paths]
    ▼
[2] verify_tests_fail (shell step)
    │ Asserts: non-zero exit, valid failure types
    ▼
[3] implement (SDK step — implementation agent)
    │ ctx.implementation_files = [new/modified paths]
    ▼
[4] verify_tests_pass (shell step)
    │ Asserts: zero exit, 100% coverage
    │ On failure: retry with ctx.feedback += [error details]
    ▼
[5] refactor (SDK step — refactor agent)
    │ ctx.refactored_files = [modified paths]
    ▼
[6] verify_tests_pass (shell step)
    │ Asserts: zero exit, 100% coverage still
    ▼
[7] bd close (shell step, always_run=True)
    │ Closes Beads issue regardless of prior failures
    ▼
Done
```

**Note:** Field names in the data flow (`ctx.test_files`, `ctx.implementation_files`, `ctx.refactored_files`, `ctx.feedback`) are **illustrative**, showing what kind of data flows between steps. The exact `WorkflowContext` field names, types, and signatures are defined in the implementing story when `engine/types.py` is built. The architecture specifies the *pattern* (immutable context, steps produce updated context), not the field-level schema.

Each step reads from and writes to `WorkflowContext`. The context accumulates state as it flows through the pipeline. On failure at any verification step, `with_verification` retries with accumulated feedback.

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**

| Decision Pair | Compatible? | Notes |
|---|---|---|
| D1 (SDK wrapper) + D6 (TDD) | Yes | TDD phases test through the proxy; EUTs test real SDK. No conflict. |
| D1 (SDK wrapper) + D3 (tool config) | Yes | mypy strict validates Pydantic models; ruff checks io_ops.py imports. |
| D3 (tool config) + D4 (CI pipeline) | Yes | CI runs identical tools: `uv run pytest`, `uv run mypy`, `uv run ruff check`. |
| D5 (dispatch registry) + D6 (TDD) | Yes | TDD workflow is dispatchable. Dispatch calls load_workflow, engine runs TDD phases. |
| D2 (dependencies) + D4 (CI) | Yes | mise-action installs all runtimes; `uv sync --frozen` installs exact versions. |
| D6 (TDD) + Step 5 (patterns) | Yes | RED/GREEN/REFACTOR phases follow step creation checklist and io_ops boundary. |

**Version Compatibility:**

| Package | Version | Python >=3.11 | Cross-compatible |
|---|---|---|---|
| `claude-agent-sdk` | 0.1.27 | Yes (requires >=3.10) | Yes |
| `returns` | 0.26.0 | Yes | Yes (mypy plugin configured) |
| `pydantic` | 2.12.5 | Yes | Yes |
| `rich` | 14.3.1 | Yes | Yes |

No version conflicts detected. All dependencies compatible with each other and Python 3.11.

**Pattern Consistency:** Step 5 patterns (step structure, import ordering, ROP usage, naming) directly support the decisions from step 4. Step 6 boundaries enforce the patterns (all I/O through io_ops.py, no cross-boundary imports).

**Structure Alignment:** Step 3 project tree matches step 6 boundaries. Every directory falls within exactly one boundary. No orphaned paths.

### Requirements Coverage Validation

**Functional Requirements (45 FRs):**

| FR Category | FRs | Architecture Coverage | Status |
|---|---|---|---|
| Workflow Execution (FR1-6) | 6 | Engine executor, combinators, WorkflowContext, always_run, retry | Covered |
| Workflow Definition (FR7-11) | 5 | Tier 1 API (Workflow/Step dataclasses), declarative composition | Covered |
| Quality Verification (FR12-17) | 6 | Inline shell steps in implement_verify_close, with_verification combinator, accumulated feedback | Covered |
| Issue Integration (FR18-22) | 5 | adw_dispatch.py, adw_trigger_cron.py, load_workflow(), bd CLI via io_ops | Covered |
| BMAD-to-Beads Bridge (FR23-27) | 5 | Bridge steps (parse/create/write), convert_stories_to_beads workflow | Covered |
| Commands (FR28-32) | 5 | .claude/commands/*.md + Python modules, command inventory table | Covered |
| Observability (FR33-36) | 4 | log_hook_event, build_context_bundle steps, CLI hook shims | Covered* |
| Safety (FR37-40) | 4 | block_dangerous_command step, security log writes, CLI hook shim | Covered* |
| Dev Environment (FR41-45) | 5 | pyproject.toml, .mise.toml, uv.lock, CI pipeline, CLAUDE.md | Covered |

\* **Naming discrepancy:** FR36 references `adws/observability/` and FR40 references shared safety code. The architecture places these as steps in `adws/adw_modules/steps/` (not separate directories), per user directive that all functionality flows through the four-layer pipeline. The functional requirement is fully met; only the path differs from the PRD's original language. Flag as PRD errata for Epics & Stories phase.

**Non-Functional Requirements (20 NFRs):**

| NFR Category | NFRs | Architecture Coverage | Status |
|---|---|---|---|
| Reliability (NFR1-4) | 4 | ROP error handling, always_run steps, fail-open hooks | Covered |
| Reproducibility (NFR5-8) | 4 | uv.lock, npm ci, .mise.toml, identical CI/local environments | Covered |
| Testability (NFR9-13) | 5 | 100% coverage, io_ops boundary, mypy strict, ruff ALL, Tier 1/2 separation | Covered |
| Security (NFR14-16) | 3 | Regex patterns, audit logging, .gitignore | Covered |
| Integration (NFR17-20) | 4 | bd CLI only, SDK only, no direct BMAD reads in execution, shared hook modules | Covered** |

\** **NFR19 nuance:** "ADWS must never read BMAD files directly" -- the architecture has `read_bmad_story()` in io_ops.py for the conversion workflow. During execution workflows (`implement_verify_close`, `implement_close`), BMAD files are never accessed. The NFR is met; the conversion-only scope is enforced by the Step 6 integration points footnote.

**Coverage: 45/45 FRs covered. 20/20 NFRs covered. Zero gaps.**

### Implementation Readiness Validation

**Decision Completeness:**
- All 6 decisions documented with specific versions, code examples, and rationale
- Every TBD from step 3 deferred checklist resolved in step 4 with cross-references
- EUT documentation unambiguous after 4 rounds of correction
- Tool config includes inline comments for non-Python developer

**Structure Completeness:**
- Full project directory tree with every file (step 3)
- FR-to-structure mapping (step 6)
- Every boundary diagrammed (step 6)
- Integration points table with io_ops function names (step 6)

**Pattern Completeness:**
- Step creation checklist (6 mandatory items)
- 8 mandatory agent rules
- Code examples for every pattern (step structure, io_ops, workflows, TDD annotations, error classes)
- Anti-patterns documented alongside correct patterns

### Gap Analysis

**Critical Gaps:** None.

**Minor Gaps:**

1. **Step 5 party mode review:** Step 5 (Implementation Patterns) was saved as draft without party mode review. The content is substantive and informed by all prior decisions, but hasn't had the adversarial scrutiny that steps 3, 4, and 6 received. Low risk -- the patterns are derived from the source project's established conventions.

2. **FR36/FR40 PRD path mismatch:** The PRD references `adws/observability/` and separate safety code. The architecture correctly places these as steps, but the PRD language is now stale. This is a PRD errata task for the Epics & Stories phase, not an architecture gap.

3. **WorkflowContext field-level schema:** Deliberately deferred (step 6 marks field names as illustrative). Defined during implementation when `engine/types.py` is built. Correct deferral, not a gap.

4. **Cron trigger scheduling mechanism:** `adw_trigger_cron.py` polls `bd ready`, but the architecture intentionally does not specify how the polling is scheduled (system cron, CI scheduled workflow, manual invocation). This is an implementation detail for the story that builds the cron trigger (Phase 2). An implementing agent should not invent a scheduling mechanism without a story specifying it.

5. **`implement_close` TDD exemption:** `implement_close` intentionally skips TDD phases (no `write_failing_tests`, no `verify_tests_fail`). It is the fast-track workflow for non-code changes (config tweaks, dependency bumps). If a change touches Python code, `--cov-fail-under=100` catches it regardless. The TDD mandate from Decision 6 applies to `implement_verify_close`; `implement_close` relies on coverage enforcement as the safety net.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context analyzed (step 2)
- [x] Scale and complexity assessed (step 2)
- [x] Technical constraints identified (step 2)
- [x] Cross-cutting concerns mapped (step 2)

**Architectural Decisions**
- [x] 6 decisions documented with versions and code examples (step 4)
- [x] Technology stack fully specified with exact pinned versions (steps 3, 4)
- [x] Integration patterns defined through io_ops boundary (steps 4, 5, 6)
- [x] TDD enforcement architecturally built into workflow engine (step 4, Decision 6)

**Implementation Patterns**
- [x] Naming conventions established with examples and anti-patterns (step 5)
- [x] Structure patterns defined for steps, io_ops, workflows, tests (step 5)
- [x] Communication patterns specified (WorkflowContext, error propagation) (step 5)
- [x] Process patterns documented (step creation checklist, TDD annotations) (step 5)

**Project Structure**
- [x] Complete directory tree defined (step 3)
- [x] Component boundaries diagrammed (step 6)
- [x] Integration points mapped with io_ops functions (step 6)
- [x] Requirements-to-structure mapping complete (step 6)

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level:** High

**Key Strengths:**
- Four-layer ROP pipeline gives clear separation of concerns with single mock point
- TDD enforcement is architectural, not aspirational -- separate agents per phase with shell verification gates
- Enemy Unit Tests catch real SDK changes with real API calls
- Every decision was refined through multiple party mode rounds including adversarial review
- Complete project structure mirrors proven source architecture

**Areas for Future Enhancement:**
- Step 5 party mode review (low priority -- patterns are well-established)
- io_ops.py scaling decision (deferred to Phase 1 MVP completion when function count is known)
- GREEN phase retry-and-split combinator (deferred to implementation patterns)

### Implementation Handoff

**Document Precedence:** This architecture document is the **single source of truth** for implementing agents. The PRD provides requirements, the brainstorming provides rationale, but this document is what agents follow. If there is ever a conflict between the PRD's language and the architecture's decisions (e.g., the PRD says `adws/observability/` but the architecture places it in `adws/adw_modules/steps/`), **the architecture wins**.

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented in this file
- Use implementation patterns from step 5 consistently across all modules
- Respect the four-layer pipeline boundary -- steps never import I/O directly
- Follow the step creation checklist for every new step (errors → io_ops → step → __init__ → tests → verify)
- Enforce TDD: RED (tests fail for right reason) → GREEN (minimum code) → REFACTOR (tests still pass)
- Refer to this document for all architectural questions before inventing solutions

**First Implementation Priority:** Scaffold story (Phase 1 MVP) as defined in the Scaffold Story DoD (steps 3 + 4).

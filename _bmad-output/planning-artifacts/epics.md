---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-02-01'
inputDocuments: ['_bmad-output/planning-artifacts/prd.md', '_bmad-output/planning-artifacts/architecture.md']
---

# tab-groups-windows-list - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for tab-groups-windows-list, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: Engine can execute a workflow as a sequence of steps with ROP-based error handling
- FR2: Engine can execute each step as a fresh SDK call via `ClaudeSDKClient`
- FR3: Engine can propagate context (outputs/inputs) between sequential steps
- FR4: Engine can halt on step failure and propagate `PipelineError` with structured details
- FR5: Engine can execute `always_run` steps even after previous step failures
- FR6: Engine can retry failed steps with configurable `max_attempts` and delay
- FR7: Developer can define workflows declaratively using `Workflow` and `Step` types without ROP knowledge
- FR8: Developer can compose workflows using combinators (`with_verification`, `sequence`)
- FR9: Developer can define conditional steps that execute based on context predicates
- FR10: Developer can define data flow between steps via `output`/`input_from` parameters
- FR11: Developer can mark steps as shell commands for direct subprocess execution
- FR12: Engine can run `/verify` to execute the full local quality gate
- FR13: Verify step can run `npm test` (Jest unit tests)
- FR14: Verify step can run `npm run test:e2e` (Playwright end-to-end tests)
- FR15: Verify step can run Python linting and type checking on `adws/` code
- FR16: Engine can accumulate feedback from all failed verify attempts in `WorkflowContext.feedback`
- FR17: Engine can pass accumulated feedback as explicit context to subsequent `/implement` retries
- FR18: Engine can receive a Beads issue ID and extract the workflow tag from its description
- FR19: Engine can dispatch the appropriate workflow based on the extracted workflow tag
- FR20: Engine can close a Beads issue upon successful workflow completion via `bd close`
- FR21: Cron trigger can poll Beads for open issues with workflow tags ready for dispatch
- FR22: Cron trigger can execute dispatched workflows without manual intervention
- FR23: Developer can convert BMAD stories to Beads issues via `/convert-stories-to-beads`
- FR24: Converter can parse BMAD epic/story markdown and extract full story content
- FR25: Converter can create Beads issues with the entire story as issue description
- FR26: Converter can embed `{workflow_name}` tag in the Beads issue description for dispatch
- FR27: Converter can write `beads_id` back into the source BMAD story file for tracking
- FR28: Each command exists as a Claude command `.md` (natural language entry point) backed by a Python module in `adws/` (testable logic)
- FR29: Developer can invoke `/implement` to execute implementation from a Beads issue description
- FR30: Developer can invoke `/verify` to run the full local quality gate
- FR31: Developer can invoke `/prime` to load codebase context into a session
- FR32: Developer can invoke `/build` for fast-track trivial changes
- FR33: System can log all hook events to session-specific JSONL files in `agents/hook_logs/`
- FR34: System can track files read/written during sessions to `agents/context_bundles/`
- FR35: Developer can reload previous session context via `/load_bundle`
- FR36: CLI hooks and SDK HookMatchers share the same underlying Python modules with zero duplicated logic
- FR37: System can block dangerous bash commands matching known destructive patterns (e.g., `rm -rf /`)
- FR38: System can log blocked commands to `agents/security_logs/` for audit
- FR39: System can suggest safer alternatives for blocked commands
- FR40: Safety module serves both CLI hooks (interactive) and SDK HookMatchers (engine) via shared code
- FR41: All Python dependencies are installed reproducibly via `uv` with exact versions in `uv.lock`
- FR42: All JS dependencies are installed reproducibly via `npm ci` with exact versions in `package-lock.json`
- FR43: Runtime versions (Python, Node.js) are pinned in `mise.toml`
- FR44: CI validates both Python and JS codebases in a unified pipeline
- FR45: Developer can run all quality checks locally before pushing to CI

### NonFunctional Requirements

- NFR1: Engine must handle step failures gracefully via ROP -- no uncaught exceptions, no partial state corruption
- NFR2: Failed workflows must leave Beads issues in a recoverable state (open, with failure context logged)
- NFR3: `always_run` steps (e.g., `bd close`) must execute even after upstream failures
- NFR4: Hook failures (observability, safety) must not block the operation they're observing -- fail-open with stderr logging
- NFR5: `uv sync --frozen` must succeed on any machine with the correct Python version -- zero network-dependent resolution
- NFR6: `npm ci` must produce identical `node_modules/` on any machine with the correct Node.js version
- NFR7: `mise.toml` must be the single source of truth for all runtime versions
- NFR8: CI and local dev environments must produce identical test results given the same code -- no environment-dependent flakiness
- NFR9: All `adws/` Python code must have 100% test coverage measured by pytest-cov
- NFR10: All I/O operations must be isolated behind `io_ops.py` boundary -- single mock point for all tests
- NFR11: All Python code must pass mypy type checking with strict mode
- NFR12: All Python code must pass ruff linting with no suppressions
- NFR13: Workflow definitions (Tier 1) must be testable without mocking ROP internals
- NFR14: Dangerous command blocker must block all patterns in the defined regex set with zero false negatives on known patterns
- NFR15: All blocked commands must be logged to `agents/security_logs/` with timestamp, command, and reason
- NFR16: No credentials, API keys, or secrets may be committed to source control -- `.gitignore` must cover all sensitive patterns
- NFR17: ADWS must interact with Beads exclusively via `bd` CLI commands -- no direct file manipulation of `.beads/` internals
- NFR18: ADWS must interact with Claude exclusively via `claude-agent-sdk` Python API -- no subprocess CLI wrapping
- NFR19: ADWS must never read BMAD files directly during execution workflows -- the Beads issue description is the only contract
- NFR20: All hook entry points (CLI shims in `.claude/hooks/`) must delegate to shared `adws/` Python modules -- no standalone logic in hook scripts

### Additional Requirements

**From Architecture -- Scaffold & Structure:**
- Manual scaffold mirroring source project structure (Option C selected). This is Epic 1 Story 1.
- Dual-toolchain contract: `uv` manages Python, `npm` manages JS, `mise` pins both runtimes
- `pyproject.toml` and `uv.lock` at project root (flat layout, NOT nested under adws/)
- `CLAUDE.md` at project root with TDD mandate (scaffold deliverable)
- `.env.sample` at project root with `ANTHROPIC_API_KEY` (scaffold deliverable)
- `.gitignore` additions for Python artifacts

**From Architecture -- SDK Integration (Decision 1):**
- Thin Pydantic wrapper: `AdwsRequest`/`AdwsResponse` models at SDK boundary in `io_ops.py`
- Pipeline code never imports `claude-agent-sdk` directly -- only `io_ops.py` does
- Enemy Unit Tests (EUTs): test REAL SDK with REAL API calls, NOTHING mocked, credentials everywhere

**From Architecture -- Dependencies (Decision 2):**
- `pydantic` 2.12.5 confirmed for SDK wrapper types
- `rich` 14.3.1 confirmed for dispatch/trigger terminal output
- `dotenv` dropped -- mise handles env loading via `env_file = '.env'`

**From Architecture -- Tool Configuration (Decision 3):**
- mypy strict mode with returns plugin
- ruff ALL with justified ignores (D, ANN101, ANN102, COM812, ISC001)
- pytest 100% line and branch coverage, strict markers, enemy marker registered

**From Architecture -- CI Pipeline (Decision 4):**
- Parallel Python and JavaScript CI jobs
- `jdx/mise-action@v2` for bootstrapping
- `ANTHROPIC_API_KEY` as GitHub Actions secret for EUTs

**From Architecture -- Dispatch (Decision 5):**
- `dispatchable` boolean flag on Workflow dataclass
- `load_workflow()` is pure lookup; policy in `adw_dispatch.py`
- `list_workflows(dispatchable_only=False)` filter on Tier 1 API

**From Architecture -- TDD Enforcement (Decision 6):**
- Agent-to-agent pair programming via separate SDK calls per TDD phase
- `write_failing_tests` step (RED phase -- test agent)
- `verify_tests_fail` step (shell gate -- validates expected failure types)
- `refactor` step (REFACTOR phase -- cleanup agent)
- TDD workflow: RED → verify fail → GREEN → verify pass → REFACTOR → verify pass → close
- ATDD integration with BMAD TEA workflow for story-level test scaffolds

**From Architecture -- Implementation Patterns (Step 5):**
- Step creation checklist (6 mandatory items: errors → io_ops → step → __init__ → tests → verify)
- Step signature: `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`
- One public function per step matching filename
- Absolute imports only (`from adws.adw_modules.X import Y`)
- io_ops function pattern: returns IOResult, catches specific exceptions, transforms types
- Workflow definitions are declarative data, not imperative code
- RED phase annotation pattern: `"""RED: <expected failure reason>"""`

**From Architecture -- Scaffold Story DoD (Steps 3 + 4):**
- `mise install` succeeds
- `uv sync` installs all dependencies from `uv.lock`
- `bd doctor` runs clean
- At least one test per layer (step, engine, workflow structure)
- `uv run mypy adws/` passes
- `uv run ruff check adws/` passes
- CI pipeline gates merges (verified with deliberately failing test)
- At least one test committed RED-first in separate commit from implementation

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Workflow execution with ROP error handling |
| FR2 | Epic 2 | Step execution as fresh SDK call via ClaudeSDKClient |
| FR3 | Epic 2 | Context propagation between sequential steps |
| FR4 | Epic 2 | Halt on failure, propagate PipelineError |
| FR5 | Epic 2 | Execute always_run steps after failures |
| FR6 | Epic 2 | Retry with configurable max_attempts and delay |
| FR7 | Epic 2 | Declarative Workflow and Step types |
| FR8 | Epic 2 | Workflow combinators (with_verification, sequence) |
| FR9 | Epic 2 | Conditional steps via context predicates |
| FR10 | Epic 2 | Data flow via output/input_from parameters |
| FR11 | Epic 2 | Shell command steps for subprocess execution |
| FR12 | Epic 3 | /verify quality gate execution |
| FR13 | Epic 3 | Run npm test (Jest unit tests) |
| FR14 | Epic 3 | Run npm run test:e2e (Playwright E2E tests) |
| FR15 | Epic 3 | Run Python linting and type checking |
| FR16 | Epic 3 | Accumulate feedback from failed verify attempts |
| FR17 | Epic 3 | Pass accumulated feedback to /implement retries |
| FR18 | Epic 7 | Receive Beads issue ID, extract workflow tag |
| FR19 | Epic 7 | Dispatch workflow by extracted tag |
| FR20 | Epic 7 | Close Beads issue on successful completion |
| FR21 | Epic 7 | Cron trigger polls for open issues |
| FR22 | Epic 7 | Execute dispatched workflows unattended |
| FR23 | Epic 6 | /convert-stories-to-beads command |
| FR24 | Epic 6 | Parse BMAD epic/story markdown |
| FR25 | Epic 6 | Create Beads issues with story content |
| FR26 | Epic 6 | Embed workflow_name tag in Beads issue |
| FR27 | Epic 6 | Write beads_id back to BMAD story file |
| FR28 | Epic 4 | Command .md entry point + Python module pattern |
| FR29 | Epic 4 | /implement command with TDD workflow |
| FR30 | Epic 4 | /verify command entry point |
| FR31 | Epic 4 | /prime command for context loading |
| FR32 | Epic 4 | /build command for fast-track changes |
| FR33 | Epic 5 | Log hook events to JSONL files |
| FR34 | Epic 5 | Track files read/written to context bundles |
| FR35 | Epic 5 | /load_bundle for session context reload |
| FR36 | Epic 5 | Shared hook modules (CLI + SDK) |
| FR37 | Epic 5 | Block dangerous bash commands |
| FR38 | Epic 5 | Log blocked commands to security_logs |
| FR39 | Epic 5 | Suggest safer alternatives for blocked commands |
| FR40 | Epic 5 | Shared safety module (CLI + SDK) |
| FR41 | Epic 1 | Python dependencies via uv with exact versions |
| FR42 | Epic 1 | JS dependencies via npm ci with exact versions |
| FR43 | Epic 1 | Runtime versions pinned in mise.toml |
| FR44 | Epic 1 | CI validates both Python and JS codebases |
| FR45 | Epic 1 | Developer can run all quality checks locally |

### Standing NFR Constraints

| NFR | Description | Applies To |
|-----|-------------|------------|
| NFR1 | Graceful failure via ROP, no uncaught exceptions | Epics 2, 3, 4, 7 |
| NFR2 | Failed workflows leave Beads issues recoverable | Epics 4, 7 |
| NFR3 | always_run steps execute after upstream failures | Epics 2, 4, 7 |
| NFR4 | Hook failures fail-open with stderr logging | Epic 5 |
| NFR5 | uv sync --frozen zero network resolution | Epic 1 |
| NFR6 | npm ci identical node_modules | Epic 1 |
| NFR7 | mise.toml single source of truth for runtimes | Epic 1 |
| NFR8 | CI and local produce identical results | Epic 1 |
| NFR9 | 100% test coverage on all adws/ code | **All epics** (standing gate) |
| NFR10 | All I/O behind io_ops.py boundary | Epics 1, 2, 3, 4, 5, 6, 7 |
| NFR11 | mypy strict mode passes | **All epics** (standing gate) |
| NFR12 | ruff linting no suppressions | **All epics** (standing gate) |
| NFR13 | Workflow definitions testable without mocking ROP | Epics 2, 4, 7 |
| NFR14 | Command blocker zero false negatives | Epic 5 |
| NFR15 | Blocked commands logged with timestamp/reason | Epic 5 |
| NFR16 | No secrets in source control | **All epics** (standing gate) |
| NFR17 | Beads via bd CLI only | Epics 4, 6, 7 |
| NFR18 | Claude via SDK API only, no subprocess CLI | Epics 2, 4 |
| NFR19 | Never read BMAD during execution workflows | Epics 4, 7 |
| NFR20 | Hook shims delegate to shared adws/ modules | Epic 5 |
| EUT* | Every io_ops SDK function must have a corresponding Enemy Unit Test (derived from NFR18 + Decision 1) | Epics 2, 4 |

## Epic List

### Epic 1: Project Foundation & Developer Environment

Developer can clone the repo, install all dependencies via `mise install && uv sync && npm ci`, run quality gates locally, and have CI validate both codebases. Scaffold includes skeleton implementations with at least one test per layer (step, engine, workflow structure), the `io_ops.py` boundary module with at least one real function and test, and a workflow name registry (constants/enum) so downstream epics can reference valid workflow names without importing Tier 1 types.

**FRs covered:** FR41, FR42, FR43, FR44, FR45

**Notes:** Scaffold DoD from architecture. Workflow name registry enables Epic 6 (Converter) to stay on Track B without depending on Epic 2. io_ops.py boundary established here so all subsequent epics code against the pattern (NFR10). CI config enforces NFR9 (100% coverage gate) from day one.

#### Story 1.1: Project Scaffold & Dual-Toolchain Setup

As an ADWS developer,
I want the Python project scaffold with dual-toolchain support alongside the existing JavaScript extension,
So that I have a reproducible development environment for building pipeline code.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `mise install`
**Then** Python and Node.js are installed at the versions pinned in `mise.toml`
**And** `mise.toml` is the single source of truth for all runtime versions (NFR7)

**Given** mise has installed runtimes
**When** I run `uv sync`
**Then** all Python dependencies are installed from `uv.lock` with exact versions (NFR5)
**And** `pyproject.toml` exists at project root (flat layout, NOT nested under `adws/`)
**And** dependencies include: `returns`, `pydantic` 2.12.5, `rich` 14.3.1, `claude-agent-sdk`
**And** dev dependencies include: `pytest`, `pytest-cov`, `mypy`, `ruff`, `returns` mypy plugin

**Given** mise has installed runtimes
**When** I run `npm ci`
**Then** all JS dependencies are installed from `package-lock.json` with exact versions (NFR6)

**Given** the project is set up
**When** I inspect the directory structure
**Then** `adws/` exists with `__init__.py` and `adw_modules/` subdirectory
**And** `adws/tests/` exists for Python tests
**And** `CLAUDE.md` exists at project root with TDD mandate
**And** `.env.sample` exists at project root with `ANTHROPIC_API_KEY` placeholder
**And** `.gitignore` includes Python artifacts (`*.pyc`, `__pycache__`, `.venv`, `.mypy_cache`, `.ruff_cache`)
**And** no credentials or secrets are committed (NFR16)

**Given** the project is set up
**When** I run `bd doctor`
**Then** it reports clean status

**Given** `pyproject.toml` exists
**When** I inspect tool configurations
**Then** `[tool.mypy]` has `strict = true` and `returns` plugin configured
**And** `[tool.ruff.lint]` has `select = ["ALL"]` with justified ignores (D, ANN101, ANN102, COM812, ISC001)
**And** `[tool.pytest.ini_options]` has 100% line and branch coverage, strict markers, and `enemy` marker registered

#### Story 1.2: Skeleton Layer Implementations & TDD Foundation

As an ADWS developer,
I want skeleton implementations across all four pipeline layers with passing tests,
So that subsequent stories have established patterns to follow and quality gates are enforced from the start.

**Acceptance Criteria:**

**Given** the scaffold from Story 1.1
**When** I inspect `adws/adw_modules/errors.py`
**Then** `PipelineError` dataclass is defined with structured error fields (step_name, error_type, message, context)

**Given** the scaffold from Story 1.1
**When** I inspect `adws/adw_modules/io_ops.py`
**Then** at least one real function exists following the io_ops pattern (returns `IOResult`, catches specific exceptions)
**And** the module establishes the I/O boundary pattern -- all external I/O goes through this module (NFR10)

**Given** the scaffold from Story 1.1
**When** I inspect the `adws/adw_modules/` directory
**Then** a skeleton step function exists with correct signature: `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`
**And** a skeleton engine module exists
**And** a skeleton workflow definition exists as declarative data (not imperative code)
**And** a workflow name registry (constants/enum) exists with valid workflow names for downstream epics

**Given** all skeleton modules exist
**When** I run `uv run pytest adws/tests/`
**Then** at least one test per layer passes (step, engine, workflow structure)
**And** 100% line and branch coverage is maintained (NFR9)

**Given** the git history
**When** I inspect commits for this story
**Then** at least one test was committed RED-first in a separate commit from its implementation
**And** the RED commit has `"""RED: <expected failure reason>"""` annotation

**Given** all skeleton modules exist
**When** I run `uv run mypy adws/`
**Then** type checking passes with strict mode (NFR11)

**Given** all skeleton modules exist
**When** I run `uv run ruff check adws/`
**Then** linting passes with zero violations (NFR12)

#### Story 1.3: CI Pipeline & Quality Gate Enforcement

As an ADWS developer,
I want a unified CI pipeline that validates both Python and JavaScript code on every push,
So that quality gates are enforced and broken code cannot be merged.

**Acceptance Criteria:**

**Given** code is pushed to the repository
**When** the CI pipeline runs
**Then** Python and JavaScript jobs execute in parallel
**And** Python job runs `uv run mypy adws/`, `uv run ruff check adws/`, and `uv run pytest` with 100% coverage requirement
**And** JavaScript job runs `npm test` (Jest) and `npm run test:e2e` (Playwright)

**Given** the CI pipeline is configured
**When** I inspect the GitHub Actions workflow
**Then** it uses `jdx/mise-action@v2` for bootstrapping runtimes
**And** `ANTHROPIC_API_KEY` is configured as a GitHub Actions secret for future EUTs

**Given** a deliberately failing test is pushed
**When** the CI pipeline runs
**Then** the merge is blocked
**And** the failure is clearly reported in the PR checks

**Given** all tests pass
**When** I run quality checks locally with `uv run mypy adws/ && uv run ruff check adws/ && uv run pytest && npm test`
**Then** results match what CI produces (NFR8)

---

### Epic 2: Pipeline Engine & Workflow Types

A sample workflow executes three steps through the engine, with one step deliberately failing, demonstrating ROP error handling, context propagation, retry, and always_run behavior. Developer can define new workflows as declarative data structures without ROP knowledge.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11

**Notes:** Core infrastructure and highest-risk epic. Tier 1 (Workflow/Step types), Tier 2 (step functions), Tier 3 (engine). Introduces ROP (`returns` library), SDK client, WorkflowContext, PipelineError, and the engine execution loop -- all tightly coupled. Story ordering is critical: error types first, then io_ops SDK functions, then step signatures, then engine logic, then workflow definitions, then combinators. ClaudeSDKClient in io_ops.py -- every io_ops SDK function must have a corresponding EUT proving real SDK communication with real API calls per Decision 1. Shell step execution (FR11) must be solid before Epic 3 can wrap it.

#### Story 2.1: Error Types & WorkflowContext

As an ADWS developer,
I want foundational data types for pipeline errors and workflow state,
So that all pipeline components have a consistent contract for error propagation and context sharing.

**Acceptance Criteria:**

**Given** the skeleton from Epic 1
**When** I inspect `adws/adw_modules/errors.py`
**Then** `PipelineError` is a dataclass with fields: `step_name` (str), `error_type` (str), `message` (str), `context` (dict)
**And** it is immutable and serializable for logging

**Given** the skeleton from Epic 1
**When** I inspect `adws/adw_modules/workflow_context.py`
**Then** `WorkflowContext` is defined with `inputs` (dict), `outputs` (dict), and `feedback` (list) fields
**And** context supports accumulating feedback from failed verify attempts
**And** context supports propagating outputs from one step as inputs to the next

**Given** both types are defined
**When** I run `uv run pytest adws/tests/`
**Then** tests validate PipelineError construction, serialization, and field access
**And** tests validate WorkflowContext input/output propagation and feedback accumulation
**And** 100% coverage is maintained (NFR9)

#### Story 2.2: io_ops SDK Client & Enemy Unit Tests

As an ADWS developer,
I want a thin SDK client wrapper in io_ops.py with Pydantic boundary models,
So that pipeline code interacts with Claude exclusively through a testable I/O boundary.

**Acceptance Criteria:**

**Given** the io_ops boundary from Epic 1
**When** I inspect `adws/adw_modules/io_ops.py`
**Then** `ClaudeSDKClient` wraps the `claude-agent-sdk` Python API
**And** `AdwsRequest` and `AdwsResponse` are Pydantic models at the SDK boundary
**And** pipeline code never imports `claude-agent-sdk` directly -- only `io_ops.py` does (NFR18)

**Given** `ClaudeSDKClient` is implemented
**When** I run the EUT marked `@pytest.mark.enemy`
**Then** the test makes a REAL API call through the REAL SDK with REAL credentials
**And** nothing is mocked -- the test proves actual SDK communication (Decision 1)
**And** the test requires `ANTHROPIC_API_KEY` environment variable

**Given** all io_ops SDK functions
**When** I inspect the test suite
**Then** every io_ops SDK function has a corresponding Enemy Unit Test (EUT* constraint)
**And** unit tests with mocked io_ops also exist for fast CI feedback

#### Story 2.3: Step Function Type & Shell Command Execution

As an ADWS developer,
I want a formalized step function type and shell command execution capability,
So that I can define pipeline steps with a consistent signature and execute subprocess commands as steps.

**Acceptance Criteria:**

**Given** the error types from Story 2.1
**When** I inspect the step function type definition
**Then** the signature is `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`
**And** one public function per step file matching the filename
**And** absolute imports only (`from adws.adw_modules.X import Y`)

**Given** the io_ops boundary
**When** I inspect `io_ops.py` shell execution
**Then** `run_shell_command` function exists that executes subprocess commands
**And** it returns `IOResult`, catches specific exceptions, and transforms to `PipelineError` on failure
**And** it captures stdout and stderr for context propagation

**Given** shell execution is implemented
**When** a step is marked as a shell command (FR11)
**Then** the engine can execute it via `run_shell_command` instead of an SDK call
**And** shell step output is captured in `WorkflowContext.outputs`

**Given** all step-related code
**When** I run tests
**Then** shell command success and failure paths are both tested
**And** 100% coverage is maintained (NFR9)

#### Story 2.4: Engine Core - Sequential Execution & Error Handling

As an ADWS developer,
I want the engine to execute workflows as a sequence of steps with ROP-based error handling,
So that step failures are handled gracefully without uncaught exceptions or partial state corruption.

**Acceptance Criteria:**

**Given** a workflow with multiple steps
**When** the engine executes the workflow
**Then** steps run in sequence with ROP-based error handling (FR1)
**And** each SDK step is executed as a fresh SDK call via `ClaudeSDKClient` (FR2)
**And** context (outputs/inputs) propagates between sequential steps (FR3)

**Given** a step fails during execution
**When** the engine processes the failure
**Then** execution halts and `PipelineError` propagates with structured details (FR4)
**And** no uncaught exceptions occur (NFR1)
**And** no partial state corruption -- context is consistent up to the failed step

**Given** all engine code
**When** I run tests
**Then** tests cover: successful multi-step execution, mid-pipeline failure, context propagation across steps
**And** tests validate PipelineError contains correct step_name, error_type, and message
**And** 100% coverage is maintained (NFR9)

#### Story 2.5: Engine - always_run Steps & Retry Logic

As an ADWS developer,
I want the engine to support always_run steps and configurable retry logic,
So that cleanup steps execute regardless of failures and transient errors can be recovered.

**Acceptance Criteria:**

**Given** a workflow with `always_run` steps
**When** a previous step fails
**Then** the engine still executes all `always_run` steps (FR5, NFR3)
**And** the original failure is preserved and propagated after always_run steps complete

**Given** a step with `max_attempts > 1` configured
**When** the step fails on initial execution
**Then** the engine retries up to `max_attempts` times with configurable delay (FR6)
**And** retry attempts receive the accumulated context including failure information
**And** if all retries exhaust, the final PipelineError propagates

**Given** a step with retry that succeeds on a later attempt
**When** the engine processes the retry
**Then** execution continues normally from that step
**And** context propagation resumes as if the step succeeded on first try

**Given** all retry and always_run code
**When** I run tests
**Then** tests cover: always_run after success, always_run after failure, retry success on Nth attempt, retry exhaustion
**And** 100% coverage is maintained (NFR9)

#### Story 2.6: Declarative Workflow & Step Types with Data Flow

As an ADWS developer,
I want to define workflows as declarative data structures with data flow and conditional logic,
So that I can compose pipelines without understanding ROP internals.

**Acceptance Criteria:**

**Given** the skeleton types from Epic 1
**When** I inspect the full `Workflow` and `Step` dataclasses
**Then** `Workflow` is declarative data with name, steps list, and `dispatchable` boolean flag (Decision 5)
**And** `Step` supports `output` and `input_from` parameters for data flow between steps (FR10)
**And** `Step` supports a `condition` predicate for conditional execution (FR9)
**And** workflow definitions are declarative data, not imperative code

**Given** a workflow with `input_from` data flow
**When** the engine executes it
**Then** outputs from step N are available as inputs to step N+1 via the declared mapping
**And** missing input_from references produce a clear PipelineError

**Given** a workflow with conditional steps
**When** the engine evaluates the condition predicate against the current context
**Then** steps with truthy conditions execute normally
**And** steps with falsy conditions are skipped without error

**Given** the `list_workflows` function
**When** I call `list_workflows(dispatchable_only=True)`
**Then** only workflows with `dispatchable=True` are returned
**And** `list_workflows(dispatchable_only=False)` returns all workflows

**Given** workflow definitions
**When** I test them
**Then** workflow structure is testable without mocking ROP internals (NFR13)
**And** 100% coverage is maintained (NFR9)

#### Story 2.7: Workflow Combinators & Sample Workflow

As an ADWS developer,
I want workflow combinators and a sample workflow demonstrating the full pipeline,
So that I can compose complex workflows from simple building blocks and verify the engine works end-to-end.

**Acceptance Criteria:**

**Given** the engine and workflow types from previous stories
**When** I use `with_verification` combinator
**Then** it wraps a step with a verification step that runs after the main step
**And** the combinator is composable with other combinators

**Given** the engine and workflow types
**When** I use `sequence` combinator
**Then** it composes multiple workflows into a single sequential workflow
**And** context propagates across the composed workflows

**Given** a sample workflow with three steps
**When** one step is configured to deliberately fail
**Then** the engine demonstrates: ROP error handling, context propagation through successful steps, PipelineError on the failing step, retry logic on the failing step, always_run step executing after the failure
**And** this sample workflow serves as the integration test proving the full Epic 2 pipeline works end-to-end

**Given** all combinator code
**When** I run tests
**Then** tests cover: with_verification success, with_verification failure, sequence composition, sample workflow full execution
**And** 100% coverage is maintained (NFR9)

---

### Epic 3: Verify Pipeline

Engine can run the full local quality gate executing Jest unit tests, Playwright E2E tests, and Python linting/type checking. Failed verify attempts accumulate feedback that flows into subsequent retry context.

**FRs covered:** FR12, FR13, FR14, FR15, FR16, FR17

**Notes:** Story ordering critical: verify steps wrap shell execution from Epic 2 (FR11). Each verify sub-step (npm test, npm run test:e2e, uv run mypy, uv run ruff) is an io_ops shell function before it becomes a pipeline step.

#### Story 3.1: Verify io_ops Shell Functions

As an ADWS developer,
I want io_ops functions for each quality gate tool,
So that the verify pipeline can invoke test runners and linters through the established I/O boundary.

**Acceptance Criteria:**

**Given** `run_shell_command` from Epic 2 exists in io_ops
**When** I inspect io_ops verify functions
**Then** `run_jest_tests()` executes `npm test` and parses output for pass/fail status, failure messages, and affected files (FR13)
**And** `run_playwright_tests()` executes `npm run test:e2e` and parses output similarly (FR14)
**And** `run_mypy_check()` executes `uv run mypy adws/` and parses type errors (FR15)
**And** `run_ruff_check()` executes `uv run ruff check adws/` and parses lint violations (FR15)

**Given** each io_ops verify function
**When** it returns results
**Then** the return type is `IOResult[PipelineError, VerifyResult]` following the io_ops pattern
**And** `VerifyResult` contains structured data: tool name, pass/fail, error list, raw output

**Given** a tool execution fails (nonzero exit code)
**When** io_ops processes the result
**Then** failure details are captured in structured form (not just raw stderr)
**And** the PipelineError includes the tool name and parseable error output

**Given** all io_ops verify functions
**When** I run tests
**Then** both success and failure paths are covered for each function
**And** tests mock `run_shell_command` at the io_ops boundary (NFR10)
**And** 100% coverage is maintained (NFR9)

#### Story 3.2: Verify Pipeline Steps & Quality Gate Workflow

As an ADWS developer,
I want pipeline steps and a workflow definition for the full local quality gate,
So that `/verify` can execute all quality checks as a composable pipeline.

**Acceptance Criteria:**

**Given** io_ops verify functions from Story 3.1
**When** I inspect verify pipeline steps
**Then** each step wraps its io_ops function with the standard step signature: `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`
**And** step output includes structured `VerifyResult` in `WorkflowContext.outputs`

**Given** all verify steps exist
**When** I inspect the `verify` workflow definition
**Then** it composes all verify steps (Jest, Playwright, mypy, ruff) into a single quality gate workflow (FR12)
**And** the workflow is declarative data, not imperative code
**And** the workflow runs all checks even if earlier checks fail (each is independent)

**Given** the verify workflow is executed by the engine
**When** all checks pass
**Then** the workflow succeeds with all VerifyResults in context outputs

**Given** the verify workflow is executed
**When** one or more checks fail
**Then** the workflow completes all checks before reporting aggregate failure
**And** all individual failures are captured in the result

**Given** all verify pipeline code
**When** I run tests
**Then** tests cover: all-pass, single-failure, multiple-failures scenarios
**And** 100% coverage is maintained (NFR9)

#### Story 3.3: Feedback Accumulation & Retry Context

As an ADWS developer,
I want verify failures to accumulate as structured feedback that flows into implementation retries,
So that the implementation agent knows exactly what failed and can fix it on retry.

**Acceptance Criteria:**

**Given** a verify workflow execution that fails
**When** the engine processes the failure
**Then** structured feedback is accumulated in `WorkflowContext.feedback` (FR16)
**And** feedback includes: which tool failed, specific error messages, affected files, attempt number

**Given** accumulated feedback from previous verify attempts
**When** the engine passes context to a subsequent `/implement` retry
**Then** the full feedback history is available as explicit context (FR17)
**And** the implementation agent receives all previous failure details, not just the most recent

**Given** multiple verify-implement cycles
**When** feedback accumulates across attempts
**Then** each attempt's feedback is preserved with its attempt number
**And** feedback does not duplicate -- each cycle adds new entries

**Given** all feedback accumulation code
**When** I run tests
**Then** tests cover: single failure feedback, multi-attempt accumulation, feedback passed to retry context
**And** 100% coverage is maintained (NFR9)

---

### Epic 4: Developer Commands & TDD Workflow

Developer can invoke /implement, /verify, /build, and /prime commands. /implement executes the full TDD-enforced workflow (RED -> verify fail -> GREEN -> verify pass -> REFACTOR -> verify pass -> close). Each command has a `.md` entry point backed by a Python module.

**FRs covered:** FR28, FR29, FR30, FR31, FR32

**Notes:** FR count understates weight. FR29 (/implement) alone carries the full Decision 6 TDD workflow -- expect 5+ stories for implement_verify_close (write_failing_tests, verify_tests_fail, implement, refactor, plus orchestrating workflow definition). FR30-32 are lighter (single story each). Every io_ops SDK function must have a corresponding EUT. Must never read BMAD files during execution (NFR19) -- Beads issue description is the only contract.

#### Story 4.1: Command Pattern - .md Entry Points & Python Module Wiring

As an ADWS developer,
I want a consistent pattern for defining commands as Claude command .md files backed by Python modules,
So that every command has a natural language entry point and testable logic separated cleanly.

**Acceptance Criteria:**

**Given** the adws project structure from Epic 1
**When** I inspect the command pattern
**Then** each command has a `.md` file in the Claude commands directory as its natural language entry point
**And** each `.md` file delegates to a Python module in `adws/` for testable logic (FR28)
**And** the Python module follows the io_ops boundary pattern for any external I/O

**Given** the command pattern is established
**When** I create a new command
**Then** I follow the pattern: `.md` entry point + Python module + tests
**And** the template/pattern is documented for consistency across all commands

**Given** the command pattern
**When** I run tests
**Then** the wiring between .md entry point and Python module is verified
**And** 100% coverage is maintained (NFR9)

#### Story 4.2: /verify Command Entry Point

As an ADWS developer,
I want to invoke `/verify` to run the full local quality gate,
So that I can check code quality through a single command before pushing.

**Acceptance Criteria:**

**Given** the command pattern from Story 4.1 and the verify pipeline from Epic 3
**When** I invoke `/verify`
**Then** the command .md entry point delegates to the Python module
**And** the Python module triggers the verify workflow from Epic 3 (FR30)
**And** Jest, Playwright, mypy, and ruff checks all execute

**Given** all verify checks pass
**When** /verify completes
**Then** a success summary is displayed with results from each tool

**Given** one or more checks fail
**When** /verify completes
**Then** a structured failure report shows which tools failed and why
**And** the report is suitable for feeding into implementation retries

**Given** /verify command code
**When** I run tests
**Then** success and failure paths are covered
**And** 100% coverage is maintained (NFR9)

#### Story 4.3: /prime Command for Context Loading

As an ADWS developer,
I want to invoke `/prime` to load codebase context into a session,
So that subsequent commands operate with full awareness of the project structure and conventions.

**Acceptance Criteria:**

**Given** the command pattern from Story 4.1
**When** I invoke `/prime`
**Then** the command reads relevant project files (CLAUDE.md, architecture docs, directory structure) (FR31)
**And** context is loaded into the session for use by subsequent commands

**Given** /prime has loaded context
**When** I inspect the loaded context
**Then** it includes project structure, coding conventions, and TDD mandate
**And** it does NOT include secrets or credentials

**Given** /prime command code
**When** I run tests
**Then** context loading paths are covered
**And** 100% coverage is maintained (NFR9)

#### Story 4.4: /build Command & implement_close Workflow

As an ADWS developer,
I want to invoke `/build` for fast-track trivial changes using a simplified workflow,
So that simple tasks bypass full TDD ceremony while still meeting the 100% coverage gate.

**Acceptance Criteria:**

**Given** the command pattern from Story 4.1
**When** I invoke `/build`
**Then** it executes the `implement_close` workflow (FR32)
**And** this workflow is TDD-exempt per architecture -- 100% coverage gate is the safety net

**Given** the implement_close workflow
**When** it executes
**Then** it runs: implement (SDK step) -> verify_tests_pass -> bd close (always_run)
**And** there is no write_failing_tests or verify_tests_fail phase
**And** bd close executes via `bd` CLI (NFR17) even if implement fails (NFR3)

**Given** the implement step fails
**When** the engine processes the failure
**Then** the Beads issue remains open in a recoverable state (NFR2)
**And** bd close still runs as always_run step

**Given** /build command code
**When** I run tests
**Then** success path, failure path, and always_run behavior are covered
**And** 100% coverage is maintained (NFR9)

#### Story 4.5: write_failing_tests Step (RED Phase)

As an ADWS developer,
I want a RED phase step that writes failing tests via a dedicated test agent,
So that TDD enforcement starts with verified failing tests before any implementation.

**Acceptance Criteria:**

**Given** the step function signature from Epic 2
**When** `write_failing_tests` executes
**Then** it makes a fresh SDK call via `ClaudeSDKClient` with a test agent system prompt (Decision 6)
**And** the agent writes tests with `"""RED: <expected failure reason>"""` annotation on each test
**And** the step is a separate SDK call from the implementation step (agent-to-agent pairing)

**Given** the test agent produces tests
**When** the step completes successfully
**Then** test files are written to the project
**And** the `WorkflowContext.outputs` contains the list of test files created

**Given** write_failing_tests io_ops SDK function
**When** I inspect the test suite
**Then** an EUT exists proving real SDK communication with real API calls (EUT* constraint)
**And** unit tests with mocked io_ops exist for fast CI feedback
**And** 100% coverage is maintained (NFR9)

#### Story 4.6: verify_tests_fail Step (RED Gate)

As an ADWS developer,
I want a RED gate that confirms tests fail for the right expected reason,
So that broken tests (SyntaxError) are caught before proceeding to implementation.

**Acceptance Criteria:**

**Given** tests written by the write_failing_tests step
**When** `verify_tests_fail` executes as a shell step
**Then** it runs the test suite and confirms tests fail

**Given** tests fail with valid failure types
**When** the step evaluates failure reasons
**Then** `ImportError` and `AssertionError` are accepted as valid RED failures
**And** the step succeeds, allowing progression to GREEN phase

**Given** tests fail with invalid failure types
**When** the step evaluates failure reasons
**Then** `SyntaxError` is rejected as a broken test (not a valid RED failure)
**And** the step fails with a PipelineError explaining the tests are broken, not correctly RED

**Given** tests unexpectedly pass
**When** the step evaluates results
**Then** the step fails with a PipelineError explaining tests should fail in RED phase

**Given** verify_tests_fail code
**When** I run tests
**Then** tests cover: valid failure (ImportError), valid failure (AssertionError), invalid failure (SyntaxError), unexpected pass
**And** 100% coverage is maintained (NFR9)

#### Story 4.7: implement & refactor Steps (GREEN & REFACTOR Phases)

As an ADWS developer,
I want GREEN and REFACTOR phase steps using dedicated agent roles,
So that implementation and cleanup are separate concerns with distinct system prompts.

**Acceptance Criteria:**

**Given** the step function signature from Epic 2
**When** `implement` step executes (GREEN phase)
**Then** it makes a fresh SDK call via `ClaudeSDKClient` with an implementation agent system prompt
**And** the agent receives the Beads issue description as context (NFR19 -- never reads BMAD files)
**And** the agent receives accumulated feedback from any previous verify failures (FR17)

**Given** the step function signature
**When** `refactor` step executes (REFACTOR phase)
**Then** it makes a fresh SDK call via `ClaudeSDKClient` with a refactor agent system prompt (Decision 6)
**And** the agent focuses on cleanup without changing behavior

**Given** both SDK steps
**When** I inspect the test suite
**Then** EUTs exist for both io_ops SDK functions proving real API communication (EUT* constraint)
**And** unit tests with mocked io_ops exist for fast CI feedback
**And** 100% coverage is maintained (NFR9)

#### Story 4.8: implement_verify_close Workflow & /implement Command

As an ADWS developer,
I want the full TDD-enforced workflow orchestrating all phases and the /implement command to invoke it,
So that every implementation follows RED -> GREEN -> REFACTOR with automated verification gates.

**Acceptance Criteria:**

**Given** all TDD steps from Stories 4.5-4.7 and the verify pipeline from Epic 3
**When** I inspect the `implement_verify_close` workflow definition
**Then** it composes: write_failing_tests -> verify_tests_fail -> implement -> verify_tests_pass -> refactor -> verify_tests_pass -> bd close
**And** bd close is marked `always_run=True` (NFR3)
**And** the workflow is declarative data, not imperative code

**Given** the /implement command is invoked with a Beads issue
**When** the command executes
**Then** it reads the Beads issue description via `bd` CLI (NFR17)
**And** it passes the description as context to the TDD workflow
**And** it never reads BMAD files directly (NFR19)

**Given** the full TDD workflow executes successfully
**When** all phases complete (RED -> verify fail -> GREEN -> verify pass -> REFACTOR -> verify pass)
**Then** `bd close` closes the Beads issue
**And** the workflow result indicates success

**Given** any phase fails after retries are exhausted
**When** the engine processes the failure
**Then** the Beads issue remains open in a recoverable state with failure context logged (NFR2)
**And** bd close still executes as always_run (NFR3)
**And** accumulated feedback is preserved for manual retry

**Given** implement_verify_close workflow code
**When** I run tests
**Then** tests cover: full success path, RED failure (bad tests), GREEN failure (implementation fails), REFACTOR failure, always_run bd close after failure
**And** 100% coverage is maintained (NFR9)

---

### Epic 5: Observability & Safety Hooks

System provides audit trail of all agent activity (hook events, file tracking, context bundles) and blocks dangerous commands with logged audit and safer alternatives. Developer can reload session context via /load_bundle.

**FRs covered:** FR33, FR34, FR35, FR36, FR37, FR38, FR39, FR40

**Notes:** Track B -- implementable alongside Epic 2+. Zero engine dependency. Contains two independent sub-tracks: **Observability** (FR33-36: event logging, file tracking, context bundles, shared hook modules) and **Safety** (FR37-40: command blocker, audit logging, safer alternatives, shared safety modules). Neither sub-track depends on the other. Fail-open design (NFR4). Deliverables include both the Python modules in `adws/` AND the `.claude/hooks/*.sh` shim scripts that wire CLI hook entry points to those modules (NFR20).

#### Story 5.1: Hook Event Logger Module & CLI/SDK Wiring

As an ADWS developer,
I want all hook events logged to session-specific JSONL files via a shared module,
So that I have a complete audit trail of agent activity accessible from both CLI hooks and SDK engine.

**Acceptance Criteria:**

**Given** a hook event occurs (any hook type)
**When** the event logger processes it
**Then** a JSONL entry is written to a session-specific file in `agents/hook_logs/` (FR33)
**And** the entry includes timestamp, event type, hook name, and relevant payload data

**Given** the event logger Python module in `adws/`
**When** I inspect the CLI hook wiring
**Then** `.claude/hooks/hook_logger.sh` delegates to the Python module via `uv run python -m adws.hooks.event_logger`
**And** the shim contains no standalone logic -- all logic is in the Python module (NFR20)

**Given** the same event logger module
**When** used by the SDK engine via HookMatcher
**Then** the HookMatcher calls the same Python module with zero duplicated logic (FR36)

**Given** the event logger encounters an error
**When** it fails to write a log entry
**Then** it logs the error to stderr and does NOT block the operation being observed (NFR4)

**Given** all event logger code
**When** I run tests
**Then** tests cover: successful logging, session-specific file creation, fail-open behavior, CLI and SDK entry points
**And** 100% coverage is maintained (NFR9)

#### Story 5.2: File Tracker & Context Bundles

As an ADWS developer,
I want files read and written during sessions tracked to context bundles,
So that session activity can be replayed and context can be restored later.

**Acceptance Criteria:**

**Given** a file is read or written during a session
**When** the file tracker processes the event
**Then** the file path and operation type are recorded in a session-specific bundle in `agents/context_bundles/` (FR34)

**Given** the file tracker Python module
**When** used by CLI hooks and SDK HookMatchers
**Then** both entry points use the same underlying module with zero duplicated logic (FR36)

**Given** the file tracker encounters an error
**When** it fails to record a file operation
**Then** it logs to stderr and does NOT block the observed operation (NFR4)

**Given** all file tracker code
**When** I run tests
**Then** tests cover: read tracking, write tracking, session-specific bundling, fail-open behavior
**And** 100% coverage is maintained (NFR9)

#### Story 5.3: /load_bundle Command

As an ADWS developer,
I want to invoke `/load_bundle` to reload context from a previous session,
So that I can resume work with full awareness of what was done in a prior session.

**Acceptance Criteria:**

**Given** a context bundle exists from a previous session in `agents/context_bundles/`
**When** I invoke `/load_bundle`
**Then** the command reads the bundle and loads file context into the current session (FR35)
**And** the command follows the .md entry point + Python module pattern from Epic 4 (FR28)

**Given** the specified bundle does not exist
**When** /load_bundle is invoked
**Then** a clear error message indicates the bundle was not found
**And** available bundles are listed for the user to choose from

**Given** /load_bundle command code
**When** I run tests
**Then** tests cover: successful load, missing bundle, bundle listing
**And** 100% coverage is maintained (NFR9)

#### Story 5.4: Dangerous Command Blocker with Audit Logging

As an ADWS developer,
I want dangerous bash commands blocked with audit logging and safer alternatives,
So that destructive operations are prevented and all block events are traceable.

**Acceptance Criteria:**

**Given** a bash command is about to execute
**When** it matches a known destructive pattern (e.g., `rm -rf /`, `git push --force`) (FR37)
**Then** the command is blocked and does NOT execute
**And** a safer alternative is suggested to the user (FR39)

**Given** a command is blocked
**When** the blocker logs the event
**Then** an entry is written to `agents/security_logs/` with timestamp, the blocked command, and the reason for blocking (FR38, NFR15)

**Given** the blocker regex pattern set
**When** tested against all known destructive patterns
**Then** zero false negatives occur -- every defined pattern is caught (NFR14)

**Given** the safety Python module in `adws/`
**When** used by CLI hooks
**Then** `.claude/hooks/command_blocker.sh` delegates to the Python module with no standalone logic (NFR20)
**And** the SDK HookMatcher uses the same module with zero duplicated logic (FR40)

**Given** the blocker encounters an internal error
**When** it fails to evaluate a command
**Then** it logs to stderr and does NOT block the command (NFR4 -- fail-open)

**Given** all command blocker code
**When** I run tests
**Then** tests cover: known destructive patterns blocked, safe commands allowed, alternative suggestions, audit log entries, fail-open on internal error, CLI and SDK entry points
**And** 100% coverage is maintained (NFR9)

---

### Epic 6: BMAD-to-Beads Story Converter

Developer can convert BMAD stories to Beads issues via /convert-stories-to-beads, embedding workflow tags for dispatch and writing beads_id back into source BMAD files for tracking.

**FRs covered:** FR23, FR24, FR25, FR26, FR27

**Notes:** Track B -- depends on Epic 1 only. Uses workflow name registry from scaffold (not Tier 1 types) to embed valid `{workflow_name}` tags. Interacts with Beads exclusively via `bd` CLI (NFR17). Respects NFR19 boundary -- BMAD files read only during conversion, never during execution.

#### Story 6.1: BMAD Markdown Parser

As an ADWS developer,
I want to parse BMAD epic/story markdown files and extract structured story content,
So that the converter can create Beads issues from planning artifacts.

**Acceptance Criteria:**

**Given** a BMAD epic markdown file with stories
**When** the parser processes it
**Then** it extracts each story's title, user story (As a/I want/So that), and acceptance criteria (FR24)
**And** it extracts story metadata (epic number, story number, FRs covered)

**Given** a BMAD file with multiple epics and stories
**When** the parser processes it
**Then** all stories are extracted with correct epic-to-story relationships
**And** no story content is lost or truncated

**Given** a malformed or incomplete BMAD file
**When** the parser encounters an error
**Then** it returns a clear PipelineError identifying what was unparseable and where

**Given** all parser code
**When** I run tests
**Then** tests cover: single story, multiple stories, multiple epics, malformed input, edge cases (empty AC, missing fields)
**And** 100% coverage is maintained (NFR9)

#### Story 6.2: Beads Issue Creator with Workflow Tags

As an ADWS developer,
I want to create Beads issues from parsed story content with embedded workflow tags,
So that each issue is ready for automated dispatch.

**Acceptance Criteria:**

**Given** parsed story content from Story 6.1
**When** the creator generates a Beads issue
**Then** it calls `bd create` via io_ops shell function (NFR17 -- Beads via bd CLI only)
**And** the entire story content is the issue description (FR25)
**And** a `{workflow_name}` tag is embedded in the description using the workflow name registry from Epic 1 (FR26)

**Given** the workflow name registry
**When** the creator embeds a workflow tag
**Then** only valid workflow names from the registry are used
**And** invalid or missing workflow names produce a clear PipelineError

**Given** `bd create` succeeds
**When** the issue is created
**Then** the returned Beads issue ID is captured for bidirectional tracking

**Given** `bd create` fails
**When** the creator processes the error
**Then** a PipelineError propagates with the bd CLI error details

**Given** all creator code
**When** I run tests
**Then** tests cover: successful creation, workflow tag embedding, invalid workflow name, bd CLI failure
**And** 100% coverage is maintained (NFR9)

#### Story 6.3: Bidirectional Tracking & /convert-stories-to-beads Command

As an ADWS developer,
I want beads_id written back into source BMAD files and a command to orchestrate the full conversion,
So that planning artifacts stay linked to execution issues and I can convert stories with a single command.

**Acceptance Criteria:**

**Given** a Beads issue is created from a BMAD story
**When** the tracker processes the result
**Then** `beads_id` is written back into the source BMAD story file (FR27)
**And** the original story content is preserved -- only the beads_id field is added

**Given** the /convert-stories-to-beads command is invoked
**When** it executes
**Then** the command .md entry point delegates to the Python module (FR23)
**And** the full flow runs: parse BMAD markdown -> create Beads issues -> embed workflow tags -> write beads_id back
**And** progress is reported for each story processed

**Given** a story already has a beads_id
**When** conversion runs on it
**Then** it skips the story (idempotent -- no duplicate issues created)

**Given** conversion of multiple stories
**When** one story fails to convert
**Then** the failure is reported but remaining stories continue processing
**And** successfully converted stories have their beads_id written back

**Given** all conversion code
**When** I run tests
**Then** tests cover: full conversion flow, beads_id writeback, idempotent skip, partial failure handling
**And** 100% coverage is maintained (NFR9)

---

### Epic 7: Automated Dispatch & Cron Trigger

System autonomously polls Beads for open issues with workflow tags, dispatches the appropriate workflow, executes it, and closes the issue on success -- zero manual intervention.

**FRs covered:** FR18, FR19, FR20, FR21, FR22

**Notes:** Capstone. Dispatch mechanism: `load_workflow()` pure lookup + policy enforcement in `adw_dispatch.py` per Decision 5. `dispatchable` flag on Workflow dataclass gates which workflows the cron trigger can invoke. Interacts with Beads exclusively via `bd` CLI (NFR17). Must never read BMAD files during execution (NFR19).

#### Story 7.1: Issue Tag Extraction & Workflow Dispatch

As an ADWS developer,
I want the engine to extract workflow tags from Beads issues and dispatch the correct workflow,
So that issues are automatically routed to the right execution pipeline.

**Acceptance Criteria:**

**Given** a Beads issue ID
**When** the engine receives it
**Then** it reads the issue description via `bd show` through io_ops (NFR17 -- Beads via bd CLI only) (FR18)
**And** it extracts the `{workflow_name}` tag from the description

**Given** an extracted workflow tag
**When** `load_workflow()` performs lookup
**Then** it returns the matching Workflow definition as pure data (Decision 5)
**And** `adw_dispatch.py` enforces the `dispatchable` flag policy (FR19)

**Given** a non-dispatchable workflow tag
**When** dispatch policy is evaluated
**Then** the dispatch is rejected with a clear PipelineError explaining the workflow is not dispatchable

**Given** a workflow tag that doesn't match any registered workflow
**When** lookup is performed
**Then** a PipelineError propagates with the unknown tag and available workflow names

**Given** the engine processes a Beads issue
**When** executing the dispatch
**Then** it never reads BMAD files directly -- the Beads issue description is the only contract (NFR19)

**Given** all dispatch code
**When** I run tests
**Then** tests cover: successful extraction and dispatch, non-dispatchable rejection, unknown tag, missing tag in description
**And** 100% coverage is maintained (NFR9)

#### Story 7.2: Workflow Execution & Issue Closure

As an ADWS developer,
I want dispatched workflows to execute through the engine and close their Beads issue on success,
So that completed work is automatically tracked without manual intervention.

**Acceptance Criteria:**

**Given** a dispatched workflow from Story 7.1
**When** the engine executes it
**Then** the full workflow runs through the engine with ROP error handling (NFR1)
**And** context propagation, retry logic, and always_run steps function as defined in Epic 2

**Given** workflow execution succeeds
**When** the engine processes the result
**Then** `bd close` is called via io_ops to close the Beads issue (FR20, NFR17)
**And** the closure includes a success summary in the close reason

**Given** workflow execution fails after retries are exhausted
**When** the engine processes the failure
**Then** the Beads issue remains open in a recoverable state (NFR2)
**And** failure context is logged to the issue (step name, error details, attempt count)
**And** `bd close` still executes as `always_run` but with failure context rather than success (NFR3)

**Given** all execution and closure code
**When** I run tests
**Then** tests cover: successful execution and close, failure with recoverable state, always_run after failure
**And** 100% coverage is maintained (NFR9)

#### Story 7.3: Cron Trigger - Polling & Autonomous Execution

As an ADWS developer,
I want a cron trigger that polls Beads for ready issues and executes workflows autonomously,
So that routine work is processed without manual intervention.

**Acceptance Criteria:**

**Given** the cron trigger is running
**When** it polls Beads
**Then** it calls `bd list --status=open` via io_ops to find open issues (FR21, NFR17)
**And** it filters issues to those containing `{workflow_name}` tags matching dispatchable workflows

**Given** one or more ready issues are found
**When** the trigger processes them
**Then** it dispatches and executes each workflow without manual intervention (FR22)
**And** it uses the dispatch mechanism from Story 7.1 and execution from Story 7.2

**Given** no ready issues are found
**When** the trigger completes a poll cycle
**Then** it sleeps until the next poll interval and re-polls

**Given** the trigger encounters an error during polling
**When** it processes the error
**Then** it logs the error and continues to the next poll cycle (does not crash)
**And** affected issues remain in their current state for the next cycle

**Given** multiple ready issues exist
**When** the trigger processes them
**Then** issues are processed sequentially (one at a time) to avoid resource contention
**And** a failure on one issue does not prevent processing of subsequent issues

**Given** all cron trigger code
**When** I run tests
**Then** tests cover: successful poll and dispatch, no ready issues, poll error recovery, multi-issue sequential processing, single issue failure isolation
**And** 100% coverage is maintained (NFR9)

---

### Dependency & Parallelism Map

| Epic | FRs | Count | Dependencies | Track |
|------|-----|-------|-------------|-------|
| 1: Foundation | FR41-45 | 5 | None | Base |
| 2: Engine & Types | FR1-11 | 11 | Epic 1 | Track A |
| 3: Verify Pipeline | FR12-17 | 6 | Epics 1+2 | Track A |
| 4: Commands & TDD | FR28-32 | 5 | Epics 1+2+3 | Track A |
| 5: Hooks | FR33-40 | 8 | Epic 1 | Track B |
| 6: Converter | FR23-27 | 5 | Epic 1 | Track B |
| 7: Dispatch | FR18-22 | 5 | Epics 1+2+3+4 | Track A |
| **Total** | | **45** | | |

**Track A** (Core Pipeline): 1 -> 2 -> 3 -> 4 -> 7
**Track B** (Parallel): 1 -> {5, 6} *(implementable alongside Track A epics)*

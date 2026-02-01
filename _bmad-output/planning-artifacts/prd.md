---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments: ['_bmad-output/brainstorming/brainstorming-session-2026-01-31.md', 'README.md', 'HANDOVER.md', 'AGENTS.md']
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 1
  projectDocs: 3
workflowType: 'prd'
classification:
  projectType: 'Developer Tool'
  domain: 'General'
  complexity: 'Medium'
  projectContext: 'brownfield'
---

# Product Requirements Document - Agentic Layer (ADWS + BMAD + Beads Integration)

**Author:** Chad
**Date:** 2026-01-31

## Executive Summary

The Agentic Layer is a Python-based developer workflow engine that automates the implement → verify → close cycle for software development tasks. It ports and evolves the ADWS (Agentic Developer Workflow System) from agentic-ai-cli-example into the tab-groups-windows-list project, integrating cleanly with BMAD (planning) and Beads (issue tracking).

**Differentiator:** One-directional flow from planning to execution -- `BMAD (planning) → Beads (tracking) → ADWS (execution)` -- with a novel BMAD-to-Beads bridge that neither system provides natively. The engine uses native `claude-agent-sdk` calls (not CLI subprocess wrapping) with fresh SDK calls per step and accumulated feedback for explicit context control.

**Two Permanent Layers:**
- **Agentic Layer** (this PRD) -- the system that builds and maintains the system
- **Application Layer** -- the Chrome extension itself

Both layers co-evolve indefinitely. The agentic layer modifies the application layer through automated workflows.

## Project Classification

- **Project Type:** Developer Tool (SDK-based agentic workflow engine)
- **Domain:** General (developer productivity tooling)
- **Complexity:** Medium
- **Project Context:** Brownfield (adding agentic layer to existing Chrome extension project)

## Zero Touch Engineering Principle

**CORE GUIDING PRINCIPLE:** The agentic system operates autonomously. The human reviews successful outcomes and resolves only problems that AI agents cannot resolve after exhausting automated recovery. All workflows, dispatch logic, failure handling, and agent prompts must be designed to minimize human intervention.

**Human involvement is limited to:**
- Reviewing successfully completed work (code review, acceptance)
- Resolving problems that AI agents have failed to solve after tiered automated recovery
- Strategic decisions (planning, prioritization, architecture changes)

**Human is NOT involved in:**
- Routine workflow dispatch or monitoring
- Transient failure recovery (automatic retry with backoff)
- Failure triage for classifiable error patterns (AI triage agent handles this)
- Re-opening or re-dispatching failed issues (automated triage handles this)

This principle must be reflected in all workflow designs, agent system prompts, dispatch logic, and documentation.

## Success Criteria

### User Success

The "user" is the developer operating the agentic layer:
- Beads issues dispatched automatically via cron trigger -- no manual workflow invocation needed
- `implement_verify_close` loop runs to completion without intervention on well-scoped stories
- BMAD stories convert cleanly to Beads issues via `/convert-stories-to-beads` with `beads_id` tracked back in BMAD files
- `/verify` catches real failures (test, lint, e2e) before declaring completion
- Observability logs are useful for debugging failed runs, not noise

### Technical Success

- All ADWS Python code is type-safe, linted, and tested with 100% coverage in CI
- ROP patterns enforced at engine layer; workflow authors never see `IOResult`
- Zero duplicated logic -- CLI hooks and SDK HookMatchers share the same `adws/` Python modules
- One-directional flow enforced: BMAD → Beads → ADWS (no bidirectional dependencies)
- Native `claude-agent-sdk` calls (no CLI subprocess wrapping)
- Fresh SDK calls per step with accumulated feedback (explicit context control)
- Fully reproducible builds across all toolchains (see Dependency Management & Reproducibility)

### Measurable Outcomes

- `bd doctor` runs clean
- `uv run pytest` passes with full coverage on all `adws/` code
- `npm test` + `npm run test:e2e` + Python linting all pass in CI
- At least 2 workflows operational: `implement_verify_close` and `implement_close`
- Dangerous command blocker blocks known destructive patterns and logs them

## Product Scope & Phased Development

### MVP Strategy

**MVP Approach:** Problem-Solving MVP -- the minimum agentic infrastructure that enables end-to-end automated workflow execution on a single Beads issue. If `implement_verify_close` can pick up one issue, implement it, verify it passes tests, and close it, the core value is proven.

**Resource Requirements:** Single developer (Chad) + Claude Code/SDK.

### Phase 1: MVP (P0-P1)

**Core Journeys Supported:** J1 (dispatch work), J2 (verify catches failure), J4 (add a workflow)

**Must-Have Capabilities:**
1. `adws/` directory scaffold with `pyproject.toml`, `uv.lock`, `mise.toml` -- all dependencies pinned to exact versions
2. Core engine with ROP: types, executor, combinators, steps, error hierarchy
3. SDK-native step execution via `ClaudeSDKClient`
4. `/implement` and `/verify` commands (dual-layer: `.md` + Python)
5. `implement_verify_close` and `implement_close` workflow definitions
6. `/verify` running full local quality gate
7. Beads initialized (`bd doctor` clean)
8. CI pipeline extended for Python (pytest + linting alongside existing JS pipeline)

**Explicitly NOT in MVP:**
- BMAD-to-Beads converter (manual `bd create` is fine)
- Cron trigger (manual `adw_dispatch.py` invocation is fine)
- Observability hooks and safety modules
- `/load_bundle`, `/prime`, `/build` commands

### Phase 2: Integration Bridge (P2)

- `/convert-stories-to-beads` command + Python module
- `adw_dispatch.py` adapted for SDK
- `adw_trigger_cron.py` for automated polling
- `/prime` and `/build` commands

### Phase 3: Observability, Safety, Docs (P3-P4)

- Unified observability (`adws/observability/`) with shared modules for CLI hooks and SDK HookMatchers
- Dangerous command blocker (`adws/safety/`)
- `/load_bundle` command
- Comprehensive documentation

### Risk Mitigation

**Technical Risks:**
- `claude-agent-sdk` is relatively new -- mitigated by mocking at SDK boundary for all tests, allowing swap if needed
- ROP learning curve -- mitigated by strict two-tier separation; workflow authors never see ROP types
- Dual-toolchain CI complexity -- mitigated by `mise.toml` pinning exact runtime versions, `uv.lock` + `package-lock.json` for deterministic installs

**Reproducibility Risks:**
- Floating dependencies causing CI/local drift -- mitigated by zero tolerance for unpinned versions, `npm ci` in CI (not `npm install`), `uv sync --frozen` in CI
- Runtime version mismatches -- mitigated by `mise.toml` as single source of truth for Python/Node.js versions

**Resource Risks:**
- Single developer -- mitigated by keeping MVP minimal, leveraging the agentic layer itself to accelerate development once bootstrapped
- If blocked on SDK issues, can fall back to subprocess CLI calls temporarily (the source project already works this way)

## User Journeys

### Journey 1: Developer Plans and Dispatches Work (Happy Path)

Chad has a new feature to add to the Chrome extension. He runs BMAD planning workflows to produce epics and stories. Once stories are ready, he runs `/convert-stories-to-beads`, which parses the BMAD story markdown, creates Beads issues with the full story as description (including `{implement_verify_close}` workflow tag), and writes `beads_id` back into the BMAD file. The cron trigger picks up the issue, dispatches `implement_verify_close`, the engine runs `/implement` → `/verify` (with retry loop on failure, accumulating feedback) → `bd close`. Chad reviews the commit and moves on.

**Capabilities revealed:** BMAD-to-Beads converter, cron trigger, workflow dispatch, implement/verify loop, automatic close.

### Journey 2: Verify Loop Catches a Failure (Edge Case)

The engine runs `/implement` on a Beads issue. The `/verify` step runs `npm test` and a test fails. The engine captures the failure output, adds it to `WorkflowContext.feedback`, and retries `/implement` with the accumulated feedback as explicit context. On the second attempt, the implementation passes all tests. The workflow closes the issue.

If all 3 attempts fail, the workflow exits with a `PipelineError`, the issue remains open in Beads, and observability logs capture the full failure chain for Chad to debug manually.

**Capabilities revealed:** Accumulated feedback, fresh SDK calls per retry, quality gate (`npm test`, `npm run test:e2e`, Python linting), failure logging, graceful degradation.

### Journey 3: Developer Works Interactively (Manual Session)

Chad opens a Claude Code session to work on something hands-on. The CLI hooks fire: the universal hook logger captures all tool calls to `agents/hook_logs/`, and the context bundle builder tracks files read/written to `agents/context_bundles/`. The dangerous command blocker intercepts any `rm -rf /` attempts. All hooks use the same shared Python modules in `adws/` that the SDK engine uses -- zero duplicated logic. If the session crashes, Chad can run `/load_bundle` in a new session to reload context from the bundle.

**Capabilities revealed:** CLI hook shims, shared observability modules, dangerous command blocker, `/load_bundle` command, `agents/` directory structure.

### Journey 4: Developer Adds a New Workflow

Chad needs a new workflow pattern (e.g., `implement_close` for trivial config changes). He creates a declarative `Workflow` definition in `adws/workflows/` using `Step` and optional combinators like `with_verification`. He never touches ROP types -- that's the engine's job. He writes tests that mock at the I/O boundary (`io_ops.py`). The workflow is automatically discoverable by `adw_dispatch.py`.

**Capabilities revealed:** Two-tier architecture (workflow vs engine), declarative Step/Workflow API, combinator library, single mock point, workflow discovery.

### Journey 5: CI Enforces Quality (System Actor)

A PR is pushed. CI runs `npm test` (Jest, 100% coverage), `npm run test:e2e` (Playwright), and `uv run pytest` (ADWS Python tests with coverage) plus Python linting/type checking. Both layers -- application and agentic -- are validated in the same pipeline. A failure in either blocks the merge.

**Capabilities revealed:** Dual-layer CI, Python toolchain alongside JS toolchain, unified quality gate.

### Journey Requirements Summary

| Capability Area | Journeys |
|---|---|
| BMAD-to-Beads converter | J1 |
| Cron trigger + dispatch | J1, J2 |
| SDK-native engine execution | J1, J2, J4 |
| Implement/verify loop with feedback | J1, J2 |
| Full local quality gate | J2, J5 |
| CLI hook observability | J3 |
| Dangerous command blocker | J3 |
| Context bundle / load_bundle | J3 |
| Declarative workflow API | J4 |
| Dual-layer CI pipeline | J5 |

## Developer Tool Specific Requirements

### Dependency Management & Reproducibility

**CRITICAL REQUIREMENT:** All dependencies across all toolchains MUST be pinned to exact versions with lockfiles committed to source control. No floating versions, no range specifiers, no `^` or `~` prefixes. Every build -- local dev, CI, fresh clone -- MUST produce identical dependency trees.

| Toolchain | Config File | Lockfile | Version Strategy |
|---|---|---|---|
| Python (ADWS) | `pyproject.toml` | `uv.lock` | Exact pins, lockfile committed |
| JavaScript (App) | `package.json` | `package-lock.json` | Exact pins, lockfile committed |
| Runtime versions | `mise.toml` | N/A (pinned in file) | Exact Node.js, Python, uv versions |
| Pre-commit / linting | `pyproject.toml` | Via uv.lock | Tool versions locked |

- `uv lock` and `npm ci` (not `npm install`) in CI
- `mise.toml` pins exact runtime versions (Python 3.11.x, Node.js x.y.z)
- Renovate/Dependabot updates go through PR + CI, never auto-merged without green checks
- No `requirements.txt` with unpinned versions -- `uv.lock` is the single source of truth for Python

### Language & Runtime Matrix

| Layer | Language | Runtime | Package Manager |
|---|---|---|---|
| ADWS Engine | Python 3.11+ | uv | pip/uv (`pyproject.toml` + `uv.lock`) |
| Application | JavaScript/TypeScript | Node.js | npm (`package.json` + `package-lock.json`) |
| Commands | Markdown (`.md`) + Python | Claude Code + uv | N/A |
| Runtime Versions | N/A | mise | `mise.toml` (pinned) |

### API Surface (Workflow Author Interface)

The public API is deliberately minimal (Tier 1 -- domain intent):
- `Workflow(name, description, steps)` -- declarative workflow definition
- `Step(command, output, input_from, shell, always_run, retry, when)` -- step definition
- `WorkflowContext` -- immutable context passed between steps
- `with_verification(implement, verify, max_attempts)` -- combinator for implement/verify loops
- `run_workflow(workflow, context)` -- execution entry point

ROP types (`IOResult`, `PipelineError`, `bind`, `flow`) are Tier 2 internals -- never exposed to workflow authors.

### Migration Guide (from agentic-ai-cli-example)

| Source Component | Target | Change |
|---|---|---|
| `adws/adw_modules/engine/` | `adws/engine/` | Restructure, add SDK types |
| `adws/adw_modules/steps/` | `adws/steps/` | Replace subprocess calls with SDK |
| `agent.py` (subprocess) | SDK `ClaudeSDKClient` | Full rewrite to native SDK |
| `workflows/*.py` | `adws/workflows/` | Drop `/plan` and `/chore` workflows |
| `.claude/commands/*.md` | `.claude/commands/*.md` | Port `/implement`, `/verify`, `/prime`, `/build` |
| N/A (new) | `adws/observability/` | Port from elite-context-engineering |
| N/A (new) | `adws/safety/` | Port dangerous command blocker |
| N/A (new) | `/convert-stories-to-beads` | Novel bridge (no source equivalent) |

## Functional Requirements

### Workflow Execution

- FR1: Engine can execute a workflow as a sequence of steps with ROP-based error handling
- FR2: Engine can execute each step as a fresh SDK call via `ClaudeSDKClient`
- FR3: Engine can propagate context (outputs/inputs) between sequential steps
- FR4: Engine can halt on step failure and propagate `PipelineError` with structured details
- FR5: Engine can execute `always_run` steps even after previous step failures
- FR6: Engine can retry failed steps with configurable `max_attempts` and delay

### Workflow Definition

- FR7: Developer can define workflows declaratively using `Workflow` and `Step` types without ROP knowledge
- FR8: Developer can compose workflows using combinators (`with_verification`, `sequence`)
- FR9: Developer can define conditional steps that execute based on context predicates
- FR10: Developer can define data flow between steps via `output`/`input_from` parameters
- FR11: Developer can mark steps as shell commands for direct subprocess execution

### Quality Verification

- FR12: Engine can run `/verify` to execute the full local quality gate
- FR13: Verify step can run `npm test` (Jest unit tests)
- FR14: Verify step can run `npm run test:e2e` (Playwright end-to-end tests)
- FR15: Verify step can run Python linting and type checking on `adws/` code
- FR16: Engine can accumulate feedback from all failed verify attempts in `WorkflowContext.feedback`
- FR17: Engine can pass accumulated feedback as explicit context to subsequent `/implement` retries

### Issue Integration

- FR18: Engine can receive a Beads issue ID and extract the workflow tag from its description
- FR19: Engine can dispatch the appropriate workflow based on the extracted workflow tag
- FR20: Engine can close a Beads issue upon successful workflow completion via `bd close --reason`
- FR21: Cron trigger can poll Beads for open issues with workflow tags ready for dispatch, excluding issues with active failure metadata
- FR22: Cron trigger can execute dispatched workflows without manual intervention

### Autonomous Failure Recovery

- FR46: Finalize step (always_run) closes issues on success via `bd close --reason` or tags with structured failure metadata on failure via `bd update --notes`
- FR47: Cron trigger dispatch guard skips issues with active failure metadata (structured `ADWS_FAILED` notes)
- FR48: Triage workflow reviews failed issues with tiered escalation: Tier 1 (automatic retry with exponential backoff), Tier 2 (AI triage agent analyzes and adjusts), Tier 3 (human escalation only after automated recovery is exhausted)

### BMAD-to-Beads Bridge

- FR23: Developer can convert BMAD stories to Beads issues via `/convert-stories-to-beads`
- FR24: Converter can parse BMAD epic/story markdown and extract full story content
- FR25: Converter can create Beads issues with the entire story as issue description
- FR26: Converter can embed `{workflow_name}` tag in the Beads issue description for dispatch
- FR27: Converter can write `beads_id` back into the source BMAD story file for tracking

### Commands (Dual-Layer Pattern)

- FR28: Each command exists as a Claude command `.md` (natural language entry point) backed by a Python module in `adws/` (testable logic)
- FR29: Developer can invoke `/implement` to execute implementation from a Beads issue description
- FR30: Developer can invoke `/verify` to run the full local quality gate
- FR31: Developer can invoke `/prime` to load codebase context into a session
- FR32: Developer can invoke `/build` for fast-track trivial changes

### Observability

- FR33: System can log all hook events to session-specific JSONL files in `agents/hook_logs/`
- FR34: System can track files read/written during sessions to `agents/context_bundles/`
- FR35: Developer can reload previous session context via `/load_bundle`
- FR36: CLI hooks and SDK HookMatchers share the same underlying Python modules in `adws/observability/` with zero duplicated logic

### Safety

- FR37: System can block dangerous bash commands matching known destructive patterns (e.g., `rm -rf /`)
- FR38: System can log blocked commands to `agents/security_logs/` for audit
- FR39: System can suggest safer alternatives for blocked commands
- FR40: Safety module serves both CLI hooks (interactive) and SDK HookMatchers (engine) via shared code

### Developer Environment & Reproducibility

- FR41: All Python dependencies are installed reproducibly via `uv` with exact versions in `uv.lock`
- FR42: All JS dependencies are installed reproducibly via `npm ci` with exact versions in `package-lock.json`
- FR43: Runtime versions (Python, Node.js) are pinned in `mise.toml`
- FR44: CI validates both Python and JS codebases in a unified pipeline
- FR45: Developer can run all quality checks locally before pushing to CI

## Non-Functional Requirements

### Reliability

- NFR1: Engine must handle step failures gracefully via ROP -- no uncaught exceptions, no partial state corruption
- NFR2: Failed workflows must leave Beads issues in a recoverable state: open with structured failure metadata (`ADWS_FAILED` notes including attempt count, error classification, and failure summary). Issues remain dispatchable only after automated triage clears them for retry.
- NFR3: `always_run` steps (e.g., `finalize`) must execute even after upstream failures
- NFR4: Hook failures (observability, safety) must not block the operation they're observing -- fail-open with stderr logging

### Reproducibility

- NFR5: `uv sync --frozen` must succeed on any machine with the correct Python version -- zero network-dependent resolution
- NFR6: `npm ci` must produce identical `node_modules/` on any machine with the correct Node.js version
- NFR7: `mise.toml` must be the single source of truth for all runtime versions
- NFR8: CI and local dev environments must produce identical test results given the same code -- no environment-dependent flakiness

### Testability

- NFR9: All `adws/` Python code must have 100% test coverage measured by pytest-cov
- NFR10: All I/O operations must be isolated behind `io_ops.py` boundary -- single mock point for all tests
- NFR11: All Python code must pass mypy type checking with strict mode
- NFR12: All Python code must pass ruff linting with no suppressions
- NFR13: Workflow definitions (Tier 1) must be testable without mocking ROP internals

### Security

- NFR14: Dangerous command blocker must block all patterns in the defined regex set with zero false negatives on known patterns
- NFR15: All blocked commands must be logged to `agents/security_logs/` with timestamp, command, and reason
- NFR16: No credentials, API keys, or secrets may be committed to source control -- `.gitignore` must cover all sensitive patterns

### Integration

- NFR17: ADWS must interact with Beads exclusively via `bd` CLI commands -- no direct file manipulation of `.beads/` internals
- NFR18: ADWS must interact with Claude exclusively via `claude-agent-sdk` Python API -- no subprocess CLI wrapping
- NFR19: ADWS must never read BMAD files directly -- the Beads issue description (containing the converted BMAD story) is the only contract
- NFR20: All hook entry points (CLI shims in `.claude/hooks/`) must delegate to shared `adws/` Python modules -- no standalone logic in hook scripts

### Autonomy

- NFR21: The cron trigger must never dispatch an issue with active failure metadata. A separate triage workflow governs retry eligibility, clearing failure metadata only after appropriate cooldown or AI triage analysis.
- NFR22: All workflow agent system prompts must be designed for autonomous operation -- agents must not request human input during execution. Failures propagate as structured data for automated recovery, not as questions for the human.

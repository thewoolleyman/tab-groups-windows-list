# ADWS - Agentic Developer Workflow System

> **CRITICAL BOUNDARY: This directory is the AGENTIC LAYER ONLY.**
>
> `adws/` contains the workflow engine, pipeline steps, execution infrastructure,
> and everything needed to orchestrate AI-driven development workflows.
>
> **Application code DOES NOT belong here.** Features like native messaging hosts,
> browser detection, UI components, or Chrome extension logic belong in the
> APPLICATION LAYER (project root: `popup.js`, `background.js`, `native-host/`, `tests/`).
>
> See [AGENTIC_VS_APPLICATION.md](../AGENTIC_VS_APPLICATION.md) for the
> complete boundary definition.

## Architecture Overview

```
adws/                           # AGENTIC LAYER (this directory)
+-- adw_modules/                # Core infrastructure
|   +-- engine/                 # Workflow execution engine (ROP)
|   +-- steps/                  # Pipeline step implementations
|   +-- commands/               # CLI command entry points
|   +-- hooks/                  # Event logging, file tracking, safety
|   +-- io_ops.py               # I/O boundary layer (single mock point)
|   +-- errors.py               # Domain error types
|   +-- types.py                # Shared type definitions
+-- workflows/                  # Declarative workflow definitions
+-- tests/                      # Agentic layer test suite
+-- adw_dispatch.py             # Workflow dispatcher
+-- adw_triage.py               # Self-healing failure recovery
+-- adw_trigger_cron.py         # Beads cron trigger
```

## Running ADWS Scripts

The three top-level Python scripts are directly executable with `uv run`.
Wrapper scripts under `scripts/` provide convenient aliases.

### Cron Trigger (`adw_trigger_cron.py`)

Polls Beads for ready issues and dispatches workflows autonomously.

```bash
uv run adws/adw_trigger_cron.py --dry-run              # Preview ready issues
uv run adws/adw_trigger_cron.py                        # Run one poll cycle
uv run adws/adw_trigger_cron.py --poll                 # Continuous polling (60s)
uv run adws/adw_trigger_cron.py --poll --poll-interval 30  # Custom interval
# Or via wrapper:
./scripts/adw-trigger-cron.sh --poll
```

### Triage (`adw_triage.py`)

Polls for failed issues and runs three-tier escalation (auto-retry, AI triage, human).

```bash
uv run adws/adw_triage.py --dry-run                    # Preview failed issues
uv run adws/adw_triage.py                              # Run one triage cycle
uv run adws/adw_triage.py --poll                       # Continuous triage (300s)
# Or via wrapper:
./scripts/adw-triage.sh --poll
```

### Dispatch (`adw_dispatch.py`)

Dispatches a workflow for a specific Beads issue. Typically called
internally by `adw_trigger_cron.py` — direct use is for testing or manual dispatch.

```bash
uv run adws/adw_dispatch.py --list                     # List dispatchable workflows
uv run adws/adw_dispatch.py --issue=beads-abc123       # Dispatch for an issue
# Or via wrapper:
./scripts/adw-dispatch.sh --list
```

### Data Flow

```
BMAD Story → /convert-stories-to-beads → Beads Issue (tagged {workflow_name})
                                              ↓
                                    adw_trigger_cron polls
                                              ↓
                                    adw_dispatch validates + executes
                                        ↓               ↓
                                    Success          Failure
                                    bd close      tag ADWS_FAILED
                                                      ↓
                                              adw_triage polls
                                              ↓       ↓       ↓
                                          Tier 1   Tier 2   Tier 3
                                          retry    AI fix   human
```

## What Belongs Here

- Workflow definitions (declarative step sequences)
- Pipeline engine (ROP execution, combinators, retry)
- Pipeline steps (SDK calls, shell command execution, beads integration)
- I/O boundary functions (SDK client, bd CLI, filesystem for agent output)
- Hook modules (event logging, file tracking, command blocking)
- Command entry points (/implement, /verify, /build, /prime)
- Tests for all of the above

## What Does NOT Belong Here

- Chrome extension code (popup.js, background.js, manifest.json)
- Native messaging hosts (browser detection, osascript, protocol framing)
- Application-specific features (window naming, tab groups, UI)
- Application test suites (Jest, Playwright)
- Build scripts, install scripts, store assets

## Key Concepts

### Railway-Oriented Programming (ROP)

The engine uses ROP patterns from the `returns` library for composable
error handling. Success flows forward; failures short-circuit the pipeline.

### Four-Layer Pipeline

```
Workflows (what to do)         -- Declarative, no ROP knowledge needed
    |
Engine (how to execute)        -- ROP orchestration, retry, always_run
    |
Steps (operations)             -- Pure logic + io_ops calls
    |
I/O Boundary (io_ops.py)      -- Single mock point for all external I/O
```

### Two-Tier Workflow System

- **Tier 1 (Workflow Layer):** Declarative definitions. Workflow authors work here.
  ROP types (`IOResult`, `flow`, `bind`) never leak into this tier.
- **Tier 2 (Engine/Steps):** Infrastructure. Engine developers work here.
  Full ROP machinery for composable error handling.

## Core Principles

1. **I/O Boundary Isolation:** All external I/O through `io_ops.py` -- single mock point
2. **Immutability:** `WorkflowContext` is frozen; steps return new contexts
3. **Explicit Errors:** Domain errors via ROP, never bare exceptions
4. **Type Safety:** mypy strict mode, Pydantic at SDK boundary
5. **Testability:** 100% coverage, io_ops mock boundary, enemy unit tests
6. **Separation of Concerns:** Agentic logic separate from application code

## Further Reading

- [Agentic vs Application Layer](../AGENTIC_VS_APPLICATION.md) -- boundary definition
- [Infrastructure Layer](adw_modules/README.md) -- engine, steps, io_ops
- [Engine](adw_modules/engine/README.md) -- executor, combinators, types
- [Steps](adw_modules/steps/README.md) -- pipeline step implementations
- [Workflows](workflows/README.md) -- declarative workflow definitions

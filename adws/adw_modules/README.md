# ADWS Infrastructure Layer (`adw_modules/`)

> **AGENTIC LAYER ONLY.** This directory contains workflow engine infrastructure.
> Application-specific code does not belong here.
> See [../README_AGENTIC_VS_APPLICATION.md](../README_AGENTIC_VS_APPLICATION.md).

## Architecture

```
Workflows (../workflows/)       -- Defines what to do (Tier 1)
    |
Engine (engine/)                -- Executes workflows with ROP (Tier 2)
    |
Steps (steps/)                  -- Maps errors, composes operations
    |
I/O Boundary (io_ops.py)       -- Wrapped impure operations (single mock point)
```

## Module Overview

### Core Modules

| Module | Purpose |
|--------|---------|
| `engine/` | Workflow execution engine (executor, combinators, types) |
| `steps/` | Pipeline step implementations (one file per step) |
| `commands/` | CLI command entry points (/implement, /verify, etc.) |
| `hooks/` | Event logging, file tracking, command blocking |
| `io_ops.py` | **ALL** external I/O (SDK calls, bd CLI, filesystem) |
| `errors.py` | Domain error types (`PipelineError` union) |
| `types.py` | Shared type definitions (`AdwsRequest`, `AdwsResponse`, etc.) |

### Key Rules

1. **`io_ops.py` is the I/O boundary.** Steps never import `subprocess`,
   `open()`, or `claude-agent-sdk` directly. All I/O goes through `io_ops.py`.
2. **Steps never call other steps.** Composition happens in workflows.
3. **Engine imports steps, steps never import engine.** No circular dependencies.
4. **ROP types stay in Tier 2.** Workflow authors never see `IOResult`.

## Error Handling Strategy

### I/O Boundary Layer (`io_ops.py`)

- Raises **only** standard Python exceptions (`OSError`, `FileNotFoundError`, etc.)
- Does **not** import domain errors
- This is the single mock point for all tests

### Steps Layer (`steps/`)

- Maps standard exceptions to domain errors
- Composes operations using ROP
- Returns `IOResult[PipelineError, WorkflowContext]`

### Engine Layer (`engine/`)

- Executes workflows with ROP orchestration
- Handles control flow (retry, conditional, always_run)
- Returns final result to caller

## Testing Strategy

- **Unit tests:** Mock `io_ops` at the boundary. Test pure logic directly.
- **Integration tests:** Test complete workflow execution.
- **Enemy Unit Tests:** Test REAL SDK with REAL API calls. Nothing mocked.

## Further Reading

- [Engine](engine/README.md) -- executor, combinators, types
- [Steps](steps/README.md) -- pipeline step implementations
- [Workflows](../workflows/README.md) -- declarative workflow definitions
- [Main ADWS README](../README.md) -- architecture overview

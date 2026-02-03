# Workflow Engine (`engine/`)

> **AGENTIC LAYER ONLY.** This directory contains the workflow execution engine.
> See [AGENTIC_VS_APPLICATION.md](../../../AGENTIC_VS_APPLICATION.md).

## Overview

The engine executes workflows defined as declarative data structures.
It manages step execution, error handling, retry logic, and control flow
using Railway-Oriented Programming (ROP) patterns.

## Architecture

```
Public API (types.py)           <-- Workflow authors use this (Tier 1)
    |
Combinators (combinators.py)    <-- Build complex patterns
    |
Executor (executor.py)          <-- ROP implementation (hidden, Tier 2)
```

## Core Modules

### `types.py` -- Type Definitions (Public API)

Immutable dataclasses that workflow authors use:

- `Step` -- A single operation in a workflow
- `Workflow` -- A named sequence of steps with `dispatchable` flag
- `WorkflowContext` -- Immutable state passed between steps

**ROP types (`IOResult`, `flow`, `bind`) are NOT exposed here.**

### `executor.py` -- Workflow Execution

- `run_workflow()` -- Public API. Raises on error.
- `run_workflow_io()` -- Returns `IOResult` for composition.
- `_execute_step()` -- Internal step execution.

### `combinators.py` -- Higher-Order Workflow Builders

- `sequence()` -- Compose multiple workflows linearly
- `with_verification()` -- Implement/verify retry loop
- `with_review()` -- Work/review/revise loop
- `with_retry()` -- Simple retry wrapper

## ROP in the Engine

```
Success Track:  ----+------+------+-------> Success
                    |      |      |
                    v      v      v
Failure Track:  ----+------+------+-------> Failure
```

User-facing API raises on error. Internal API returns `IOResult`.
Workflow authors never see ROP types.

## Control Flow

| Feature | Step Field | Behavior |
|---------|-----------|----------|
| Conditional | `when` predicate | Skip step if falsy |
| Always run | `always_run=True` | Execute even after failures |
| Stop on failure | Default | Halt pipeline on error |
| Retry | `max_attempts` | Retry with accumulated feedback |

## Testing

- Mock `io_ops` boundary for unit tests
- Test combinators with simple step sequences
- Integration tests verify full workflow execution

# Workflow Definitions (`workflows/`)

> **AGENTIC LAYER ONLY.** Workflows define what the engine executes.
> Application-specific logic does not belong here.
> See [AGENTIC_VS_APPLICATION.md](../../AGENTIC_VS_APPLICATION.md).

## What is a Workflow?

A workflow is a **declarative** definition of steps to execute in sequence.
Workflows are:

- **Immutable** -- frozen dataclasses
- **Composable** -- combine with combinators
- **Type-safe** -- validated by mypy
- **Testable** -- structure verifiable without execution

## Basic Structure

```python
from adws.adw_modules.engine.types import Workflow, Step

implement_close = Workflow(
    name="implement_close",
    description="Fast-track: implement then close",
    dispatchable=True,
    steps=[
        Step(name="implement", function="execute_sdk_call", sdk=True),
        Step(name="close", function="bd_close", always_run=True),
    ],
)
```

## Dispatch

Workflows with `dispatchable=True` can be triggered by beads issue tags.
`load_workflow(name)` is a pure lookup; policy enforcement lives in
`adw_dispatch.py`.

## Combinators

| Combinator | Purpose |
|-----------|---------|
| `sequence()` | Compose workflows linearly |
| `with_verification()` | Implement/verify retry loop |
| `with_review()` | Work/review/revise loop |
| `with_retry()` | Simple retry wrapper |

## Testing

Test workflow structure (correct steps, correct order, correct flags)
without executing the workflow. Workflow definitions are data, not code.

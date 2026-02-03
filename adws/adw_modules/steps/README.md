# Pipeline Steps (`steps/`)

> **AGENTIC LAYER ONLY.** Steps are workflow operations.
> Application-specific logic does not belong here.
> See [../../README_AGENTIC_VS_APPLICATION.md](../../README_AGENTIC_VS_APPLICATION.md).

## Overview

Steps are the building blocks of workflows. Each step:

1. Wraps an I/O operation from `io_ops.py`
2. Maps errors to domain types
3. Returns `IOResult[PipelineError, WorkflowContext]`
4. Composes cleanly with other steps

## Architecture

```
Steps (this layer)              <-- Map errors, compose operations
    |
I/O Boundary (../io_ops.py)    <-- Wrapped impure operations
```

## Core Pattern

Every step follows this pattern:

```python
"""One-line description of what this step does."""
from adws.adw_modules.errors import PipelineError, SpecificError
from adws.adw_modules.io_ops import some_io_function
from adws.adw_modules.engine.types import WorkflowContext

def step_name(ctx: WorkflowContext) -> IOResult[PipelineError, WorkflowContext]:
    """Execute the step."""
    # 1. Extract what we need from context
    # 2. Call io_ops for any I/O
    # 3. Process result (pure logic)
    # 4. Return updated context or error
```

## Rules

- **ONE public function per step**, matching the filename
- **Signature is ALWAYS** `(WorkflowContext) -> IOResult[PipelineError, WorkflowContext]`
- **Steps NEVER import** `subprocess`, `open()`, or `claude-agent-sdk` directly
- **Steps NEVER call other steps** -- composition happens in workflows
- Private helpers `_prefixed()` are allowed for pure logic

## Step Creation Checklist

1. Add error type(s) to `errors.py` and update `PipelineError` union
2. Add I/O function(s) to `io_ops.py`
3. Create step module in `steps/` following the core pattern
4. Export from `steps/__init__.py`
5. Write tests: mock io_ops, test pure logic, test error paths
6. Verify: `pytest`, `mypy`, `ruff check`

## Directory Organization

Steps are a **flat list** -- no subdirectories. Every step is equal and
follows the same pattern. The `__init__.py` groups exports with conceptual
comments for navigation.

## Testing

- Mock `io_ops` at the boundary
- Test both success and failure paths
- One test file per step module
- 100% line and branch coverage

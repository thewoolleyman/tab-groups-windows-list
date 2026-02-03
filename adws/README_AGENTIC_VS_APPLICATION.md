# Agentic Layer vs Application Layer -- Boundary Definition

> **This document defines the hard boundary between the AGENTIC LAYER
> and the APPLICATION LAYER. All agents, contributors, and automated
> workflows MUST respect this boundary.**

## The Rule

**`adws/` is the agentic layer. It contains ONLY workflow engine infrastructure.**

**Everything else is the application layer.**

If code does not directly serve workflow orchestration, pipeline execution,
step functions, or the I/O boundary for agent operations -- it does not
belong in `adws/`.

## Architecture Layers

```
APPLICATION LAYER                  <-- Your actual product
    popup.js, background.js,
    native-host/, manifest.json,
    tests/ (Jest, Playwright)
        | modifies
AGENTIC LAYER                      <-- Workflow engine (adws/)
    +-- Workflow Layer (User-Facing)
    +-- Execution Engine (Infrastructure)
    +-- Claude Code Interface
        | spawns
CLAUDE CODE CLI (External process)
```

The agentic layer is a **tool** that modifies the application layer.
The agentic layer is NOT part of the application.

## What Goes Where

### Agentic Layer (`adws/`)

| Category | Examples | Location |
|----------|----------|----------|
| Workflow definitions | `implement_verify_close`, `implement_close` | `adws/workflows/` |
| Pipeline engine | Executor, combinators, ROP types | `adws/adw_modules/engine/` |
| Pipeline steps | `write_failing_tests`, `execute_sdk_call`, `block_dangerous_command` | `adws/adw_modules/steps/` |
| I/O boundary | SDK client, bd CLI wrapper, filesystem for agent output | `adws/adw_modules/io_ops.py` |
| Command modules | `/implement`, `/verify`, `/build`, `/prime` | `adws/adw_modules/commands/` |
| Hook modules | Event logger, file tracker, command blocker | `adws/adw_modules/hooks/` |
| Dispatchers | Workflow dispatch, cron trigger, triage | `adws/adw_dispatch.py`, etc. |
| Domain types | `PipelineError`, `WorkflowContext`, `AdwsRequest` | `adws/adw_modules/types.py`, `errors.py` |
| Agentic tests | All tests for the above | `adws/tests/` |

### Application Layer (project root)

| Category | Examples | Location |
|----------|----------|----------|
| Chrome extension UI | Popup, background service worker | `popup.js`, `background.js` |
| Extension config | Manifest, permissions | `manifest.json` |
| Native messaging | Host script, browser detection, protocol | `native-host/` |
| Install scripts | User-facing installer | `native-host/install.sh` |
| Application tests | Jest unit tests, Playwright E2E | `tests/` |
| Build tooling | Extension packaging | `scripts/` |
| Store assets | Icons, screenshots | `store_assets/`, `icons/` |
| Distribution | Built extension | `dist/` |

## The Litmus Test

Before adding code to `adws/`, ask:

1. **Does this code orchestrate AI agent workflows?** If no, it doesn't belong.
2. **Is this a pipeline step that the engine executes?** If no, it doesn't belong.
3. **Is this an I/O operation that agents need?** If no, it doesn't belong.
4. **Would this code exist if this were a different application?** If no, it doesn't belong.

The agentic layer should be **application-agnostic**. The same `adws/` engine
could theoretically drive workflows for a different project. Application-specific
features like "read window names via osascript" or "detect which browser is running"
are product features, not workflow infrastructure.

## Known Violations (To Be Remediated)

The following code was incorrectly placed in the agentic layer and needs
to be moved to the application layer:

| Current Location | Should Be | Beads Issue |
|-----------------|-----------|-------------|
| `adws/native_host/` | Application layer (e.g., `src/native_host/` or keep in `native-host/`) | See beads tracker |
| `adws/tests/native_host/` | Application test directory | See beads tracker |

## Dual-Toolchain Boundary

```
+--------------------+-------------------------+
|  Python (uv)       |  JavaScript (npm)        |
|  pyproject.toml    |  package.json            |
|  uv.lock           |  package-lock.json       |
|  adws/             |  popup.js, background.js |
|  .claude/hooks/    |  tests/ (Jest/Playwright)|
|  .claude/commands/  |  manifest.json          |
+--------------------+-------------------------+
         Both share: .mise.toml, CI pipeline
```

The Python toolchain (`uv`) manages the agentic layer.
The JavaScript toolchain (`npm`) manages the application layer.
`mise` pins both runtimes.

## For Future Agents and Stories

**When creating a beads issue or BMAD story:**
- If it's about the Chrome extension, native host, or user-facing features: it's APPLICATION layer
- If it's about workflow execution, pipeline steps, or agent orchestration: it's AGENTIC layer
- When in doubt, check this document

**When implementing a story:**
- Read this document first
- Check the litmus test above
- Never add application code to `adws/`
- Never add agentic code outside `adws/`

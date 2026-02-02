# /adws-build

Fast-track trivial changes through the implement-close workflow.

## Usage

Invoke this command to quickly implement trivial changes using the simplified implement_close workflow. This bypasses full TDD ceremony; 100% coverage is the safety net.

## What it does

1. Loads the `implement_close` workflow from the ADWS workflow registry
2. Executes the implementation step (SDK call) followed by test verification
3. On success: closes the Beads issue via `bd close` (FR20, FR46)
4. On failure: tags the Beads issue with structured failure metadata via `bd update` (NFR2, NFR21)
5. Finalize always runs regardless of workflow outcome (NFR3)

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch build`

The dispatch routes to `run_build_command` in
`adws.adw_modules.commands.build`, which loads and executes
the `implement_close` workflow via `io_ops`, then handles
finalize (close on success, tag on failure) at the command
level (FR28, FR32).

All testable logic lives in `adws/adw_modules/commands/build.py` --
the .md file is the natural language entry point only (FR28).

# /adws-prime

Load codebase context into the current session.

## Usage

Invoke this command to prime the session with project context for subsequent development commands.

## What it does

1. Reads project configuration and structure
2. Loads relevant codebase context into session
3. Prepares the environment for development workflows

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch prime`

All testable logic lives in `adws/adw_modules/commands/` -- the .md file
is the natural language entry point only (FR28).

> **Note**: Full implementation in Story 4.3.

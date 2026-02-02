# /adws-build

Fast-track trivial changes through the implement-close workflow.

## Usage

Invoke this command to quickly implement and close trivial changes without full TDD enforcement.

## What it does

1. Loads the `implement_close` workflow from the ADWS workflow registry
2. Executes the implementation step followed by close
3. Suitable for small, well-understood changes that do not require verification

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch build`

All testable logic lives in `adws/adw_modules/commands/` -- the .md file
is the natural language entry point only (FR28).

> **Note**: Full implementation in Story 4.4.

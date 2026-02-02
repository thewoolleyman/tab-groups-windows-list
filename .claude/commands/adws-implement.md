# /adws-implement

Execute the full TDD-enforced implementation workflow.

## Usage

Invoke this command to run the complete RED-GREEN-REFACTOR cycle with verification.

## What it does

1. Loads the `implement_verify_close` workflow from the ADWS workflow registry
2. Executes TDD phases: write failing tests, implement, refactor
3. Runs full verification (Jest, Playwright, mypy, ruff) after implementation
4. Closes the workflow upon successful completion

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch implement`

All testable logic lives in `adws/adw_modules/commands/` -- this .md file
is the natural language entry point only (FR28).

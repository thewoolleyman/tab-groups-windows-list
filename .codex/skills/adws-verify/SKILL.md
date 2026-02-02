---
name: 'adws-verify'
description: 'Run the full local quality gate across all configured tools.'
---

# /adws-verify

Run the full local quality gate across all configured tools.

## Usage

Invoke this command to run all quality checks (Jest, Playwright, mypy, ruff) and report results.

## What it does

1. Loads the `verify` workflow from the ADWS workflow registry
2. Executes all quality gate steps (Jest, Playwright, mypy, ruff)
3. Reports pass/fail status with error details for any failures
4. Accumulates feedback across all tools (always_run pattern)

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch verify`

Dispatch routes "verify" to `run_verify_command` in
`adws/adw_modules/commands/verify.py`, which loads and
executes the verify workflow and returns a structured
`VerifyCommandResult` with per-tool pass/fail status.

All testable logic lives in `adws/adw_modules/commands/` -- the .md file
is the natural language entry point only (FR28).

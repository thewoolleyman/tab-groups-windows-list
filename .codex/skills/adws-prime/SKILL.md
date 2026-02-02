---
name: 'adws-prime'
description: 'Load codebase context into the current session.'
---

# /adws-prime

Load codebase context into the current session.

## Usage

Invoke this command to prime the session with project context for subsequent development commands.

## What it does

1. Reads CLAUDE.md (TDD mandate and coding conventions) -- required
2. Reads architecture.md (architecture decisions) -- optional
3. Reads epics.md (epic and story breakdown) -- optional
4. Builds directory tree for adws/ module structure (depth 3)
5. Builds directory tree for project root (depth 2)
6. Assembles all context into a PrimeContextResult

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch prime`

The dispatch routes to `run_prime_command` in
`adws.adw_modules.commands.prime`, which reads files via
`io_ops.read_prime_file` and builds directory trees via
`io_ops.get_directory_tree` (FR28, FR31).

All testable logic lives in `adws/adw_modules/commands/prime.py` --
the .md file is the natural language entry point only (FR28).

---
name: 'adws-load-bundle'
description: 'Reload context from a previous session.'
---

# /adws-load-bundle

Reload context from a previous session.

## Usage

Invoke this command to reload context from a previous session's context bundle.
Pass a session_id to load a specific bundle. If no session_id is provided,
available bundles will be listed.

## What it does

1. Reads session-specific JSONL bundle from agents/context_bundles/
2. Parses file tracking entries (file paths, operations, timestamps)
3. Returns structured LoadBundleResult with parsed entries
4. If bundle not found, lists available bundles for selection

## Implementation

This command delegates to the ADWS Python module:
`uv run python -m adws.adw_modules.commands.dispatch load_bundle`

The dispatch routes to `run_load_bundle_command` in
`adws.adw_modules.commands.load_bundle`, which reads bundles via
`io_ops.read_context_bundle` and lists available bundles via
`io_ops.list_context_bundles` (FR28, FR35).

All testable logic lives in `adws/adw_modules/commands/load_bundle.py` --
the .md file is the natural language entry point only (FR28).

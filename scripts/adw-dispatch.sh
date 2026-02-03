#!/bin/bash
# Workflow dispatch — dispatches a workflow for a specific Beads issue.
#
# Usage:
#   ./scripts/adw-dispatch.sh --issue=beads-abc123   # Dispatch workflow for issue
#   ./scripts/adw-dispatch.sh --list                 # List dispatchable workflows
#   ./scripts/adw-dispatch.sh --help                 # Show all options
set -e
exec uv run adws/adw_dispatch.py "$@"

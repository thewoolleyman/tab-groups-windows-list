#!/bin/bash
# Autonomous failure triage — polls for failed issues and runs three-tier escalation.
#
# Usage:
#   ./scripts/adw-triage.sh              # Run one triage cycle
#   ./scripts/adw-triage.sh --poll       # Continuous triage (default 300s interval)
#   ./scripts/adw-triage.sh --dry-run    # Show failed issues without acting
#   ./scripts/adw-triage.sh --help       # Show all options
set -e
exec uv run adws/adw_triage.py "$@"

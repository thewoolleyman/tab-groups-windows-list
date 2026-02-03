#!/bin/bash
# Autonomous workflow trigger — polls Beads for ready issues and dispatches workflows.
#
# Usage:
#   ./scripts/adw-trigger-cron.sh              # Run one poll cycle
#   ./scripts/adw-trigger-cron.sh --poll       # Continuous polling (default 60s interval)
#   ./scripts/adw-trigger-cron.sh --dry-run    # Show what would be processed
#   ./scripts/adw-trigger-cron.sh --help       # Show all options
set -e
exec uv run adws/adw_trigger_cron.py "$@"

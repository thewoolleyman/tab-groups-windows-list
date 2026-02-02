#!/bin/bash
# Command blocker hook -- delegates to Python module (NFR20)
# All logic is in adws/hooks/command_blocker.py
# This shim contains no standalone logic.
# Fail-open (NFR4): always exit 0 so hooks never block on internal error.

uv run python -m adws.hooks.command_blocker || true

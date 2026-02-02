#!/bin/bash
# File tracker hook -- delegates to Python module (NFR20)
# All logic is in adws/hooks/file_tracker.py
# This shim contains no standalone logic.
# Fail-open (NFR4): always exit 0 so hooks never block.

uv run python -m adws.hooks.file_tracker || true

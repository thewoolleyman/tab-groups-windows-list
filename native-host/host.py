#!/usr/bin/env python3
"""Chrome native messaging host for window name reading.

This script implements the Chrome native messaging protocol
(4-byte length-prefix stdin/stdout framing) to communicate
with the Tab Groups Windows List extension.

Supported actions:
  - get_window_names: Returns window names, bounds, active
    tab titles, and hasCustomName flag for the detected
    Chromium browser (Brave Browser or Google Chrome).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so adws.native_host is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from adws.native_host.main import main  # noqa: E402

if __name__ == "__main__":
    main()

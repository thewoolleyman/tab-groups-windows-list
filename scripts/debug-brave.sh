#!/usr/bin/env bash
# Launch Brave with Chrome DevTools Protocol for autonomous debugging
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
DEBUG_PORT="${CDP_PORT:-9222}"
USER_DATA_DIR="${CDP_PROFILE:-/tmp/tgwl-debug-brave}"

# Detect Brave binary
BRAVE=""
for candidate in \
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
  "brave-browser" \
  "brave" \
  "/usr/bin/brave-browser" \
  "/snap/bin/brave"; do
  if command -v "$candidate" &>/dev/null || [ -x "$candidate" ]; then
    BRAVE="$candidate"
    break
  fi
done

if [ -z "$BRAVE" ]; then
  echo "Error: Brave browser not found" >&2
  exit 1
fi

echo "Launching Brave with CDP on port $DEBUG_PORT..."
echo "Extension: $EXT_DIR"
echo "Profile: $USER_DATA_DIR"

exec "$BRAVE" \
  --remote-debugging-port="$DEBUG_PORT" \
  --load-extension="$EXT_DIR" \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run \
  --no-default-browser-check \
  "$@"

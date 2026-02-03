#!/bin/bash
# Native messaging host installer for Tab Groups Windows List.
#
# Downloads host.py to ~/.local/lib/tab-groups-window-namer/,
# makes it executable, detects installed Chromium browsers,
# and places the native messaging manifest in each browser's
# NativeMessagingHosts directory.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thewoolleyman/tab-groups-windows-list/master/native-host/install.sh | bash
#   # or
#   bash native-host/install.sh

set -euo pipefail

EXTENSION_ID="gialhfelganamiclidkigjnjdkdbohcb"
HOST_NAME="com.tabgroups.window_namer"
INSTALL_DIR="$HOME/.local/lib/tab-groups-window-namer"
HOST_PY_URL="https://raw.githubusercontent.com/thewoolleyman/tab-groups-windows-list/master/native-host/host.py"

# ------------------------------------------------------------------
# macOS-only check
# ------------------------------------------------------------------
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Window name sync is macOS only."
    echo "This feature requires macOS to read browser window names via osascript."
    exit 0
fi

# ------------------------------------------------------------------
# Download host.py
# ------------------------------------------------------------------
echo "Installing native messaging host..."
mkdir -p "$INSTALL_DIR"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$HOST_PY_URL" -o "$INSTALL_DIR/host.py"
elif command -v wget >/dev/null 2>&1; then
    wget -q "$HOST_PY_URL" -O "$INSTALL_DIR/host.py"
else
    echo "FAIL: Neither curl nor wget found. Cannot download host.py."
    exit 1
fi

chmod +x "$INSTALL_DIR/host.py"
echo "  Downloaded host.py to $INSTALL_DIR/host.py"

# ------------------------------------------------------------------
# Build manifest JSON
# ------------------------------------------------------------------
MANIFEST_JSON=$(cat <<EOF
{
  "name": "$HOST_NAME",
  "description": "Native messaging host for Tab Groups Windows List window name reading",
  "path": "$INSTALL_DIR/host.py",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXTENSION_ID/"
  ]
}
EOF
)

# ------------------------------------------------------------------
# Browser detection and manifest installation
# ------------------------------------------------------------------
# Parallel arrays instead of associative array (bash 3.2 compat)
BROWSER_NAMES="Google Chrome|Brave Browser|Microsoft Edge|Chromium"
BROWSER_DIRS="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts|$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts|$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts|$HOME/Library/Application Support/Chromium/NativeMessagingHosts"

SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

echo ""
echo "Detecting installed browsers..."

# Save and restore IFS for pipe-delimited splitting
OLD_IFS="$IFS"
IFS="|"
set -f  # disable globbing during split
NAMES_ARRAY=($BROWSER_NAMES)
DIRS_ARRAY=($BROWSER_DIRS)
set +f
IFS="$OLD_IFS"

i=0
while [ $i -lt ${#NAMES_ARRAY[@]} ]; do
    BROWSER_NAME="${NAMES_ARRAY[$i]}"
    MANIFEST_DIR="${DIRS_ARRAY[$i]}"
    PARENT_DIR="$(dirname "$MANIFEST_DIR")"

    if [ -d "$PARENT_DIR" ]; then
        mkdir -p "$MANIFEST_DIR"
        if echo "$MANIFEST_JSON" > "$MANIFEST_DIR/$HOST_NAME.json"; then
            echo "  $BROWSER_NAME: OK"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "  $BROWSER_NAME: FAIL (could not write manifest)"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        SKIP_COUNT=$((SKIP_COUNT + 1))
    fi
    i=$((i + 1))
done

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "Installation summary:"
echo "  Browsers configured: $SUCCESS_COUNT"
if [[ $SKIP_COUNT -gt 0 ]]; then
    echo "  Browsers not found:  $SKIP_COUNT"
fi
if [[ $FAIL_COUNT -gt 0 ]]; then
    echo "  Failures:            $FAIL_COUNT"
fi

if [[ $SUCCESS_COUNT -eq 0 ]]; then
    echo ""
    echo "No Chromium browsers detected. No manifests were installed."
    echo "Supported browsers: Google Chrome, Brave Browser, Microsoft Edge, Chromium."
else
    echo ""
    echo "Done! Restart your browser for changes to take effect."
fi

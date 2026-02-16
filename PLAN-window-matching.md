# Plan: Reliable Window Matching & Autonomous Debugging

## Context

The extension matches browser windows to OS windows via bounds+title scoring through a native messaging host. This is broken on Brave: the native host returns Chrome windows mixed with Brave windows because it enumerates by process name without isolating to the calling browser. Debugging requires human intervention since the agent can't drive real browsers autonomously.

## Three workstreams (can be parallelized)

---

### 1. PID-Based Window Filtering (fixes Brave-shows-Chrome bug)

**Insight**: The native messaging host is spawned as a child process of the browser. `os.getppid()` gives the browser's PID. We can filter OS windows to only those belonging to that process tree.

**Files to modify**:
- `native-host/host.py` — add PID-based filtering to `_get_window_names_macos()` and `_get_window_names_linux()`

**Implementation**:
1. Get browser PID via `os.getppid()` at host startup
2. Build process tree (browser PID + all descendants) via `/proc` parsing (no external deps)
3. **macOS**: Use `CGWindowListCopyWindowInfo` (via subprocess calling `python3 -c "from Quartz import..."`) to get window owner PIDs, or filter JXA results by matching PID
4. **Linux**: Use `xdotool getwindowpid <wid>` (already available) to filter — only return windows whose PID is in the browser's process tree
5. Remove browser-name-based detection (`pgrep -f brave`, System Events process name) as primary filter — PID tree is authoritative

**Tests** (TDD):
- Test that `os.getppid()` is used to determine browser PID
- Test that windows from other process trees are excluded
- Test that windows from child processes of the browser are included (renderer processes)

---

### 2. CDP-Based Autonomous Debug Pipeline (unblocks agent debugging)

**Insight**: Chrome DevTools Protocol works on any Chromium browser launched with `--remote-debugging-port=9222`. No custom build needed.

**Files to create/modify**:
- `scripts/debug-brave.sh` (new) — launches Brave with debugging flags + extension loaded
- `scripts/cdp-diagnose.js` (new) — CDP client that triggers diagnostics and captures results
- `package.json` — add `diagnose:brave` script

**Implementation**:
1. Script to launch Brave: `brave --remote-debugging-port=9222 --load-extension=. --user-data-dir=/tmp/tgwl-debug`
2. CDP client connects, opens multiple windows with known URLs
3. Triggers extension diagnostic API via `chrome.runtime.sendMessage` through CDP `Runtime.evaluate`
4. Captures native host response, extension window list, matching scores
5. Compares results between Chrome and Brave runs — diffs show exactly where matching diverges

**Tests**:
- Integration test that verifies CDP connection and diagnostic capture
- Comparative test runner that flags scoring differences between browsers

---

### 3. Upstream Chromium Feature Request (fire-and-forget)

**Action**: File a bug at [crbug.com](https://crbug.com) requesting `chrome.windows.Window.name` property.

**Key arguments**:
- `chrome.windows.update()` already accepts bounds/state — `name` is a natural addition
- Window naming is an OS-level feature users already use (macOS: Window > Name Window)
- Extensions currently need native messaging hosts just to read window names — disproportionate complexity
- Could be gated behind `"windows.name"` permission for privacy

**Deliverable**: Draft the bug report text for the user to submit (requires a Google account).

---

## Execution Order

1. **PID filtering** first — smallest change, biggest impact, fixes the user-facing bug
2. **CDP debug pipeline** second — enables verifying the PID fix on Brave autonomously
3. **Upstream request** — draft the text anytime, user submits when ready

## Verification

- Run `npm run diagnose` on Brave → native host should only return Brave windows
- Run `npm run diagnose:brave` (new) → agent-driven, no human needed
- Compare Chrome vs Brave diagnostic output → no cross-contamination
- Existing tests pass: `npx jest --no-coverage`

# Chromium Feature Request Draft

> Copy-paste the sections below into https://crbug.com (requires Google account).

---

## Title

Feature request: Add chrome.windows.Window.name property

## Component

Platform>Extensions>API

## Type

Feature request

---

## Body

### Summary

Extensions that manage windows (tab managers, window organizers, session restorers) have no API to read or set OS-level window names or titles. The `chrome.windows.Window` type exposes `id`, `focused`, `state`, `bounds`, and `tabs`, but nothing for the human-readable window name.

The only current workaround requires a native messaging host that shells out to OS-specific tools:

- **macOS**: `osascript` (AppleScript) to call `System Events`
- **Linux**: `xprop` / `xdotool` to manipulate `_NET_WM_NAME`
- **Windows**: Win32 `SetWindowText` / `GetWindowText` API

This is disproportionate complexity for reading and writing a single string property.

### Proposed API Addition

Add a `name` (string) property to `chrome.windows.Window`:

```js
// Reading
const win = await chrome.windows.get(windowId);
console.log(win.name); // e.g. "Research" or ""

// Writing
await chrome.windows.update(windowId, { name: "Research" });
```

**Details:**

- Add `name` as an optional string property on `chrome.windows.Window`.
- Allow setting it via `chrome.windows.update(windowId, { name: "..." })`.
- Return the OS-level window title when set, or an empty string if the extension has not set a name.
- Gate behind a new `"windows.name"` permission to preserve user privacy (window titles can reveal page content).
- Fire `chrome.windows.onNameChanged` (or extend `onBoundsChanged` / add a general `onUpdated`) when the name changes.

### Use Cases

1. **Tab managers** that let users name their windows for easy identification (e.g. "Work", "Personal", "Research").
2. **Session restorers** that want to preserve window identity across browser restarts, not just tab URLs.
3. **Productivity tools** that organize windows by project or context and need a persistent label.
4. **Accessibility tools** that set descriptive window titles for screen readers and OS-level window switchers.
5. **macOS parity**: macOS Chrome already supports Window > Name Window natively via the menu bar. Exposing this to extensions would make the feature programmable.

### Current Workaround

The only way to achieve this today is:

1. Bundle a native messaging host with the extension.
2. The host runs a platform-specific binary or script.
3. On macOS: call `osascript -e 'tell application "System Events" ...'`
4. On Linux: call `xdotool set-window --name "..." <window_id>`
5. On Windows: call `SetWindowText()` via a compiled helper.

This requires:

- A separate installer for the native host.
- Platform-specific code for three operating systems.
- The `"nativeMessaging"` permission.
- Users to trust and install an additional binary outside the Chrome Web Store.

All of this just to read or write a window title string.

### Precedent

`chrome.windows.update()` already accepts `left`, `top`, `width`, `height`, `state`, `focused`, and `drawAttention`. A `name` property is a natural, minimal addition to this surface. The data is already present at the OS level; the API simply needs to expose it.

### Related

- **Canonical Chromium issue:** https://issues.chromium.org/issues/40174035 — "Programmatic access to window-name from chrome.windows extension API"
- Related: https://issues.chromium.org/issues/40944834, https://issues.chromium.org/issues/40236151
- macOS: Window > Name Window (built-in Chrome feature, not exposed to extensions)
- Firefox: No equivalent API exists there either, making this a chance for Chrome to lead.

---

*Filed by the maintainer of [Tab Groups Windows List](https://github.com/nickmessing/tab-groups-windows-list), a tab/window management extension that currently requires a native messaging host solely for window naming.*

# Comment for Chromium Issues

> Paste this comment on both issues:
> - https://issues.chromium.org/issues/40944834
> - https://issues.chromium.org/issues/40236151
>
> Then star both issues.

---

Adding a +1 with real-world implementation details on the workaround burden.

I maintain [Tab Groups Windows List](https://chromewebstore.google.com/detail/tab-groups-windows-list/gialhfelganamiclidkigjnjdkdbohcb), a Chrome extension that shows a hierarchical view of windows, tab groups, and tabs. The single most-requested feature is **custom window names** — users want to label windows "Work", "Research", "Personal", etc.

Since `chrome.windows.Window` has no `name` property, we built a **native messaging host** as the workaround. Here's what that actually costs:

**Three platform-specific code paths:**
- **macOS**: JXA via `osascript` to query window names from the app object
- **Linux**: `xdotool` + `xprop` to read `_NET_WM_NAME`, with PID-based process tree filtering to isolate the calling browser's windows from other Chromium instances (e.g. Brave vs Chrome)
- **Windows**: Win32 API calls

**Matching problem:** The native host returns OS-level windows (name + bounds), but the extension API returns `chrome.windows` (id + bounds). We have to match them by scoring bounds overlap + active tab title similarity. This is fragile — window managers report different coordinate systems than Chrome, and on Linux, Chrome overwrites `_NET_WM_NAME` on every tab switch, making custom names ephemeral.

**Installation friction:** Users must run a separate `install.sh` / `install.bat` that copies the host binary and registers a NativeMessagingHosts manifest per browser. This is the #1 support issue — users install the extension from the Web Store, then wonder why window names don't work until they run the installer.

**What we'd delete if this API existed:**
- 400+ lines of Python (native host)
- Platform-specific install scripts for macOS/Linux/Windows
- Bounds-based window matching algorithm
- PID-based process tree filtering
- The entire `nativeMessaging` permission requirement

The proposed API is minimal: a `name` string on `chrome.windows.Window`, settable via `chrome.windows.update()`, gated behind a permission. `chrome.windows.update()` already accepts `left/top/width/height/state/focused` — `name` is a natural addition.

Source: https://github.com/thewoolleyman/tab-groups-windows-list (see `native-host/host.py` for the full workaround)

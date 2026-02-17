# Comment for Chromium Issue #40174035

> **Canonical issue:** https://issues.chromium.org/issues/40174035
> "Programmatic access to window-name from chrome.windows extension API"
>
> Paste this comment there and star it.
>
> Related/duplicate issues (star these too):
> - https://issues.chromium.org/issues/40944834 — "expose window names via Chrome extension API"
> - https://issues.chromium.org/issues/40236151 — "Use chrome.windows API to set window name"

---

## The Comment

Adding a +1 with implementation analysis and a concrete proposal to unblock this.

### Real-world workaround burden

I maintain [Tab Groups Windows List](https://chromewebstore.google.com/detail/tab-groups-windows-list/gialhfelganamiclidkigjnjdkdbohcb), a Chrome extension that displays a hierarchical view of windows, tab groups, and tabs. Since `chrome.windows.Window` has no `name` property, we built a **native messaging host** to read OS-level window names. The cost:

- **400+ lines of Python** with three platform-specific code paths (osascript on macOS, xdotool/xprop on Linux, Win32 on Windows)
- **PID-based process tree filtering** on Linux to isolate the calling browser's windows from other Chromium instances (e.g. Brave vs Chrome running simultaneously)
- **A bounds+title scoring algorithm** to match native OS windows to `chrome.windows.Window` objects — fragile because window managers report different coordinate systems than Chrome
- **A separate install script** per platform that users must run outside the Web Store — our #1 support issue

### The implementation is straightforward

I've reviewed the Chromium source and the data is already there:

**`Browser` already stores the user title** (`chrome/browser/ui/browser.h`):
```cpp
std::string user_title_;
const std::string& user_title() const { return user_title_; }
void SetWindowUserTitle(const std::string& user_title);
```

This is the value set via the existing right-click → "Name Window" menu (shipped since Chrome 88/90).

**`CreateWindowValueForExtension`** (`chrome/browser/extensions/extension_tab_util.cc`) constructs the `chrome.windows.Window` dict. It currently populates `id`, `focused`, `top`, `left`, `width`, `height`, `tabs`, `incognito`, `type`, `state`, `alwaysOnTop` — but does **not** include `user_title_`. Adding it is one line:
```cpp
window_value["title"] = browser->user_title();
```

**`windows.json`** schema would need a new optional string property on the `Window` type and a corresponding parameter in `update()`.

**`WindowsEventRouter`** (`chrome/browser/extensions/api/tabs/windows_event_router.cc`) already fires events for bounds/focus changes. A `windows.onTitleChanged` event (or just extending `onBoundsChanged` to be `onUpdated`) would follow the same pattern.

### The permission question (the actual blocker)

Comment #21 on this thread raises the key question: **which permission should gate access to window titles?**

The options as I see them:

1. **Reuse `"tabs"` permission** — The `tabs` permission already gates `tabs.Tab.url`, `tabs.Tab.title`, and `tabs.Tab.favIconUrl` via the `ScrubTabBehavior` mechanism in `extension_tab_util.cc`. Window titles (which often contain the active tab's page title) are arguably the same sensitivity class. **Downside**: The `tabs` permission is already overloaded and triggers a broad install warning ("Read your browsing history"). Adding window names wouldn't change the warning text but further broadens what `tabs` grants.

2. **New `"windowNames"` permission** — A dedicated permission with a narrow warning like "Read and change your window names". **Downside**: Creates a third permission in the windows/tabs space (alongside `tabs` and the implicit windows access). Comment #21 specifically raised concern about a "third permission." However, this is the cleanest approach because window names are user-chosen labels, categorically different from browsing-history-derived tab titles.

3. **No additional permission** — Window names are user-assigned labels with no browsing-history sensitivity. Unlike `tabs.Tab.title` (which leaks page titles and therefore visited URLs), `user_title_` is explicitly set by the user and contains only what they typed. An extension that can already call `chrome.windows.getAll()` (no permission needed) can see window IDs, bounds, and state — the user-assigned name is arguably less sensitive than those. **This is my recommendation**: expose `title` (read-only) with no additional permission, and gate `chrome.windows.update({title: ...})` (write) behind the existing implicit windows access.

### Proposed path forward

Given that:
- The data (`user_title_`) already exists in `Browser`
- The construction point (`CreateWindowValueForExtension`) is identified
- The schema (`windows.json`) change is minimal
- The event system (`WindowsEventRouter`) has patterns to follow

The only blocker is **a decision on permissions**. I'd suggest posting a brief intent-to-implement on chromium-extensions@ with the three permission options above and asking for a decision. Once that's resolved, the actual CL is small — probably a few hundred lines across the schema, tab_util, and event router.

I'm happy to draft or contribute to a CL if there's alignment on the permission approach.

Source: https://github.com/thewoolleyman/tab-groups-windows-list

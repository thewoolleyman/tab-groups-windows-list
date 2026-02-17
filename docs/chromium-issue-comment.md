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

**`CreateWindowValueForExtension`** (`chrome/browser/extensions/browser_extension_window_controller.cc`) constructs the `chrome.windows.Window` dict. It currently populates `id`, `focused`, `top`, `left`, `width`, `height`, `tabs`, `incognito`, `type`, `state`, `alwaysOnTop` — but does **not** include `user_title_`. Adding it is one line:
```cpp
dict.Set("title", browser->user_title());
```

**`windows.json`** schema would need a new optional string property on the `Window` type and a corresponding parameter in `update()`.

**`WindowsEventRouter`** (`chrome/browser/extensions/api/tabs/windows_event_router.cc`) already fires events for bounds/focus changes. A `windows.onTitleChanged` event (or just extending `onBoundsChanged` to be `onUpdated`) would follow the same pattern.

### The permission question (the actual blocker)

Comment #21 on this thread raises the key question: **which permission should gate access to window titles?**

To answer this, it helps to compare what `user_title_` actually is versus what the existing `tabs` permission protects:

| | `tab.title` (gated by `"tabs"`) | `window.user_title_` (proposed) |
|---|---|---|
| **Source** | `<title>` element of the active web page | Explicitly typed by the user via Chrome's "Name Window" menu |
| **Privacy risk** | Leaks browsing history (e.g. "Gmail - john@example.com") | Contains only what the user deliberately typed (e.g. "Work") |
| **Changes automatically** | Yes, on every navigation | No, only when user manually renames |
| **Default value** | Always populated from page content | Empty string (most windows have no title) |

Every other `Window` property — `id`, `bounds`, `state`, `type`, `focused`, `incognito`, `alwaysOnTop` — is already available with **no permission at all**. There is no `"windows"` entry in `_permission_features.json`; `chrome.windows.getAll()` is implicit.

The three options as I see them:

1. **Reuse `"tabs"` permission** — The `tabs` permission already gates `tabs.Tab.url`, `tabs.Tab.title`, and `tabs.Tab.favIconUrl` via the `ScrubTabBehavior` / `GetScrubTabBehavior()` mechanism in `extension_tab_util.cc`. **Downside**: Semantically wrong — window names aren't tab data. This would force extensions that only need window names to request `"tabs"`, which warns users about reading browsing history. That's misleading for a user-set label.

2. **New `"windowNames"` permission** — A dedicated permission with a narrow warning like "Read and change your window names". **Downside**: Creates a third permission in the windows/tabs space. Comment #21 specifically raised concern about a "third permission." Also likely overkill given that `user_title_` is user-set metadata, not browsing-derived content.

3. **No additional permission (my recommendation)** — `user_title_` is user-intentional metadata, categorically the same as `state`, `bounds`, or `alwaysOnTop` — all of which are ungated. An extension that can already see window IDs, bounds, incognito status, and focus state should be able to see a label the user explicitly typed. Expose `title` (read-only) with no additional permission; gate `chrome.windows.update({title: ...})` (write) behind the existing implicit windows access.

### Proposed path forward

Given that:
- The data (`user_title_`) already exists in `Browser`
- The construction point (`CreateWindowValueForExtension`) is identified
- The schema (`windows.json`) change is minimal
- The event system (`WindowsEventRouter`) has patterns to follow

The only blocker is **a decision on permissions**. I'd suggest posting a brief intent-to-implement on chromium-extensions@ with the three permission options above and asking for a decision. Once that's resolved, the actual CL is small — probably a few hundred lines across the schema, tab_util, and event router.

I'm happy to draft or contribute to a CL if there's alignment on the permission approach.

Source: https://github.com/thewoolleyman/tab-groups-windows-list

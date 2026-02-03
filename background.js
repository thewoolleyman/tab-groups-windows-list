/**
 * Tab Groups & Windows List - Background Service Worker
 *
 * Bridges the native messaging host (which reads OS-level window names)
 * with the Chrome extension by:
 * 1. Calling the native host on startup and when windows are created
 * 2. Matching native window data to extension windows by bounds
 * 3. Caching {windowId: {name, urlFingerprint}} in chrome.storage.local
 * 4. Updating urlFingerprints when tabs change
 * 5. Retaining closed window entries for restart matching via Jaccard similarity
 * 6. Exposing a message API for popup.js
 */

const NATIVE_HOST_NAME = 'com.pbjtime.tab_groups_windows_list';
const JACCARD_THRESHOLD = 0.6;

/**
 * Compute a URL fingerprint for a window's tabs.
 * Returns sorted unique hostnames joined with pipe.
 * @param {Array} tabs - Array of tab objects with url property
 * @returns {string} - Pipe-separated sorted unique hostnames
 */
function computeUrlFingerprint(tabs) {
  if (!tabs || tabs.length === 0) return '';

  const hostnames = new Set();
  for (const tab of tabs) {
    if (!tab.url) continue;
    try {
      const url = new URL(tab.url);
      if (url.hostname) {
        hostnames.add(url.hostname);
      }
    } catch (_e) {
      // Skip invalid URLs (about:blank, etc.)
    }
  }

  const sorted = Array.from(hostnames).sort();
  return sorted.join('|');
}

/**
 * Match native host windows to extension windows by comparing bounds.
 * Only returns matches for windows where hasCustomName is true.
 * @param {Array} nativeWindows - Windows from native host with {name, bounds, hasCustomName}
 * @param {Array} extensionWindows - Windows from chrome.windows.getAll with {id, left, top, width, height}
 * @returns {Array} - Array of {windowId, name, hasCustomName} for matched windows
 */
function matchWindowsByBounds(nativeWindows, extensionWindows) {
  /* istanbul ignore next - defensive null guard */
  if (!nativeWindows || !extensionWindows) return [];

  const matches = [];

  for (const native of nativeWindows) {
    if (!native.hasCustomName) continue;

    const bounds = native.bounds;
    /* istanbul ignore next - defensive null guard */
    if (!bounds) continue;

    for (const ext of extensionWindows) {
      if (
        bounds.x === ext.left &&
        bounds.y === ext.top &&
        bounds.width === ext.width &&
        bounds.height === ext.height
      ) {
        matches.push({
          windowId: ext.id,
          name: native.name,
          hasCustomName: native.hasCustomName,
        });
        break;
      }
    }
  }

  return matches;
}

/**
 * Calculate Jaccard similarity between two pipe-separated fingerprints.
 * @param {string} fp1 - First fingerprint (pipe-separated hostnames)
 * @param {string} fp2 - Second fingerprint (pipe-separated hostnames)
 * @returns {number} - Jaccard similarity (0.0 to 1.0)
 */
function jaccardSimilarity(fp1, fp2) {
  if (!fp1 && !fp2) return 0.0;
  if (!fp1 || !fp2) return 0.0;

  const set1 = new Set(fp1.split('|').filter(Boolean));
  const set2 = new Set(fp2.split('|').filter(Boolean));

  /* istanbul ignore next - already handled by empty string checks above */
  if (set1.size === 0 && set2.size === 0) return 0.0;

  let intersection = 0;
  for (const item of set1) {
    if (set2.has(item)) intersection++;
  }

  const union = new Set([...set1, ...set2]).size;
  /* istanbul ignore next - already handled by empty string checks above */
  if (union === 0) return 0.0;

  return intersection / union;
}

/**
 * Fetch window names from native host and cache them with URL fingerprints.
 * Called on service worker start and on chrome.windows.onCreated.
 */
async function fetchAndCacheWindowNames() {
  try {
    const nativeResponse = await new Promise((resolve) => {
      chrome.runtime.sendNativeMessage(
        NATIVE_HOST_NAME,
        { action: 'get_window_names' },
        (response) => {
          if (chrome.runtime.lastError || !response) {
            resolve(null);
            return;
          }
          resolve(response);
        },
      );
    });

    if (!nativeResponse || !nativeResponse.success) return;

    const extensionWindows = await chrome.windows.getAll({ populate: true });
    const matched = matchWindowsByBounds(nativeResponse.windows, extensionWindows);

    if (matched.length === 0) return;

    // Read existing cache
    const stored = await chrome.storage.local.get('windowNames');
    const windowNames = stored.windowNames || {};

    // Update cache with matched windows
    for (const match of matched) {
      const extWin = extensionWindows.find((w) => w.id === match.windowId);
      /* istanbul ignore next - extWin always exists when matched by bounds */
      const tabs = extWin?.tabs || [];
      const fingerprint = computeUrlFingerprint(tabs);

      windowNames[String(match.windowId)] = {
        name: match.name,
        urlFingerprint: fingerprint,
      };
    }

    await chrome.storage.local.set({ windowNames });
  /* istanbul ignore next - defensive catch for native host errors */
  } catch (_e) {
    // Silently handle errors - native host may not be installed
  }
}

/**
 * Update the URL fingerprint for a specific window in the cache.
 * @param {number} windowId - The window ID to update
 */
async function updateUrlFingerprint(windowId) {
  try {
    const stored = await chrome.storage.local.get('windowNames');
    /* istanbul ignore next - defensive fallback for missing storage key */
    const windowNames = stored.windowNames || {};

    const key = String(windowId);
    if (!windowNames[key]) return;

    const tabs = await chrome.tabs.query({ windowId });
    const fingerprint = computeUrlFingerprint(tabs);

    windowNames[key] = {
      ...windowNames[key],
      urlFingerprint: fingerprint,
    };

    await chrome.storage.local.set({ windowNames });
  /* istanbul ignore next - defensive catch for storage errors */
  } catch (_e) {
    // Silently handle errors
  }
}

/**
 * Handle startup matching: match current windows to previously closed entries
 * using Jaccard similarity of hostname sets.
 */
async function handleStartupMatching() {
  try {
    const stored = await chrome.storage.local.get('windowNames');
    const windowNames = stored.windowNames || {};

    // Collect closed entries
    const closedEntries = [];
    for (const [id, entry] of Object.entries(windowNames)) {
      if (entry.closed) {
        closedEntries.push({ id, ...entry });
      }
    }

    if (closedEntries.length === 0) return;

    // Get current windows
    const currentWindows = await chrome.windows.getAll({ populate: true });

    // Find current windows that don't have cached names
    const unmatchedWindows = currentWindows.filter(
      (w) => !windowNames[String(w.id)] || windowNames[String(w.id)].closed,
    );

    if (unmatchedWindows.length === 0) return;

    const usedClosedIds = new Set();

    for (const win of unmatchedWindows) {
      /* istanbul ignore next - windows from getAll always have tabs with populate:true */
      const currentFingerprint = computeUrlFingerprint(win.tabs || []);
      let bestMatch = null;
      let bestSimilarity = 0;

      for (const closed of closedEntries) {
        if (usedClosedIds.has(closed.id)) continue;

        const similarity = jaccardSimilarity(
          currentFingerprint,
          closed.urlFingerprint,
        );

        if (similarity > bestSimilarity && similarity >= JACCARD_THRESHOLD) {
          bestMatch = closed;
          bestSimilarity = similarity;
        }
      }

      if (bestMatch) {
        // Assign the name from the closed entry to the current window
        windowNames[String(win.id)] = {
          name: bestMatch.name,
          urlFingerprint: currentFingerprint,
        };
        // Remove the old closed entry
        delete windowNames[bestMatch.id];
        usedClosedIds.add(bestMatch.id);
      }
    }

    await chrome.storage.local.set({ windowNames });
  /* istanbul ignore next - defensive catch for startup errors */
  } catch (_e) {
    // Silently handle errors
  }
}

// --- Event listener registration ---

// Window created: fetch fresh names from native host
chrome.windows.onCreated.addListener(async (_window) => {
  await fetchAndCacheWindowNames();
});

// Window removed: mark as closed but retain for restart matching
chrome.windows.onRemoved.addListener(async (windowId) => {
  try {
    const stored = await chrome.storage.local.get('windowNames');
    /* istanbul ignore next - defensive fallback for missing storage key */
    const windowNames = stored.windowNames || {};
    const key = String(windowId);

    if (windowNames[key]) {
      windowNames[key].closed = true;
      await chrome.storage.local.set({ windowNames });
    }
  /* istanbul ignore next - defensive catch for storage errors */
  } catch (_e) {
    // Silently handle errors
  }
});

// Tab events: update URL fingerprint for affected window
chrome.tabs.onCreated.addListener(async (tab) => {
  if (tab.windowId) {
    await updateUrlFingerprint(tab.windowId);
  }
});

chrome.tabs.onRemoved.addListener(async (_tabId, removeInfo) => {
  if (removeInfo && removeInfo.windowId && !removeInfo.isWindowClosing) {
    await updateUrlFingerprint(removeInfo.windowId);
  }
});

chrome.tabs.onUpdated.addListener(async (_tabId, _changeInfo, tab) => {
  if (tab && tab.windowId) {
    await updateUrlFingerprint(tab.windowId);
  }
});

chrome.tabs.onAttached.addListener(async (_tabId, attachInfo) => {
  /* istanbul ignore next - Chrome always provides attachInfo */
  if (attachInfo && attachInfo.newWindowId) {
    await updateUrlFingerprint(attachInfo.newWindowId);
  }
});

chrome.tabs.onDetached.addListener(async (_tabId, detachInfo) => {
  /* istanbul ignore next - Chrome always provides detachInfo */
  if (detachInfo && detachInfo.oldWindowId) {
    await updateUrlFingerprint(detachInfo.oldWindowId);
  }
});

// Message API for popup.js
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.action === 'getWindowNames') {
    chrome.storage.local.get('windowNames').then((stored) => {
      /* istanbul ignore next - defensive fallback for missing storage key */
      const names = stored.windowNames || {};
      sendResponse({
        success: true,
        windowNames: names,
      });
    });
    return true; // Keep message channel open for async response
  }

  sendResponse({
    success: false,
    error: `Unknown action: ${message.action}`,
  });
  return false;
});

// On service worker start: fetch names and handle startup matching
fetchAndCacheWindowNames();
handleStartupMatching();

// Export for testing (CommonJS module support)
/* istanbul ignore next - environment detection for module exports */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    computeUrlFingerprint,
    matchWindowsByBounds,
    jaccardSimilarity,
    fetchAndCacheWindowNames,
    updateUrlFingerprint,
    handleStartupMatching,
    NATIVE_HOST_NAME,
    JACCARD_THRESHOLD,
  };
}

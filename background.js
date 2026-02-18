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

const NATIVE_HOST_NAME = 'com.tabgroups.window_namer';
const JACCARD_THRESHOLD = 0.6;

/**
 * Detect the current browser from the user agent string.
 * Returns the macOS application name used by osascript.
 * @returns {string} Browser application name
 */
function detectBrowser() {
  // Brave exposes navigator.brave API; its UA string is Chrome-like (no "Brave")
  if (typeof navigator !== 'undefined' && navigator.brave) return 'Brave Browser';
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent || '' : '';
  if (/Brave/i.test(ua)) return 'Brave Browser';
  if (/Edg\//i.test(ua)) return 'Microsoft Edge';
  if (/Chromium/i.test(ua)) return 'Chromium';
  return 'Google Chrome';
}

/**
 * Tagged logger for pipeline observability.
 * All messages use [TGWL:<stage>] prefix for easy filtering.
 * @param {string} stage - Pipeline stage identifier
 * @param {...*} args - Arguments to log
 */
function tgwlLog(stage, ...args) {
  console.log(`[TGWL:${stage}]`, ...args);
}

/**
 * Tagged error logger for pipeline observability.
 * @param {string} stage - Pipeline stage identifier
 * @param {...*} args - Arguments to log
 */
function tgwlError(stage, ...args) {
  console.error(`[TGWL:${stage}]`, ...args);
}

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
      // Skip invalid URLs (about:blank, etc.) - not an error
    }
  }

  const sorted = Array.from(hostnames).sort();
  return sorted.join('|');
}

/**
 * Match native host windows to extension windows using a scoring algorithm.
 * Primary: active tab title match (2 pts). Secondary: bounds match (1 pt).
 * Only returns matches for windows where hasCustomName is true.
 * @param {Array} nativeWindows - Windows from native host with {name, bounds, hasCustomName, activeTabTitle?}
 * @param {Array} extensionWindows - Windows from chrome.windows.getAll with {id, left, top, width, height, tabs?}
 * @returns {Array} - Array of {windowId, name, hasCustomName} for matched windows
 */
function matchWindowsByBounds(nativeWindows, extensionWindows) {
  /* istanbul ignore next - defensive null guard */
  if (!nativeWindows || !extensionWindows) return [];

  const matches = [];
  const usedExtensionIds = new Set();

  for (const native of nativeWindows) {
    if (!native.hasCustomName) continue;

    const bounds = native.bounds;
    /* istanbul ignore next - defensive null guard */
    if (!bounds) continue;

    let bestExt = null;
    let bestScore = 0;

    for (const ext of extensionWindows) {
      if (usedExtensionIds.has(ext.id)) continue;

      let score = 0;

      // Bounds match: 1 point
      if (
        bounds.x === ext.left &&
        bounds.y === ext.top &&
        bounds.width === ext.width &&
        bounds.height === ext.height
      ) {
        score += 1;
      }

      // Active tab title match: 2 points
      if (native.activeTabTitle && ext.tabs) {
        const activeTab = ext.tabs.find((t) => t.active);
        if (activeTab && activeTab.title === native.activeTabTitle) {
          score += 2;
        }
      }

      if (score > bestScore) {
        bestScore = score;
        bestExt = ext;
      }
    }

    if (bestExt && bestScore > 0) {
      tgwlLog('matching', `"${native.name}" -> ext ${bestExt.id} (score=${bestScore})`);
      usedExtensionIds.add(bestExt.id);
      matches.push({
        windowId: bestExt.id,
        name: native.name,
        hasCustomName: native.hasCustomName,
      });
    } else {
      tgwlLog('matching', `"${native.name}" -> no match (bestScore=${bestScore})`);
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
 * Log extension data to disk via the native host.
 * Fire-and-forget — does not block the caller.
 * @param {string} event - Event name for log identification
 * @param {object} data - Data to log
 */
function logExtensionData(event, data) {
  try {
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST_NAME,
      { action: 'log_extension_data', data: { source: 'background.js', event, ...data } },
      /* istanbul ignore next - fire-and-forget callback */
      () => { if (chrome.runtime.lastError) { /* silently ignore */ } },
    );
  /* istanbul ignore next - defensive */
  } catch (_e) {
    // Never let logging break the pipeline
  }
}

/**
 * Fetch window names from native host and cache them with URL fingerprints.
 * Called on service worker start and on chrome.windows.onCreated.
 */
async function fetchAndCacheWindowNames() {
  try {
    const browser = detectBrowser();
    tgwlLog('native-req', 'Sending get_window_names to', NATIVE_HOST_NAME, 'browser:', browser);
    const nativeResponse = await new Promise((resolve) => {
      chrome.runtime.sendNativeMessage(
        NATIVE_HOST_NAME,
        { action: 'get_window_names', browser },
        (response) => {
          if (chrome.runtime.lastError || !response) {
            tgwlError('native-res', 'Native host error:', chrome.runtime.lastError?.message || 'no response');
            resolve(null);
            return;
          }
          tgwlLog('native-res', 'Received response:', JSON.stringify(response).substring(0, 500));
          resolve(response);
        },
      );
    });

    if (!nativeResponse || !nativeResponse.success) {
      tgwlLog('native-res', 'No valid response, skipping match');
      return;
    }

    const extensionWindows = await chrome.windows.getAll({ populate: true });
    tgwlLog('ext-windows', extensionWindows.map((w) => ({
      id: w.id, left: w.left, top: w.top, width: w.width, height: w.height,
      activeTabTitle: w.tabs?.find((t) => t.active)?.title, tabCount: w.tabs?.length,
    })));

    const matched = matchWindowsByBounds(nativeResponse.windows, extensionWindows);
    tgwlLog('match-result', `${matched.length} matches:`, JSON.stringify(matched));

    // Log match results to disk via native host
    logExtensionData('match_result', {
      matchCount: matched.length,
      matches: matched,
      nativeWindowCount: nativeResponse.windows.length,
      extensionWindowCount: extensionWindows.length,
    });

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

    tgwlLog('cache-write', 'Updating cache:', JSON.stringify(windowNames));
    await chrome.storage.local.set({ windowNames });

    // Log final cache state to disk
    logExtensionData('cache_updated', { windowNames });
  /* istanbul ignore next - defensive catch for native host errors */
  } catch (e) {
    tgwlError('error', 'fetchAndCacheWindowNames failed:', e?.message || e);
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
  } catch (e) {
    tgwlError('error', `updateUrlFingerprint(${windowId}) failed:`, e?.message || e);
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
    tgwlLog('cache-read', 'Startup cache:', JSON.stringify(windowNames));

    // Collect closed entries
    const closedEntries = [];
    for (const [id, entry] of Object.entries(windowNames)) {
      if (entry.closed) {
        closedEntries.push({ id, ...entry });
      }
    }

    if (closedEntries.length === 0) {
      tgwlLog('startup-match', 'No closed entries, skipping');
      return;
    }

    // Get current windows
    const currentWindows = await chrome.windows.getAll({ populate: true });

    // Find current windows that don't have cached names
    const unmatchedWindows = currentWindows.filter(
      (w) => !windowNames[String(w.id)] || windowNames[String(w.id)].closed,
    );

    if (unmatchedWindows.length === 0) {
      tgwlLog('startup-match', 'All windows already cached, skipping');
      return;
    }

    tgwlLog('startup-match', `${closedEntries.length} closed entries, ${unmatchedWindows.length} unmatched windows`);
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

        tgwlLog('startup-match', `Window ${win.id} vs closed ${closed.id} ("${closed.name}"): Jaccard=${similarity.toFixed(3)}`);

        if (similarity > bestSimilarity && similarity >= JACCARD_THRESHOLD) {
          bestMatch = closed;
          bestSimilarity = similarity;
        }
      }

      if (bestMatch) {
        tgwlLog('startup-match', `Matched window ${win.id} -> "${bestMatch.name}" (similarity=${bestSimilarity.toFixed(3)})`);
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
  } catch (e) {
    tgwlError('error', 'handleStartupMatching failed:', e?.message || e);
  }
}

// --- Window focus order tracking for MRU sort ---

let windowFocusOrder = []; // Most recent window ID first

/**
 * Initialize focus order from storage.
 * If none of the stored IDs match current windows (e.g. after Chrome restart),
 * re-seed with the current window IDs in default order.
 */
async function initFocusOrder() {
  try {
    const stored = await chrome.storage.local.get('windowFocusOrder');
    const storedOrder = stored.windowFocusOrder || [];
    const wins = await chrome.windows.getAll();
    const currentIds = new Set(wins.map(w => w.id));

    // Check if any stored IDs are still valid
    const hasValidIds = storedOrder.some(id => currentIds.has(id));

    if (storedOrder.length === 0 || !hasValidIds) {
      // No stored order or all IDs are stale — seed with current windows
      windowFocusOrder = wins.map(w => w.id);
    } else {
      // Keep valid IDs in their stored order, append any new windows at the end
      const validOrder = storedOrder.filter(id => currentIds.has(id));
      const validSet = new Set(validOrder);
      const newIds = wins.filter(w => !validSet.has(w.id)).map(w => w.id);
      windowFocusOrder = [...validOrder, ...newIds];
    }

    await chrome.storage.local.set({ windowFocusOrder });
  } catch (_e) {
    // Non-critical
  }
}

// Track window focus changes
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;
  // Move to front
  windowFocusOrder = [windowId, ...windowFocusOrder.filter(id => id !== windowId)];
  try {
    await chrome.storage.local.set({ windowFocusOrder });
  } catch (_e) {
    // Non-critical
  }
});

// --- Event listener registration ---

// Window created: fetch fresh names from native host
chrome.windows.onCreated.addListener(async (_window) => {
  await fetchAndCacheWindowNames();
});

// Window removed: mark as closed but retain for restart matching, clean up focus order
chrome.windows.onRemoved.addListener(async (windowId) => {
  try {
    const stored = await chrome.storage.local.get('windowNames');
    /* istanbul ignore next - defensive fallback for missing storage key */
    const windowNames = stored.windowNames || {};
    const key = String(windowId);

    if (windowNames[key]) {
      tgwlLog('cache-write', `Marking window ${windowId} as closed`);
      windowNames[key].closed = true;
      await chrome.storage.local.set({ windowNames });
    }
  /* istanbul ignore next - defensive catch for storage errors */
  } catch (e) {
    tgwlError('error', `onRemoved(${windowId}) failed:`, e?.message || e);
  }

  // Clean up focus order: remove all IDs that no longer correspond to open windows
  try {
    const currentWindows = await chrome.windows.getAll();
    const currentIds = new Set(currentWindows.map(w => w.id));
    const cleaned = windowFocusOrder.filter(id => currentIds.has(id));
    if (cleaned.length !== windowFocusOrder.length) {
      windowFocusOrder = cleaned;
      await chrome.storage.local.set({ windowFocusOrder });
    }
  } catch (_e) {
    // Non-critical
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

/**
 * Run full diagnostic pipeline and return structured report.
 * @returns {Promise<Object>} Diagnostic report
 */
async function runDiagnosis() {
  const diagnosis = {
    timestamp: new Date().toISOString(),
    nativeHost: { name: NATIVE_HOST_NAME, reachable: false, error: null, rawResponse: null, windowCount: 0, customNameCount: 0 },
    extensionWindows: [],
    matching: { pairs: [], totalMatches: 0 },
    cache: { before: {}, after: {} },
  };

  try {
    // Read cache before
    const storedBefore = await chrome.storage.local.get('windowNames');
    diagnosis.cache.before = storedBefore.windowNames || {};

    // Call native host
    const diagBrowser = detectBrowser();
    const nativeResponse = await new Promise((resolve) => {
      chrome.runtime.sendNativeMessage(
        NATIVE_HOST_NAME,
        { action: 'get_window_names', browser: diagBrowser },
        (response) => {
          if (chrome.runtime.lastError || !response) {
            diagnosis.nativeHost.error = chrome.runtime.lastError?.message || 'no response';
            resolve(null);
            return;
          }
          resolve(response);
        },
      );
    });

    if (nativeResponse && nativeResponse.success) {
      diagnosis.nativeHost.reachable = true;
      diagnosis.nativeHost.rawResponse = nativeResponse;
      diagnosis.nativeHost.windowCount = nativeResponse.windows?.length || 0;
      diagnosis.nativeHost.customNameCount = (nativeResponse.windows || []).filter((w) => w.hasCustomName).length;
    }

    // Get extension windows
    const extensionWindows = await chrome.windows.getAll({ populate: true });
    diagnosis.extensionWindows = extensionWindows.map((w) => ({
      id: w.id, left: w.left, top: w.top, width: w.width, height: w.height,
      activeTabTitle: w.tabs?.find((t) => t.active)?.title || null,
      tabCount: w.tabs?.length || 0,
    }));

    // Run matching with detailed scoring
    if (nativeResponse?.success && nativeResponse.windows) {
      for (const native of nativeResponse.windows) {
        if (!native.hasCustomName) continue;
        const bounds = native.bounds;
        if (!bounds) continue;

        for (const ext of extensionWindows) {
          let titleScore = 0;
          let boundsScore = 0;

          if (bounds.x === ext.left && bounds.y === ext.top && bounds.width === ext.width && bounds.height === ext.height) {
            boundsScore = 1;
          }
          if (native.activeTabTitle && ext.tabs) {
            const activeTab = ext.tabs.find((t) => t.active);
            if (activeTab && activeTab.title === native.activeTabTitle) {
              titleScore = 2;
            }
          }

          const totalScore = titleScore + boundsScore;
          diagnosis.matching.pairs.push({
            nativeName: native.name, nativeTitle: native.activeTabTitle || null,
            nativeBounds: bounds, extId: ext.id,
            extTitle: ext.tabs?.find((t) => t.active)?.title || null,
            extBounds: { x: ext.left, y: ext.top, width: ext.width, height: ext.height },
            titleScore, boundsScore, totalScore, matched: false,
          });
        }
      }

      // Mark actual matches
      const matched = matchWindowsByBounds(nativeResponse.windows, extensionWindows);
      diagnosis.matching.totalMatches = matched.length;
      for (const m of matched) {
        const pair = diagnosis.matching.pairs.find((p) => p.nativeName === m.name && p.extId === m.windowId);
        /* istanbul ignore else - pair always exists since scoring creates all combos */
        if (pair) pair.matched = true;
      }
    }

    // Read cache after
    const storedAfter = await chrome.storage.local.get('windowNames');
    diagnosis.cache.after = storedAfter.windowNames || {};

    // Fetch host debug log tail
    if (diagnosis.nativeHost.reachable) {
      try {
        const logResponse = await new Promise((resolve) => {
          chrome.runtime.sendNativeMessage(
            NATIVE_HOST_NAME,
            { action: 'get_debug_log' },
            (response) => {
              if (chrome.runtime.lastError || !response) {
                resolve(null);
                return;
              }
              resolve(response);
            },
          );
        });
        diagnosis.hostLogTail = logResponse?.log || '(unavailable)';
      } catch (_e) {
        /* istanbul ignore next - defensive: Promise wrapper prevents throw */
        diagnosis.hostLogTail = '(error fetching log)';
      }
    } else {
      diagnosis.hostLogTail = '(native host not reachable)';
    }

  /* istanbul ignore next - defensive */
  } catch (e) {
    diagnosis.error = e?.message || String(e);
  }

  return diagnosis;
}

// Message API for popup.js
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.action === 'getWindowNames') {
    tgwlLog('cache-read', 'Popup requested window names');
    // Always fetch fresh data from native host before returning,
    // to avoid race condition where popup reads stale/empty cache
    // before the service worker's startup fetch has completed.
    fetchAndCacheWindowNames().then(() => {
      return chrome.storage.local.get('windowNames');
    }).then((stored) => {
      /* istanbul ignore next - defensive fallback for missing storage key */
      const names = stored.windowNames || {};
      tgwlLog('cache-read', 'Returning cache to popup:', JSON.stringify(names));
      sendResponse({
        success: true,
        windowNames: names,
      });
    });
    return true; // Keep message channel open for async response
  }

  if (message.action === 'getWindowFocusOrder') {
    sendResponse({ success: true, focusOrder: windowFocusOrder });
    return false;
  }

  if (message.action === 'diagnose') {
    tgwlLog('diagnose', 'Running diagnostic pipeline');
    runDiagnosis().then((diagnosis) => {
      tgwlLog('diagnose', 'Diagnostic complete');
      sendResponse({ success: true, diagnosis });
    });
    return true; // Keep message channel open for async response
  }

  sendResponse({
    success: false,
    error: `Unknown action: ${message.action}`,
  });
  return false;
});

// On service worker start: fetch names, handle startup matching, init focus order
fetchAndCacheWindowNames();
handleStartupMatching();
initFocusOrder();

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
    runDiagnosis,
    logExtensionData,
    detectBrowser,
    initFocusOrder,
    tgwlLog,
    tgwlError,
    NATIVE_HOST_NAME,
    JACCARD_THRESHOLD,
  };
}

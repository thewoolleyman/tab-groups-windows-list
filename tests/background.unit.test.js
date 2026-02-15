/**
 * Unit tests for background.js service worker
 *
 * RED phase: These tests define the expected behavior for the background
 * service worker that bridges the native messaging host and the extension.
 *
 * background.js responsibilities:
 * 1. Call native host on startup and on chrome.windows.onCreated
 * 2. Match native host response windows to extension windows by bounds
 * 3. Cache {windowId: {name, urlFingerprint}} in chrome.storage.local
 * 4. Update urlFingerprint on tab events (created/removed/updated/attached/detached)
 * 5. Mark closed windows but retain for restart matching
 * 6. On startup: match via Jaccard similarity of hostname sets
 * 7. Expose a message API for popup.js via chrome.runtime.sendMessage
 */

// --- Chrome API mock setup ---
let windowsCreatedListeners = [];
let windowsRemovedListeners = [];
let tabsCreatedListeners = [];
let tabsRemovedListeners = [];
let tabsUpdatedListeners = [];
let tabsAttachedListeners = [];
let tabsDetachedListeners = [];
let runtimeMessageListeners = [];
let runtimeInstalledListeners = [];
let storageData = {};

const mockChrome = {
  runtime: {
    sendNativeMessage: jest.fn(),
    onMessage: {
      addListener: jest.fn((fn) => runtimeMessageListeners.push(fn)),
    },
    onInstalled: {
      addListener: jest.fn((fn) => runtimeInstalledListeners.push(fn)),
    },
  },
  windows: {
    getAll: jest.fn(),
    onCreated: {
      addListener: jest.fn((fn) => windowsCreatedListeners.push(fn)),
    },
    onRemoved: {
      addListener: jest.fn((fn) => windowsRemovedListeners.push(fn)),
    },
  },
  tabs: {
    query: jest.fn(),
    onCreated: {
      addListener: jest.fn((fn) => tabsCreatedListeners.push(fn)),
    },
    onRemoved: {
      addListener: jest.fn((fn) => tabsRemovedListeners.push(fn)),
    },
    onUpdated: {
      addListener: jest.fn((fn) => tabsUpdatedListeners.push(fn)),
    },
    onAttached: {
      addListener: jest.fn((fn) => tabsAttachedListeners.push(fn)),
    },
    onDetached: {
      addListener: jest.fn((fn) => tabsDetachedListeners.push(fn)),
    },
  },
  storage: {
    local: {
      get: jest.fn((keys) => Promise.resolve(storageData)),
      set: jest.fn((data) => {
        Object.assign(storageData, data);
        return Promise.resolve();
      }),
    },
  },
};

// Set globals before requiring background.js
global.chrome = mockChrome;

// Helper to reset all mocks
function resetMocks() {
  windowsCreatedListeners = [];
  windowsRemovedListeners = [];
  tabsCreatedListeners = [];
  tabsRemovedListeners = [];
  tabsUpdatedListeners = [];
  tabsAttachedListeners = [];
  tabsDetachedListeners = [];
  runtimeMessageListeners = [];
  runtimeInstalledListeners = [];
  storageData = {};
  jest.clearAllMocks();

  // Re-register listener capture functions
  mockChrome.windows.onCreated.addListener.mockImplementation((fn) =>
    windowsCreatedListeners.push(fn),
  );
  mockChrome.windows.onRemoved.addListener.mockImplementation((fn) =>
    windowsRemovedListeners.push(fn),
  );
  mockChrome.tabs.onCreated.addListener.mockImplementation((fn) =>
    tabsCreatedListeners.push(fn),
  );
  mockChrome.tabs.onRemoved.addListener.mockImplementation((fn) =>
    tabsRemovedListeners.push(fn),
  );
  mockChrome.tabs.onUpdated.addListener.mockImplementation((fn) =>
    tabsUpdatedListeners.push(fn),
  );
  mockChrome.tabs.onAttached.addListener.mockImplementation((fn) =>
    tabsAttachedListeners.push(fn),
  );
  mockChrome.tabs.onDetached.addListener.mockImplementation((fn) =>
    tabsDetachedListeners.push(fn),
  );
  mockChrome.runtime.onMessage.addListener.mockImplementation((fn) =>
    runtimeMessageListeners.push(fn),
  );
  mockChrome.runtime.onInstalled.addListener.mockImplementation((fn) =>
    runtimeInstalledListeners.push(fn),
  );
}

// --- Import background.js (will fail until the file exists) ---
// Listeners registered at module load time are captured here
let background;
let initialListeners = {};

beforeAll(() => {
  background = require('../background.js');
  // Save references to listeners registered at module load time
  initialListeners = {
    windowsCreated: [...windowsCreatedListeners],
    windowsRemoved: [...windowsRemovedListeners],
    tabsCreated: [...tabsCreatedListeners],
    tabsRemoved: [...tabsRemovedListeners],
    tabsUpdated: [...tabsUpdatedListeners],
    tabsAttached: [...tabsAttachedListeners],
    tabsDetached: [...tabsDetachedListeners],
    runtimeMessage: [...runtimeMessageListeners],
  };
});

beforeEach(() => {
  resetMocks();
});

// =============================================================
// 0. Native host name consistency
// =============================================================

describe('native host name consistency', () => {
  test('NATIVE_HOST_NAME should match the installer manifest name', () => {
    // The native messaging host is registered as 'com.tabgroups.window_namer'
    // by install.sh and installer.py. background.js must use the same name.
    expect(background.NATIVE_HOST_NAME).toBe('com.tabgroups.window_namer');
  });
});

// =============================================================
// 1. Module exports and utility functions
// =============================================================

describe('background.js module exports', () => {
  test('should export computeUrlFingerprint function', () => {
    expect(typeof background.computeUrlFingerprint).toBe('function');
  });

  test('should export matchWindowsByBounds function', () => {
    expect(typeof background.matchWindowsByBounds).toBe('function');
  });

  test('should export jaccardSimilarity function', () => {
    expect(typeof background.jaccardSimilarity).toBe('function');
  });

  test('should export fetchAndCacheWindowNames function', () => {
    expect(typeof background.fetchAndCacheWindowNames).toBe('function');
  });

  test('should export updateUrlFingerprint function', () => {
    expect(typeof background.updateUrlFingerprint).toBe('function');
  });

  test('should export handleStartupMatching function', () => {
    expect(typeof background.handleStartupMatching).toBe('function');
  });
});

// =============================================================
// 2. computeUrlFingerprint
// =============================================================

describe('computeUrlFingerprint', () => {
  test('should extract sorted unique hostnames joined with pipe', () => {
    const tabs = [
      { url: 'https://github.com/some/repo' },
      { url: 'https://google.com/search?q=test' },
      { url: 'https://github.com/another/repo' },
    ];
    const result = background.computeUrlFingerprint(tabs);
    expect(result).toBe('github.com|google.com');
  });

  test('should return empty string for empty tabs array', () => {
    expect(background.computeUrlFingerprint([])).toBe('');
  });

  test('should handle tabs with no URL', () => {
    const tabs = [
      { url: 'https://example.com' },
      { },
      { url: '' },
    ];
    const result = background.computeUrlFingerprint(tabs);
    expect(result).toBe('example.com');
  });

  test('should handle chrome:// URLs by including them', () => {
    const tabs = [
      { url: 'chrome://extensions' },
      { url: 'https://example.com' },
    ];
    const result = background.computeUrlFingerprint(tabs);
    // chrome:// URLs have "extensions" as hostname-like part
    // Implementation should handle gracefully
    expect(result).toContain('example.com');
  });

  test('should deduplicate hostnames', () => {
    const tabs = [
      { url: 'https://github.com/page1' },
      { url: 'https://github.com/page2' },
      { url: 'https://github.com/page3' },
    ];
    expect(background.computeUrlFingerprint(tabs)).toBe('github.com');
  });

  test('should sort hostnames alphabetically', () => {
    const tabs = [
      { url: 'https://zebra.com' },
      { url: 'https://alpha.com' },
      { url: 'https://middle.com' },
    ];
    expect(background.computeUrlFingerprint(tabs)).toBe('alpha.com|middle.com|zebra.com');
  });

  test('should handle about:blank and other special URLs', () => {
    const tabs = [
      { url: 'about:blank' },
      { url: 'https://example.com' },
    ];
    const result = background.computeUrlFingerprint(tabs);
    expect(result).toContain('example.com');
  });
});

// =============================================================
// 3. matchWindowsByBounds
// =============================================================

describe('matchWindowsByBounds', () => {
  test('should match native windows to extension windows by bounds', () => {
    const nativeWindows = [
      { name: 'My Window', bounds: { x: 0, y: 0, width: 1920, height: 1080 }, hasCustomName: true },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 0, width: 1920, height: 1080, tabs: [] },
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toEqual([
      { windowId: 1, name: 'My Window', hasCustomName: true },
    ]);
  });

  test('should match multiple windows correctly', () => {
    const nativeWindows = [
      { name: 'Window A', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true },
      { name: 'Window B', bounds: { x: 100, y: 100, width: 1024, height: 768 }, hasCustomName: true },
    ];
    const extensionWindows = [
      { id: 1, left: 100, top: 100, width: 1024, height: 768, tabs: [] },
      { id: 2, left: 0, top: 0, width: 800, height: 600, tabs: [] },
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toContainEqual({ windowId: 2, name: 'Window A', hasCustomName: true });
    expect(result).toContainEqual({ windowId: 1, name: 'Window B', hasCustomName: true });
  });

  test('should return empty array when no matches found', () => {
    const nativeWindows = [
      { name: 'Window', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true },
    ];
    const extensionWindows = [
      { id: 1, left: 500, top: 500, width: 1920, height: 1080, tabs: [] },
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toEqual([]);
  });

  test('should handle empty native windows array', () => {
    const result = background.matchWindowsByBounds([], [{ id: 1, left: 0, top: 0, width: 800, height: 600, tabs: [] }]);
    expect(result).toEqual([]);
  });

  test('should handle empty extension windows array', () => {
    const result = background.matchWindowsByBounds(
      [{ name: 'Win', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true }],
      [],
    );
    expect(result).toEqual([]);
  });

  test('should only return matches for windows with hasCustomName true', () => {
    const nativeWindows = [
      { name: 'Tab Title', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: false },
      { name: 'Custom Name', bounds: { x: 100, y: 100, width: 1024, height: 768 }, hasCustomName: true },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 0, width: 800, height: 600, tabs: [] },
      { id: 2, left: 100, top: 100, width: 1024, height: 768, tabs: [] },
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    // Only the window with hasCustomName: true should be in results
    expect(result).toEqual([
      { windowId: 2, name: 'Custom Name', hasCustomName: true },
    ]);
  });
});

// =============================================================
// 3b. matchWindowsByBounds - title-based matching (realistic macOS)
// =============================================================

describe('matchWindowsByBounds - title-based matching', () => {
  // Shared bounds that simulate maximized macOS windows (common real-world scenario)
  const SHARED_BOUNDS = { x: 0, y: 33, width: 1728, height: 1084 };

  test('should match 3 windows sharing identical bounds via activeTabTitle', () => {
    const nativeWindows = [
      { name: 'Dev Window', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'GitHub - repo' },
      { name: 'Research', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'Google Scholar' },
      { name: 'Comms', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'Slack | general' },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Slack | general', active: true },
        { title: 'Discord', active: false },
      ]},
      { id: 2, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'GitHub - repo', active: true },
        { title: 'VS Code', active: false },
      ]},
      { id: 3, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Google Scholar', active: true },
        { title: 'Wikipedia', active: false },
      ]},
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toHaveLength(3);
    expect(result).toContainEqual({ windowId: 2, name: 'Dev Window', hasCustomName: true });
    expect(result).toContainEqual({ windowId: 3, name: 'Research', hasCustomName: true });
    expect(result).toContainEqual({ windowId: 1, name: 'Comms', hasCustomName: true });
  });

  test('should match mix of shared + unique bounds correctly', () => {
    const nativeWindows = [
      { name: 'Maximized A', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'Tab A' },
      { name: 'Maximized B', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'Tab B' },
      { name: 'Side Window', bounds: { x: 900, y: 33, width: 800, height: 600 }, hasCustomName: true, activeTabTitle: 'Tab C' },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Tab B', active: true },
      ]},
      { id: 2, left: 900, top: 33, width: 800, height: 600, tabs: [
        { title: 'Tab C', active: true },
      ]},
      { id: 3, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Tab A', active: true },
      ]},
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toHaveLength(3);
    expect(result).toContainEqual({ windowId: 3, name: 'Maximized A', hasCustomName: true });
    expect(result).toContainEqual({ windowId: 1, name: 'Maximized B', hasCustomName: true });
    expect(result).toContainEqual({ windowId: 2, name: 'Side Window', hasCustomName: true });
  });

  test('should use bounds as tiebreaker when activeTabTitle matches multiple windows', () => {
    // Two native windows with same activeTabTitle but different bounds
    const nativeWindows = [
      { name: 'Left GitHub', bounds: { x: 0, y: 0, width: 960, height: 1080 }, hasCustomName: true, activeTabTitle: 'GitHub' },
      { name: 'Right GitHub', bounds: { x: 960, y: 0, width: 960, height: 1080 }, hasCustomName: true, activeTabTitle: 'GitHub' },
    ];
    const extensionWindows = [
      { id: 1, left: 960, top: 0, width: 960, height: 1080, tabs: [
        { title: 'GitHub', active: true },
      ]},
      { id: 2, left: 0, top: 0, width: 960, height: 1080, tabs: [
        { title: 'GitHub', active: true },
      ]},
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toHaveLength(2);
    expect(result).toContainEqual({ windowId: 2, name: 'Left GitHub', hasCustomName: true });
    expect(result).toContainEqual({ windowId: 1, name: 'Right GitHub', hasCustomName: true });
  });

  // --- Edge cases ---

  test('should fall back to bounds-only when native window missing activeTabTitle', () => {
    const nativeWindows = [
      { name: 'Legacy Window', bounds: { x: 0, y: 0, width: 1920, height: 1080 }, hasCustomName: true },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 0, width: 1920, height: 1080, tabs: [
        { title: 'Some Tab', active: true },
      ]},
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toEqual([
      { windowId: 1, name: 'Legacy Window', hasCustomName: true },
    ]);
  });

  test('should fall back to bounds-only when extension window has no tabs array', () => {
    const nativeWindows = [
      { name: 'Window', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true, activeTabTitle: 'My Tab' },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 0, width: 800, height: 600 },
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toEqual([
      { windowId: 1, name: 'Window', hasCustomName: true },
    ]);
  });

  test('should fall back to bounds-only when extension window has no active tab', () => {
    const nativeWindows = [
      { name: 'Window', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true, activeTabTitle: 'My Tab' },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 0, width: 800, height: 600, tabs: [
        { title: 'Tab 1', active: false },
        { title: 'Tab 2', active: false },
      ]},
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    expect(result).toEqual([
      { windowId: 1, name: 'Window', hasCustomName: true },
    ]);
  });

  test('should prevent one extension window from matching twice (dedup)', () => {
    // Two native windows both want the same extension window
    const nativeWindows = [
      { name: 'First', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'Unique Tab' },
      { name: 'Second', bounds: SHARED_BOUNDS, hasCustomName: true, activeTabTitle: 'Unique Tab' },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Unique Tab', active: true },
      ]},
      { id: 2, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Other Tab', active: true },
      ]},
    ];
    const result = background.matchWindowsByBounds(nativeWindows, extensionWindows);
    // Extension window 1 should only be matched once
    const idsMatched = result.map(r => r.windowId);
    const uniqueIds = new Set(idsMatched);
    expect(uniqueIds.size).toBe(idsMatched.length);
  });
});

// =============================================================
// 4. jaccardSimilarity
// =============================================================

describe('jaccardSimilarity', () => {
  test('should return 1.0 for identical sets', () => {
    expect(background.jaccardSimilarity('a|b|c', 'a|b|c')).toBe(1.0);
  });

  test('should return 0.0 for completely disjoint sets', () => {
    expect(background.jaccardSimilarity('a|b', 'c|d')).toBe(0.0);
  });

  test('should calculate correct similarity for overlapping sets', () => {
    // intersection = {a, b}, union = {a, b, c, d} => 2/4 = 0.5
    expect(background.jaccardSimilarity('a|b|c', 'a|b|d')).toBeCloseTo(0.5, 5);
  });

  test('should return 0.0 for two empty strings', () => {
    expect(background.jaccardSimilarity('', '')).toBe(0.0);
  });

  test('should return 0.0 when one is empty and other is not', () => {
    expect(background.jaccardSimilarity('a|b', '')).toBe(0.0);
    expect(background.jaccardSimilarity('', 'a|b')).toBe(0.0);
  });

  test('should handle single-element fingerprints', () => {
    expect(background.jaccardSimilarity('github.com', 'github.com')).toBe(1.0);
    expect(background.jaccardSimilarity('github.com', 'google.com')).toBe(0.0);
  });
});

// =============================================================
// 5. fetchAndCacheWindowNames
// =============================================================

describe('fetchAndCacheWindowNames', () => {
  test('should call native host with get_window_names action', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({ success: true, windows: [] });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    await background.fetchAndCacheWindowNames();

    expect(mockChrome.runtime.sendNativeMessage).toHaveBeenCalledWith(
      'com.tabgroups.window_namer',
      { action: 'get_window_names', browser: expect.any(String) },
      expect.any(Function),
    );
  });

  test('should match native windows to extension windows and cache names', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({
          success: true,
          windows: [
            { name: 'Dev Window', bounds: { x: 0, y: 0, width: 1920, height: 1080 }, hasCustomName: true },
          ],
        });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, left: 0, top: 0, width: 1920, height: 1080, tabs: [{ url: 'https://github.com' }] },
    ]);

    await background.fetchAndCacheWindowNames();

    expect(mockChrome.storage.local.set).toHaveBeenCalled();
    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    expect(setCall.windowNames).toBeDefined();
    expect(setCall.windowNames['1']).toBeDefined();
    expect(setCall.windowNames['1'].name).toBe('Dev Window');
    expect(setCall.windowNames['1'].urlFingerprint).toBe('github.com');
  });

  test('should handle native host failure gracefully', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({ success: false, error: 'Host not found' });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    // Should not throw
    await expect(background.fetchAndCacheWindowNames()).resolves.not.toThrow();
  });

  test('should handle chrome.runtime.lastError gracefully', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        chrome.runtime.lastError = { message: 'Native host has exited.' };
        callback(undefined);
        chrome.runtime.lastError = undefined;
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    await expect(background.fetchAndCacheWindowNames()).resolves.not.toThrow();
  });

  test('should compute urlFingerprint for each matched window', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({
          success: true,
          windows: [
            { name: 'Test Win', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true },
          ],
        });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 42,
        left: 0, top: 0, width: 800, height: 600,
        tabs: [
          { url: 'https://github.com/repo' },
          { url: 'https://stackoverflow.com/question' },
        ],
      },
    ]);

    await background.fetchAndCacheWindowNames();

    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    expect(setCall.windowNames['42'].urlFingerprint).toBe('github.com|stackoverflow.com');
  });
});

// =============================================================
// 6. updateUrlFingerprint
// =============================================================

describe('updateUrlFingerprint', () => {
  test('should update the fingerprint for the affected window', async () => {
    // Set up existing cache
    storageData = {
      windowNames: {
        '1': { name: 'My Window', urlFingerprint: 'github.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // The window now has a new tab
    mockChrome.tabs.query.mockResolvedValue([
      { url: 'https://github.com/repo' },
      { url: 'https://google.com/search' },
    ]);

    await background.updateUrlFingerprint(1);

    expect(mockChrome.storage.local.set).toHaveBeenCalled();
    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    expect(setCall.windowNames['1'].urlFingerprint).toBe('github.com|google.com');
    expect(setCall.windowNames['1'].name).toBe('My Window');
  });

  test('should not update if window is not in cache', async () => {
    storageData = { windowNames: {} };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    await background.updateUrlFingerprint(999);

    expect(mockChrome.storage.local.set).not.toHaveBeenCalled();
  });

  test('should handle empty tabs list', async () => {
    storageData = {
      windowNames: {
        '5': { name: 'Empty Win', urlFingerprint: 'old.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);
    mockChrome.tabs.query.mockResolvedValue([]);

    await background.updateUrlFingerprint(5);

    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    expect(setCall.windowNames['5'].urlFingerprint).toBe('');
  });
});

// =============================================================
// 7. Window removal (mark as closed, retain for restart matching)
// =============================================================

describe('window removal handling', () => {
  test('should not modify cache if window is not cached', async () => {
    storageData = { windowNames: {} };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    const listener = initialListeners.windowsRemoved[0];
    await listener(999);

    // set should not be called since window 999 is not in cache
    expect(mockChrome.storage.local.set).not.toHaveBeenCalled();
  });

  test('should mark window as closed but retain in cache', async () => {
    storageData = {
      windowNames: {
        '1': { name: 'My Window', urlFingerprint: 'github.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // Use listener captured at module load time
    expect(initialListeners.windowsRemoved.length).toBeGreaterThan(0);
    const listener = initialListeners.windowsRemoved[0];

    await listener(1);

    expect(mockChrome.storage.local.set).toHaveBeenCalled();
    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    expect(setCall.windowNames['1'].closed).toBe(true);
    expect(setCall.windowNames['1'].name).toBe('My Window');
  });
});

// =============================================================
// 8. Startup matching (Jaccard similarity)
// =============================================================

describe('handleStartupMatching', () => {
  test('should re-associate names from closed entries by Jaccard similarity', async () => {
    // Cached data from previous session with closed entries
    storageData = {
      windowNames: {
        '100': { name: 'Dev Window', urlFingerprint: 'github.com|stackoverflow.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // Current windows have similar tabs
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [
          { url: 'https://github.com/new-repo' },
          { url: 'https://stackoverflow.com/new-question' },
        ],
      },
    ]);

    await background.handleStartupMatching();

    expect(mockChrome.storage.local.set).toHaveBeenCalled();
    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    // Window 5 should be associated with 'Dev Window' name (Jaccard = 1.0 > 0.6)
    expect(setCall.windowNames['5'].name).toBe('Dev Window');
  });

  test('should not match when Jaccard similarity is below 0.6 threshold', async () => {
    storageData = {
      windowNames: {
        '100': { name: 'Dev Window', urlFingerprint: 'github.com|stackoverflow.com|docs.python.org|reddit.com|twitter.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // Current window has mostly different tabs
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [
          { url: 'https://github.com/repo' },
          { url: 'https://youtube.com' },
          { url: 'https://netflix.com' },
          { url: 'https://amazon.com' },
          { url: 'https://facebook.com' },
        ],
      },
    ]);

    await background.handleStartupMatching();

    const setCall = mockChrome.storage.local.set.mock.calls[0]?.[0];
    // Should not have matched the name since Jaccard < 0.6
    if (setCall && setCall.windowNames && setCall.windowNames['5']) {
      expect(setCall.windowNames['5'].name).not.toBe('Dev Window');
    }
  });

  test('should match best similarity when multiple closed entries exist', async () => {
    storageData = {
      windowNames: {
        '100': { name: 'Work Window', urlFingerprint: 'github.com|jira.com', closed: true },
        '200': { name: 'Fun Window', urlFingerprint: 'youtube.com|reddit.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [
          { url: 'https://youtube.com' },
          { url: 'https://reddit.com' },
        ],
      },
    ]);

    await background.handleStartupMatching();

    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    expect(setCall.windowNames['5'].name).toBe('Fun Window');
  });

  test('should skip non-closed entries when collecting closed entries', async () => {
    // Mix of closed and non-closed entries
    storageData = {
      windowNames: {
        '100': { name: 'Open Window', urlFingerprint: 'github.com' },
        '200': { name: 'Closed Window', urlFingerprint: 'github.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [{ url: 'https://github.com' }],
      },
    ]);

    await background.handleStartupMatching();

    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    // Should match the closed entry
    expect(setCall.windowNames['5'].name).toBe('Closed Window');
    // Open entry should remain untouched
    expect(setCall.windowNames['100']).toBeDefined();
    expect(setCall.windowNames['100'].name).toBe('Open Window');
  });

  test('should exit early when all current windows are already cached (not closed)', async () => {
    storageData = {
      windowNames: {
        '5': { name: 'Already Cached', urlFingerprint: 'github.com' },
        '100': { name: 'Closed Entry', urlFingerprint: 'reddit.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // Current window 5 is already cached and not closed
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [{ url: 'https://github.com' }],
      },
    ]);

    await background.handleStartupMatching();

    // storage.local.set should NOT have been called since all windows are already matched
    expect(mockChrome.storage.local.set).not.toHaveBeenCalled();
  });

  test('should not reassign closed entry already used by another window', async () => {
    storageData = {
      windowNames: {
        '100': { name: 'Shared Name', urlFingerprint: 'github.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [{ url: 'https://github.com' }],
      },
      {
        id: 6,
        left: 100, top: 100, width: 800, height: 600,
        tabs: [{ url: 'https://github.com' }],
      },
    ]);

    await background.handleStartupMatching();

    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    // Only one window should get the name (the first one matched)
    const namedWindows = Object.values(setCall.windowNames).filter(v => v.name === 'Shared Name');
    expect(namedWindows.length).toBe(1);
  });

  test('should remove matched closed entries after reassignment', async () => {
    storageData = {
      windowNames: {
        '100': { name: 'Dev Window', urlFingerprint: 'github.com', closed: true },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 5,
        left: 0, top: 0, width: 1920, height: 1080,
        tabs: [{ url: 'https://github.com' }],
      },
    ]);

    await background.handleStartupMatching();

    const setCall = mockChrome.storage.local.set.mock.calls[0][0];
    // Old closed entry should be removed
    expect(setCall.windowNames['100']).toBeUndefined();
    // New entry should exist
    expect(setCall.windowNames['5']).toBeDefined();
  });
});

// =============================================================
// 9. Message API for popup.js
// =============================================================

describe('message API for popup.js', () => {
  test('should register a runtime.onMessage listener', () => {
    expect(initialListeners.runtimeMessage.length).toBeGreaterThan(0);
  });

  test('should respond with cached names on getWindowNames message', async () => {
    storageData = {
      windowNames: {
        '1': { name: 'Dev Window', urlFingerprint: 'github.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // Handler now calls fetchAndCacheWindowNames() first, so mock native host
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({ success: true, windows: [] });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    // Use listener captured at module load time
    const listener = initialListeners.runtimeMessage[0];

    const sendResponse = jest.fn();
    const result = listener(
      { action: 'getWindowNames' },
      { tab: { id: 1 } },
      sendResponse,
    );

    // Should return true to indicate async response
    expect(result).toBe(true);

    // Wait for async processing (fetch + cache read)
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(sendResponse).toHaveBeenCalledWith({
      success: true,
      windowNames: {
        '1': { name: 'Dev Window', urlFingerprint: 'github.com' },
      },
    });
  });

  test('should trigger fresh fetchAndCacheWindowNames before returning cache', async () => {
    // Simulate race condition: cache is empty, but native host has data
    storageData = {};
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    // Native host will return a window with custom name
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({
          success: true,
          windows: [
            { name: 'My Dev Window', bounds: { x: 0, y: 0, width: 1920, height: 1080 }, hasCustomName: true, activeTabTitle: 'GitHub' },
          ],
        });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 42, left: 0, top: 0, width: 1920, height: 1080, tabs: [
        { url: 'https://github.com', title: 'GitHub', active: true },
      ]},
    ]);

    const listener = initialListeners.runtimeMessage[0];
    const sendResponse = jest.fn();
    listener(
      { action: 'getWindowNames' },
      { tab: { id: 1 } },
      sendResponse,
    );

    // Wait for async processing (fetch + cache read)
    await new Promise((resolve) => setTimeout(resolve, 50));

    // The handler should have fetched fresh data from native host
    expect(mockChrome.runtime.sendNativeMessage).toHaveBeenCalled();

    // Response should contain the freshly fetched window name
    expect(sendResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        success: true,
        windowNames: expect.objectContaining({
          '42': expect.objectContaining({ name: 'My Dev Window' }),
        }),
      }),
    );
  });

  test('should respond with error for unknown action', async () => {
    const listener = initialListeners.runtimeMessage[0];

    const sendResponse = jest.fn();
    listener(
      { action: 'unknownAction' },
      { tab: { id: 1 } },
      sendResponse,
    );

    // Wait for async processing
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(sendResponse).toHaveBeenCalledWith({
      success: false,
      error: expect.any(String),
    });
  });
});

// =============================================================
// 10. Event listener registration
// =============================================================

describe('event listener registration', () => {
  test('should register windows.onCreated listener', () => {
    expect(initialListeners.windowsCreated.length).toBeGreaterThan(0);
  });

  test('should register windows.onRemoved listener', () => {
    expect(initialListeners.windowsRemoved.length).toBeGreaterThan(0);
  });

  test('should register tabs.onCreated listener', () => {
    expect(initialListeners.tabsCreated.length).toBeGreaterThan(0);
  });

  test('should register tabs.onRemoved listener', () => {
    expect(initialListeners.tabsRemoved.length).toBeGreaterThan(0);
  });

  test('should register tabs.onUpdated listener', () => {
    expect(initialListeners.tabsUpdated.length).toBeGreaterThan(0);
  });

  test('should register tabs.onAttached listener', () => {
    expect(initialListeners.tabsAttached.length).toBeGreaterThan(0);
  });

  test('should register tabs.onDetached listener', () => {
    expect(initialListeners.tabsDetached.length).toBeGreaterThan(0);
  });

  test('should register runtime.onMessage listener', () => {
    expect(initialListeners.runtimeMessage.length).toBeGreaterThan(0);
  });
});

// =============================================================
// 11. Tab event handlers trigger fingerprint update
// =============================================================

describe('tab event handlers', () => {
  test('tabs.onCreated should trigger fingerprint update for the window', async () => {
    // Set up cache with one window
    storageData = {
      windowNames: {
        '1': { name: 'My Window', urlFingerprint: 'github.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);
    mockChrome.tabs.query.mockResolvedValue([
      { url: 'https://github.com' },
      { url: 'https://newsite.com' },
    ]);

    const listener = initialListeners.tabsCreated[0];

    // Simulate tab created event
    await listener({ id: 10, windowId: 1, url: 'https://newsite.com' });

    // Should have updated fingerprint
    expect(mockChrome.tabs.query).toHaveBeenCalledWith({ windowId: 1 });
  });

  test('tabs.onRemoved should trigger fingerprint update for the window', async () => {
    storageData = {
      windowNames: {
        '1': { name: 'My Window', urlFingerprint: 'github.com|google.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);
    mockChrome.tabs.query.mockResolvedValue([
      { url: 'https://github.com' },
    ]);

    const listener = initialListeners.tabsRemoved[0];

    // onRemoved passes (tabId, removeInfo)
    await listener(10, { windowId: 1, isWindowClosing: false });

    expect(mockChrome.tabs.query).toHaveBeenCalledWith({ windowId: 1 });
  });

  test('tabs.onUpdated should trigger fingerprint update for the tab window', async () => {
    storageData = {
      windowNames: {
        '1': { name: 'My Window', urlFingerprint: 'github.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);
    mockChrome.tabs.query.mockResolvedValue([
      { url: 'https://newdomain.com' },
    ]);

    const listener = initialListeners.tabsUpdated[0];

    // onUpdated passes (tabId, changeInfo, tab)
    await listener(10, { url: 'https://newdomain.com' }, { id: 10, windowId: 1 });

    expect(mockChrome.tabs.query).toHaveBeenCalledWith({ windowId: 1 });
  });

  test('tabs.onCreated should not update if tab has no windowId', async () => {
    const listener = initialListeners.tabsCreated[0];

    // Tab with no windowId
    await listener({ id: 10 });

    // Should not have queried tabs
    expect(mockChrome.tabs.query).not.toHaveBeenCalled();
  });

  test('tabs.onRemoved should not update if window is closing', async () => {
    const listener = initialListeners.tabsRemoved[0];

    // isWindowClosing is true - should skip update
    await listener(10, { windowId: 1, isWindowClosing: true });

    expect(mockChrome.tabs.query).not.toHaveBeenCalled();
  });

  test('tabs.onUpdated should not update if tab has no windowId', async () => {
    const listener = initialListeners.tabsUpdated[0];

    // Tab with no windowId
    await listener(10, { url: 'https://test.com' }, { id: 10 });

    expect(mockChrome.tabs.query).not.toHaveBeenCalled();
  });

  test('tabs.onAttached should trigger fingerprint update for the new window', async () => {
    storageData = {
      windowNames: {
        '2': { name: 'Target Window', urlFingerprint: 'github.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);
    mockChrome.tabs.query.mockResolvedValue([
      { url: 'https://github.com' },
      { url: 'https://attached.com' },
    ]);

    const listener = initialListeners.tabsAttached[0];

    // onAttached passes (tabId, attachInfo)
    await listener(10, { newWindowId: 2, newPosition: 0 });

    expect(mockChrome.tabs.query).toHaveBeenCalledWith({ windowId: 2 });
  });

  test('tabs.onDetached should trigger fingerprint update for the old window', async () => {
    storageData = {
      windowNames: {
        '3': { name: 'Source Window', urlFingerprint: 'github.com|detached.com' },
      },
    };
    mockChrome.storage.local.get.mockResolvedValue(storageData);
    mockChrome.tabs.query.mockResolvedValue([
      { url: 'https://github.com' },
    ]);

    const listener = initialListeners.tabsDetached[0];

    // onDetached passes (tabId, detachInfo)
    await listener(10, { oldWindowId: 3, oldPosition: 1 });

    expect(mockChrome.tabs.query).toHaveBeenCalledWith({ windowId: 3 });
  });
});

// =============================================================
// 12. Window onCreated triggers native host fetch
// =============================================================

describe('window creation handling', () => {
  test('windows.onCreated should trigger fetchAndCacheWindowNames', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({ success: true, windows: [] });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    const listener = initialListeners.windowsCreated[0];

    await listener({ id: 1 });

    // Should have called native host
    expect(mockChrome.runtime.sendNativeMessage).toHaveBeenCalled();
  });
});

// =============================================================
// 13. Structured logging (tgwlLog / tgwlError)
// =============================================================

describe('structured logging', () => {
  test('tgwlLog should log with [TGWL:<stage>] prefix', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    background.tgwlLog('test-stage', 'hello', 123);
    expect(consoleSpy).toHaveBeenCalledWith('[TGWL:test-stage]', 'hello', 123);
    consoleSpy.mockRestore();
  });

  test('tgwlError should log with [TGWL:<stage>] prefix via console.error', () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    background.tgwlError('test-stage', 'bad thing');
    expect(consoleSpy).toHaveBeenCalledWith('[TGWL:test-stage]', 'bad thing');
    consoleSpy.mockRestore();
  });

  test('fetchAndCacheWindowNames should log native-req on call', async () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        callback({ success: true, windows: [] });
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    await background.fetchAndCacheWindowNames();

    const logCalls = consoleSpy.mock.calls.map((c) => c[0]);
    expect(logCalls).toContain('[TGWL:native-req]');
    consoleSpy.mockRestore();
  });

  test('fetchAndCacheWindowNames should log error on native host failure', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        chrome.runtime.lastError = { message: 'Host not found' };
        callback(undefined);
        chrome.runtime.lastError = undefined;
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);

    await background.fetchAndCacheWindowNames();

    const errorCalls = consoleSpy.mock.calls.map((c) => c[0]);
    expect(errorCalls).toContain('[TGWL:native-res]');
    consoleSpy.mockRestore();
  });

  test('matchWindowsByBounds should log matching details', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    const nativeWindows = [
      { name: 'Win', bounds: { x: 0, y: 0, width: 800, height: 600 }, hasCustomName: true },
    ];
    const extensionWindows = [
      { id: 1, left: 0, top: 0, width: 800, height: 600, tabs: [] },
    ];
    background.matchWindowsByBounds(nativeWindows, extensionWindows);

    const logCalls = consoleSpy.mock.calls.map((c) => c[0]);
    expect(logCalls).toContain('[TGWL:matching]');
    consoleSpy.mockRestore();
  });
});

// =============================================================
// 14. Diagnostic message API (diagnose action)
// =============================================================

describe('diagnose action', () => {
  test('should respond with structured diagnosis report', async () => {
    // Set up native host to return windows
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        if (message.action === 'get_window_names') {
          callback({
            success: true,
            windows: [
              { name: 'Dev', bounds: { x: 0, y: 0, width: 1920, height: 1080 }, hasCustomName: true, activeTabTitle: 'GitHub' },
            ],
          });
        } else if (message.action === 'get_debug_log') {
          callback({ success: true, log: '2026-01-01 test log line' });
        } else {
          callback({ success: true });
        }
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, left: 0, top: 0, width: 1920, height: 1080, tabs: [
        { url: 'https://github.com', title: 'GitHub', active: true },
      ]},
    ]);
    storageData = { windowNames: {} };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

    const listener = initialListeners.runtimeMessage[0];
    const sendResponse = jest.fn();
    listener({ action: 'diagnose' }, { tab: { id: 1 } }, sendResponse);

    // Wait for async processing
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(sendResponse).toHaveBeenCalledWith(
      expect.objectContaining({
        success: true,
        diagnosis: expect.objectContaining({
          timestamp: expect.any(String),
          nativeHost: expect.objectContaining({
            name: 'com.tabgroups.window_namer',
            reachable: true,
          }),
          extensionWindows: expect.any(Array),
          matching: expect.objectContaining({
            pairs: expect.any(Array),
            totalMatches: expect.any(Number),
          }),
          cache: expect.objectContaining({
            before: expect.any(Object),
            after: expect.any(Object),
          }),
          hostLogTail: expect.any(String),
        }),
      }),
    );

    consoleSpy.mockRestore();
  });

  test('should report native host as unreachable when it fails', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        chrome.runtime.lastError = { message: 'Host not found' };
        callback(undefined);
        chrome.runtime.lastError = undefined;
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([]);
    storageData = { windowNames: {} };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});

    const listener = initialListeners.runtimeMessage[0];
    const sendResponse = jest.fn();
    listener({ action: 'diagnose' }, { tab: { id: 1 } }, sendResponse);

    await new Promise((resolve) => setTimeout(resolve, 100));

    const response = sendResponse.mock.calls[0][0];
    expect(response.success).toBe(true);
    expect(response.diagnosis.nativeHost.reachable).toBe(false);
    expect(response.diagnosis.nativeHost.error).toBeTruthy();
    expect(response.diagnosis.hostLogTail).toBe('(native host not reachable)');

    consoleSpy.mockRestore();
    console.error.mockRestore();
  });

  test('should include score breakdown in matching pairs', async () => {
    mockChrome.runtime.sendNativeMessage.mockImplementation(
      (hostName, message, callback) => {
        if (message.action === 'get_window_names') {
          callback({
            success: true,
            windows: [
              { name: 'Dev', bounds: { x: 0, y: 33, width: 1728, height: 1084 }, hasCustomName: true, activeTabTitle: 'GitHub' },
            ],
          });
        } else {
          callback({ success: true, log: '' });
        }
      },
    );
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'GitHub', active: true },
      ]},
      { id: 2, left: 0, top: 33, width: 1728, height: 1084, tabs: [
        { title: 'Other', active: true },
      ]},
    ]);
    storageData = { windowNames: {} };
    mockChrome.storage.local.get.mockResolvedValue(storageData);

    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

    const listener = initialListeners.runtimeMessage[0];
    const sendResponse = jest.fn();
    listener({ action: 'diagnose' }, { tab: { id: 1 } }, sendResponse);

    await new Promise((resolve) => setTimeout(resolve, 100));

    const diag = sendResponse.mock.calls[0][0].diagnosis;
    expect(diag.matching.pairs.length).toBe(2); // 1 native x 2 ext windows
    const matchedPair = diag.matching.pairs.find((p) => p.matched);
    expect(matchedPair).toBeDefined();
    expect(matchedPair.titleScore).toBe(2);
    expect(matchedPair.boundsScore).toBe(1);
    expect(matchedPair.totalScore).toBe(3);

    consoleSpy.mockRestore();
  });

  test('should export runDiagnosis function', () => {
    expect(typeof background.runDiagnosis).toBe('function');
  });
});

describe('detectBrowser', () => {
  test('should return Google Chrome when no specific browser detected', () => {
    expect(background.detectBrowser()).toBe('Google Chrome');
  });

  test('should export detectBrowser function', () => {
    expect(typeof background.detectBrowser).toBe('function');
  });
});

describe('logExtensionData', () => {
  test('should send log_extension_data to native host', () => {
    mockChrome.runtime.sendNativeMessage.mockClear();
    mockChrome.runtime.lastError = null;

    background.logExtensionData('test_event', { key: 'value' });

    expect(mockChrome.runtime.sendNativeMessage).toHaveBeenCalledWith(
      'com.tabgroups.window_namer',
      {
        action: 'log_extension_data',
        data: { source: 'background.js', event: 'test_event', key: 'value' },
      },
      expect.any(Function),
    );
  });

  test('should not throw when native host returns error', () => {
    mockChrome.runtime.sendNativeMessage.mockClear();
    mockChrome.runtime.lastError = { message: 'host not found' };

    expect(() => {
      background.logExtensionData('test_event', { key: 'value' });
      // Trigger the callback to simulate error response
      const callback = mockChrome.runtime.sendNativeMessage.mock.calls[0][2];
      callback(null);
    }).not.toThrow();
  });

  test('should export logExtensionData function', () => {
    expect(typeof background.logExtensionData).toBe('function');
  });
});

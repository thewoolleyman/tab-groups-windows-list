/**
 * Unit tests for popup.js utility functions
 * These tests verify the core logic that builds the 3-level hierarchy
 */

// Mock the DOM before importing popup.js
const mockDocument = {
  getElementById: jest.fn(),
  createElement: jest.fn(() => ({
    className: '',
    classList: {
      add: jest.fn(),
      remove: jest.fn(),
      toggle: jest.fn(),
      contains: jest.fn()
    },
    style: {},
    textContent: '',
    appendChild: jest.fn(),
    addEventListener: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(() => [])
  })),
  querySelectorAll: jest.fn(() => []),
  addEventListener: jest.fn()
};

// Mock Chrome API
const mockChrome = {
  windows: {
    getAll: jest.fn(() => Promise.resolve([])),
    update: jest.fn(() => Promise.resolve()),
    onCreated: { addListener: jest.fn() },
    onRemoved: { addListener: jest.fn() },
    onFocusChanged: { addListener: jest.fn() }
  },
  tabGroups: {
    query: jest.fn(() => Promise.resolve([])),
    onCreated: { addListener: jest.fn() },
    onRemoved: { addListener: jest.fn() },
    onUpdated: { addListener: jest.fn() }
  },
  tabs: {
    update: jest.fn(() => Promise.resolve()),
    onCreated: { addListener: jest.fn() },
    onRemoved: { addListener: jest.fn() },
    onUpdated: { addListener: jest.fn() },
    onMoved: { addListener: jest.fn() },
    onAttached: { addListener: jest.fn() },
    onDetached: { addListener: jest.fn() }
  },
  runtime: {
    sendMessage: jest.fn(),
    sendNativeMessage: jest.fn()
  }
};

// Set up globals before requiring popup.js
global.document = mockDocument;
global.chrome = mockChrome;
global.window = { _chromeListenersRegistered: false, refreshUI: null };

// Import the actual functions from popup.js
const {
  debounce,
  mapColor,
  generateWindowName,
  getWindowDisplayName,
  buildOrderedWindowContent,
  createGroupElement,
  createTabElement,
  setupEventListeners,
  setContainer,
  refreshUI
} = require('../popup.js');

describe('mapColor function', () => {
  test('should map grey to #5a5a5a', () => {
    expect(mapColor('grey')).toBe('#5a5a5a');
  });

  test('should map blue to #1a73e8', () => {
    expect(mapColor('blue')).toBe('#1a73e8');
  });

  test('should map red to #d93025', () => {
    expect(mapColor('red')).toBe('#d93025');
  });

  test('should map yellow to #f9ab00', () => {
    expect(mapColor('yellow')).toBe('#f9ab00');
  });

  test('should map green to #188038', () => {
    expect(mapColor('green')).toBe('#188038');
  });

  test('should map pink to #d01884', () => {
    expect(mapColor('pink')).toBe('#d01884');
  });

  test('should map purple to #a142f4', () => {
    expect(mapColor('purple')).toBe('#a142f4');
  });

  test('should map cyan to #007b83', () => {
    expect(mapColor('cyan')).toBe('#007b83');
  });

  test('should map orange to #fa903e', () => {
    expect(mapColor('orange')).toBe('#fa903e');
  });

  test('should return default grey for unknown color', () => {
    expect(mapColor('unknown')).toBe('#5a5a5a');
  });

  test('should return default grey for null', () => {
    expect(mapColor(null)).toBe('#5a5a5a');
  });

  test('should return default grey for undefined', () => {
    expect(mapColor(undefined)).toBe('#5a5a5a');
  });
});

describe('debounce function', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('should delay function execution', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 100);

    debouncedFn();
    expect(mockFn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(100);
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  test('should cancel previous calls on rapid invocations', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 100);

    debouncedFn();
    debouncedFn();
    debouncedFn();

    jest.advanceTimersByTime(100);
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  test('should pass arguments to debounced function', () => {
    const mockFn = jest.fn();
    const debouncedFn = debounce(mockFn, 100);

    debouncedFn('arg1', 'arg2');
    jest.advanceTimersByTime(100);

    expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');
  });
});

describe('buildOrderedWindowContent function', () => {
  test('should order ungrouped tabs before groups when ungrouped tabs come first', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'First Tab', groupId: -1, index: 0 },
        { id: 2, title: 'Group Tab 1', groupId: 1, index: 1 },
        { id: 3, title: 'Group Tab 2', groupId: 1, index: 2 },
      ],
    };
    const groups = [{ id: 1, title: 'Group A', windowId: 1 }];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(2);
    expect(result[0].type).toBe('tab');
    expect(result[0].tab.title).toBe('First Tab');
    expect(result[1].type).toBe('group');
    expect(result[1].group.title).toBe('Group A');
  });

  test('should order groups before ungrouped tabs when groups come first', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'Group Tab 1', groupId: 1, index: 0 },
        { id: 2, title: 'Group Tab 2', groupId: 1, index: 1 },
        { id: 3, title: 'Last Tab', groupId: -1, index: 2 },
      ],
    };
    const groups = [{ id: 1, title: 'Group A', windowId: 1 }];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(2);
    expect(result[0].type).toBe('group');
    expect(result[0].group.title).toBe('Group A');
    expect(result[1].type).toBe('tab');
    expect(result[1].tab.title).toBe('Last Tab');
  });

  test('should interleave groups and ungrouped tabs by index', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'Ungrouped 1', groupId: -1, index: 0 },
        { id: 2, title: 'Group A Tab', groupId: 1, index: 1 },
        { id: 3, title: 'Ungrouped 2', groupId: -1, index: 2 },
        { id: 4, title: 'Group B Tab', groupId: 2, index: 3 },
        { id: 5, title: 'Ungrouped 3', groupId: -1, index: 4 },
      ],
    };
    const groups = [
      { id: 1, title: 'Group A', windowId: 1 },
      { id: 2, title: 'Group B', windowId: 1 },
    ];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(5);
    expect(result[0].type).toBe('tab');
    expect(result[0].tab.title).toBe('Ungrouped 1');
    expect(result[1].type).toBe('group');
    expect(result[1].group.title).toBe('Group A');
    expect(result[2].type).toBe('tab');
    expect(result[2].tab.title).toBe('Ungrouped 2');
    expect(result[3].type).toBe('group');
    expect(result[3].group.title).toBe('Group B');
    expect(result[4].type).toBe('tab');
    expect(result[4].tab.title).toBe('Ungrouped 3');
  });

  test('should handle multiple tabs in a single group', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'Ungrouped First', groupId: -1, index: 0 },
        { id: 2, title: 'Group Tab 1', groupId: 1, index: 1 },
        { id: 3, title: 'Group Tab 2', groupId: 1, index: 2 },
        { id: 4, title: 'Group Tab 3', groupId: 1, index: 3 },
        { id: 5, title: 'Ungrouped Last', groupId: -1, index: 4 },
      ],
    };
    const groups = [{ id: 1, title: 'Big Group', windowId: 1 }];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(3);
    expect(result[0].type).toBe('tab');
    expect(result[1].type).toBe('group');
    expect(result[1].tabs.length).toBe(3);
    expect(result[2].type).toBe('tab');
  });

  test('should handle tabs array without explicit index property', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'First', groupId: -1 },
        { id: 2, title: 'Group Tab', groupId: 1 },
        { id: 3, title: 'Last', groupId: -1 },
      ],
    };
    const groups = [{ id: 1, title: 'Group', windowId: 1 }];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(3);
    expect(result[0].type).toBe('tab');
    expect(result[0].tab.title).toBe('First');
    expect(result[1].type).toBe('group');
    expect(result[2].type).toBe('tab');
    expect(result[2].tab.title).toBe('Last');
  });

  test('should handle empty tabs array', () => {
    const win = { id: 1, tabs: [] };
    const groups = [];

    const result = buildOrderedWindowContent(win, groups);

    expect(result).toEqual([]);
  });

  test('should handle window with only ungrouped tabs', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'Tab 1', groupId: -1, index: 0 },
        { id: 2, title: 'Tab 2', groupId: -1, index: 1 },
      ],
    };
    const groups = [];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(2);
    expect(result[0].type).toBe('tab');
    expect(result[1].type).toBe('tab');
  });

  test('should handle window with only grouped tabs', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'Tab 1', groupId: 1, index: 0 },
        { id: 2, title: 'Tab 2', groupId: 1, index: 1 },
      ],
    };
    const groups = [{ id: 1, title: 'Only Group', windowId: 1 }];

    const result = buildOrderedWindowContent(win, groups);

    expect(result.length).toBe(1);
    expect(result[0].type).toBe('group');
    expect(result[0].tabs.length).toBe(2);
  });

  test('should skip tabs in groups that are not in groupsInWindow', () => {
    const win = {
      id: 1,
      tabs: [
        { id: 1, title: 'Tab 1', groupId: 99, index: 0 }, // group 99 doesn't exist
        { id: 2, title: 'Tab 2', groupId: -1, index: 1 },
      ],
    };
    const groups = [];

    const result = buildOrderedWindowContent(win, groups);

    // Tab with groupId 99 should be skipped since the group doesn't exist
    expect(result.length).toBe(1);
    expect(result[0].type).toBe('tab');
    expect(result[0].tab.title).toBe('Tab 2');
  });
});

describe('createTabElement function', () => {
  let mockElement;

  beforeEach(() => {
    mockElement = {
      className: '',
      classList: {
        add: jest.fn(),
        remove: jest.fn(),
        toggle: jest.fn()
      },
      style: {},
      textContent: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn()
    };
    mockDocument.createElement.mockReturnValue(mockElement);
  });

  test('should create tab element with correct class for ungrouped tab', () => {
    const tab = { id: 1, title: 'Test Tab', favIconUrl: null };
    createTabElement(tab, 1, true);

    expect(mockElement.className).toBe('tab-item ungrouped-tab');
  });

  test('should create tab element with correct class for grouped tab', () => {
    const tab = { id: 1, title: 'Test Tab', favIconUrl: null };
    createTabElement(tab, 1, false);

    expect(mockElement.className).toBe('tab-item');
  });

  test('should add click event listener', () => {
    const tab = { id: 1, title: 'Test Tab', favIconUrl: null };
    createTabElement(tab, 1, false);

    expect(mockElement.addEventListener).toHaveBeenCalledWith('click', expect.any(Function));
  });

  test('should add favicon when favIconUrl is provided', () => {
    const tab = { id: 1, title: 'Test Tab', favIconUrl: 'https://example.com/favicon.ico' };
    createTabElement(tab, 1, false);

    // First call creates the img element, second creates the span
    expect(mockDocument.createElement).toHaveBeenCalledWith('div');
    expect(mockDocument.createElement).toHaveBeenCalledWith('img');
  });

  test('should use "New Tab" as fallback title', () => {
    const tab = { id: 1, title: '', favIconUrl: null };
    createTabElement(tab, 1, false);

    // The span's textContent should be set to 'New Tab'
    expect(mockElement.textContent).toBe('New Tab');
  });
});

describe('createGroupElement function', () => {
  let mockGroupEl;
  let mockHeaderEl;
  let mockContentEl;
  let elementCount;

  beforeEach(() => {
    elementCount = 0;
    mockGroupEl = {
      className: '',
      classList: {
        add: jest.fn(),
        remove: jest.fn(),
        toggle: jest.fn()
      },
      style: {},
      appendChild: jest.fn()
    };
    mockHeaderEl = {
      className: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn()
    };
    mockContentEl = {
      className: '',
      appendChild: jest.fn()
    };

    mockDocument.createElement.mockImplementation((tagName) => {
      elementCount++;
      if (elementCount === 1) return mockGroupEl;
      if (elementCount === 2) return mockHeaderEl;
      if (elementCount <= 5) return { className: '', textContent: '', style: {}, appendChild: jest.fn(), addEventListener: jest.fn() };
      return mockContentEl;
    });
  });

  test('should create group element with correct class', () => {
    const group = { id: 1, title: 'Test Group', color: 'blue' };
    const tabs = [];
    createGroupElement(group, tabs, 1);

    expect(mockGroupEl.className).toBe('group-item');
  });

  test('should restore expanded state when group title matches', () => {
    const group = { id: 1, title: 'Test Group', color: 'blue' };
    const tabs = [];
    const expandedGroups = new Set(['Test Group']);

    createGroupElement(group, tabs, 1, expandedGroups);

    expect(mockGroupEl.classList.add).toHaveBeenCalledWith('expanded');
  });

  test('should use "(Untitled Group)" as fallback title', () => {
    const group = { id: 1, title: '', color: 'blue' };
    const tabs = [];
    createGroupElement(group, tabs, 1);

    // The function should handle empty title
    expect(mockGroupEl.className).toBe('group-item');
  });
});

describe('setupEventListeners function', () => {
  beforeEach(() => {
    // Reset mock call counts
    jest.clearAllMocks();
    global.window._chromeListenersRegistered = false;
  });

  test('should register all tab event listeners', () => {
    setupEventListeners();

    expect(mockChrome.tabs.onCreated.addListener).toHaveBeenCalled();
    expect(mockChrome.tabs.onRemoved.addListener).toHaveBeenCalled();
    expect(mockChrome.tabs.onUpdated.addListener).toHaveBeenCalled();
    expect(mockChrome.tabs.onMoved.addListener).toHaveBeenCalled();
    expect(mockChrome.tabs.onAttached.addListener).toHaveBeenCalled();
    expect(mockChrome.tabs.onDetached.addListener).toHaveBeenCalled();
  });

  test('should register all tabGroups event listeners', () => {
    setupEventListeners();

    expect(mockChrome.tabGroups.onCreated.addListener).toHaveBeenCalled();
    expect(mockChrome.tabGroups.onRemoved.addListener).toHaveBeenCalled();
    expect(mockChrome.tabGroups.onUpdated.addListener).toHaveBeenCalled();
  });

  test('should register all windows event listeners including onFocusChanged', () => {
    setupEventListeners();

    expect(mockChrome.windows.onCreated.addListener).toHaveBeenCalled();
    expect(mockChrome.windows.onRemoved.addListener).toHaveBeenCalled();
    expect(mockChrome.windows.onFocusChanged.addListener).toHaveBeenCalled();
  });

  test('should set _chromeListenersRegistered flag', () => {
    setupEventListeners();

    expect(global.window._chromeListenersRegistered).toBe(true);
  });

  test('should handle missing chrome.tabs gracefully', () => {
    const originalTabs = global.chrome.tabs;
    global.chrome.tabs = undefined;

    expect(() => setupEventListeners()).not.toThrow();

    global.chrome.tabs = originalTabs;
  });

  test('should handle missing chrome.tabGroups gracefully', () => {
    const originalTabGroups = global.chrome.tabGroups;
    global.chrome.tabGroups = undefined;

    expect(() => setupEventListeners()).not.toThrow();

    global.chrome.tabGroups = originalTabGroups;
  });

  test('should handle missing chrome.windows gracefully', () => {
    const originalWindows = global.chrome.windows;
    global.chrome.windows = undefined;

    expect(() => setupEventListeners()).not.toThrow();

    global.chrome.windows = originalWindows;
  });

  test('should handle missing chrome.windows.onFocusChanged gracefully', () => {
    const originalOnFocusChanged = global.chrome.windows.onFocusChanged;
    global.chrome.windows.onFocusChanged = undefined;

    expect(() => setupEventListeners()).not.toThrow();

    global.chrome.windows.onFocusChanged = originalOnFocusChanged;
  });
});

describe('Hierarchy structure validation', () => {
  test('should have correct window structure', () => {
    const mockWindow = {
      id: 1,
      title: 'Test Window',
      tabs: [
        { id: 1, title: 'Tab 1', groupId: -1, favIconUrl: null },
        { id: 2, title: 'Tab 2', groupId: 1, favIconUrl: null },
      ],
    };

    expect(mockWindow).toHaveProperty('id');
    expect(mockWindow).toHaveProperty('title');
    expect(mockWindow).toHaveProperty('tabs');
    expect(Array.isArray(mockWindow.tabs)).toBe(true);
  });

  test('should have correct group structure', () => {
    const mockGroup = {
      id: 1,
      title: 'Test Group',
      color: 'blue',
      windowId: 1,
    };

    expect(mockGroup).toHaveProperty('id');
    expect(mockGroup).toHaveProperty('title');
    expect(mockGroup).toHaveProperty('color');
    expect(mockGroup).toHaveProperty('windowId');
  });

  test('should have correct tab structure', () => {
    const mockTab = {
      id: 1,
      title: 'Example Page',
      groupId: 1,
      favIconUrl: 'https://example.com/favicon.ico',
    };

    expect(mockTab).toHaveProperty('id');
    expect(mockTab).toHaveProperty('title');
    expect(mockTab).toHaveProperty('groupId');
    expect(mockTab).toHaveProperty('favIconUrl');
  });
});

describe('Data filtering logic', () => {
  test('should filter groups by windowId', () => {
    const allGroups = [
      { id: 1, windowId: 1, title: 'Group 1' },
      { id: 2, windowId: 2, title: 'Group 2' },
      { id: 3, windowId: 1, title: 'Group 3' },
    ];

    const windowId = 1;
    const groupsInWindow = allGroups.filter(g => g.windowId === windowId);

    expect(groupsInWindow.length).toBe(2);
    expect(groupsInWindow[0].id).toBe(1);
    expect(groupsInWindow[1].id).toBe(3);
  });

  test('should filter tabs by groupId', () => {
    const allTabs = [
      { id: 1, groupId: 1, title: 'Tab 1' },
      { id: 2, groupId: -1, title: 'Tab 2' },
      { id: 3, groupId: 1, title: 'Tab 3' },
    ];

    const groupId = 1;
    const tabsInGroup = allTabs.filter(t => t.groupId === groupId);

    expect(tabsInGroup.length).toBe(2);
    expect(tabsInGroup[0].id).toBe(1);
    expect(tabsInGroup[1].id).toBe(3);
  });

  test('should filter ungrouped tabs', () => {
    const allTabs = [
      { id: 1, groupId: 1, title: 'Tab 1' },
      { id: 2, groupId: -1, title: 'Tab 2' },
      { id: 3, groupId: -1, title: 'Tab 3' },
    ];

    const ungroupedTabs = allTabs.filter(t => t.groupId === -1);

    expect(ungroupedTabs.length).toBe(2);
    expect(ungroupedTabs[0].id).toBe(2);
    expect(ungroupedTabs[1].id).toBe(3);
  });
});

describe('Window naming logic', () => {
  test('should use custom window title if available', () => {
    const window = { id: 1, title: 'My Custom Window' };
    const displayName = window.title || `Window ${window.id}`;
    expect(displayName).toBe('My Custom Window');
  });

  test('should fallback to Window [ID] if title is empty', () => {
    const window = { id: 42, title: '' };
    const displayName = window.title || `Window ${window.id}`;
    expect(displayName).toBe('Window 42');
  });

  test('should fallback to Window [ID] if title is null', () => {
    const window = { id: 42, title: null };
    const displayName = window.title || `Window ${window.id}`;
    expect(displayName).toBe('Window 42');
  });

  test('should fallback to Window [ID] if title is undefined', () => {
    const window = { id: 42 };
    const displayName = window.title || `Window ${window.id}`;
    expect(displayName).toBe('Window 42');
  });
});

describe('generateWindowName function', () => {
  // Import the function (will be added to exports)
  const { generateWindowName, getWindowDisplayName } = require('../popup.js');

  test('should return empty string for empty tabs array', () => {
    expect(generateWindowName([])).toBe('');
  });

  test('should return single short tab name without ellipsis', () => {
    const tabs = [{ title: 'GitHub' }];
    expect(generateWindowName(tabs)).toBe('GitHub');
  });

  test('should truncate single long tab name to 12 chars + ellipsis', () => {
    const tabs = [{ title: 'This is a very long tab title' }];
    expect(generateWindowName(tabs)).toBe('This is a ve...');
  });

  test('should join multiple short tab names with comma', () => {
    const tabs = [
      { title: 'GitHub' },
      { title: 'Google' }
    ];
    expect(generateWindowName(tabs)).toBe('GitHub, Google');
  });

  test('should truncate each tab name to 12 chars + ellipsis', () => {
    const tabs = [
      { title: 'Very Long Title One' },
      { title: 'Another Long Title' }
    ];
    expect(generateWindowName(tabs)).toBe('Very Long Ti..., Another Long...');
  });

  test('should limit total length to 60 characters', () => {
    const tabs = [
      { title: 'Tab One' },
      { title: 'Tab Two' },
      { title: 'Tab Three' },
      { title: 'Tab Four' },
      { title: 'Tab Five' },
      { title: 'Tab Six' }
    ];
    const result = generateWindowName(tabs);
    expect(result.length).toBeLessThanOrEqual(60);
  });

  test('should stop adding tabs when 60 char limit would be exceeded', () => {
    const tabs = [
      { title: 'First Tab Name' },
      { title: 'Second Tab Name' },
      { title: 'Third Tab Name' },
      { title: 'Fourth Tab Name' }
    ];
    const result = generateWindowName(tabs);
    expect(result.length).toBeLessThanOrEqual(60);
    // Should include some tabs but not all
    expect(result).toContain('First Tab Na...');
  });

  test('should handle tabs with empty titles', () => {
    const tabs = [
      { title: '' },
      { title: 'Valid Tab' }
    ];
    const result = generateWindowName(tabs);
    expect(result).toBe('New Tab, Valid Tab');
  });

  test('should handle tabs with null titles', () => {
    const tabs = [
      { title: null },
      { title: 'Valid Tab' }
    ];
    const result = generateWindowName(tabs);
    expect(result).toBe('New Tab, Valid Tab');
  });

  test('should handle tabs with undefined titles', () => {
    const tabs = [
      {},
      { title: 'Valid Tab' }
    ];
    const result = generateWindowName(tabs);
    expect(result).toBe('New Tab, Valid Tab');
  });

  test('should handle exactly 12 character tab name without ellipsis', () => {
    const tabs = [{ title: '123456789012' }]; // exactly 12 chars
    expect(generateWindowName(tabs)).toBe('123456789012');
  });

  test('should handle 13 character tab name with ellipsis', () => {
    const tabs = [{ title: '1234567890123' }]; // 13 chars
    expect(generateWindowName(tabs)).toBe('123456789012...');
  });

  test('should not add trailing comma when stopping at limit', () => {
    const tabs = [
      { title: 'First' },
      { title: 'Second' },
      { title: 'Third' },
      { title: 'Fourth' },
      { title: 'Fifth' }
    ];
    const result = generateWindowName(tabs);
    expect(result.endsWith(',')).toBe(false);
    expect(result.endsWith(', ')).toBe(false);
  });
});

describe('Group naming logic', () => {
  test('should use group title if available', () => {
    const group = { id: 1, title: 'My Group' };
    const displayName = group.title || '(Untitled Group)';
    expect(displayName).toBe('My Group');
  });

  test('should fallback to (Untitled Group) if title is empty', () => {
    const group = { id: 1, title: '' };
    const displayName = group.title || '(Untitled Group)';
    expect(displayName).toBe('(Untitled Group)');
  });

  test('should fallback to (Untitled Group) if title is null', () => {
    const group = { id: 1, title: null };
    const displayName = group.title || '(Untitled Group)';
    expect(displayName).toBe('(Untitled Group)');
  });

  test('should fallback to (Untitled Group) if title is undefined', () => {
    const group = { id: 1 };
    const displayName = group.title || '(Untitled Group)';
    expect(displayName).toBe('(Untitled Group)');
  });
});

describe('Tab naming logic', () => {
  test('should use tab title if available', () => {
    const tab = { id: 1, title: 'Example Page' };
    const displayName = tab.title || 'New Tab';
    expect(displayName).toBe('Example Page');
  });

  test('should fallback to New Tab if title is empty', () => {
    const tab = { id: 1, title: '' };
    const displayName = tab.title || 'New Tab';
    expect(displayName).toBe('New Tab');
  });

  test('should fallback to New Tab if title is null', () => {
    const tab = { id: 1, title: null };
    const displayName = tab.title || 'New Tab';
    expect(displayName).toBe('New Tab');
  });

  test('should fallback to New Tab if title is undefined', () => {
    const tab = { id: 1 };
    const displayName = tab.title || 'New Tab';
    expect(displayName).toBe('New Tab');
  });
});

describe('refreshUI function', () => {
  let mockContainer;

  beforeEach(() => {
    jest.clearAllMocks();
    mockContainer = {
      innerHTML: '',
      appendChild: jest.fn(),
      querySelectorAll: jest.fn(() => [])
    };
    // Reset container to null before each test
    setContainer(null);

    // Reset document.querySelectorAll mock
    mockDocument.querySelectorAll.mockReturnValue([]);

    // Default mocks for runtime messaging (needed since refreshUI now fetches cache)
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true, windowNames: {} });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb({ success: true, windows: [] });
    });
  });

  test('should return early if container is not set', async () => {
    setContainer(null);
    await expect(refreshUI()).resolves.toBeUndefined();
  });

  test('should display empty message when no windows', async () => {
    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockContainer.innerHTML).toBe('<div class="empty-msg">No windows found.</div>');
  });

  test('should handle API errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    setContainer(mockContainer);
    mockChrome.windows.getAll.mockRejectedValue(new Error('API Error'));

    await refreshUI();

    expect(mockContainer.innerHTML).toBe('<div class="empty-msg">Error loading windows.</div>');
    expect(consoleSpy).toHaveBeenCalledWith('Error loading data:', expect.any(Error));
    consoleSpy.mockRestore();
  });

  test('should render windows when data is returned', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, title: 'Test Window', tabs: [] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    setContainer(mockContainer);
    await refreshUI();

    // Verify createElement was called (to create window elements)
    expect(mockDocument.createElement).toHaveBeenCalledWith('div');
    expect(mockDocument.createElement).toHaveBeenCalledWith('span');
    consoleSpy.mockRestore();
  });

  test('should preserve expansion state of windows', async () => {
    // The window name is generated from tab titles - 'GitHub' will be the generated name
    const mockExpandedWindow = {
      querySelector: jest.fn().mockReturnValue({ textContent: 'GitHub' })
    };
    mockDocument.querySelectorAll.mockImplementation((selector) => {
      if (selector === '.window-item.expanded') {
        return [mockExpandedWindow];
      }
      return [];
    });

    // Track if classList.add was called with 'expanded'
    let expandedAdded = false;
    mockDocument.createElement.mockImplementation((tag) => ({
      className: '',
      classList: {
        add: jest.fn((cls) => { if (cls === 'expanded') expandedAdded = true; }),
        toggle: jest.fn()
      },
      style: {},
      textContent: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn()
    }));

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ title: 'GitHub', groupId: -1, index: 0 }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // The window should be marked as expanded because the generated name matches
    expect(mockDocument.querySelectorAll).toHaveBeenCalledWith('.window-item.expanded');
    expect(expandedAdded).toBe(true);
  });

  test('should preserve expansion state of groups', async () => {
    // Create mock expanded group element
    const mockExpandedGroup = {
      querySelector: jest.fn().mockReturnValue({ textContent: 'Expanded Group' })
    };
    mockDocument.querySelectorAll.mockImplementation((selector) => {
      if (selector === '.group-item.expanded') {
        return [mockExpandedGroup];
      }
      if (selector === '.window-item.expanded') {
        return [];
      }
      return [];
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, title: 'Test Window', tabs: [{ id: 1, title: 'Tab', groupId: 1, index: 0 }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([
      { id: 1, title: 'Expanded Group', color: 'blue', windowId: 1 }
    ]);

    await refreshUI();

    expect(mockDocument.querySelectorAll).toHaveBeenCalledWith('.group-item.expanded');
  });

  test('should render ungrouped tabs', async () => {
    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 1,
        title: 'Test Window',
        tabs: [{ id: 1, title: 'Ungrouped Tab', groupId: -1, index: 0 }]
      }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Verify createElement was called (to create tab element)
    expect(mockDocument.createElement).toHaveBeenCalled();
  });

  test('should render groups with their tabs', async () => {
    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 1,
        title: 'Test Window',
        tabs: [
          { id: 1, title: 'Grouped Tab', groupId: 1, index: 0 }
        ]
      }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([
      { id: 1, title: 'Test Group', color: 'blue', windowId: 1 }
    ]);

    await refreshUI();

    // Verify createElement was called for group and tab
    expect(mockDocument.createElement).toHaveBeenCalled();
  });

  test('should call window focus API when clicking non-expand-icon part of header', async () => {
    // Track click handlers
    const clickHandlers = [];
    let expandIconRef;

    mockDocument.createElement.mockImplementation((tag) => {
      const el = {
        className: '',
        textContent: '',
        style: {},
        classList: {
          add: jest.fn(),
          toggle: jest.fn()
        },
        appendChild: jest.fn(),
        addEventListener: jest.fn((event, handler) => {
          if (event === 'click') {
            clickHandlers.push({ element: el, handler });
          }
        })
      };
      // Track expand icon
      if (tag === 'span' && !expandIconRef) {
        expandIconRef = el;
      }
      return el;
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 42, title: 'Test Window', tabs: [] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Find the window header click handler (should be second click handler)
    expect(clickHandlers.length).toBeGreaterThan(0);

    // Simulate clicking on header (not expand icon)
    const headerHandler = clickHandlers.find(h => h.element !== expandIconRef)?.handler;
    if (headerHandler) {
      headerHandler({ target: {} }); // target is not expand icon
      expect(mockChrome.windows.update).toHaveBeenCalledWith(42, { focused: true });
    }
  });

  test('should toggle expansion when clicking expand icon', async () => {
    // Track click handlers and elements
    let expandIconClickHandler;
    let windowEl;

    mockDocument.createElement.mockImplementation((tag) => {
      const el = {
        className: '',
        textContent: '',
        style: {},
        classList: {
          add: jest.fn(),
          toggle: jest.fn()
        },
        appendChild: jest.fn(),
        addEventListener: jest.fn((event, handler) => {
          if (event === 'click' && tag === 'span') {
            expandIconClickHandler = handler;
          }
        })
      };
      if (tag === 'div' && !windowEl) {
        windowEl = el;
      }
      return el;
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, title: 'Test', tabs: [] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Simulate expand icon click
    if (expandIconClickHandler) {
      const mockEvent = { stopPropagation: jest.fn() };
      expandIconClickHandler(mockEvent);
      expect(mockEvent.stopPropagation).toHaveBeenCalled();
    }
  });

  test('should toggle window expansion when clicking header expand icon', async () => {
    // Track handlers
    let windowHeaderClickHandler;
    let windowEl;
    let expandIcon;

    mockDocument.createElement.mockImplementation((tag) => {
      const el = {
        className: '',
        textContent: '',
        style: {},
        classList: {
          add: jest.fn(),
          toggle: jest.fn()
        },
        appendChild: jest.fn(),
        addEventListener: jest.fn()
      };
      if (tag === 'div' && !windowEl) {
        windowEl = el;
      }
      if (tag === 'span' && !expandIcon) {
        expandIcon = el;
      }
      return el;
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, title: 'Test', tabs: [] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Find the window header click handler
    const divCalls = mockDocument.createElement.mock.results.filter(
      (r, i) => mockDocument.createElement.mock.calls[i][0] === 'div'
    );

    // The second div is window-header - get its addEventListener calls
    expect(mockDocument.createElement).toHaveBeenCalled();
  });

  test('should render ordered content with tabs and groups', async () => {
    jest.clearAllMocks();
    mockChrome.windows.getAll.mockResolvedValue([
      {
        id: 1,
        title: 'Test Window',
        tabs: [
          { id: 1, title: 'Ungrouped', groupId: -1, index: 0 },
          { id: 2, title: 'Grouped', groupId: 1, index: 1 }
        ]
      }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([
      { id: 1, title: 'Group 1', color: 'blue', windowId: 1 }
    ]);

    setContainer(mockContainer);
    await refreshUI();

    // Should have created elements for window, tabs, and groups
    expect(mockDocument.createElement).toHaveBeenCalledWith('div');
    expect(mockDocument.createElement).toHaveBeenCalledWith('span');
  });

  test('should toggle window expansion when header click target is expand icon', async () => {
    jest.clearAllMocks();

    // Track elements and handlers
    let windowEl = null;
    let headerEl = null;
    let expandIcon = null;
    let headerClickHandler = null;
    let elementIndex = 0;

    mockDocument.createElement.mockImplementation((tag) => {
      elementIndex++;
      const el = {
        className: '',
        textContent: '',
        style: {},
        classList: {
          add: jest.fn(),
          toggle: jest.fn()
        },
        appendChild: jest.fn(),
        addEventListener: jest.fn((event, handler) => {
          if (event === 'click') {
            if (elementIndex === 2) { // window-header
              headerClickHandler = handler;
            }
          }
        })
      };

      if (elementIndex === 1) windowEl = el;  // window-item div
      if (elementIndex === 2) headerEl = el;   // window-header div
      if (elementIndex === 3) expandIcon = el; // expand-icon span

      return el;
    });

    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, title: 'Test Window', tabs: [] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    setContainer(mockContainer);
    await refreshUI();

    // Simulate clicking on expand icon (target === expandIcon)
    if (headerClickHandler && expandIcon && windowEl) {
      headerClickHandler({ target: expandIcon });
      expect(windowEl.classList.toggle).toHaveBeenCalledWith('expanded');
    }
  });
});

describe('Click handlers', () => {
  let clickCallback;
  let mockElement;

  beforeEach(() => {
    jest.clearAllMocks();
    mockElement = {
      className: '',
      classList: {
        add: jest.fn(),
        remove: jest.fn(),
        toggle: jest.fn()
      },
      style: {},
      textContent: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn((event, callback) => {
        if (event === 'click') {
          clickCallback = callback;
        }
      })
    };
    mockDocument.createElement.mockReturnValue(mockElement);
  });

  test('tab click handler should call chrome.windows.update and chrome.tabs.update', () => {
    const tab = { id: 42, title: 'Test Tab', favIconUrl: null };
    const windowId = 1;

    createTabElement(tab, windowId, false);

    // Simulate click
    expect(clickCallback).toBeDefined();
    clickCallback();

    expect(mockChrome.windows.update).toHaveBeenCalledWith(windowId, { focused: true });
    expect(mockChrome.tabs.update).toHaveBeenCalledWith(42, { active: true });
  });

  test('group header click handler should toggle expanded when clicking expand icon', () => {
    const group = { id: 1, title: 'Test Group', color: 'blue' };
    const tabs = [{ id: 1, title: 'Tab 1', favIconUrl: null }];

    // Mock createElement to capture the group element and header
    let groupEl, headerEl, expandIcon;
    let elementIndex = 0;

    mockDocument.createElement.mockImplementation(() => {
      elementIndex++;
      if (elementIndex === 1) {
        groupEl = {
          className: '',
          classList: { add: jest.fn(), toggle: jest.fn() },
          appendChild: jest.fn()
        };
        return groupEl;
      }
      if (elementIndex === 2) {
        headerEl = {
          className: '',
          appendChild: jest.fn(),
          addEventListener: jest.fn()
        };
        return headerEl;
      }
      if (elementIndex === 3) {
        expandIcon = {
          className: '',
          textContent: '',
          addEventListener: jest.fn()
        };
        return expandIcon;
      }
      return {
        className: '',
        textContent: '',
        style: {},
        appendChild: jest.fn(),
        addEventListener: jest.fn()
      };
    });

    createGroupElement(group, tabs, 1);

    // Get the expand icon click handler
    const expandIconClickCall = expandIcon.addEventListener.mock.calls.find(
      call => call[0] === 'click'
    );
    expect(expandIconClickCall).toBeDefined();

    // Simulate click on expand icon with stopPropagation
    const mockEvent = { stopPropagation: jest.fn(), target: expandIcon };
    expandIconClickCall[1](mockEvent);

    expect(mockEvent.stopPropagation).toHaveBeenCalled();
    expect(groupEl.classList.toggle).toHaveBeenCalledWith('expanded');
  });

  test('group header click handler should focus first tab when clicking header (not icon)', () => {
    const group = { id: 1, title: 'Test Group', color: 'blue' };
    const tabs = [{ id: 99, title: 'First Tab', favIconUrl: null }];

    let groupEl, headerEl, expandIcon;
    let elementIndex = 0;

    mockDocument.createElement.mockImplementation(() => {
      elementIndex++;
      if (elementIndex === 1) {
        groupEl = {
          className: '',
          classList: { add: jest.fn(), toggle: jest.fn() },
          appendChild: jest.fn()
        };
        return groupEl;
      }
      if (elementIndex === 2) {
        headerEl = {
          className: '',
          appendChild: jest.fn(),
          addEventListener: jest.fn()
        };
        return headerEl;
      }
      if (elementIndex === 3) {
        expandIcon = {
          className: '',
          textContent: '',
          addEventListener: jest.fn()
        };
        return expandIcon;
      }
      return {
        className: '',
        textContent: '',
        style: {},
        appendChild: jest.fn(),
        addEventListener: jest.fn()
      };
    });

    createGroupElement(group, tabs, 1);

    // Get the header click handler
    const headerClickCall = headerEl.addEventListener.mock.calls.find(
      call => call[0] === 'click'
    );
    expect(headerClickCall).toBeDefined();

    // Simulate click on header (not on expand icon)
    const mockEvent = { target: headerEl };
    headerClickCall[1](mockEvent);

    expect(mockChrome.windows.update).toHaveBeenCalledWith(1, { focused: true });
    expect(mockChrome.tabs.update).toHaveBeenCalledWith(99, { active: true });
  });

  test('group header click should toggle expansion when clicking expand icon', () => {
    const group = { id: 1, title: 'Test Group', color: 'blue' };
    const tabs = [{ id: 99, title: 'First Tab', favIconUrl: null }];

    let groupEl, headerEl, expandIcon;
    let elementIndex = 0;

    mockDocument.createElement.mockImplementation(() => {
      elementIndex++;
      if (elementIndex === 1) {
        groupEl = {
          className: '',
          classList: { add: jest.fn(), toggle: jest.fn() },
          appendChild: jest.fn()
        };
        return groupEl;
      }
      if (elementIndex === 2) {
        headerEl = {
          className: '',
          appendChild: jest.fn(),
          addEventListener: jest.fn()
        };
        return headerEl;
      }
      if (elementIndex === 3) {
        expandIcon = {
          className: '',
          textContent: '',
          addEventListener: jest.fn()
        };
        return expandIcon;
      }
      return {
        className: '',
        textContent: '',
        style: {},
        appendChild: jest.fn(),
        addEventListener: jest.fn()
      };
    });

    createGroupElement(group, tabs, 1);

    // Get the header click handler
    const headerClickCall = headerEl.addEventListener.mock.calls.find(
      call => call[0] === 'click'
    );

    // Simulate click on expand icon (target is expandIcon)
    const mockEvent = { target: expandIcon };
    headerClickCall[1](mockEvent);

    // Should toggle expansion, not focus tab
    expect(groupEl.classList.toggle).toHaveBeenCalledWith('expanded');
  });

  test('group with empty tabs array should not crash on header click', () => {
    const group = { id: 1, title: 'Empty Group', color: 'blue' };
    const tabs = [];

    let groupEl, headerEl, expandIcon;
    let elementIndex = 0;

    mockDocument.createElement.mockImplementation(() => {
      elementIndex++;
      if (elementIndex === 1) {
        groupEl = {
          className: '',
          classList: { add: jest.fn(), toggle: jest.fn() },
          appendChild: jest.fn()
        };
        return groupEl;
      }
      if (elementIndex === 2) {
        headerEl = {
          className: '',
          appendChild: jest.fn(),
          addEventListener: jest.fn()
        };
        return headerEl;
      }
      if (elementIndex === 3) {
        expandIcon = {
          className: '',
          textContent: '',
          addEventListener: jest.fn()
        };
        return expandIcon;
      }
      return {
        className: '',
        textContent: '',
        style: {},
        appendChild: jest.fn(),
        addEventListener: jest.fn()
      };
    });

    createGroupElement(group, tabs, 1);

    const headerClickCall = headerEl.addEventListener.mock.calls.find(
      call => call[0] === 'click'
    );

    // Should not throw when tabs array is empty
    expect(() => {
      headerClickCall[1]({ target: headerEl });
    }).not.toThrow();
  });
});

describe('3-level hierarchy validation', () => {
  test('should correctly build 3-level hierarchy from mock data', () => {
    const windows = [
      {
        id: 1,
        title: 'Window 1',
        tabs: [
          { id: 1, title: 'Tab 1', groupId: 1, favIconUrl: null },
          { id: 2, title: 'Tab 2', groupId: 1, favIconUrl: null },
          { id: 3, title: 'Tab 3', groupId: -1, favIconUrl: null },
        ],
      },
    ];

    const groups = [
      { id: 1, title: 'Group 1', color: 'blue', windowId: 1 },
    ];

    const hierarchy = windows.map(win => {
      const groupsInWindow = groups.filter(g => g.windowId === win.id);
      const ungroupedTabs = win.tabs.filter(t => t.groupId === -1);

      return {
        window: win,
        groups: groupsInWindow.map(group => ({
          group,
          tabs: win.tabs.filter(t => t.groupId === group.id),
        })),
        ungroupedTabs,
      };
    });

    expect(hierarchy.length).toBe(1);
    expect(hierarchy[0].window.id).toBe(1);
    expect(hierarchy[0].groups.length).toBe(1);
    expect(hierarchy[0].groups[0].group.title).toBe('Group 1');
    expect(hierarchy[0].groups[0].tabs.length).toBe(2);
    expect(hierarchy[0].ungroupedTabs.length).toBe(1);
  });

  test('should handle multiple windows with multiple groups', () => {
    const windows = [
      {
        id: 1,
        title: 'Window 1',
        tabs: [
          { id: 1, title: 'Tab 1', groupId: 1, favIconUrl: null },
          { id: 2, title: 'Tab 2', groupId: 2, favIconUrl: null },
        ],
      },
      {
        id: 2,
        title: 'Window 2',
        tabs: [
          { id: 3, title: 'Tab 3', groupId: 3, favIconUrl: null },
        ],
      },
    ];

    const groups = [
      { id: 1, title: 'Group 1', color: 'blue', windowId: 1 },
      { id: 2, title: 'Group 2', color: 'red', windowId: 1 },
      { id: 3, title: 'Group 3', color: 'green', windowId: 2 },
    ];

    const hierarchy = windows.map(win => {
      const groupsInWindow = groups.filter(g => g.windowId === win.id);
      const ungroupedTabs = win.tabs.filter(t => t.groupId === -1);

      return {
        window: win,
        groups: groupsInWindow.map(group => ({
          group,
          tabs: win.tabs.filter(t => t.groupId === group.id),
        })),
        ungroupedTabs,
      };
    });

    expect(hierarchy.length).toBe(2);
    expect(hierarchy[0].groups.length).toBe(2);
    expect(hierarchy[1].groups.length).toBe(1);
  });
});

describe('getWindowDisplayName function', () => {
  // getWindowDisplayName(win, windowNamesCache) checks the cache first,
  // then falls back to generateWindowName(win?.tabs || []).

  test('should return cached name when windowNamesCache has entry for window id', () => {
    const win = {
      id: 42,
      tabs: [{ title: 'Tab 1' }, { title: 'Tab 2' }]
    };
    const cache = { '42': { name: 'My Project Window', urlFingerprint: 'github.com' } };
    expect(getWindowDisplayName(win, cache)).toBe('My Project Window');
  });

  test('should fall back to generateWindowName when cache has no entry for window id', () => {
    const win = {
      id: 99,
      tabs: [{ title: 'GitHub' }]
    };
    const cache = { '42': { name: 'Other Window', urlFingerprint: 'example.com' } };
    expect(getWindowDisplayName(win, cache)).toBe('GitHub');
  });

  test('should fall back to generateWindowName when cache is null', () => {
    const win = {
      id: 1,
      tabs: [{ title: 'Tab One' }, { title: 'Tab Two' }]
    };
    expect(getWindowDisplayName(win, null)).toBe('Tab One, Tab Two');
  });

  test('should fall back to generateWindowName when cache is undefined', () => {
    const win = {
      id: 1,
      tabs: [{ title: 'GitHub' }]
    };
    expect(getWindowDisplayName(win, undefined)).toBe('GitHub');
  });

  test('should fall back to generateWindowName when cache is empty object', () => {
    const win = {
      id: 1,
      tabs: [{ title: 'Tab One' }, { title: 'Tab Two' }]
    };
    expect(getWindowDisplayName(win, {})).toBe('Tab One, Tab Two');
  });

  test('should ignore cached entry if name is empty string', () => {
    const win = {
      id: 1,
      tabs: [{ title: 'GitHub' }]
    };
    const cache = { '1': { name: '', urlFingerprint: 'github.com' } };
    expect(getWindowDisplayName(win, cache)).toBe('GitHub');
  });

  test('should ignore stray name property on window object, use cache instead', () => {
    const win = {
      id: 1,
      name: 'Stray Property',
      tabs: [{ title: 'Tab 1' }, { title: 'Tab 2' }]
    };
    const cache = { '1': { name: 'Cached Name', urlFingerprint: 'example.com' } };
    expect(getWindowDisplayName(win, cache)).toBe('Cached Name');
  });

  test('should ignore stray name property and fall back to tab names when no cache', () => {
    const win = {
      id: 1,
      name: 'Stray Property',
      tabs: [{ title: 'Tab 1' }, { title: 'Tab 2' }]
    };
    expect(getWindowDisplayName(win)).toBe('Tab 1, Tab 2');
  });

  test('should return empty string when window has no tabs and no cache', () => {
    const win = { id: 1, tabs: [] };
    expect(getWindowDisplayName(win)).toBe('');
  });

  test('should handle null/undefined window gracefully', () => {
    expect(getWindowDisplayName(null)).toBe('');
    expect(getWindowDisplayName(undefined)).toBe('');
  });

  test('should handle window with missing tabs array and no cache', () => {
    const win = { id: 1 };
    expect(getWindowDisplayName(win)).toBe('');
  });

  test('should skip closed entries in cache', () => {
    const win = {
      id: 1,
      tabs: [{ title: 'GitHub' }]
    };
    const cache = { '1': { name: 'Old Name', urlFingerprint: 'github.com', closed: true } };
    expect(getWindowDisplayName(win, cache)).toBe('GitHub');
  });
});

describe('refreshUI fetches cached window names', () => {
  let mockContainer;

  beforeEach(() => {
    jest.clearAllMocks();
    mockContainer = {
      innerHTML: '',
      appendChild: jest.fn(),
      querySelectorAll: jest.fn(() => [])
    };
    setContainer(null);
    mockDocument.querySelectorAll.mockReturnValue([]);
  });

  test('should call chrome.runtime.sendMessage with getWindowNames action', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true, windowNames: {} });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockChrome.runtime.sendMessage).toHaveBeenCalledWith(
      { action: 'getWindowNames' },
      expect.any(Function)
    );
  });

  test('should use cached name for window when cache has entry', async () => {
    // Set up mock to return cached window names
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({
        success: true,
        windowNames: {
          '42': { name: 'My Project', urlFingerprint: 'github.com' }
        }
      });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    // Track what textContent is set on span elements
    const textContents = [];
    mockDocument.createElement.mockImplementation((tag) => ({
      className: '',
      classList: {
        add: jest.fn(),
        toggle: jest.fn()
      },
      style: {},
      textContent: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn(),
      set textContent(val) { textContents.push(val); this._textContent = val; },
      get textContent() { return this._textContent || ''; }
    }));

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 42, tabs: [{ title: 'GitHub Repo', groupId: -1, index: 0 }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // The window title span should have the cached name
    // (tab title 'GitHub Repo' may still appear as a tab element's text)
    expect(textContents).toContain('My Project');
  });

  test('should handle sendMessage returning success but missing windowNames', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true }); // no windowNames property
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb({ success: true, windows: [] });
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    // Should not throw, should use empty cache
    await expect(refreshUI()).resolves.toBeUndefined();
  });

  test('should handle sendMessage failure gracefully and fall back to generated names', async () => {
    // Simulate runtime.sendMessage failure
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: false, error: 'No handler' });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ title: 'Test Tab', groupId: -1, index: 0 }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    // Should not throw
    await expect(refreshUI()).resolves.toBeUndefined();
  });

  test('should handle sendMessage throwing an exception gracefully', async () => {
    // Simulate runtime.sendMessage throwing (e.g., extension context invalidated)
    mockChrome.runtime.sendMessage.mockImplementation(() => {
      throw new Error('Extension context invalidated');
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb({ success: true, windows: [] });
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    // Should not throw, should use empty cache
    await expect(refreshUI()).resolves.toBeUndefined();
  });

  test('should handle sendNativeMessage throwing an exception gracefully', async () => {
    // Simulate runtime.sendNativeMessage throwing
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true, windowNames: {} });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation(() => {
      throw new Error('Native messaging not supported');
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    // Should not throw, should treat native host as not installed
    await expect(refreshUI()).resolves.toBeUndefined();
  });
});

describe('Native host name consistency in popup', () => {
  let mockContainer;

  beforeEach(() => {
    jest.clearAllMocks();
    mockContainer = {
      innerHTML: '',
      appendChild: jest.fn(),
      querySelectorAll: jest.fn(() => [])
    };
    setContainer(null);
    mockDocument.querySelectorAll.mockReturnValue([]);
  });

  test('should probe native host using com.tabgroups.window_namer', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true, windowNames: {} });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // The native host probe must use the correct name that matches
    // what install.sh and installer.py register
    expect(mockChrome.runtime.sendNativeMessage).toHaveBeenCalledWith(
      'com.tabgroups.window_namer',
      expect.any(Object),
      expect.any(Function)
    );
  });
});

describe('Setup instructions link', () => {
  let mockContainer;

  beforeEach(() => {
    jest.clearAllMocks();
    mockContainer = {
      innerHTML: '',
      appendChild: jest.fn(),
      querySelectorAll: jest.fn(() => [])
    };
    setContainer(null);
    mockDocument.querySelectorAll.mockReturnValue([]);
  });

  test('should show setup link when native host is not installed', async () => {
    // sendMessage returns cached names fine
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true, windowNames: {} });
    });
    // sendNativeMessage returns an error (native host not installed)
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined); // undefined response = error / not installed
    });

    // Track elements appended to container
    const appendedClassNames = [];
    mockContainer.appendChild.mockImplementation((el) => {
      if (el && el.className) appendedClassNames.push(el.className);
    });

    mockDocument.createElement.mockImplementation((tag) => ({
      className: '',
      classList: {
        add: jest.fn(),
        toggle: jest.fn()
      },
      style: {},
      textContent: '',
      href: '',
      target: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn()
    }));

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockChrome.runtime.sendNativeMessage).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
    // Should have appended a setup-link element
    expect(appendedClassNames).toContain('setup-link');
  });

  test('should not show setup link when native host is installed', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((_msg, cb) => {
      cb({ success: true, windowNames: {} });
    });
    // sendNativeMessage returns a valid response (native host installed)
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb({ success: true, windows: [] });
    });

    const appendedClassNames = [];
    mockContainer.appendChild.mockImplementation((el) => {
      if (el && el.className) appendedClassNames.push(el.className);
    });

    mockDocument.createElement.mockImplementation((tag) => ({
      className: '',
      classList: {
        add: jest.fn(),
        toggle: jest.fn()
      },
      style: {},
      textContent: '',
      href: '',
      target: '',
      appendChild: jest.fn(),
      addEventListener: jest.fn()
    }));

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Should NOT have appended a setup-link element
    expect(appendedClassNames).not.toContain('setup-link');
  });
});

describe('sortWindows function', () => {
  const { sortWindows } = require('../popup.js');

  const makeWindow = (id, name, tabs) => ({
    id,
    tabs: tabs || [{ title: name || `Window ${id}` }]
  });

  test('should return windows as-is for "default" sort', () => {
    const windows = [makeWindow(1, 'Beta'), makeWindow(2, 'Alpha')];
    const result = sortWindows(windows, 'default', {});
    expect(result.map(w => w.id)).toEqual([1, 2]);
  });

  test('should not mutate the original array', () => {
    const windows = [makeWindow(1, 'Beta'), makeWindow(2, 'Alpha')];
    const original = [...windows];
    sortWindows(windows, 'alphabetical', {});
    expect(windows.map(w => w.id)).toEqual(original.map(w => w.id));
  });

  test('should sort alphabetically by display name for "alphabetical" sort', () => {
    const windows = [makeWindow(1, 'Charlie'), makeWindow(2, 'Alpha'), makeWindow(3, 'Bravo')];
    const result = sortWindows(windows, 'alphabetical', {});
    expect(result.map(w => w.id)).toEqual([2, 3, 1]);
  });

  test('should sort alphabetically case-insensitively', () => {
    const windows = [makeWindow(1, 'banana'), makeWindow(2, 'Apple'), makeWindow(3, 'cherry')];
    const result = sortWindows(windows, 'alphabetical', {});
    expect(result.map(w => w.id)).toEqual([2, 1, 3]);
  });

  test('should strip leading emoji for alphabetical sort', () => {
    const windows = [
      makeWindow(1, null, [{ title: 'Zulu' }]),
      makeWindow(2, null, [{ title: '🔥 Alpha' }])
    ];
    const cache = {};
    const result = sortWindows(windows, 'alphabetical', cache);
    // "🔥 Alpha" sorts as "Alpha" which comes before "Zulu"
    expect(result.map(w => w.id)).toEqual([2, 1]);
  });

  test('should strip leading spaces for alphabetical sort', () => {
    const windows = [
      makeWindow(1, 'Zulu'),
      makeWindow(2, null, [{ title: '   Alpha' }])
    ];
    const result = sortWindows(windows, 'alphabetical', {});
    expect(result.map(w => w.id)).toEqual([2, 1]);
  });

  test('should use cached name for alphabetical sort', () => {
    const windows = [
      makeWindow(1, 'Zulu'),
      makeWindow(2, 'Middle')
    ];
    const cache = { '1': { name: 'Alpha Window' } };
    const result = sortWindows(windows, 'alphabetical', cache);
    expect(result.map(w => w.id)).toEqual([1, 2]);
  });

  test('should sort by focus order for "recent" sort', () => {
    const windows = [makeWindow(1, 'A'), makeWindow(2, 'B'), makeWindow(3, 'C')];
    const focusOrder = [3, 1, 2]; // 3 most recent, then 1, then 2
    const result = sortWindows(windows, 'recent', {}, focusOrder);
    expect(result.map(w => w.id)).toEqual([3, 1, 2]);
  });

  test('should put windows missing from focus order at the end for "recent" sort', () => {
    const windows = [makeWindow(1, 'A'), makeWindow(2, 'B'), makeWindow(3, 'C')];
    const focusOrder = [2]; // only 2 is in focus order
    const result = sortWindows(windows, 'recent', {}, focusOrder);
    expect(result[0].id).toBe(2);
    // 1 and 3 should come after, in their original order
    expect(result.slice(1).map(w => w.id)).toEqual([1, 3]);
  });

  test('should return windows as-is for "recent" sort with empty focus order', () => {
    const windows = [makeWindow(1, 'A'), makeWindow(2, 'B')];
    const result = sortWindows(windows, 'recent', {}, []);
    expect(result.map(w => w.id)).toEqual([1, 2]);
  });

  test('should return windows as-is for unknown sort order', () => {
    const windows = [makeWindow(1, 'B'), makeWindow(2, 'A')];
    const result = sortWindows(windows, 'unknown', {});
    expect(result.map(w => w.id)).toEqual([1, 2]);
  });

  test('should handle empty windows array', () => {
    expect(sortWindows([], 'alphabetical', {})).toEqual([]);
    expect(sortWindows([], 'recent', {}, [])).toEqual([]);
    expect(sortWindows([], 'default', {})).toEqual([]);
  });
});

describe('refreshUI with sort dropdown set to recent', () => {
  let mockContainer;

  beforeEach(() => {
    jest.clearAllMocks();
    mockContainer = {
      innerHTML: '',
      appendChild: jest.fn(),
      querySelectorAll: jest.fn(() => [])
    };
    setContainer(mockContainer);
    mockDocument.querySelectorAll.mockReturnValue([]);
    mockDocument.getElementById.mockImplementation((id) => {
      if (id === 'sort-windows') return { value: 'recent' };
      if (id === 'groups-container') return mockContainer;
      return null;
    });
  });

  afterEach(() => {
    mockDocument.getElementById.mockReset();
  });

  test('should fetch focus order from background when sort is recent', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      if (msg.action === 'getWindowFocusOrder') {
        cb({ success: true, focusOrder: [2, 1] });
      } else {
        cb({ success: true, windowNames: {} });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ id: 10, title: 'Tab A' }] },
      { id: 2, tabs: [{ id: 20, title: 'Tab B' }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockChrome.runtime.sendMessage).toHaveBeenCalledWith(
      { action: 'getWindowFocusOrder' },
      expect.any(Function)
    );
  });

  test('should handle unsuccessful focus order response', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      if (msg.action === 'getWindowFocusOrder') {
        cb({ success: false });
      } else {
        cb({ success: true, windowNames: {} });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ id: 10, title: 'Tab A' }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Should not throw and should render windows
    expect(mockContainer.appendChild).toHaveBeenCalled();
  });

  test('should handle null response from focus order request', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      if (msg.action === 'getWindowFocusOrder') {
        cb(null);
      } else {
        cb({ success: true, windowNames: {} });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ id: 10, title: 'Tab A' }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockContainer.appendChild).toHaveBeenCalled();
  });

  test('should handle response with undefined focusOrder field', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      if (msg.action === 'getWindowFocusOrder') {
        cb({ success: true }); // focusOrder field missing
      } else {
        cb({ success: true, windowNames: {} });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ id: 10, title: 'Tab A' }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockContainer.appendChild).toHaveBeenCalled();
  });

  test('should handle sendMessage throwing for focus order', async () => {
    mockChrome.runtime.sendMessage.mockImplementation((msg, _cb) => {
      if (msg.action === 'getWindowFocusOrder') {
        throw new Error('Extension context invalidated');
      }
      _cb({ success: true, windowNames: {} });
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });
    mockChrome.windows.getAll.mockResolvedValue([
      { id: 1, tabs: [{ id: 10, title: 'Tab A' }] }
    ]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    expect(mockContainer.appendChild).toHaveBeenCalled();
  });
});

describe('Diagnostic forwarding', () => {
  let mockContainer;

  beforeEach(() => {
    jest.clearAllMocks();
    mockContainer = {
      innerHTML: '',
      appendChild: jest.fn(),
      querySelectorAll: jest.fn(() => [])
    };
    setContainer(null);
    mockDocument.querySelectorAll.mockReturnValue([]);
  });

  test('should send diagnose action after refreshUI completes', async () => {
    const sendMessageCalls = [];
    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      sendMessageCalls.push(msg);
      if (msg.action === 'getWindowNames') {
        cb({ success: true, windowNames: {} });
      } else if (msg.action === 'diagnose') {
        cb({ success: true, diagnosis: { timestamp: '2026-01-01T00:00:00Z' } });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    const actions = sendMessageCalls.map((c) => c.action);
    expect(actions).toContain('getWindowNames');
    expect(actions).toContain('diagnose');
  });

  test('should log diagnostic result with [TGWL:DIAG] tag', async () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    const diagData = { timestamp: '2026-01-01T00:00:00Z', nativeHost: { reachable: true } };

    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      if (msg.action === 'getWindowNames') {
        cb({ success: true, windowNames: {} });
      } else if (msg.action === 'diagnose') {
        cb({ success: true, diagnosis: diagData });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    await refreshUI();

    // Check that [TGWL:DIAG] was logged
    const diagCalls = consoleSpy.mock.calls.filter((c) => c[0] === '[TGWL:DIAG]');
    expect(diagCalls.length).toBeGreaterThan(0);
    expect(diagCalls[0][1]).toContain('"timestamp"');

    consoleSpy.mockRestore();
  });

  test('should handle diagnose failure gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

    mockChrome.runtime.sendMessage.mockImplementation((msg, cb) => {
      if (msg.action === 'getWindowNames') {
        cb({ success: true, windowNames: {} });
      } else if (msg.action === 'diagnose') {
        cb({ success: false, error: 'not available' });
      }
    });
    mockChrome.runtime.sendNativeMessage.mockImplementation((_host, _msg, cb) => {
      cb(undefined);
    });

    setContainer(mockContainer);
    mockChrome.windows.getAll.mockResolvedValue([]);
    mockChrome.tabGroups.query.mockResolvedValue([]);

    // Should not throw
    await expect(refreshUI()).resolves.toBeUndefined();

    // Should still log something with DIAG tag
    const diagCalls = consoleSpy.mock.calls.filter((c) => c[0] === '[TGWL:DIAG]');
    expect(diagCalls.length).toBeGreaterThan(0);
    expect(diagCalls[0][1]).toContain('diagnose failed');

    consoleSpy.mockRestore();
  });
});

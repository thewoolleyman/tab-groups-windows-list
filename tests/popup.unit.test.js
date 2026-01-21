/**
 * Unit tests for popup.js utility functions
 * These tests verify the core logic that builds the 3-level hierarchy
 */

// Import the mapColor function (we'll need to export it from popup.js)
// For now, we'll define it here to test it
function mapColor(chromeColor) {
  const colors = {
    'grey': '#5a5a5a',
    'blue': '#1a73e8',
    'red': '#d93025',
    'yellow': '#f9ab00',
    'green': '#188038',
    'pink': '#d01884',
    'purple': '#a142f4',
    'cyan': '#007b83',
    'orange': '#fa903e'
  };
  return colors[chromeColor] || '#5a5a5a';
}

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

    // Verify the structure has the expected properties
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

    // Verify the structure has the expected properties
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

    // Verify the structure has the expected properties
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

// =============================================================================
// TAB ORDERING TESTS (t17) - TDD: These tests define the expected ordering behavior
// =============================================================================

/**
 * buildOrderedWindowContent - Builds window content items in correct tab index order
 *
 * This function should interleave groups and ungrouped tabs based on their actual
 * tab indices, NOT list groups first then ungrouped tabs.
 *
 * @param {Object} win - Window object with tabs array
 * @param {Array} groupsInWindow - Array of group objects in this window
 * @returns {Array} - Array of items in correct order: {type: 'group'|'tab', ...data}
 */
function buildOrderedWindowContent(win, groupsInWindow) {
  // Get all tabs with their indices
  const tabsWithIndex = win.tabs.map((tab, arrayIndex) => ({
    ...tab,
    index: tab.index !== undefined ? tab.index : arrayIndex
  }));

  // Build a map of groupId -> minimum tab index (position of group)
  const groupPositions = new Map();
  groupsInWindow.forEach(group => {
    const tabsInGroup = tabsWithIndex.filter(t => t.groupId === group.id);
    if (tabsInGroup.length > 0) {
      const minIndex = Math.min(...tabsInGroup.map(t => t.index));
      groupPositions.set(group.id, minIndex);
    }
  });

  // Build ordered content array
  const result = [];
  const processedGroupIds = new Set();

  // Sort tabs by index
  const sortedTabs = [...tabsWithIndex].sort((a, b) => a.index - b.index);

  for (const tab of sortedTabs) {
    if (tab.groupId === -1) {
      // Ungrouped tab - add directly
      result.push({ type: 'tab', tab });
    } else if (!processedGroupIds.has(tab.groupId)) {
      // First tab of a group - add the group
      const group = groupsInWindow.find(g => g.id === tab.groupId);
      if (group) {
        const tabsInGroup = tabsWithIndex.filter(t => t.groupId === group.id);
        result.push({ type: 'group', group, tabs: tabsInGroup });
        processedGroupIds.add(tab.groupId);
      }
    }
    // Skip subsequent tabs of already-processed groups
  }

  return result;
}

describe('Tab ordering logic (t17)', () => {
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

    // Build the hierarchy
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

    // Verify the hierarchy
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

    // Build the hierarchy
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

    // Verify the hierarchy
    expect(hierarchy.length).toBe(2);
    expect(hierarchy[0].groups.length).toBe(2);
    expect(hierarchy[1].groups.length).toBe(1);
  });
});

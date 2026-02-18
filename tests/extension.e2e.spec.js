/**
 * E2E Tests for Tab Groups & Windows List Chrome Extension
 * 
 * These tests verify the popup UI structure and behavior.
 * Since the extension requires Chrome APIs that aren't available in a regular browser context,
 * we test the static HTML/CSS/JS structure and mock the Chrome API responses.
 */

const { test, expect } = require("@playwright/test");
const path = require("path");
const fs = require("fs");

// Read the popup.html file and serve it as a local file
const popupPath = path.join(__dirname, "..", "popup.html");

// Rich mock data: 2 windows, 2 groups per window, 2 tabs per group
const richMockData = {
  windows: [
    {
      id: 1,
      title: "Work Window",
      tabs: [
        { id: 1, title: "Project Dashboard", groupId: 1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 2, title: "Code Review", groupId: 1, favIconUrl: "https://github.com/favicon.ico" },
        { id: 3, title: "Documentation", groupId: 2, favIconUrl: "https://docs.example.com/favicon.ico" },
        { id: 4, title: "API Reference", groupId: 2, favIconUrl: "https://api.example.com/favicon.ico" },
      ],
    },
    {
      id: 2,
      title: "Personal Window",
      tabs: [
        { id: 5, title: "Email Inbox", groupId: 3, favIconUrl: "https://mail.example.com/favicon.ico" },
        { id: 6, title: "Calendar", groupId: 3, favIconUrl: "https://calendar.example.com/favicon.ico" },
        { id: 7, title: "News Feed", groupId: 4, favIconUrl: "https://news.example.com/favicon.ico" },
        { id: 8, title: "Weather", groupId: 4, favIconUrl: "https://weather.example.com/favicon.ico" },
      ],
    },
  ],
  groups: [
    { id: 1, title: "Development", color: "blue", windowId: 1 },
    { id: 2, title: "Research", color: "green", windowId: 1 },
    { id: 3, title: "Communication", color: "red", windowId: 2 },
    { id: 4, title: "Entertainment", color: "purple", windowId: 2 },
  ],
};

// =============================================================================
// BUG FIX TEST DATA: Windows with ungrouped tabs and mixed scenarios
// =============================================================================

// Bug #1: Tab titles should show the actual tab title (this is already working, 
// but we need to verify the window title is shown correctly for the WINDOW, not tabs)

// Bug #2: Windows with NO groups should still show all their tabs
const windowWithNoGroupsMockData = {
  windows: [
    {
      id: 1,
      title: "Window With No Groups",
      tabs: [
        { id: 1, title: "Ungrouped Tab 1", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 2, title: "Ungrouped Tab 2", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 3, title: "Ungrouped Tab 3", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
      ],
    },
  ],
  groups: [],
};

// Bug #2 continued: Windows with SOME grouped and SOME ungrouped tabs
const mixedGroupedUngroupedMockData = {
  windows: [
    {
      id: 1,
      title: "Mixed Window",
      tabs: [
        { id: 1, title: "Grouped Tab A", groupId: 1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 2, title: "Grouped Tab B", groupId: 1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 3, title: "Ungrouped Tab X", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 4, title: "Ungrouped Tab Y", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
      ],
    },
  ],
  groups: [
    { id: 1, title: "My Group", color: "blue", windowId: 1 },
  ],
};

// Multiple windows with different scenarios
const multiWindowMixedMockData = {
  windows: [
    {
      id: 1,
      title: "Window With Groups Only",
      tabs: [
        { id: 1, title: "Tab in Group 1", groupId: 1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 2, title: "Tab in Group 2", groupId: 2, favIconUrl: "https://example.com/favicon.ico" },
      ],
    },
    {
      id: 2,
      title: "Window With No Groups",
      tabs: [
        { id: 3, title: "Standalone Tab A", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
        { id: 4, title: "Standalone Tab B", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
      ],
    },
    {
      id: 3,
      title: "Window With Mixed Tabs",
      tabs: [
        { id: 5, title: "Grouped Tab", groupId: 3, favIconUrl: "https://example.com/favicon.ico" },
        { id: 6, title: "Loose Tab", groupId: -1, favIconUrl: "https://example.com/favicon.ico" },
      ],
    },
  ],
  groups: [
    { id: 1, title: "Group A", color: "blue", windowId: 1 },
    { id: 2, title: "Group B", color: "green", windowId: 1 },
    { id: 3, title: "Group C", color: "red", windowId: 3 },
  ],
};

// Helper function to set up the page with mock data
async function setupPageWithMockData(page, mockData = richMockData) {
  await page.goto(`file://${popupPath}`);

  await page.addInitScript((data) => {
    // Store mock data for potential updates
    window._mockData = data;

    // Create event listener mock
    const createEventMock = () => ({
      addListener: () => {},
      removeListener: () => {},
    });

    window.chrome = {
      windows: {
        getAll: () => Promise.resolve(window._mockData.windows),
        update: () => Promise.resolve(),
        onCreated: createEventMock(),
        onRemoved: createEventMock(),
        onFocusChanged: createEventMock(),
      },
      tabGroups: {
        query: () => Promise.resolve(window._mockData.groups),
        onCreated: createEventMock(),
        onRemoved: createEventMock(),
        onUpdated: createEventMock(),
      },
      tabs: {
        update: () => Promise.resolve(),
        onCreated: createEventMock(),
        onRemoved: createEventMock(),
        onUpdated: createEventMock(),
        onMoved: createEventMock(),
        onAttached: createEventMock(),
        onDetached: createEventMock(),
      },
      runtime: {
        sendMessage: (msg, cb) => {
          if (msg.action === 'getWindowNames') {
            cb({ success: true, windowNames: window._mockWindowNames || {} });
          } else if (msg.action === 'getWindowFocusOrder') {
            cb({ success: true, focusOrder: window._mockFocusOrder || [] });
          } else if (msg.action === 'diagnose') {
            cb({ success: false });
          } else {
            cb({ success: false, error: 'unknown action' });
          }
        },
        sendNativeMessage: (_host, _msg, cb) => { cb(undefined); },
      },
    };
  }, mockData);

  await page.reload();
  await page.waitForTimeout(500);
}

// Helper function to expand all windows and groups
async function expandAllHierarchy(page) {
  // Expand all windows
  const windows = page.locator(".window-item");
  const windowCount = await windows.count();
  
  for (let i = 0; i < windowCount; i++) {
    const windowItem = windows.nth(i);
    const expandIcon = windowItem.locator(".expand-icon").first();
    await expandIcon.click();
    await page.waitForTimeout(100);
  }
  
  // Expand all groups
  const groups = page.locator(".group-item");
  const groupCount = await groups.count();
  
  for (let i = 0; i < groupCount; i++) {
    const groupItem = groups.nth(i);
    const expandIcon = groupItem.locator(".expand-icon").first();
    await expandIcon.click();
    await page.waitForTimeout(100);
  }
}

// =============================================================================
// BUG FIX TESTS - TDD: These tests should FAIL initially
// =============================================================================

test.describe("BUG FIX #1: Tab titles display correctly", () => {
  test("tabs should display their actual title, not the window title", async ({ page }) => {
    await setupPageWithMockData(page, richMockData);
    
    // Expand first window and first group
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();
    
    const firstGroup = firstWindow.locator(".group-item").first();
    await firstGroup.locator(".expand-icon").first().click();
    
    // Verify tab titles are correct (not the window title)
    const tabItems = firstGroup.locator(".tab-item");
    await expect(tabItems.first()).toContainText("Project Dashboard");
    await expect(tabItems.nth(1)).toContainText("Code Review");
    
    // Make sure they DON'T contain the window title
    await expect(tabItems.first()).not.toContainText("Work Window");
    await expect(tabItems.nth(1)).not.toContainText("Work Window");
  });
});

test.describe("BUG FIX #2: Windows with no groups show all tabs", () => {
  test("window with NO groups should still be displayed", async ({ page }) => {
    await setupPageWithMockData(page, windowWithNoGroupsMockData);

    // The window should be visible
    const windows = page.locator(".window-item");
    await expect(windows).toHaveCount(1);

    // Window name is now generated from tab titles (truncated to 12 chars + ...)
    await expect(page.locator(".window-header")).toContainText("Ungrouped Ta...");
  });

  test("window with NO groups should show all ungrouped tabs when expanded", async ({ page }) => {
    await setupPageWithMockData(page, windowWithNoGroupsMockData);
    
    // Expand the window
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();
    
    // All 3 ungrouped tabs should be visible
    const tabItems = windowItem.locator(".tab-item");
    await expect(tabItems).toHaveCount(3);
    
    // Verify tab titles
    await expect(tabItems.nth(0)).toContainText("Ungrouped Tab 1");
    await expect(tabItems.nth(1)).toContainText("Ungrouped Tab 2");
    await expect(tabItems.nth(2)).toContainText("Ungrouped Tab 3");
  });

  test("window with MIXED grouped and ungrouped tabs should show both", async ({ page }) => {
    await setupPageWithMockData(page, mixedGroupedUngroupedMockData);
    
    // Expand the window
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();
    
    // Should have 1 group
    const groups = windowItem.locator(".group-item");
    await expect(groups).toHaveCount(1);
    
    // Expand the group
    await groups.first().locator(".expand-icon").first().click();
    
    // Group should have 2 tabs
    const groupedTabs = groups.first().locator(".tab-item");
    await expect(groupedTabs).toHaveCount(2);
    await expect(groupedTabs.nth(0)).toContainText("Grouped Tab A");
    await expect(groupedTabs.nth(1)).toContainText("Grouped Tab B");
    
    // Window content should also have 2 ungrouped tabs (direct children, not in a group)
    // These should be siblings of the group, not inside it
    const ungroupedTabs = windowItem.locator(".content > .ungrouped-tab");
    await expect(ungroupedTabs).toHaveCount(2);
    await expect(ungroupedTabs.nth(0)).toContainText("Ungrouped Tab X");
    await expect(ungroupedTabs.nth(1)).toContainText("Ungrouped Tab Y");
  });

  test("multiple windows with different scenarios should all display correctly", async ({ page }) => {
    await setupPageWithMockData(page, multiWindowMixedMockData);
    
    // Should have 3 windows
    const windows = page.locator(".window-item");
    await expect(windows).toHaveCount(3);
    
    // Expand all windows
    for (let i = 0; i < 3; i++) {
      await windows.nth(i).locator(".expand-icon").first().click();
      await page.waitForTimeout(100);
    }
    
    // Window 1: Groups Only - should have 2 groups, no ungrouped tabs
    const window1 = windows.nth(0);
    await expect(window1.locator(".group-item")).toHaveCount(2);
    await expect(window1.locator(".content > .ungrouped-tab")).toHaveCount(0);
    
    // Window 2: No Groups - should have 0 groups, 2 ungrouped tabs
    const window2 = windows.nth(1);
    await expect(window2.locator(".group-item")).toHaveCount(0);
    await expect(window2.locator(".content > .ungrouped-tab")).toHaveCount(2);
    await expect(window2.locator(".tab-item").nth(0)).toContainText("Standalone Tab A");
    await expect(window2.locator(".tab-item").nth(1)).toContainText("Standalone Tab B");
    
    // Window 3: Mixed - should have 1 group AND 1 ungrouped tab
    const window3 = windows.nth(2);
    await expect(window3.locator(".group-item")).toHaveCount(1);
    await expect(window3.locator(".content > .ungrouped-tab")).toHaveCount(1);
    await expect(window3.locator(".content > .ungrouped-tab").first()).toContainText("Loose Tab");
  });

  test("should capture screenshot of window with no groups", async ({ page }) => {
    await setupPageWithMockData(page, windowWithNoGroupsMockData);
    
    // Expand the window
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();
    await page.waitForTimeout(300);
    
    await page.screenshot({
      path: "screenshots/window-no-groups.png",
      fullPage: true,
    });
    
    // Verify structure
    const tabItems = windowItem.locator(".tab-item");
    await expect(tabItems).toHaveCount(3);
  });

  test("should capture screenshot of mixed grouped and ungrouped tabs", async ({ page }) => {
    await setupPageWithMockData(page, mixedGroupedUngroupedMockData);
    
    // Expand window and group
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();
    await windowItem.locator(".group-item").first().locator(".expand-icon").first().click();
    await page.waitForTimeout(300);
    
    await page.screenshot({
      path: "screenshots/mixed-grouped-ungrouped.png",
      fullPage: true,
    });
  });

  test("should capture screenshot of multiple windows with different scenarios", async ({ page }) => {
    await setupPageWithMockData(page, multiWindowMixedMockData);
    
    // Expand all windows
    const windows = page.locator(".window-item");
    for (let i = 0; i < 3; i++) {
      await windows.nth(i).locator(".expand-icon").first().click();
      await page.waitForTimeout(100);
    }
    
    // Expand all groups
    const groups = page.locator(".group-item");
    const groupCount = await groups.count();
    for (let i = 0; i < groupCount; i++) {
      await groups.nth(i).locator(".expand-icon").first().click();
      await page.waitForTimeout(100);
    }
    
    await page.waitForTimeout(300);
    
    await page.screenshot({
      path: "screenshots/multi-window-scenarios.png",
      fullPage: true,
    });
  });
});

// =============================================================================
// LIVE UI UPDATES TESTS (t18) - TDD: These tests verify event listeners are set up
// =============================================================================

test.describe("LIVE UI UPDATES (t18): UI should update when tabs/windows change", () => {
  test("should have refresh function available in popup", async ({ page }) => {
    await setupPageWithMockData(page, richMockData);

    // Check that refreshUI function exists and is callable
    const hasRefreshUI = await page.evaluate(() => {
      return typeof window.refreshUI === 'function';
    });

    expect(hasRefreshUI).toBe(true);
  });

  test("should have event listeners registered", async ({ page }) => {
    await setupPageWithMockData(page, richMockData);

    // Check that chrome event listeners were set up
    const listenersSetup = await page.evaluate(() => {
      // The mock chrome object should have listeners registered
      return window._chromeListenersRegistered === true;
    });

    expect(listenersSetup).toBe(true);
  });

  test("refreshUI should update the display when called", async ({ page }) => {
    // Set up initial data
    await setupPageWithMockData(page, richMockData);

    // Verify initial state - should have 2 windows
    await expect(page.locator(".window-item")).toHaveCount(2);

    // Update the mock data to simulate a change
    await page.evaluate(() => {
      // Simulate adding a third window to the mock
      window._mockData = {
        windows: [
          ...window._mockData.windows,
          {
            id: 3,
            title: "New Window",
            tabs: [
              { id: 100, title: "New Tab", groupId: -1, favIconUrl: null },
            ],
          },
        ],
        groups: window._mockData.groups,
      };

      // Update the mock chrome API to return new data
      window.chrome.windows.getAll = () => Promise.resolve(window._mockData.windows);
    });

    // Call refresh
    await page.evaluate(() => {
      if (typeof window.refreshUI === 'function') {
        window.refreshUI();
      }
    });

    // Wait for refresh to complete
    await page.waitForTimeout(500);

    // Should now have 3 windows
    await expect(page.locator(".window-item")).toHaveCount(3);
  });
});

// =============================================================================
// WINDOW NAMING TESTS (t21) - Window names based on tab titles
// =============================================================================

// Test data for window naming
const windowNamingMockData = {
  windows: [
    {
      id: 1,
      tabs: [
        { id: 1, title: "GitHub", groupId: -1, index: 0, favIconUrl: null },
        { id: 2, title: "Google", groupId: -1, index: 1, favIconUrl: null },
      ],
    },
  ],
  groups: [],
};

const longTabNamesMockData = {
  windows: [
    {
      id: 1,
      tabs: [
        { id: 1, title: "Very Long Tab Title That Should Be Truncated", groupId: -1, index: 0, favIconUrl: null },
        { id: 2, title: "Another Extremely Long Tab Title", groupId: -1, index: 1, favIconUrl: null },
      ],
    },
  ],
  groups: [],
};

const manyTabsMockData = {
  windows: [
    {
      id: 1,
      tabs: [
        { id: 1, title: "Tab One", groupId: -1, index: 0, favIconUrl: null },
        { id: 2, title: "Tab Two", groupId: -1, index: 1, favIconUrl: null },
        { id: 3, title: "Tab Three", groupId: -1, index: 2, favIconUrl: null },
        { id: 4, title: "Tab Four", groupId: -1, index: 3, favIconUrl: null },
        { id: 5, title: "Tab Five", groupId: -1, index: 4, favIconUrl: null },
        { id: 6, title: "Tab Six", groupId: -1, index: 5, favIconUrl: null },
        { id: 7, title: "Tab Seven", groupId: -1, index: 6, favIconUrl: null },
      ],
    },
  ],
  groups: [],
};

test.describe("WINDOW NAMING (t21): Window names generated from tab titles", () => {
  test("window name should be generated from short tab titles", async ({ page }) => {
    await setupPageWithMockData(page, windowNamingMockData);

    // The window name should be "GitHub, Google"
    const windowHeader = page.locator(".window-header").first();
    await expect(windowHeader).toContainText("GitHub, Google");
  });

  test("long tab names should be truncated to 12 chars + ellipsis", async ({ page }) => {
    await setupPageWithMockData(page, longTabNamesMockData);

    const windowHeader = page.locator(".window-header").first();
    // "Very Long Ta..." (15 chars), "Another Extr..." (15 chars)
    await expect(windowHeader).toContainText("Very Long Ta...");
    await expect(windowHeader).toContainText("Another Extr...");
  });

  test("window name should not exceed 60 characters", async ({ page }) => {
    await setupPageWithMockData(page, manyTabsMockData);

    const windowHeader = page.locator(".window-header").first();
    const windowText = await windowHeader.locator("span:last-child").textContent();

    // The window name should be <= 60 chars
    expect(windowText.length).toBeLessThanOrEqual(60);

    // Should contain at least the first few tabs
    expect(windowText).toContain("Tab One");
    expect(windowText).toContain("Tab Two");
  });

  test("window name should update when tabs change (live update)", async ({ page }) => {
    await setupPageWithMockData(page, windowNamingMockData);

    // Verify initial window name
    const windowHeader = page.locator(".window-header").first();
    await expect(windowHeader).toContainText("GitHub, Google");

    // Update mock data to change tab titles
    await page.evaluate(() => {
      window._mockData = {
        windows: [
          {
            id: 1,
            tabs: [
              { id: 1, title: "New Tab 1", groupId: -1, index: 0, favIconUrl: null },
              { id: 2, title: "New Tab 2", groupId: -1, index: 1, favIconUrl: null },
            ],
          },
        ],
        groups: [],
      };
      window.chrome.windows.getAll = () => Promise.resolve(window._mockData.windows);
    });

    // Trigger refresh
    await page.evaluate(() => window.refreshUI());
    await page.waitForTimeout(500);

    // Window name should now reflect new tabs
    await expect(windowHeader).toContainText("New Tab 1, New Tab 2");
  });

  test("empty tab title should show 'New Tab' as fallback", async ({ page }) => {
    const emptyTitleMockData = {
      windows: [
        {
          id: 1,
          tabs: [
            { id: 1, title: "", groupId: -1, index: 0, favIconUrl: null },
            { id: 2, title: "Valid Tab", groupId: -1, index: 1, favIconUrl: null },
          ],
        },
      ],
      groups: [],
    };

    await setupPageWithMockData(page, emptyTitleMockData);

    const windowHeader = page.locator(".window-header").first();
    await expect(windowHeader).toContainText("New Tab, Valid Tab");
  });

  test("should capture screenshot of window with generated name", async ({ page }) => {
    await setupPageWithMockData(page, manyTabsMockData);

    // Expand the window
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();
    await page.waitForTimeout(300);

    await page.screenshot({
      path: "screenshots/window-naming-generated.png",
      fullPage: true,
    });
  });
});

// =============================================================================
// TAB ORDERING TESTS (t17) - TDD: These tests verify correct tab/group order
// =============================================================================

// Test data where ungrouped tabs should appear BEFORE groups
const ungroupedFirstMockData = {
  windows: [
    {
      id: 1,
      title: "Test Window",
      tabs: [
        { id: 1, title: "First Ungrouped", groupId: -1, index: 0, favIconUrl: null },
        { id: 2, title: "Second Ungrouped", groupId: -1, index: 1, favIconUrl: null },
        { id: 3, title: "Group Tab 1", groupId: 1, index: 2, favIconUrl: null },
        { id: 4, title: "Group Tab 2", groupId: 1, index: 3, favIconUrl: null },
      ],
    },
  ],
  groups: [{ id: 1, title: "My Group", color: "blue", windowId: 1 }],
};

// Test data with interleaved tabs and groups
const interleavedMockData = {
  windows: [
    {
      id: 1,
      title: "Interleaved Window",
      tabs: [
        { id: 1, title: "Ungrouped A", groupId: -1, index: 0, favIconUrl: null },
        { id: 2, title: "Group 1 Tab", groupId: 1, index: 1, favIconUrl: null },
        { id: 3, title: "Ungrouped B", groupId: -1, index: 2, favIconUrl: null },
        { id: 4, title: "Group 2 Tab", groupId: 2, index: 3, favIconUrl: null },
        { id: 5, title: "Ungrouped C", groupId: -1, index: 4, favIconUrl: null },
      ],
    },
  ],
  groups: [
    { id: 1, title: "First Group", color: "blue", windowId: 1 },
    { id: 2, title: "Second Group", color: "red", windowId: 1 },
  ],
};

test.describe("TAB ORDERING (t17): Groups and tabs should display in actual window order", () => {
  test("ungrouped tabs at start should appear before groups", async ({ page }) => {
    await setupPageWithMockData(page, ungroupedFirstMockData);

    // Expand the window
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();

    // Get all direct children of window content (groups and ungrouped tabs)
    const windowContent = windowItem.locator(".content").first();
    const contentChildren = windowContent.locator("> *");

    // Should have 3 items: 2 ungrouped tabs, then 1 group
    await expect(contentChildren).toHaveCount(3);

    // First two items should be ungrouped tabs
    const firstChild = contentChildren.nth(0);
    const secondChild = contentChildren.nth(1);
    const thirdChild = contentChildren.nth(2);

    await expect(firstChild).toHaveClass(/ungrouped-tab/);
    await expect(firstChild).toContainText("First Ungrouped");

    await expect(secondChild).toHaveClass(/ungrouped-tab/);
    await expect(secondChild).toContainText("Second Ungrouped");

    // Third item should be the group
    await expect(thirdChild).toHaveClass(/group-item/);
  });

  test("interleaved tabs and groups should maintain correct order", async ({ page }) => {
    await setupPageWithMockData(page, interleavedMockData);

    // Expand the window
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();

    // Get all direct children of window content
    const windowContent = windowItem.locator(".content").first();
    const contentChildren = windowContent.locator("> *");

    // Should have 5 items in order: tab, group, tab, group, tab
    await expect(contentChildren).toHaveCount(5);

    // Check the order
    await expect(contentChildren.nth(0)).toHaveClass(/ungrouped-tab/);
    await expect(contentChildren.nth(0)).toContainText("Ungrouped A");

    await expect(contentChildren.nth(1)).toHaveClass(/group-item/);
    await expect(contentChildren.nth(1).locator(".group-header")).toContainText("First Group");

    await expect(contentChildren.nth(2)).toHaveClass(/ungrouped-tab/);
    await expect(contentChildren.nth(2)).toContainText("Ungrouped B");

    await expect(contentChildren.nth(3)).toHaveClass(/group-item/);
    await expect(contentChildren.nth(3).locator(".group-header")).toContainText("Second Group");

    await expect(contentChildren.nth(4)).toHaveClass(/ungrouped-tab/);
    await expect(contentChildren.nth(4)).toContainText("Ungrouped C");
  });

  test("should capture screenshot of correctly ordered interleaved content", async ({ page }) => {
    await setupPageWithMockData(page, interleavedMockData);

    // Expand window and groups
    const windowItem = page.locator(".window-item").first();
    await windowItem.locator(".expand-icon").first().click();

    const groups = windowItem.locator(".group-item");
    const groupCount = await groups.count();
    for (let i = 0; i < groupCount; i++) {
      await groups.nth(i).locator(".expand-icon").first().click();
      await page.waitForTimeout(100);
    }

    await page.waitForTimeout(300);

    await page.screenshot({
      path: "screenshots/interleaved-ordering.png",
      fullPage: true,
    });
  });
});

// =============================================================================
// EXISTING TESTS - These should continue to pass
// =============================================================================

test.describe("Extension Popup UI Structure", () => {
  test.beforeEach(async ({ page }) => {
    await setupPageWithMockData(page);
  });

  test("should display the header with title and help button", async ({ page }) => {
    await expect(page.locator(".header h2")).toContainText("Tab Groups");
    await expect(page.locator("#help-btn")).toBeVisible();
  });

  test("should open and close help modal", async ({ page }) => {
    await page.click("#help-btn");
    await expect(page.locator("#help-modal")).toBeVisible();
    await page.click("#close-modal");
    await expect(page.locator("#help-modal")).toBeHidden();
  });

  test("should display window items at the top level", async ({ page }) => {
    const windowItems = page.locator(".window-item");
    await expect(windowItems).toHaveCount(2);
  });

  test("should display correct window titles (generated from tab names)", async ({ page }) => {
    const windowHeaders = page.locator(".window-header");
    // Window names are now generated from tab titles
    // Window 1 tabs: "Project Dashboard", "Code Review", "Documentation", "API Reference"
    await expect(windowHeaders.first()).toContainText("Project Dash...");
    // Window 2 tabs: "Email Inbox", "Calendar", "News Feed", "Weather"
    await expect(windowHeaders.nth(1)).toContainText("Email Inbox");
  });

  test("should expand window to show groups", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    const expandIcon = firstWindow.locator(".expand-icon").first();

    await expect(firstWindow).not.toHaveClass(/expanded/);
    await expandIcon.click();
    await expect(firstWindow).toHaveClass(/expanded/);
    await expect(firstWindow.locator(".content").first()).toBeVisible();
  });

  test("should display 2 groups per window", async ({ page }) => {
    // Expand first window
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    const groupItems = firstWindow.locator(".group-item");
    await expect(groupItems).toHaveCount(2);
  });

  test("should display groups with color dots", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    const groupDots = firstWindow.locator(".group-dot");
    await expect(groupDots).toHaveCount(2);
    await expect(groupDots.first()).toBeVisible();
  });

  test("should display correct group titles", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    const groupHeaders = firstWindow.locator(".group-header");
    await expect(groupHeaders.first()).toContainText("Development");
    await expect(groupHeaders.nth(1)).toContainText("Research");
  });

  test("should expand group to show 2 tabs", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    const firstGroup = firstWindow.locator(".group-item").first();
    await firstGroup.locator(".expand-icon").first().click();

    const tabItems = firstGroup.locator(".tab-item");
    await expect(tabItems).toHaveCount(2);
  });

  test("should display correct tab titles", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();
    
    const firstGroup = firstWindow.locator(".group-item").first();
    await firstGroup.locator(".expand-icon").first().click();

    const tabItems = firstGroup.locator(".tab-item");
    await expect(tabItems.first()).toContainText("Project Dashboard");
    await expect(tabItems.nth(1)).toContainText("Code Review");
  });

  test("should have proper 3-level hierarchy structure", async ({ page }) => {
    // Level 1: 2 Windows
    const windows = page.locator(".window-item");
    await expect(windows).toHaveCount(2);

    // Expand first window
    await windows.first().locator(".expand-icon").first().click();

    // Level 2: 2 Groups in first window
    const groups = windows.first().locator(".group-item");
    await expect(groups).toHaveCount(2);

    // Expand first group
    await groups.first().locator(".expand-icon").first().click();

    // Level 3: 2 Tabs in first group
    const tabs = groups.first().locator(".tab-item");
    await expect(tabs).toHaveCount(2);
  });
});

test.describe("Screenshot Tests - Fully Expanded Hierarchy", () => {
  test("should capture screenshot of fully expanded 3-level hierarchy", async ({ page }) => {
    await setupPageWithMockData(page);
    
    // Expand all windows and groups
    await expandAllHierarchy(page);
    
    // Wait for animations to complete
    await page.waitForTimeout(300);
    
    // Capture screenshot of the fully expanded hierarchy
    await page.screenshot({
      path: "screenshots/hierarchy-fully-expanded.png",
      fullPage: true,
    });
    
    // Verify the structure is correct
    const windows = page.locator(".window-item.expanded");
    await expect(windows).toHaveCount(2);
    
    const groups = page.locator(".group-item.expanded");
    await expect(groups).toHaveCount(4);
    
    const tabs = page.locator(".tab-item");
    await expect(tabs).toHaveCount(8);
  });

  test("should capture screenshot of Window 1 with all groups expanded", async ({ page }) => {
    await setupPageWithMockData(page);
    
    // Expand only the first window and its groups
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();
    
    const groups = firstWindow.locator(".group-item");
    const groupCount = await groups.count();
    for (let i = 0; i < groupCount; i++) {
      await groups.nth(i).locator(".expand-icon").first().click();
      await page.waitForTimeout(100);
    }
    
    await page.waitForTimeout(300);
    
    await page.screenshot({
      path: "screenshots/window-1-expanded.png",
      fullPage: true,
    });
    
    // Verify Window 1 structure
    await expect(firstWindow).toHaveClass(/expanded/);
    const expandedGroups = firstWindow.locator(".group-item.expanded");
    await expect(expandedGroups).toHaveCount(2);
  });

  test("should capture screenshot of Window 2 with all groups expanded", async ({ page }) => {
    await setupPageWithMockData(page);
    
    // Expand only the second window and its groups
    const secondWindow = page.locator(".window-item").nth(1);
    await secondWindow.locator(".expand-icon").first().click();
    
    const groups = secondWindow.locator(".group-item");
    const groupCount = await groups.count();
    for (let i = 0; i < groupCount; i++) {
      await groups.nth(i).locator(".expand-icon").first().click();
      await page.waitForTimeout(100);
    }
    
    await page.waitForTimeout(300);
    
    await page.screenshot({
      path: "screenshots/window-2-expanded.png",
      fullPage: true,
    });
    
    // Verify Window 2 structure
    await expect(secondWindow).toHaveClass(/expanded/);
    const expandedGroups = secondWindow.locator(".group-item.expanded");
    await expect(expandedGroups).toHaveCount(2);
  });

  test("should capture screenshot of collapsed state", async ({ page }) => {
    await setupPageWithMockData(page);
    
    // Don't expand anything - capture collapsed state
    await page.waitForTimeout(300);
    
    await page.screenshot({
      path: "screenshots/hierarchy-collapsed.png",
      fullPage: true,
    });
    
    // Verify collapsed state
    const windows = page.locator(".window-item");
    await expect(windows).toHaveCount(2);
    
    const expandedWindows = page.locator(".window-item.expanded");
    await expect(expandedWindows).toHaveCount(0);
  });
});

test.describe("Visual Styling", () => {
  test.beforeEach(async ({ page }) => {
    await setupPageWithMockData(page);
  });

  test("should have pointer cursor on clickable elements", async ({ page }) => {
    const windowHeader = page.locator(".window-header").first();
    const cursor = await windowHeader.evaluate((el) => 
      window.getComputedStyle(el).cursor
    );
    expect(cursor).toBe("pointer");
  });

  test("should have proper expand icon rotation when expanded", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    const expandIcon = firstWindow.locator(".expand-icon").first();

    const transformBefore = await expandIcon.evaluate((el) => 
      window.getComputedStyle(el).transform
    );

    await expandIcon.click();

    const transformAfter = await expandIcon.evaluate((el) => 
      window.getComputedStyle(el).transform
    );

    expect(transformAfter).not.toBe(transformBefore);
  });

  test("should display different colors for different groups", async ({ page }) => {
    await expandAllHierarchy(page);
    
    const groupDots = page.locator(".group-dot");
    const colors = [];
    
    const count = await groupDots.count();
    for (let i = 0; i < count; i++) {
      const color = await groupDots.nth(i).evaluate((el) => 
        window.getComputedStyle(el).backgroundColor
      );
      colors.push(color);
    }
    
    // Verify we have 4 different colors (blue, green, red, purple)
    const uniqueColors = [...new Set(colors)];
    expect(uniqueColors.length).toBe(4);
  });
});

// =============================================================================
// WINDOW SORTING TESTS - Sort dropdown and window ordering
// =============================================================================

// Test data: windows with names that sort differently than creation order
const sortTestMockData = {
  windows: [
    {
      id: 1,
      tabs: [
        { id: 1, title: "Charlie Project", groupId: -1, index: 0, favIconUrl: null },
      ],
    },
    {
      id: 2,
      tabs: [
        { id: 2, title: "Alpha Project", groupId: -1, index: 0, favIconUrl: null },
      ],
    },
    {
      id: 3,
      tabs: [
        { id: 3, title: "Bravo Project", groupId: -1, index: 0, favIconUrl: null },
      ],
    },
  ],
  groups: [],
};

test.describe("WINDOW SORTING: Sort dropdown and window ordering", () => {
  test("should display sort dropdown in header", async ({ page }) => {
    await setupPageWithMockData(page, sortTestMockData);

    const sortSelect = page.locator("#sort-windows");
    await expect(sortSelect).toBeVisible();
    await expect(sortSelect).toHaveValue("default");
  });

  test("should have Default, A-Z, and Recent options", async ({ page }) => {
    await setupPageWithMockData(page, sortTestMockData);

    const options = page.locator("#sort-windows option");
    await expect(options).toHaveCount(3);
    await expect(options.nth(0)).toHaveText("Default");
    await expect(options.nth(1)).toHaveText("A-Z");
    await expect(options.nth(2)).toHaveText("Recent");
  });

  test("default sort should show windows in Chrome API order", async ({ page }) => {
    await setupPageWithMockData(page, sortTestMockData);

    const windowHeaders = page.locator(".window-header");
    await expect(windowHeaders.nth(0)).toContainText("Charlie Proj");
    await expect(windowHeaders.nth(1)).toContainText("Alpha Projec");
    await expect(windowHeaders.nth(2)).toContainText("Bravo Projec");
  });

  test("A-Z sort should reorder windows alphabetically", async ({ page }) => {
    await setupPageWithMockData(page, sortTestMockData);

    // Select alphabetical sort
    await page.selectOption("#sort-windows", "alphabetical");
    await page.waitForTimeout(500);

    const windowHeaders = page.locator(".window-header");
    // Alpha, Bravo, Charlie
    await expect(windowHeaders.nth(0)).toContainText("Alpha Projec");
    await expect(windowHeaders.nth(1)).toContainText("Bravo Projec");
    await expect(windowHeaders.nth(2)).toContainText("Charlie Proj");
  });

  test("A-Z sort should strip leading emoji for ordering", async ({ page }) => {
    const emojiMockData = {
      windows: [
        { id: 1, tabs: [{ id: 1, title: "Zulu Tab", groupId: -1, index: 0, favIconUrl: null }] },
        { id: 2, tabs: [{ id: 2, title: "🔥 Alpha Tab", groupId: -1, index: 0, favIconUrl: null }] },
      ],
      groups: [],
    };

    await setupPageWithMockData(page, emojiMockData);

    await page.selectOption("#sort-windows", "alphabetical");
    await page.waitForTimeout(500);

    const windowHeaders = page.locator(".window-header");
    // "🔥 Alpha Tab" should sort as "Alpha Tab" — before "Zulu Tab"
    await expect(windowHeaders.nth(0)).toContainText("Alpha Tab");
    await expect(windowHeaders.nth(1)).toContainText("Zulu Tab");
  });

  test("Recent sort should order by focus order from background", async ({ page }) => {
    // Use setupPageWithMockData first, then set focus order and re-trigger
    await setupPageWithMockData(page, sortTestMockData);

    // Set focus order after page is loaded (mock is already in place)
    await page.evaluate(() => {
      window._mockFocusOrder = [3, 1, 2];
    });

    await page.selectOption("#sort-windows", "recent");
    await page.waitForTimeout(500);

    const windowHeaders = page.locator(".window-header");
    // Window 3 (Bravo), Window 1 (Charlie), Window 2 (Alpha)
    await expect(windowHeaders.nth(0)).toContainText("Bravo Projec");
    await expect(windowHeaders.nth(1)).toContainText("Charlie Proj");
    await expect(windowHeaders.nth(2)).toContainText("Alpha Projec");
  });

  test("switching back to Default should restore original order", async ({ page }) => {
    await setupPageWithMockData(page, sortTestMockData);

    // Sort alphabetically first
    await page.selectOption("#sort-windows", "alphabetical");
    await page.waitForTimeout(500);

    // Switch back to default
    await page.selectOption("#sort-windows", "default");
    await page.waitForTimeout(500);

    const windowHeaders = page.locator(".window-header");
    await expect(windowHeaders.nth(0)).toContainText("Charlie Proj");
    await expect(windowHeaders.nth(1)).toContainText("Alpha Projec");
    await expect(windowHeaders.nth(2)).toContainText("Bravo Projec");
  });

  test("sort dropdown should be positioned between title and help button", async ({ page }) => {
    await setupPageWithMockData(page, sortTestMockData);

    const header = page.locator(".header");
    const children = header.locator("> *");

    // Order: h2, select, button
    const tagNames = [];
    const count = await children.count();
    for (let i = 0; i < count; i++) {
      const tag = await children.nth(i).evaluate(el => el.tagName.toLowerCase());
      tagNames.push(tag);
    }
    expect(tagNames).toEqual(["h2", "select", "button"]);
  });
});

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

// Helper function to set up the page with mock data
async function setupPageWithMockData(page, mockData = richMockData) {
  await page.goto(`file://${popupPath}`);
  
  await page.addInitScript((data) => {
    window.chrome = {
      windows: {
        getAll: () => Promise.resolve(data.windows),
        update: () => Promise.resolve(),
      },
      tabGroups: {
        query: () => Promise.resolve(data.groups),
      },
      tabs: {
        update: () => Promise.resolve(),
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

  test("should display correct window titles", async ({ page }) => {
    const windowHeaders = page.locator(".window-header");
    await expect(windowHeaders.first()).toContainText("Work Window");
    await expect(windowHeaders.nth(1)).toContainText("Personal Window");
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

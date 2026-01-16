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

test.describe("Extension Popup UI Structure", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the popup.html file directly
    await page.goto(`file://${popupPath}`);
    
    // Mock the Chrome API
    await page.addInitScript(() => {
      window.chrome = {
        windows: {
          getAll: () => Promise.resolve([
            {
              id: 1,
              title: "Test Window 1",
              tabs: [
                { id: 1, title: "Tab 1 in Group 1", groupId: 1, favIconUrl: null },
                { id: 2, title: "Tab 2 in Group 1", groupId: 1, favIconUrl: null },
                { id: 3, title: "Ungrouped Tab", groupId: -1, favIconUrl: null },
              ],
            },
            {
              id: 2,
              title: "Test Window 2",
              tabs: [
                { id: 4, title: "Tab in Group 2", groupId: 2, favIconUrl: null },
              ],
            },
          ]),
          update: () => Promise.resolve(),
        },
        tabGroups: {
          query: () => Promise.resolve([
            { id: 1, title: "Group 1", color: "blue", windowId: 1 },
            { id: 2, title: "Group 2", color: "red", windowId: 2 },
          ]),
        },
        tabs: {
          update: () => Promise.resolve(),
        },
      };
    });
    
    // Reload to apply the mock
    await page.reload();
    
    // Wait for the popup to initialize
    await page.waitForTimeout(500);
  });

  test("should display the header with title and help button", async ({ page }) => {
    await expect(page.locator(".header h2")).toContainText("Tab Groups");
    await expect(page.locator("#help-btn")).toBeVisible();
  });

  test("should open and close help modal", async ({ page }) => {
    // Click help button
    await page.click("#help-btn");
    await expect(page.locator("#help-modal")).toBeVisible();

    // Close modal
    await page.click("#close-modal");
    await expect(page.locator("#help-modal")).toBeHidden();
  });

  test("should display window items at the top level", async ({ page }) => {
    const windowItems = page.locator(".window-item");
    await expect(windowItems).toHaveCount(2);
  });

  test("should display correct window titles", async ({ page }) => {
    const windowHeaders = page.locator(".window-header");
    await expect(windowHeaders.first()).toContainText("Test Window 1");
    await expect(windowHeaders.nth(1)).toContainText("Test Window 2");
  });

  test("should expand window to show groups and tabs", async ({ page }) => {
    const firstWindow = page.locator(".window-item").first();
    const expandIcon = firstWindow.locator(".expand-icon").first();

    // Initially not expanded
    await expect(firstWindow).not.toHaveClass(/expanded/);

    // Click to expand
    await expandIcon.click();

    // Now expanded
    await expect(firstWindow).toHaveClass(/expanded/);

    // Content should be visible
    await expect(firstWindow.locator(".content").first()).toBeVisible();
  });

  test("should display groups with color dots inside expanded windows", async ({ page }) => {
    // Expand the first window
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    // Check for group items
    const groupItems = firstWindow.locator(".group-item");
    await expect(groupItems).toHaveCount(1);

    // Check for color dot
    const groupDot = groupItems.first().locator(".group-dot");
    await expect(groupDot).toBeVisible();
  });

  test("should display correct group title", async ({ page }) => {
    // Expand the first window
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    // Check group title
    const groupHeader = firstWindow.locator(".group-header").first();
    await expect(groupHeader).toContainText("Group 1");
  });

  test("should expand group to show tabs", async ({ page }) => {
    // Expand the first window
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    // Expand the first group
    const firstGroup = firstWindow.locator(".group-item").first();
    await firstGroup.locator(".expand-icon").first().click();

    // Group should be expanded
    await expect(firstGroup).toHaveClass(/expanded/);

    // Tabs should be visible
    const tabItems = firstGroup.locator(".tab-item");
    await expect(tabItems).toHaveCount(2);
  });

  test("should display correct tab titles", async ({ page }) => {
    // Expand window and group
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();
    
    const firstGroup = firstWindow.locator(".group-item").first();
    await firstGroup.locator(".expand-icon").first().click();

    // Check tab titles
    const tabItems = firstGroup.locator(".tab-item");
    await expect(tabItems.first()).toContainText("Tab 1 in Group 1");
    await expect(tabItems.nth(1)).toContainText("Tab 2 in Group 1");
  });

  test("should display ungrouped tabs directly under window", async ({ page }) => {
    // Expand the first window
    const firstWindow = page.locator(".window-item").first();
    await firstWindow.locator(".expand-icon").first().click();

    // Check for ungrouped tabs (direct children of window content, not inside groups)
    const windowContent = firstWindow.locator(".content").first();
    const ungroupedTabs = windowContent.locator("> .tab-item");
    await expect(ungroupedTabs).toHaveCount(1);
    await expect(ungroupedTabs.first()).toContainText("Ungrouped Tab");
  });

  test("should have proper 3-level hierarchy structure", async ({ page }) => {
    // This test verifies the complete 3-level hierarchy:
    // Level 1: Windows
    // Level 2: Groups (inside windows)
    // Level 3: Tabs (inside groups)

    // Level 1: Check windows exist
    const windows = page.locator(".window-item");
    await expect(windows).toHaveCount(2);

    // Expand first window
    await windows.first().locator(".expand-icon").first().click();

    // Level 2: Check groups exist inside window
    const groups = windows.first().locator(".group-item");
    await expect(groups).toHaveCount(1);

    // Expand first group
    await groups.first().locator(".expand-icon").first().click();

    // Level 3: Check tabs exist inside group
    const tabs = groups.first().locator(".tab-item");
    await expect(tabs).toHaveCount(2);
  });
});

test.describe("Visual Styling", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`file://${popupPath}`);
    
    await page.addInitScript(() => {
      window.chrome = {
        windows: {
          getAll: () => Promise.resolve([
            {
              id: 1,
              title: "Test Window",
              tabs: [
                { id: 1, title: "Test Tab", groupId: 1, favIconUrl: null },
              ],
            },
          ]),
          update: () => Promise.resolve(),
        },
        tabGroups: {
          query: () => Promise.resolve([
            { id: 1, title: "Test Group", color: "blue", windowId: 1 },
          ]),
        },
        tabs: {
          update: () => Promise.resolve(),
        },
      };
    });
    
    await page.reload();
    await page.waitForTimeout(500);
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

    // Before expansion
    const transformBefore = await expandIcon.evaluate((el) => 
      window.getComputedStyle(el).transform
    );

    // Expand
    await expandIcon.click();

    // After expansion - should have rotation
    const transformAfter = await expandIcon.evaluate((el) => 
      window.getComputedStyle(el).transform
    );

    expect(transformAfter).not.toBe(transformBefore);
  });
});

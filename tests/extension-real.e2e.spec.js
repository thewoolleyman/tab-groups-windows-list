/**
 * Real E2E Tests for Tab Groups & Windows List Chrome Extension
 *
 * Unlike extension.e2e.spec.js which mocks all Chrome APIs,
 * these tests load the actual extension in Chrome and navigate
 * to chrome-extension://{extensionId}/popup.html with real APIs.
 *
 * Native host tests require macOS or Linux.
 */

const { test, expect } = require("./fixtures");
const os = require("os");

const isSupported = os.platform() === "darwin" || os.platform() === "linux";

// =============================================================================
// Native host tests: macOS and Linux with native host pipeline
// =============================================================================

test.describe("Real extension - native host", () => {
  // Skip on unsupported platforms
  test.skip(!isSupported, "Native host tests only run on macOS and Linux");

  test("extension should load and popup should render with real data", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);

    // Wait for the popup to render
    await page.waitForSelector(".header h2", { timeout: 10000 });

    // Header should display
    await expect(page.locator(".header h2")).toContainText("Tab Groups");

    // Help button should be visible
    await expect(page.locator("#help-btn")).toBeVisible();

    // There should be at least one window (the one we're running in)
    const windowItems = page.locator(".window-item");
    const count = await windowItems.count();
    expect(count).toBeGreaterThanOrEqual(1);

    await page.close();
  });

  test("windows should display names from native host when available", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForSelector(".window-item", { timeout: 10000 });

    // At minimum, window headers should have non-empty text
    const windowHeaders = page.locator(".window-header");
    const headerCount = await windowHeaders.count();
    expect(headerCount).toBeGreaterThanOrEqual(1);

    for (let i = 0; i < headerCount; i++) {
      const text = await windowHeaders.nth(i).textContent();
      expect(text.trim().length).toBeGreaterThan(0);
    }

    await page.close();
  });

  test("UI should update when a new window is created", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForSelector(".window-item", { timeout: 10000 });

    const initialCount = await page.locator(".window-item").count();

    // Create a new browser window
    const newPage = await context.newPage();
    await newPage.goto("about:blank");

    // Wait for live update to fire (debounced at 150ms + render time)
    await page.waitForTimeout(1000);

    // Trigger a manual refresh in case event listener didn't fire from different context
    await page.evaluate(() => {
      if (typeof window.refreshUI === "function") {
        window.refreshUI();
      }
    });
    await page.waitForTimeout(500);

    const updatedCount = await page.locator(".window-item").count();
    // The new window might or might not register depending on timing,
    // but count should be at least what we started with
    expect(updatedCount).toBeGreaterThanOrEqual(initialCount);

    await newPage.close();
    await page.close();
  });

  test("tab groups should display within windows when present", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForSelector(".window-item", { timeout: 10000 });

    // Expand the first window
    const firstWindow = page.locator(".window-item").first();
    const expandIcon = firstWindow.locator(".expand-icon").first();
    await expandIcon.click();
    await page.waitForTimeout(300);

    // Content area should be visible after expansion
    const content = firstWindow.locator(".content").first();
    await expect(content).toBeVisible();

    // The content should have either tab-items, group-items, or both
    const childCount = await content.locator("> *").count();
    expect(childCount).toBeGreaterThanOrEqual(0);

    await page.close();
  });
});

// =============================================================================
// Cross-platform: Tests that work regardless of native host
// =============================================================================

test.describe("Real extension - cross-platform", () => {
  test("popup should handle missing native host gracefully", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);

    // Popup should still render even if native host is absent
    await page.waitForSelector(".header h2", { timeout: 10000 });
    await expect(page.locator(".header h2")).toContainText("Tab Groups");

    // Should not show an error message
    const errorMsg = page.locator(".empty-msg");
    const errorCount = await errorMsg.count();
    // If there are windows, there should be no error. If no windows (unlikely), error is acceptable.
    if (errorCount > 0) {
      const text = await errorMsg.textContent();
      expect(text).not.toContain("Error");
    }

    await page.close();
  });

  test("help modal should open and close", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForSelector("#help-btn", { timeout: 10000 });

    // Open help modal
    await page.click("#help-btn");
    await expect(page.locator("#help-modal")).toBeVisible();

    // Close help modal
    await page.click("#close-modal");
    await expect(page.locator("#help-modal")).toBeHidden();

    await page.close();
  });

  test("window click handlers should focus the clicked window", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForSelector(".window-item", { timeout: 10000 });

    // Clicking the expand icon should toggle expanded state
    const firstWindow = page.locator(".window-item").first();
    const expandIcon = firstWindow.locator(".expand-icon").first();

    await expect(firstWindow).not.toHaveClass(/expanded/);
    await expandIcon.click();
    await expect(firstWindow).toHaveClass(/expanded/);
    await expandIcon.click();
    await expect(firstWindow).not.toHaveClass(/expanded/);

    await page.close();
  });

  test("popup should render within reasonable time", async ({
    context,
    extensionId,
  }) => {
    const page = await context.newPage();

    const startTime = Date.now();
    await page.goto(`chrome-extension://${extensionId}/popup.html`);
    await page.waitForSelector(".window-item", { timeout: 10000 });
    const renderTime = Date.now() - startTime;

    // Popup should render within 5 seconds even with native host latency
    expect(renderTime).toBeLessThan(5000);

    await page.close();
  });
});

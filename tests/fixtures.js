/**
 * Playwright fixtures for Chrome extension testing
 * Based on: https://playwright.dev/docs/chrome-extensions
 * 
 * This extension is a popup-only Manifest V3 extension without a background service worker.
 * We use a different approach to get the extension ID.
 */

const { test: base, chromium } = require("@playwright/test");
const path = require("path");
const fs = require("fs");

/**
 * Custom test fixture that loads the extension and provides the extension ID
 */
const test = base.extend({
  context: async ({}, use) => {
    const pathToExtension = path.join(__dirname, "..");
    const context = await chromium.launchPersistentContext("", {
      channel: "chromium",
      headless: false,
      args: [
        `--disable-extensions-except=${pathToExtension}`,
        `--load-extension=${pathToExtension}`,
        "--no-sandbox",
      ],
    });
    await use(context);
    await context.close();
  },
  extensionId: async ({ context }, use) => {
    // For popup-only extensions without a service worker,
    // we need to get the extension ID from the extensions page
    const page = await context.newPage();
    await page.goto("chrome://extensions");
    
    // Wait for the extensions page to load
    await page.waitForTimeout(1000);
    
    // Get the extension ID from the page
    // The extension ID is displayed on the extensions page
    const extensionId = await page.evaluate(() => {
      // Try to find the extension card
      const extensionsManager = document.querySelector("extensions-manager");
      if (extensionsManager && extensionsManager.shadowRoot) {
        const itemsList = extensionsManager.shadowRoot.querySelector("extensions-item-list");
        if (itemsList && itemsList.shadowRoot) {
          const items = itemsList.shadowRoot.querySelectorAll("extensions-item");
          for (const item of items) {
            if (item.shadowRoot) {
              const name = item.shadowRoot.querySelector("#name");
              if (name && name.textContent.includes("Tab Groups")) {
                // Get the ID from the item's id attribute
                return item.id;
              }
            }
          }
        }
      }
      return null;
    });
    
    await page.close();
    
    if (!extensionId) {
      // Fallback: read the extension ID from a known location or use a hardcoded approach
      // For testing purposes, we'll try to navigate to the popup directly
      // and extract the ID from the URL
      const manifestPath = path.join(__dirname, "..", "manifest.json");
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      
      // Generate a predictable extension ID based on the extension path
      // This is a workaround for testing purposes
      throw new Error("Could not determine extension ID. Please ensure the extension is loaded correctly.");
    }
    
    await use(extensionId);
  },
});

const expect = test.expect;

module.exports = { test, expect };

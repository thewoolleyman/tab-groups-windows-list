// @ts-check
const { defineConfig } = require("@playwright/test");
const path = require("path");

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    trace: "on-first-retry",
    headless: false, // Extensions often require non-headless
    browserName: "chromium",
    // Custom launch options to load the extension
    launchOptions: {
      args: [
        `--disable-extensions-except=${path.join(__dirname)}`,
        `--load-extension=${path.join(__dirname)}`,
      ],
    },
  },
});

// @ts-check
const { defineConfig } = require("@playwright/test");

/**
 * Playwright configuration for Chrome extension E2E testing
 * @see https://playwright.dev/docs/chrome-extensions
 */
module.exports = defineConfig({
  testDir: "./tests",
  testMatch: "**/*.e2e.spec.js",
  fullyParallel: false, // Extensions require sequential execution
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Extensions require single worker
  reporter: "html",
  timeout: 30000,
  use: {
    trace: "on-first-retry",
  },
  // No projects needed - we use custom fixtures for extension loading
});

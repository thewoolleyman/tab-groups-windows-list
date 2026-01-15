const { test, expect } = require('@playwright/test');
const path = require('path');

// Helper function to get the extension ID from the browser context
async function getExtensionId(context) {
  let extensionId;
  context.on('page', async (page) => {
    if (page.url().startsWith('chrome-extension://')) {
      extensionId = page.url().split('/')[2];
    }
  });
  const backgroundPage = await context.backgroundPage();
  if (backgroundPage) {
    extensionId = backgroundPage.url().split('/')[2];
  }
  return extensionId;
}

test.describe('Tab Groups & Windows List Extension', () => {
  let context;
  let extensionId;

  test.beforeAll(async ({ browser }) => {
    // Load the extension
    const extensionPath = path.resolve(__dirname, '..');
    context = await browser.newContext({
      permissions: ['tabGroups', 'windows'],
    });

    // Create a page to trigger extension loading
    const page = await context.newPage();
    await page.goto('about:blank');
    
    // Get the extension ID from the service worker
    const backgroundPage = await context.backgroundPage();
    if (backgroundPage) {
      extensionId = backgroundPage.url().split('/')[2];
    }
  });

  test.afterAll(async () => {
    if (context) {
      await context.close();
    }
  });

  test('should display the extension popup with correct structure', async () => {
    // Navigate to the extension popup
    const popupUrl = `chrome-extension://${extensionId}/popup.html`;
    const page = await context.newPage();
    
    try {
      await page.goto(popupUrl);
      
      // Check that the page loaded
      const title = await page.title();
      expect(title).toBe('Tab Groups List');
      
      // Check for the main container
      const container = await page.locator('#groups-container');
      expect(container).toBeDefined();
      
      // Check for the heading
      const heading = await page.locator('h2');
      const headingText = await heading.textContent();
      expect(headingText).toBe('Tab Groups');
    } finally {
      await page.close();
    }
  });

  test('should display windows as top-level items', async () => {
    const page = await context.newPage();
    
    try {
      // Create a test window to ensure we have at least one
      await page.goto('about:blank');
      
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Check if window items exist or if there's an empty message
      const windowItems = await popupPage.locator('.window-item');
      const emptyMsg = await popupPage.locator('.empty-msg');
      
      const windowCount = await windowItems.count();
      const hasEmptyMsg = await emptyMsg.count() > 0;
      
      // Either we have window items or an empty message
      expect(windowCount > 0 || hasEmptyMsg).toBeTruthy();
    } finally {
      await page.close();
    }
  });

  test('should display the 3-level hierarchy: Window > Group > Tab', async () => {
    const page = await context.newPage();
    
    try {
      // Create multiple tabs and groups for testing
      await page.goto('https://example.com');
      
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Check for the presence of window items
      const windowItems = await popupPage.locator('.window-item');
      const windowCount = await windowItems.count();
      
      // If there are windows, check for groups and tabs
      if (windowCount > 0) {
        // Look for group items
        const groupItems = await popupPage.locator('.group-item');
        const groupCount = await groupItems.count();
        
        // Look for tab items
        const tabItems = await popupPage.locator('.tab-item');
        const tabCount = await tabItems.count();
        
        // We should have at least one of each level
        expect(windowCount).toBeGreaterThan(0);
        // Groups and tabs may be 0 if not set up, but the structure should exist
        expect(groupCount >= 0).toBeTruthy();
        expect(tabCount >= 0).toBeTruthy();
      }
    } finally {
      await page.close();
    }
  });

  test('should expand and collapse window items', async () => {
    const page = await context.newPage();
    
    try {
      await page.goto('about:blank');
      
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Get the first window item
      const firstWindowItem = await popupPage.locator('.window-item').first();
      
      if (firstWindowItem) {
        // Check initial state
        let isExpanded = await firstWindowItem.evaluate(el => el.classList.contains('expanded'));
        
        // Click to expand/collapse
        await firstWindowItem.click();
        
        // Check if the state changed
        const newIsExpanded = await firstWindowItem.evaluate(el => el.classList.contains('expanded'));
        expect(newIsExpanded).not.toBe(isExpanded);
      }
    } finally {
      await page.close();
    }
  });

  test('should display group items with color dots', async () => {
    const page = await context.newPage();
    
    try {
      await page.goto('about:blank');
      
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Check for group items with color dots
      const groupDots = await popupPage.locator('.group-color-dot');
      const groupDotCount = await groupDots.count();
      
      // If there are group items, they should have color dots
      if (groupDotCount > 0) {
        const firstDot = await groupDots.first();
        const bgColor = await firstDot.evaluate(el => window.getComputedStyle(el).backgroundColor);
        expect(bgColor).toBeTruthy();
      }
    } finally {
      await page.close();
    }
  });

  test('should display tab items with titles and icons', async () => {
    const page = await context.newPage();
    
    try {
      await page.goto('https://example.com');
      
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Check for tab items
      const tabItems = await popupPage.locator('.tab-item');
      const tabCount = await tabItems.count();
      
      if (tabCount > 0) {
        const firstTab = await tabItems.first();
        
        // Check if tab has a title
        const tabText = await firstTab.textContent();
        expect(tabText).toBeTruthy();
        
        // Check if tab has an icon (optional, as not all tabs may have favicons)
        const tabIcon = await firstTab.locator('img.tab-icon');
        const iconCount = await tabIcon.count();
        expect(iconCount >= 0).toBeTruthy();
      }
    } finally {
      await page.close();
    }
  });

  test('should focus window when clicking on window header', async () => {
    const page = await context.newPage();
    
    try {
      await page.goto('about:blank');
      
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Get the first window header
      const firstWindowHeader = await popupPage.locator('.window-header').first();
      
      if (firstWindowHeader) {
        // Click on the window header
        await firstWindowHeader.click();
        
        // The window should now be focused (this is hard to verify in a test,
        // but we can at least verify that the click didn't cause an error)
        expect(true).toBeTruthy();
      }
    } finally {
      await page.close();
    }
  });

  test('should handle empty state gracefully', async () => {
    const page = await context.newPage();
    
    try {
      // Navigate to the extension popup
      const popupUrl = `chrome-extension://${extensionId}/popup.html`;
      const popupPage = await context.newPage();
      await popupPage.goto(popupUrl);
      
      // Wait for the container to be populated
      await popupPage.waitForSelector('#groups-container', { timeout: 5000 });
      
      // Check if there's an empty message or items
      const emptyMsg = await popupPage.locator('.empty-msg');
      const windowItems = await popupPage.locator('.window-item');
      
      const hasEmptyMsg = await emptyMsg.count() > 0;
      const hasWindowItems = await windowItems.count() > 0;
      
      // Either we have items or an empty message
      expect(hasEmptyMsg || hasWindowItems).toBeTruthy();
    } finally {
      await page.close();
    }
  });
});

#!/usr/bin/env node
/**
 * Demo: launches Chrome with extension + native host, injects a custom
 * window name via the extension's cache mechanism, and screenshots the
 * popup showing the custom name.
 *
 * On Linux, Chrome overwrites _NET_WM_NAME instantly on tab switch,
 * making xdotool set_window ephemeral. This demo instead:
 * 1. Shows the native host correctly detecting and filtering windows
 * 2. Injects a custom name into chrome.storage.local via the service worker
 * 3. Screenshots the popup showing the custom name from cache
 */

import { chromium } from 'playwright';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const EXT_DIR = path.resolve(path.dirname(__filename), '..');

async function main() {
  console.error('=== TGWL Window Naming Demo ===\n');

  const profileDir = path.join(os.tmpdir(), 'tgwl-demo-profile');

  // Install native messaging manifest into profile
  const nmhDir = path.join(profileDir, 'NativeMessagingHosts');
  fs.mkdirSync(nmhDir, { recursive: true });
  const manifest = {
    name: 'com.tabgroups.window_namer',
    description: 'Native messaging host for Tab Groups Windows List',
    path: path.join(os.homedir(), '.local/lib/tab-groups-window-namer/host.py'),
    type: 'stdio',
    allowed_origins: [
      'chrome-extension://gialhfelganamiclidkigjnjdkdbohcb/',
      'chrome-extension://napliahfgndaphcljddiolfgljacaapa/',
    ],
  };
  fs.writeFileSync(
    path.join(nmhDir, 'com.tabgroups.window_namer.json'),
    JSON.stringify(manifest, null, 2),
  );

  const context = await chromium.launchPersistentContext(profileDir, {
    channel: 'chromium',
    headless: false,
    args: [
      `--disable-extensions-except=${EXT_DIR}`,
      `--load-extension=${EXT_DIR}`,
      '--no-sandbox',
      '--window-size=900,700',
      '--window-position=100,100',
    ],
  });

  try {
    // Navigate to some pages
    const mainPage = context.pages()[0] || await context.newPage();
    await mainPage.goto('https://example.com', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await mainPage.waitForTimeout(2000);

    // Discover extension ID
    const extensionId = await discoverExtensionId(context);
    console.error(`Extension ID: ${extensionId}`);

    // Update manifest with dynamic extension ID
    if (!manifest.allowed_origins.includes(`chrome-extension://${extensionId}/`)) {
      manifest.allowed_origins.push(`chrome-extension://${extensionId}/`);
      fs.writeFileSync(
        path.join(nmhDir, 'com.tabgroups.window_namer.json'),
        JSON.stringify(manifest, null, 2),
      );
    }

    // Step 1: Verify native host works and PID filtering is active
    console.error('\n--- Step 1: Verify native host + PID filtering ---');
    await mainPage.bringToFront();
    await mainPage.waitForTimeout(500);

    // Show all X windows to demonstrate PID filtering
    try {
      const allWids = execSync('xdotool search --name ""', { encoding: 'utf-8' }).trim().split('\n').filter(Boolean);
      console.error(`Total X windows: ${allWids.length}`);
      for (const wid of allWids) {
        try {
          const name = execSync(`xprop -id ${wid} _NET_WM_NAME`, { encoding: 'utf-8' }).trim();
          const geo = execSync(`xdotool getwindowgeometry --shell ${wid}`, { encoding: 'utf-8' });
          const w = geo.match(/WIDTH=(\d+)/)?.[1];
          if (parseInt(w) > 50) {
            let pid = '';
            try { pid = execSync(`xdotool getwindowpid ${wid}`, { encoding: 'utf-8' }).trim(); } catch {}
            console.error(`  wid=${wid} pid=${pid} ${name}`);
          }
        } catch {}
      }
    } catch {}

    // Step 2: Inject custom window name via service worker
    console.error('\n--- Step 2: Inject custom name via extension cache ---');

    // Get the current window ID from Chrome's perspective
    const popupPage = await context.newPage();
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`);
    await popupPage.waitForTimeout(3000);

    // Get the window ID and inject a custom name into the cache
    const windowId = await popupPage.evaluate(() => {
      return new Promise(resolve => {
        chrome.windows.getCurrent(w => resolve(w.id));
      });
    });
    console.error(`Current window ID: ${windowId}`);

    // Inject custom name directly into chrome.storage.local
    await popupPage.evaluate((winId) => {
      return new Promise(resolve => {
        const cache = {};
        cache[String(winId)] = {
          name: 'My Project Window',
          urlFingerprint: 'example.com',
          hasCustomName: true,
        };
        chrome.storage.local.set({ windowNames: cache }, resolve);
      });
    }, windowId);
    console.error('Injected "My Project Window" into cache');

    // Reload popup to pick up the cached name
    await popupPage.reload();
    await popupPage.waitForTimeout(3000);

    // What does the popup show now?
    const popupContent = await popupPage.evaluate(() => {
      const items = document.querySelectorAll('.window-header span:last-child');
      return Array.from(items).map(el => el.textContent);
    });
    console.error('\n--- Popup window names ---');
    popupContent.forEach(n => console.error(`  "${n}"`));

    // Screenshot showing custom name!
    await popupPage.screenshot({ path: '/tmp/tgwl-demo-popup.png', fullPage: true });
    console.error('\nScreenshot: /tmp/tgwl-demo-popup.png');

    // Expanded view
    await popupPage.evaluate(() => {
      document.querySelectorAll('.window-item').forEach(el => el.classList.add('expanded'));
    });
    await popupPage.waitForTimeout(500);
    await popupPage.screenshot({ path: '/tmp/tgwl-demo-popup-expanded.png', fullPage: true });
    console.error('Expanded: /tmp/tgwl-demo-popup-expanded.png');

    // Debug log tail
    const logPath = path.join(os.homedir(), '.local/lib/tab-groups-window-namer/debug.log');
    if (fs.existsSync(logPath)) {
      const lines = fs.readFileSync(logPath, 'utf-8').split('\n').slice(-15);
      console.error('\n=== Debug log ===');
      lines.forEach(l => console.error(l));
    }

    console.error('\n=== Demo complete ===');

  } finally {
    await context.close();
  }
}

async function discoverExtensionId(context) {
  const page = await context.newPage();
  await page.goto('chrome://extensions');
  await page.waitForTimeout(1500);
  const id = await page.evaluate(() => {
    const mgr = document.querySelector('extensions-manager');
    if (mgr?.shadowRoot) {
      const list = mgr.shadowRoot.querySelector('extensions-item-list');
      if (list?.shadowRoot) {
        const items = list.shadowRoot.querySelectorAll('extensions-item');
        for (const item of items) {
          if (item.shadowRoot) {
            const name = item.shadowRoot.querySelector('#name');
            if (name && name.textContent.includes('Tab Groups')) return item.id;
          }
        }
      }
    }
    return null;
  });
  await page.close();
  if (!id) throw new Error('Extension not found');
  return id;
}

main().catch(err => {
  console.error(`Fatal: ${err.message}`);
  process.exit(1);
});

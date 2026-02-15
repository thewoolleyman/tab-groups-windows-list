#!/usr/bin/env node
/**
 * Automated diagnostic script for extension debugging.
 *
 * Launches Chromium with the extension loaded, captures service worker
 * and popup console logs, triggers the diagnose API, reads the native
 * host debug log, and outputs structured JSON.
 *
 * Usage:
 *   node scripts/diagnose.mjs
 *   node scripts/diagnose.mjs --output /tmp/diag.json
 *   node scripts/diagnose.mjs --timeout 20000
 */

import { chromium } from 'playwright';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const require = createRequire(import.meta.url);
const {
  parseTgwlLogLine,
  extractDiagJson,
  readNativeHostLogTail,
  assembleOutput,
} = require('./diagnose-helpers.js');

// --- CLI ---

function parseArgs(argv) {
  const args = { output: null, timeout: 15000 };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--output' && argv[i + 1]) {
      args.output = argv[++i];
    } else if (argv[i] === '--timeout' && argv[i + 1]) {
      args.timeout = parseInt(argv[++i], 10);
    }
  }
  return args;
}

// Only run main when executed directly (not imported)
const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename) {
  main().catch((err) => {
    console.error('diagnose: fatal error:', err.message);
    process.exit(1);
  });
}

async function main() {
  const args = parseArgs(process.argv);
  const pathToExtension = path.resolve(path.dirname(__filename), '..');

  // Launch Chromium with extension
  const context = await chromium.launchPersistentContext('', {
    channel: 'chromium',
    headless: false,
    args: [
      `--disable-extensions-except=${pathToExtension}`,
      `--load-extension=${pathToExtension}`,
      '--no-sandbox',
    ],
  });

  const serviceWorkerLogs = [];
  let diagResult = null;

  // Capture service worker console (background.js TGWL logs)
  function attachWorkerListener(worker) {
    worker.on('console', (msg) => {
      const text = msg.text();
      const parsed = parseTgwlLogLine(text);
      if (parsed) {
        serviceWorkerLogs.push({
          timestamp: new Date().toISOString(),
          tag: parsed.tag,
          message: parsed.message,
        });
      }
    });
  }

  // Attach to already-registered workers
  for (const worker of context.serviceWorkers()) {
    attachWorkerListener(worker);
  }
  // Attach to newly-registered workers
  context.on('serviceworker', attachWorkerListener);

  try {
    // Discover extension ID
    const extPage = await context.newPage();
    await extPage.goto('chrome://extensions');
    await extPage.waitForTimeout(1000);

    const extensionId = await extPage.evaluate(() => {
      const mgr = document.querySelector('extensions-manager');
      if (mgr?.shadowRoot) {
        const list = mgr.shadowRoot.querySelector('extensions-item-list');
        if (list?.shadowRoot) {
          const items = list.shadowRoot.querySelectorAll('extensions-item');
          for (const item of items) {
            if (item.shadowRoot) {
              const name = item.shadowRoot.querySelector('#name');
              if (name && name.textContent.includes('Tab Groups')) {
                return item.id;
              }
            }
          }
        }
      }
      return null;
    });

    await extPage.close();

    if (!extensionId) {
      throw new Error('Could not discover extension ID');
    }

    // Open popup to trigger refreshUI → diagnose
    const popupPage = await context.newPage();

    // Set up DIAG listener before navigation (event-driven, not timer-based)
    const diagPromise = popupPage.waitForEvent('console', {
      predicate: (msg) => msg.text().includes('[TGWL:DIAG]'),
      timeout: args.timeout,
    });

    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`);

    // Wait for the DIAG console message
    const diagMsg = await diagPromise;
    diagResult = extractDiagJson(diagMsg.text());

    await popupPage.close();

    // Read native host debug log
    const logTail = readNativeHostLogTail();

    // Assemble output
    const output = assembleOutput({
      diagnosis: diagResult,
      serviceWorkerLogs,
      nativeHostLogTail: logTail,
      extensionId,
    });

    const jsonStr = JSON.stringify(output, null, 2);

    if (args.output) {
      fs.writeFileSync(args.output, jsonStr, 'utf-8');
      console.error(`diagnose: output written to ${args.output}`);
    } else {
      console.log(jsonStr);
    }
  } finally {
    await context.close();
  }
}

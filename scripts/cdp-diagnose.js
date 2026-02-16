#!/usr/bin/env node
/**
 * CDP-based diagnostic client for Tab Groups Windows List.
 * Connects to a Chromium browser with --remote-debugging-port,
 * triggers extension diagnostics, and captures results.
 *
 * Usage:
 *   node scripts/cdp-diagnose.js [--port 9222] [--output file.json]
 */

const http = require('http');
const fs = require('fs');

const CDP_PORT = parseInt(process.argv.find((_, i, a) => a[i-1] === '--port') || '9222', 10);
const OUTPUT_FILE = process.argv.find((_, i, a) => a[i-1] === '--output') || null;

async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

async function main() {
  console.error(`Connecting to CDP on port ${CDP_PORT}...`);

  // List targets
  const targets = await fetchJson(`http://127.0.0.1:${CDP_PORT}/json`);
  console.error(`Found ${targets.length} targets`);

  // Find extension background page/service worker
  const extTarget = targets.find(t =>
    t.type === 'service_worker' && t.title?.includes('Tab Groups')
  ) || targets.find(t =>
    t.type === 'background_page' && t.url?.includes('chrome-extension://')
  );

  if (!extTarget) {
    console.error('Available targets:');
    targets.forEach(t => console.error(`  ${t.type}: ${t.title || t.url}`));
    throw new Error('Extension service worker not found');
  }

  console.error(`Extension target: ${extTarget.title} (${extTarget.type})`);

  const result = {
    targets: targets.map(t => ({ type: t.type, title: t.title, url: t.url })),
    extensionId: extTarget.url?.match(/chrome-extension:\/\/([^/]+)/)?.[1] || null,
    cdpPort: CDP_PORT,
    timestamp: new Date().toISOString(),
  };

  const output = JSON.stringify(result, null, 2);
  if (OUTPUT_FILE) {
    fs.writeFileSync(OUTPUT_FILE, output);
    console.error(`Output written to ${OUTPUT_FILE}`);
  } else {
    console.log(output);
  }
}

// Only run when executed directly, not when require()'d
if (require.main === module) {
  main().catch(err => {
    console.error(`cdp-diagnose: ${err.message}`);
    process.exit(1);
  });
}

module.exports = { fetchJson, main };

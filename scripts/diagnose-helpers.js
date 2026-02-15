/**
 * Parseable helpers for the diagnostic script.
 * Extracted to CommonJS for testability with Jest.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

/**
 * Parse a [TGWL:<tag>] log line into structured form.
 * @param {string} text - Raw console message text
 * @returns {{ tag: string, message: string } | null}
 */
function parseTgwlLogLine(text) {
  const match = text.match(/^\[TGWL:([^\]]+)\]\s*(.*)/s);
  if (!match) return null;
  return { tag: match[1], message: match[2] };
}

/**
 * Extract the DIAG JSON payload from a [TGWL:DIAG] console line.
 * @param {string} text - Raw console message text
 * @returns {object | null} Parsed diagnosis object, or null
 */
function extractDiagJson(text) {
  const parsed = parseTgwlLogLine(text);
  if (!parsed || parsed.tag !== 'DIAG') return null;
  try {
    return JSON.parse(parsed.message);
  } catch {
    return null;
  }
}

/**
 * Read the last N lines of the native host debug log.
 * @param {number} [lines=50]
 * @param {string} [logPath] - Override log path (for testing)
 * @returns {string} Tail content or descriptive message
 */
function readNativeHostLogTail(lines = 50, logPath) {
  const resolvedPath = logPath ||
    path.join(os.homedir(), '.local', 'lib', 'tab-groups-window-namer', 'debug.log');
  try {
    const content = fs.readFileSync(resolvedPath, 'utf-8');
    const allLines = content.split('\n');
    return allLines.slice(-lines).join('\n');
  } catch (err) {
    if (err.code === 'ENOENT') return '(log file not found)';
    return `(error reading log: ${err.message})`;
  }
}

/**
 * Assemble the final output structure.
 * @param {object} params
 * @param {object|null} params.diagnosis - runDiagnosis() result
 * @param {Array} params.serviceWorkerLogs - Parsed TGWL log entries
 * @param {string} params.nativeHostLogTail - Debug log tail
 * @param {string} params.extensionId - Discovered extension ID
 * @param {object} [params.directHostTest] - Direct native host test result
 * @returns {object}
 */
function assembleOutput({ diagnosis, serviceWorkerLogs, nativeHostLogTail, extensionId, directHostTest }) {
  return {
    diagnosis: diagnosis || { error: 'no diagnosis received' },
    directHostTest: directHostTest || null,
    serviceWorkerLogs,
    nativeHostLogTail,
    metadata: {
      capturedAt: new Date().toISOString(),
      extensionId: extensionId || '(unknown)',
      platform: process.platform,
    },
  };
}

const { execFileSync } = require('child_process');

const PUBLISHED_EXTENSION_ID = 'gialhfelganamiclidkigjnjdkdbohcb';
const HOST_NAME = 'com.tabgroups.window_namer';

/**
 * Get the path to the Chromium NativeMessagingHosts manifest.
 * @returns {string}
 */
function getChromiumManifestPath() {
  return path.join(
    os.homedir(),
    'Library', 'Application Support', 'Chromium',
    'NativeMessagingHosts', `${HOST_NAME}.json`,
  );
}

/**
 * Patch the native messaging manifest to include a dynamic extension ID.
 * Returns the original manifest content for later restoration, or null
 * if no patching was needed (ID already present or extensionId is null).
 * If no manifest exists, creates one pointing to the installed host.py.
 * @param {string|null} extensionId - Dynamic extension ID from Playwright
 * @param {string} [manifestPath] - Override path (for testing)
 * @returns {object|null} Original manifest for restoration, or null
 */
function patchManifestForExtensionId(extensionId, manifestPath) {
  if (!extensionId) return null;

  const resolvedPath = manifestPath || getChromiumManifestPath();
  const dynamicOrigin = `chrome-extension://${extensionId}/`;

  let original = null;
  try {
    const content = fs.readFileSync(resolvedPath, 'utf-8');
    original = JSON.parse(content);
  } catch (_e) {
    // File doesn't exist — we'll create one
  }

  if (original) {
    // Check if already present
    if (original.allowed_origins && original.allowed_origins.includes(dynamicOrigin)) {
      return null;
    }

    // Clone and add the dynamic ID
    const patched = { ...original };
    patched.allowed_origins = [...(original.allowed_origins || []), dynamicOrigin];
    fs.writeFileSync(resolvedPath, JSON.stringify(patched, null, 2), 'utf-8');
    return original;
  }

  // Create new manifest
  const hostPyPath = path.join(
    os.homedir(), '.local', 'lib', 'tab-groups-window-namer', 'host.py',
  );
  const newManifest = {
    name: HOST_NAME,
    description: 'Native messaging host for Tab Groups Windows List window name reading',
    path: hostPyPath,
    type: 'stdio',
    allowed_origins: [dynamicOrigin],
  };
  fs.mkdirSync(path.dirname(resolvedPath), { recursive: true });
  fs.writeFileSync(resolvedPath, JSON.stringify(newManifest, null, 2), 'utf-8');
  return null;
}

/**
 * Restore the native messaging manifest to its original state.
 * @param {object|null} backup - Original manifest from patchManifestForExtensionId
 * @param {string} [manifestPath] - Override path (for testing)
 */
function restoreManifest(backup, manifestPath) {
  const resolvedPath = manifestPath || getChromiumManifestPath();
  try {
    if (backup) {
      fs.writeFileSync(resolvedPath, JSON.stringify(backup, null, 2), 'utf-8');
    } else {
      // We created the file — clean up
      fs.unlinkSync(resolvedPath);
    }
  } catch (_e) {
    // Best effort — don't crash if cleanup fails
  }
}

/**
 * Encode a JSON message using the Chrome native messaging protocol
 * (4-byte little-endian length prefix + JSON body).
 * @param {object} msg - Message to encode
 * @returns {Buffer}
 */
function encodeNativeMessage(msg) {
  const body = Buffer.from(JSON.stringify(msg), 'utf-8');
  const header = Buffer.alloc(4);
  header.writeUInt32LE(body.length, 0);
  return Buffer.concat([header, body]);
}

/**
 * Decode a Chrome native messaging protocol response.
 * @param {Buffer} raw - Raw response bytes
 * @returns {object|null} Parsed response, or null if invalid
 */
function decodeNativeMessage(raw) {
  if (!raw || raw.length < 4) return null;
  const length = raw.readUInt32LE(0);
  if (raw.length < 4 + length) return null;
  try {
    return JSON.parse(raw.slice(4, 4 + length).toString('utf-8'));
  } catch {
    return null;
  }
}

/**
 * Test the native host by directly spawning it and sending a request.
 * Bypasses Chrome entirely — validates the host binary works.
 * @param {string} [hostPath] - Override host.py path (for testing)
 * @returns {{ reachable: boolean, response: object|null, error: string|null, windowCount: number, customNameCount: number }}
 */
function testNativeHostDirect(hostPath) {
  const resolvedPath = hostPath ||
    path.join(os.homedir(), '.local', 'lib', 'tab-groups-window-namer', 'host.py');

  try {
    if (!fs.existsSync(resolvedPath)) {
      return { reachable: false, response: null, error: 'host.py not found', windowCount: 0, customNameCount: 0 };
    }

    const input = encodeNativeMessage({ action: 'get_window_names' });
    const result = execFileSync('python3', [resolvedPath], {
      input,
      timeout: 10000,
      maxBuffer: 1024 * 1024,
    });

    const response = decodeNativeMessage(result);
    if (!response) {
      return { reachable: false, response: null, error: 'invalid response format', windowCount: 0, customNameCount: 0 };
    }

    return {
      reachable: response.success === true,
      response,
      error: response.error || null,
      windowCount: response.windows?.length || 0,
      customNameCount: (response.windows || []).filter((w) => w.hasCustomName).length,
    };
  } catch (err) {
    return { reachable: false, response: null, error: err.message, windowCount: 0, customNameCount: 0 };
  }
}

module.exports = {
  parseTgwlLogLine,
  extractDiagJson,
  readNativeHostLogTail,
  assembleOutput,
  patchManifestForExtensionId,
  restoreManifest,
  getChromiumManifestPath,
  encodeNativeMessage,
  decodeNativeMessage,
  testNativeHostDirect,
  PUBLISHED_EXTENSION_ID,
  HOST_NAME,
};

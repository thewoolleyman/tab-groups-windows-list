const fs = require('fs');
const path = require('path');
const os = require('os');

const {
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
} = require('../scripts/diagnose-helpers');

describe('parseTgwlLogLine', () => {
  it('parses a standard TGWL log line', () => {
    expect(parseTgwlLogLine('[TGWL:native-req] Sending get_window_names'))
      .toEqual({ tag: 'native-req', message: 'Sending get_window_names' });
  });

  it('parses a tag with hyphens and numbers', () => {
    expect(parseTgwlLogLine('[TGWL:cache-read] Popup requested window names'))
      .toEqual({ tag: 'cache-read', message: 'Popup requested window names' });
  });

  it('returns null for non-TGWL lines', () => {
    expect(parseTgwlLogLine('Some random log')).toBeNull();
    expect(parseTgwlLogLine('')).toBeNull();
    expect(parseTgwlLogLine('[OTHER:tag] msg')).toBeNull();
  });

  it('handles multiline messages', () => {
    const result = parseTgwlLogLine('[TGWL:error] line1\nline2');
    expect(result).toEqual({ tag: 'error', message: 'line1\nline2' });
  });

  it('handles empty message after tag', () => {
    expect(parseTgwlLogLine('[TGWL:ping] '))
      .toEqual({ tag: 'ping', message: '' });
  });
});

describe('extractDiagJson', () => {
  it('extracts valid DIAG JSON', () => {
    const diag = { nativeHost: { reachable: true }, matching: { pairs: [] } };
    const line = `[TGWL:DIAG] ${JSON.stringify(diag)}`;
    expect(extractDiagJson(line)).toEqual(diag);
  });

  it('returns null for non-DIAG TGWL lines', () => {
    expect(extractDiagJson('[TGWL:native-req] some text')).toBeNull();
  });

  it('returns null for invalid JSON in DIAG line', () => {
    expect(extractDiagJson('[TGWL:DIAG] not-json')).toBeNull();
  });

  it('returns null for non-TGWL lines', () => {
    expect(extractDiagJson('random text')).toBeNull();
  });
});

describe('readNativeHostLogTail', () => {
  let tmpDir;
  let logFile;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'diag-test-'));
    logFile = path.join(tmpDir, 'debug.log');
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('reads the last N lines from a log file', () => {
    const lines = Array.from({ length: 10 }, (_, i) => `line ${i}`);
    fs.writeFileSync(logFile, lines.join('\n'), 'utf-8');

    const result = readNativeHostLogTail(3, logFile);
    expect(result).toBe('line 7\nline 8\nline 9');
  });

  it('returns full content when fewer lines than requested', () => {
    fs.writeFileSync(logFile, 'only line', 'utf-8');
    const result = readNativeHostLogTail(50, logFile);
    expect(result).toBe('only line');
  });

  it('returns descriptive message for missing file', () => {
    const result = readNativeHostLogTail(50, '/nonexistent/path/debug.log');
    expect(result).toBe('(log file not found)');
  });

  it('returns error message for permission errors', () => {
    // Create a directory where the file path points — readFileSync will fail
    const dirAsFile = path.join(tmpDir, 'is-a-dir');
    fs.mkdirSync(dirAsFile);
    const result = readNativeHostLogTail(50, dirAsFile);
    expect(result).toMatch(/^\(error reading log:/);
  });
});

describe('assembleOutput', () => {
  it('assembles all fields into the expected structure', () => {
    const diagnosis = { nativeHost: { reachable: true } };
    const serviceWorkerLogs = [{ timestamp: '2025-01-01T00:00:00Z', tag: 'test', message: 'hi' }];
    const nativeHostLogTail = 'log line';
    const extensionId = 'abc123';

    const result = assembleOutput({ diagnosis, serviceWorkerLogs, nativeHostLogTail, extensionId });

    expect(result.diagnosis).toBe(diagnosis);
    expect(result.serviceWorkerLogs).toBe(serviceWorkerLogs);
    expect(result.nativeHostLogTail).toBe('log line');
    expect(result.metadata.extensionId).toBe('abc123');
    expect(result.metadata.platform).toBe(process.platform);
    expect(result.metadata.capturedAt).toBeDefined();
  });

  it('includes directHostTest when provided', () => {
    const directHostTest = { reachable: true, windowCount: 5 };
    const result = assembleOutput({
      diagnosis: { nativeHost: { reachable: true } },
      serviceWorkerLogs: [],
      nativeHostLogTail: '',
      extensionId: 'abc',
      directHostTest,
    });
    expect(result.directHostTest).toBe(directHostTest);
  });

  it('uses fallback when diagnosis is null', () => {
    const result = assembleOutput({
      diagnosis: null,
      serviceWorkerLogs: [],
      nativeHostLogTail: '',
      extensionId: null,
    });

    expect(result.diagnosis).toEqual({ error: 'no diagnosis received' });
    expect(result.directHostTest).toBeNull();
    expect(result.metadata.extensionId).toBe('(unknown)');
  });
});

describe('getChromiumManifestPath', () => {
  it('returns the Chromium NativeMessagingHosts path for the host', () => {
    const result = getChromiumManifestPath();
    expect(result).toContain('Chromium');
    expect(result).toContain('NativeMessagingHosts');
    expect(result).toContain(HOST_NAME);
    expect(result).toMatch(/\.json$/);
  });
});

describe('patchManifestForExtensionId', () => {
  let tmpDir;
  let manifestPath;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'manifest-test-'));
    manifestPath = path.join(tmpDir, `${HOST_NAME}.json`);
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('adds dynamic extension ID to allowed_origins when manifest exists', () => {
    const original = {
      name: HOST_NAME,
      description: 'test',
      path: '/usr/local/bin/host.py',
      type: 'stdio',
      allowed_origins: [`chrome-extension://${PUBLISHED_EXTENSION_ID}/`],
    };
    fs.writeFileSync(manifestPath, JSON.stringify(original), 'utf-8');

    const dynamicId = 'abcdefghijklmnopqrstuvwxyzabcdef';
    const backup = patchManifestForExtensionId(dynamicId, manifestPath);

    expect(backup).toEqual(original);

    const patched = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    expect(patched.allowed_origins).toContain(`chrome-extension://${PUBLISHED_EXTENSION_ID}/`);
    expect(patched.allowed_origins).toContain(`chrome-extension://${dynamicId}/`);
    expect(patched.allowed_origins).toHaveLength(2);
  });

  it('does not duplicate if dynamic ID matches published ID', () => {
    const original = {
      name: HOST_NAME,
      description: 'test',
      path: '/usr/local/bin/host.py',
      type: 'stdio',
      allowed_origins: [`chrome-extension://${PUBLISHED_EXTENSION_ID}/`],
    };
    fs.writeFileSync(manifestPath, JSON.stringify(original), 'utf-8');

    const backup = patchManifestForExtensionId(PUBLISHED_EXTENSION_ID, manifestPath);
    expect(backup).toBeNull();

    const patched = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    expect(patched.allowed_origins).toHaveLength(1);
  });

  it('creates manifest directory and file when neither exists', () => {
    const deepPath = path.join(tmpDir, 'sub', 'dir', `${HOST_NAME}.json`);
    const dynamicId = 'abcdefghijklmnopqrstuvwxyzabcdef';

    const backup = patchManifestForExtensionId(dynamicId, deepPath);

    expect(backup).toBeNull();
    expect(fs.existsSync(deepPath)).toBe(true);

    const created = JSON.parse(fs.readFileSync(deepPath, 'utf-8'));
    expect(created.allowed_origins).toContain(`chrome-extension://${dynamicId}/`);
    expect(created.name).toBe(HOST_NAME);
  });

  it('returns null when extensionId is null', () => {
    const result = patchManifestForExtensionId(null, manifestPath);
    expect(result).toBeNull();
  });
});

describe('restoreManifest', () => {
  let tmpDir;
  let manifestPath;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'manifest-test-'));
    manifestPath = path.join(tmpDir, `${HOST_NAME}.json`);
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('restores the original manifest from backup', () => {
    const patched = { name: HOST_NAME, allowed_origins: ['chrome-extension://dynamic/', 'chrome-extension://published/'] };
    fs.writeFileSync(manifestPath, JSON.stringify(patched), 'utf-8');

    const backup = { name: HOST_NAME, allowed_origins: ['chrome-extension://published/'] };
    restoreManifest(backup, manifestPath);

    const restored = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    expect(restored).toEqual(backup);
  });

  it('removes manifest file when backup is null and file was created by patch', () => {
    fs.writeFileSync(manifestPath, '{}', 'utf-8');
    restoreManifest(null, manifestPath);
    // When backup is null, we created the file — remove it
    expect(fs.existsSync(manifestPath)).toBe(false);
  });

  it('handles missing file gracefully', () => {
    expect(() => restoreManifest({ name: HOST_NAME }, '/nonexistent/path.json')).not.toThrow();
  });
});

describe('encodeNativeMessage', () => {
  it('encodes a message with 4-byte LE length prefix', () => {
    const msg = { action: 'test' };
    const encoded = encodeNativeMessage(msg);
    const body = JSON.stringify(msg);

    expect(encoded.length).toBe(4 + body.length);
    expect(encoded.readUInt32LE(0)).toBe(body.length);
    expect(encoded.slice(4).toString('utf-8')).toBe(body);
  });
});

describe('decodeNativeMessage', () => {
  it('decodes a valid native message', () => {
    const msg = { success: true, windows: [] };
    const encoded = encodeNativeMessage(msg);
    expect(decodeNativeMessage(encoded)).toEqual(msg);
  });

  it('returns null for too-short buffer', () => {
    expect(decodeNativeMessage(Buffer.alloc(2))).toBeNull();
    expect(decodeNativeMessage(null)).toBeNull();
  });

  it('returns null for truncated body', () => {
    const header = Buffer.alloc(4);
    header.writeUInt32LE(100, 0);
    expect(decodeNativeMessage(header)).toBeNull();
  });

  it('returns null for invalid JSON', () => {
    const body = Buffer.from('not json', 'utf-8');
    const header = Buffer.alloc(4);
    header.writeUInt32LE(body.length, 0);
    expect(decodeNativeMessage(Buffer.concat([header, body]))).toBeNull();
  });
});

describe('testNativeHostDirect', () => {
  it('returns error for missing host.py', () => {
    const result = testNativeHostDirect('/nonexistent/host.py');
    expect(result.reachable).toBe(false);
    expect(result.error).toBe('host.py not found');
  });

  it('returns successful result when host.py responds correctly', () => {
    // Use the actual host.py in the repo
    const hostPath = path.join(__dirname, '..', 'native-host', 'host.py');
    if (!fs.existsSync(hostPath)) {
      // Skip if host.py doesn't exist (CI environment)
      return;
    }
    const result = testNativeHostDirect(hostPath);
    // The host should be reachable (it may or may not find windows)
    expect(result.response).toBeDefined();
    expect(result).toHaveProperty('reachable');
    expect(result).toHaveProperty('windowCount');
    expect(result).toHaveProperty('customNameCount');
    expect(typeof result.windowCount).toBe('number');
    expect(typeof result.customNameCount).toBe('number');
  });

  it('returns error for invalid response format when host produces garbage', () => {
    // Create a script that writes non-native-messaging output
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'host-test-'));
    const fakePath = path.join(tmpDir, 'fake_host.py');
    fs.writeFileSync(fakePath, `#!/usr/bin/env python3
import sys
sys.stdout.buffer.write(b"not a native message")
`, 'utf-8');
    fs.chmodSync(fakePath, 0o755);

    const result = testNativeHostDirect(fakePath);
    expect(result.reachable).toBe(false);
    expect(result.error).toBe('invalid response format');

    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('returns error when host.py execution fails (timeout or crash)', () => {
    // Create a script that exits with error
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'host-test-'));
    const crashPath = path.join(tmpDir, 'crash_host.py');
    fs.writeFileSync(crashPath, `#!/usr/bin/env python3
import sys
sys.exit(1)
`, 'utf-8');
    fs.chmodSync(crashPath, 0o755);

    const result = testNativeHostDirect(crashPath);
    expect(result.reachable).toBe(false);
    expect(result.error).toBeTruthy();
    expect(typeof result.error).toBe('string');

    fs.rmSync(tmpDir, { recursive: true, force: true });
  });
});

describe('patchManifestForExtensionId - missing allowed_origins', () => {
  let tmpDir;
  let manifestPath;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'manifest-test-'));
    manifestPath = path.join(tmpDir, `${HOST_NAME}.json`);
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('handles manifest with no allowed_origins field', () => {
    const original = {
      name: HOST_NAME,
      description: 'test',
      path: '/usr/local/bin/host.py',
      type: 'stdio',
      // No allowed_origins field at all
    };
    fs.writeFileSync(manifestPath, JSON.stringify(original), 'utf-8');

    const dynamicId = 'abcdefghijklmnopqrstuvwxyzabcdef';
    const backup = patchManifestForExtensionId(dynamicId, manifestPath);

    expect(backup).toEqual(original);

    const patched = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    expect(patched.allowed_origins).toContain(`chrome-extension://${dynamicId}/`);
    expect(patched.allowed_origins).toHaveLength(1);
  });
});

// =============================================================
// diagnose.mjs parseArgs (tested via CommonJS-compatible extract)
// =============================================================

describe('parseArgs logic', () => {
  // parseArgs is in diagnose.mjs (ESM), but the logic is simple enough
  // to replicate and test the contract here
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

  it('returns defaults with no arguments', () => {
    const result = parseArgs(['node', 'diagnose.mjs']);
    expect(result).toEqual({ output: null, timeout: 15000 });
  });

  it('parses --output flag', () => {
    const result = parseArgs(['node', 'diagnose.mjs', '--output', '/tmp/diag.json']);
    expect(result.output).toBe('/tmp/diag.json');
    expect(result.timeout).toBe(15000);
  });

  it('parses --timeout flag', () => {
    const result = parseArgs(['node', 'diagnose.mjs', '--timeout', '20000']);
    expect(result.timeout).toBe(20000);
    expect(result.output).toBeNull();
  });

  it('parses both flags together', () => {
    const result = parseArgs(['node', 'diagnose.mjs', '--output', '/tmp/out.json', '--timeout', '5000']);
    expect(result.output).toBe('/tmp/out.json');
    expect(result.timeout).toBe(5000);
  });

  it('ignores unknown flags', () => {
    const result = parseArgs(['node', 'diagnose.mjs', '--verbose', '--output', '/tmp/x.json']);
    expect(result.output).toBe('/tmp/x.json');
  });

  it('ignores --output without value', () => {
    const result = parseArgs(['node', 'diagnose.mjs', '--output']);
    expect(result.output).toBeNull();
  });
});

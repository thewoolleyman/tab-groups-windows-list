const fs = require('fs');
const path = require('path');
const os = require('os');

const {
  parseTgwlLogLine,
  extractDiagJson,
  readNativeHostLogTail,
  assembleOutput,
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

  it('uses fallback when diagnosis is null', () => {
    const result = assembleOutput({
      diagnosis: null,
      serviceWorkerLogs: [],
      nativeHostLogTail: '',
      extensionId: null,
    });

    expect(result.diagnosis).toEqual({ error: 'no diagnosis received' });
    expect(result.metadata.extensionId).toBe('(unknown)');
  });
});

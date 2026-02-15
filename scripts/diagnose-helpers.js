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
 * @returns {object}
 */
function assembleOutput({ diagnosis, serviceWorkerLogs, nativeHostLogTail, extensionId }) {
  return {
    diagnosis: diagnosis || { error: 'no diagnosis received' },
    serviceWorkerLogs,
    nativeHostLogTail,
    metadata: {
      capturedAt: new Date().toISOString(),
      extensionId: extensionId || '(unknown)',
      platform: process.platform,
    },
  };
}

module.exports = {
  parseTgwlLogLine,
  extractDiagJson,
  readNativeHostLogTail,
  assembleOutput,
};

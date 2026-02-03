#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const OUTPUT_DIR = path.join('dist', 'extension-builds');
const HTML_ASSET_PATTERN = /<(script|link|img)\b[^>]*?(src|href)=["']([^"']+)["']/gi;

function sanitizeBaseName(name) {
  if (!name || typeof name !== 'string') {
    throw new Error('Package name is required to build artifact name.');
  }

  return name
    .trim()
    .replace(/^@/, '')
    .replace(/[\s\\/]+/g, '-');
}

function formatTimestamp(date) {
  const pad = (value) => String(value).padStart(2, '0');

  return [
    date.getUTCFullYear(),
    pad(date.getUTCMonth() + 1),
    pad(date.getUTCDate())
  ].join('') +
    '-' +
    [
      pad(date.getUTCHours()),
      pad(date.getUTCMinutes()),
      pad(date.getUTCSeconds())
    ].join('');
}

function buildArtifactName(baseName, version, date = new Date()) {
  if (!version || typeof version !== 'string') {
    throw new Error('Version is required to build artifact name.');
  }

  const safeBaseName = sanitizeBaseName(baseName);
  const timestamp = formatTimestamp(date);

  return `${safeBaseName}-v${version}-${timestamp}.zip`;
}

function addFile(fileSet, value) {
  if (typeof value !== 'string') {
    return;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return;
  }

  if (trimmed.includes('*') || trimmed.includes('?') || trimmed.includes('[')) {
    return;
  }

  fileSet.add(trimmed);
}

function addFilesFrom(fileSet, value) {
  if (Array.isArray(value)) {
    value.forEach((entry) => addFile(fileSet, entry));
    return;
  }

  if (value && typeof value === 'object') {
    Object.values(value).forEach((entry) => addFile(fileSet, entry));
  }
}

function collectManifestFiles(manifest) {
  const files = new Set(['manifest.json']);

  if (manifest.action) {
    addFile(files, manifest.action.default_popup);
    addFilesFrom(files, manifest.action.default_icon);
  }

  addFilesFrom(files, manifest.icons);

  if (manifest.background) {
    addFile(files, manifest.background.service_worker);
    addFilesFrom(files, manifest.background.scripts);
  }

  if (Array.isArray(manifest.content_scripts)) {
    manifest.content_scripts.forEach((entry) => {
      addFilesFrom(files, entry.js);
      addFilesFrom(files, entry.css);
      addFile(files, entry.html);
    });
  }

  if (manifest.options_ui) {
    addFile(files, manifest.options_ui.page);
  }

  addFile(files, manifest.options_page);
  addFile(files, manifest.devtools_page);

  if (manifest.chrome_url_overrides) {
    addFilesFrom(files, manifest.chrome_url_overrides);
  }

  if (manifest.side_panel) {
    addFile(files, manifest.side_panel.default_path);
  }

  if (Array.isArray(manifest.web_accessible_resources)) {
    manifest.web_accessible_resources.forEach((entry) => {
      addFilesFrom(files, entry.resources);
    });
  }

  return Array.from(files);
}

function isRemoteAsset(assetPath) {
  return /^(?:[a-z]+:)?\/\//i.test(assetPath) || assetPath.startsWith('data:');
}

function normalizeRelativePath(relativePath) {
  return path.posix.normalize(relativePath.replace(/\\/g, '/'));
}

function collectHtmlDependencies(rootDir, fileSet) {
  const htmlFiles = Array.from(fileSet).filter((file) => file.endsWith('.html'));

  htmlFiles.forEach((htmlFile) => {
    const htmlPath = path.join(rootDir, htmlFile);
    if (!fs.existsSync(htmlPath)) {
      return;
    }

    const content = fs.readFileSync(htmlPath, 'utf8');
    const htmlDir = path.posix.dirname(normalizeRelativePath(htmlFile));

    HTML_ASSET_PATTERN.lastIndex = 0;
    let match = HTML_ASSET_PATTERN.exec(content);
    while (match) {
      const asset = match[3];
      if (!isRemoteAsset(asset)) {
        const cleaned = asset.split('#')[0].split('?')[0];
        const relativeAsset = cleaned.startsWith('/')
          ? cleaned.slice(1)
          : path.posix.join(htmlDir, cleaned);

        const normalized = normalizeRelativePath(relativeAsset);
        if (!normalized.includes('*') && !normalized.includes('?')) {
          fileSet.add(normalized);
        }
      }

      match = HTML_ASSET_PATTERN.exec(content);
    }
  });
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function ensureFilesExist(rootDir, files) {
  const missing = files.filter((file) => !fs.existsSync(path.join(rootDir, file)));

  if (missing.length > 0) {
    const details = missing.map((file) => `- ${file}`).join('\n');
    throw new Error(`Missing extension files:\n${details}`);
  }
}

function createZip(rootDir, outputPath, files) {
  const args = ['-r', outputPath, ...files];
  const result = spawnSync('zip', args, {
    cwd: rootDir,
    encoding: 'utf8'
  });

  if (result.status !== 0) {
    const stderr = result.stderr ? result.stderr.trim() : '';
    const stdout = result.stdout ? result.stdout.trim() : '';
    const message = stderr || stdout || 'Unknown zip error';
    throw new Error(`Zip failed: ${message}`);
  }
}

function buildExtension() {
  const rootDir = path.resolve(__dirname, '..');
  const pkg = readJson(path.join(rootDir, 'package.json'));
  const manifest = readJson(path.join(rootDir, 'manifest.json'));

  const baseName = sanitizeBaseName(pkg.name || manifest.name || 'extension');
  const version = manifest.version || pkg.version;

  if (!version) {
    throw new Error('Unable to determine extension version.');
  }

  const outputDir = path.join(rootDir, OUTPUT_DIR);
  fs.mkdirSync(outputDir, { recursive: true });

  const artifactName = buildArtifactName(baseName, version);
  const artifactPath = path.join(outputDir, artifactName);

  const fileSet = new Set(collectManifestFiles(manifest));
  collectHtmlDependencies(rootDir, fileSet);

  const files = Array.from(fileSet).sort();
  ensureFilesExist(rootDir, files);

  createZip(rootDir, artifactPath, files);

  process.stdout.write(`${artifactPath}\n`);
}

if (require.main === module) {
  try {
    buildExtension();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${message}\n`);
    process.exit(1);
  }
}

module.exports = {
  buildArtifactName,
  collectManifestFiles,
  formatTimestamp,
  sanitizeBaseName
};

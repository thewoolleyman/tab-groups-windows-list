const {
  buildArtifactName,
  collectManifestFiles,
  formatTimestamp,
  sanitizeBaseName
} = require('../scripts/build-extension');

describe('build-extension helpers', () => {
  test('sanitizeBaseName removes scope and path separators', () => {
    expect(sanitizeBaseName('@scope/my-extension')).toBe('scope-my-extension');
    expect(sanitizeBaseName('plain-name')).toBe('plain-name');
  });

  test('formatTimestamp outputs stable UTC timestamp', () => {
    const date = new Date(Date.UTC(2026, 1, 3, 4, 5, 6));
    expect(formatTimestamp(date)).toBe('20260203-040506');
  });

  test('buildArtifactName combines base, version, and timestamp', () => {
    const date = new Date(Date.UTC(2026, 1, 3, 4, 5, 6));
    expect(buildArtifactName('tab-groups', '1.2.3', date)).toBe(
      'tab-groups-v1.2.3-20260203-040506.zip'
    );
  });

  test('collectManifestFiles includes expected manifest paths', () => {
    const manifest = {
      action: {
        default_popup: 'popup.html',
        default_icon: {
          16: 'icons/icon16.png'
        }
      },
      icons: {
        48: 'icons/icon48.png'
      },
      background: {
        service_worker: 'background.js'
      },
      content_scripts: [
        {
          js: ['content.js'],
          css: ['content.css']
        }
      ],
      options_ui: {
        page: 'options.html'
      },
      chrome_url_overrides: {
        newtab: 'newtab.html'
      },
      side_panel: {
        default_path: 'sidepanel.html'
      },
      web_accessible_resources: [
        {
          resources: ['images/icon.png']
        }
      ]
    };

    const files = collectManifestFiles(manifest);
    const expected = [
      'manifest.json',
      'popup.html',
      'icons/icon16.png',
      'icons/icon48.png',
      'background.js',
      'content.js',
      'content.css',
      'options.html',
      'newtab.html',
      'sidepanel.html',
      'images/icon.png'
    ];

    expected.forEach((file) => {
      expect(files).toContain(file);
    });
  });
});

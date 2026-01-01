# Tab Groups & Windows List

A simple Chrome extension that provides a 2-level expandable list of your current tab groups and the windows they belong to.

**Chrome Web Store**: [Tab Groups & Windows List](https://chromewebstore.google.com/detail/tab-groups-windows-list/gialhfelganamiclidkigjnjdkdbohcb)

**Extension ID**: `gialhfelganamiclidkigjnjdkdbohcb`

## Features

- **Expandable List**: View all your tab groups at a glance and expand them to see their host window.
- **Color Matching**: Automatically matches the color of your tab groups for easy identification.
- **Lightweight**: Minimalist design with no background processes.

## Installation (Manual)

1. Download this repository as a ZIP file and extract it.
2. Open Chrome and go to `chrome://extensions/`.
3. Enable **Developer mode** in the top right corner.
4. Click **Load unpacked** and select the extracted folder.

## Developers

This section provides instructions for developers looking to maintain or deploy this extension.

### Automated Publishing to Chrome Web Store

This repository is equipped with a GitHub Action for automated publishing. This allows for a "1-button" deployment to the Chrome Web Store.

#### Prerequisites

To use the automated deployment, you must first:
1. **Register as a Chrome Web Store Developer**: Sign up at the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/).
2. **Create a New Item**: Manually upload the first version of the extension to get an `EXTENSION_ID`.
3. **Setup Google Cloud Project**:
   - Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
   - Enable the **Chrome Web Store API**.
   - Create **OAuth 2.0 Client IDs** (Web application) to get a `CLIENT_ID` and `CLIENT_SECRET`.
   - Obtain a `REFRESH_TOKEN` using the Google OAuth 2.0 Playground or a similar tool.

#### GitHub Secrets Configuration

Add the following secrets to your GitHub repository (**Settings > Secrets and variables > Actions**):

| Secret Name | Description |
|-------------|-------------|
| `EXTENSION_ID` | The unique ID of your extension in the Chrome Web Store (`gialhfelganamiclidkigjnjdkdbohcb`). |
| `CLIENT_ID` | Your Google Cloud OAuth 2.0 Client ID. |
| `CLIENT_SECRET` | Your Google Cloud OAuth 2.0 Client Secret. |
| `REFRESH_TOKEN` | The OAuth 2.0 Refresh Token for the Chrome Web Store API. |

#### Triggering a Release (GitHub Release)

Before you can publish to the Chrome Web Store, you need a ZIP file of the extension. You can generate this and create a GitHub Release using the **Create Release** workflow:

1. Navigate to the **Actions** tab.
2. Select the **Create Release** workflow.
3. Click **Run workflow**.
4. Choose the `version_type` (patch, minor, or major).
5. Once complete, a new release will be created with the `extension.zip` attached, and the version in the repository will be automatically incremented.

#### Triggering a Deployment (Chrome Web Store)

Once you have your `EXTENSION_ID` from the first manual upload (using the ZIP from the GitHub Release), you can use the **Publish to Chrome Web Store** workflow:

1. Navigate to the **Actions** tab.
2. Select the **Publish to Chrome Web Store** workflow.
3. Click **Run workflow**.
4. Choose the `publish_target` (default is `default`).

The workflow will package the current code and upload it to the store for review.

## Privacy Policy

This extension respects your privacy. 

- **Data Access**: It only accesses your tab groups, tabs, and windows information locally within your browser to generate the list.
- **No Data Collection**: It does not collect, store, or transmit any personal or sensitive user data.
- **No Third-Party Sharing**: No data is ever shared with third parties.
- **No Tracking**: There are no background trackers, analytics, or advertising scripts.

## License

This project is released into the public domain under the [UNLICENSE](LICENSE).

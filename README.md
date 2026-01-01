# Tab Groups & Windows List

A simple Chrome extension that provides a 2-level expandable list of your current tab groups and the windows they belong to.

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
| `EXTENSION_ID` | The unique ID of your extension in the Chrome Web Store. |
| `CLIENT_ID` | Your Google Cloud OAuth 2.0 Client ID. |
| `CLIENT_SECRET` | Your Google Cloud OAuth 2.0 Client Secret. |
| `REFRESH_TOKEN` | The OAuth 2.0 Refresh Token for the Chrome Web Store API. |

#### Triggering a Deployment

1. Navigate to the **Actions** tab in this repository.
2. Select the **Publish to Chrome Web Store** workflow.
3. Click **Run workflow**.
4. Choose the `publish_target` (default is `default` for public, or `trusted_testers` for private testing).

The workflow will automatically package the extension and upload it to the store for review.

## License

This project is released into the public domain under the [UNLICENSE](LICENSE).

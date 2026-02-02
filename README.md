# Tab Groups & Windows List

A simple Chrome extension that provides a 3-level expandable list of your current tab groups and the windows they belong to.

**Chrome Web Store**: [Tab Groups & Windows List](https://chromewebstore.google.com/detail/tab-groups-windows-list/gialhfelganamiclidkigjnjdkdbohcb)

**Extension ID**: `gialhfelganamiclidkigjnjdkdbohcb`

## Features

- **3-Level Hierarchy**: View all your windows, tab groups, and tabs in a nested, expandable list.
- **Color Matching**: Automatically matches the color of your tab groups for easy identification.
- **Lightweight**: Minimalist design with no background processes.

## Installation (Manual)

1. Download the latest release ZIP file from the [Releases](https://github.com/thewoolleyman/tab-groups-windows-list/releases) page.
2. Unzip the file.
3. Open Chrome and go to `chrome://extensions/`.
4. Enable **Developer mode** in the top right corner.
5. Click **Load unpacked** and select the extracted folder.

## CI/CD Pipeline for Developers

This repository has a unified CI/CD pipeline that automates the build, test, and release process. Here’s how it works:

### Pipeline Stages

The pipeline consists of four stages:

| Stage | Job Name | Description |
|-------|----------|-------------|
| **Build** | `build` | Packages the extension and extracts the version from `manifest.json`. |
| **Test** | `unit-tests`, `e2e-tests` | Runs unit and E2E tests in parallel after the build completes. Tests run autonomously without manual intervention. |
| **Release** | `release` | Automatically creates a GitHub Release with the packaged extension if tests pass. |
| **Publish** | `publish` | Publishes the extension to the Chrome Web Store after manual approval. |

### Automated GitHub Releases

On every successful push to `master` where the tests pass, a GitHub Release is automatically created. The release is tagged with the version from `manifest.json` and includes the packaged `extension.zip` file.

### Manual Publish to Chrome Web Store

While the GitHub Release is automatic, publishing to the Chrome Web Store requires **manual approval** to prevent accidental deployments.

#### How to Manually Approve a Publish

1. **Push to `master`**: Make sure your changes are pushed to the `master` branch.
2. **Wait for Tests to Pass**: The pipeline will run the build and test stages automatically.
3. **Review Deployment**: Once the tests pass, the `publish` job will start and immediately pause, showing a "Waiting for review" status.
4. **Approve in GitHub**: Go to your repository’s **Actions** tab. You will see the running pipeline. Click on it, and you will see a **"Review deployments"** button. Click it, select the `production` environment, and click **"Approve and deploy"**.

   ![Review Deployments](https://i.imgur.com/your-image-url.png) *<-- Placeholder for screenshot of the approval button*

5. **Automatic Publish**: Once approved, the workflow will proceed to upload and submit the extension to the Chrome Web Store automatically.

### One-Time Setup for Publishing

To enable the manual publish feature, you need to configure a `production` environment and add secrets.

#### 1. Create the `production` Environment

1. Go to your repository **Settings > Environments**.
2. Click **New environment**.
3. Name it `production`.
4. Enable **Required reviewers** and add yourself.
5. Click **Save protection rules**.

#### 2. Add GitHub Secrets

Add the following secrets to your repository (**Settings > Secrets and variables > Actions**):

| Secret Name | Description |
|-------------|-------------|
| `CHROME_CLIENT_ID` | Your Google Cloud OAuth 2.0 Client ID. |
| `CHROME_CLIENT_SECRET` | Your Google Cloud OAuth 2.0 Client Secret. |
| `CHROME_REFRESH_TOKEN` | The OAuth 2.0 Refresh Token for the Chrome Web Store API. |
| `CHROME_PUBLISHER_ID` | Your Chrome Web Store Publisher ID. |

For detailed instructions on how to obtain these credentials, see the [Chrome Web Store API Credentials Guide](chrome-webstore-api-credentials.md).

## Privacy Policy

This extension respects your privacy. 

- **Data Access**: It only accesses your tab groups, tabs, and windows information locally within your browser to generate the list.
- **No Data Collection**: It does not collect, store, or transmit any personal or sensitive user data.
- **No Third-Party Sharing**: No data is ever shared with third parties.
- **No Tracking**: There are no background trackers, analytics, or advertising scripts.

## License

This project is released into the public domain under the [UNLICENSE](LICENSE).

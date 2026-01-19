# How to Obtain and Configure Chrome Web Store API Credentials

This guide provides step-by-step instructions for obtaining the necessary credentials to programmatically publish your Chrome extension using the GitHub Actions workflow. You will need to create four secrets in your GitHub repository: `CHROME_CLIENT_ID`, `CHROME_CLIENT_SECRET`, `CHROME_REFRESH_TOKEN`, and `CHROME_PUBLISHER_ID`.

---

## Part 1: Obtain Your Publisher ID

Your Publisher ID is required to identify your account when making API calls.

1. Navigate to the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole).
2. Click on the **Account** tab in the left-hand menu.
3. Your **Publisher ID** will be displayed under the "Account" heading. It is a long string of characters.
4. Copy this value. You will use it for the `CHROME_PUBLISHER_ID` secret.

---

## Part 2: Obtain OAuth Client ID and Client Secret

These credentials identify your application to Google's OAuth 2.0 servers.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. In the search bar at the top, type **"Chrome Web Store API"** and select it.
4. Click the **Enable** button if it is not already enabled.
5. In the left-hand navigation menu, go to **Google Auth Platform** (or **APIs & Services > OAuth consent screen** on older interfaces).
6. If prompted to configure the Google Auth Platform, click **Get started**.
7. Complete the **4-step wizard**:
   - **Step 1 - App Information**: Enter an App name and select your User support email.
   - **Step 2 - Audience**: Select **External** (unless you have a Google Workspace organization and want Internal only).
   - **Step 3 - Contact Information**: Enter your developer contact email.
   - **Step 4 - Finish**: Review and click **Create**.
8. After completing the wizard, go to **Clients** in the left-hand navigation menu (under Google Auth Platform).
9. Click **+ Create Client**.
10. For **Application type**, choose **Web application**.
11. Give it a name (e.g., "Chrome Web Store CI").
12. Under **Authorized redirect URIs**, click **+ Add URI** and enter: `https://developers.google.com/oauthplayground`
13. Click **Create**.
14. A dialog will appear showing your **Client ID** and **Client Secret**. Copy both of these values. You will use them for the `CHROME_CLIENT_ID` and `CHROME_CLIENT_SECRET` secrets, respectively.

---

## Part 3: Obtain a Refresh Token

A Refresh Token allows your CI workflow to obtain new access tokens without manual intervention.

1. Open the [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
2. In the top right corner, click the **gear icon** (OAuth 2.0 configuration).
3. Check the box for **Use your own OAuth credentials**.
4. Paste your **Client ID** and **Client Secret** into the respective fields.
5. In the **Step 1: Select & authorize APIs** section on the left, scroll down or type to find **Chrome Web Store API v2**.
6. Select the scope: `https://www.googleapis.com/auth/chromewebstore`
7. Click the **Authorize APIs** button.
8. You will be redirected to a Google sign-in page. Sign in with the account that owns the Chrome extension.
9. Grant the application permission to access your Chrome Web Store data.
10. You will be redirected back to the OAuth Playground. In **Step 2: Exchange authorization code for tokens**, click the **Exchange authorization code for tokens** button.
11. In **Step 2**, the **Refresh token** will be displayed. Copy this value. You will use it for the `CHROME_REFRESH_TOKEN` secret.

---

## Part 4: Add Credentials to GitHub Secrets

Finally, add the four credentials you obtained as secrets to your GitHub repository.

1. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
2. Click the **New repository secret** button for each of the following secrets:

| Secret Name              | Value                                  |
| ------------------------ | -------------------------------------- |
| `CHROME_CLIENT_ID`       | The Client ID you obtained in Part 2.  |
| `CHROME_CLIENT_SECRET`   | The Client Secret you obtained in Part 2.|
| `CHROME_REFRESH_TOKEN`   | The Refresh Token you obtained in Part 3.|
| `CHROME_PUBLISHER_ID`    | The Publisher ID you obtained in Part 1. |

---

## Part 5: Using the Workflow

Once these secrets are configured, you can manually trigger the "Publish to Chrome Web Store" workflow:

1. Go to your repository's **Actions** tab.
2. Select **"Publish to Chrome Web Store"** from the left sidebar.
3. Click **"Run workflow"**.
4. Enter the version number (must match `manifest.json`).
5. Choose whether to submit for review immediately.
6. Click **"Run workflow"**.

The workflow will upload your extension and submit it for Chrome Web Store review automatically.

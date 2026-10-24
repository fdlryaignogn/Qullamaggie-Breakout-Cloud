# Qullamaggie reviewer sign-in with GitHub (V3.3)

The main public stock dashboard stays at:
https://fdlryaignogn.github.io/Qullamaggie-Breakout-Cloud/

Visitors see public read-only stock selections. Owners/collaborators with **write/admin/maintain** repository permission may review Stage-2 setups **directly inside the dashboard** using **Sign in with GitHub**. Review outcomes are still enforced and audited by the existing `review-stage2.yml` GitHub Action. Stage 3 remains EOD WATCH-only, not automatic trading.

## Deployment status

The login implementation is prepared, but **not activated** until a GitHub App and a Cloudflare Worker have been configured. `site/auth-config.json` deliberately ships with `enabled: false`; PAT workflow remains available during migration. Do not claim sign-in is enabled before an end-to-end successful test.

## Step 1 — Publish secure login gateway

1. Open https://dash.cloudflare.com/ and go to **Workers & Pages → Create application → GitHub** (Cloudflare Workers Builds).
2. Authorize **Cloudflare's Git integration** to access **only** `fdlryaignogn/Qullamaggie-Breakout-Cloud`. (This is Cloudflare's own Git deployment integration, not the GitHub App we create for review.)
3. Select the repository, default **main** branch, **root directory `review-auth`**.
4. Worker project name **`qullamaggie-review-auth`** (matches `review-auth/wrangler.toml`). Default deploy command `npx wrangler deploy`. Save and Deploy.
5. Copy the assigned exact Worker HTTPS URL, e.g. `https://qullamaggie-review-auth.YOUR-SUBDOMAIN.workers.dev`. The placeholder is *not* a real URL. `/health` should initially say `{"status":"ok","configured":false}`.

Cloudflare's Git integration can redeploy changes pushed to main. There are no paid APIs required by this code, but review Cloudflare's account/plan limits.

## Step 2 — Register your own GitHub App

1. Logged into repository owner `fdlryaignogn`, open https://github.com/settings/apps/new .
2. App name: `Qullamaggie Cloud Reviewer` (or another globally unique name).
3. Homepage URL: `https://fdlryaignogn.github.io/Qullamaggie-Breakout-Cloud/`
4. **Callback URL**: **your actual Cloudflare Worker HTTPS URL** followed by `/auth/callback`.
   Disable callback wildcard matching; use the exact URL.
5. **Webhook**: Off / Active unchecked (not used). **Request user authorization (OAuth) during installation**: Off (sign-in starts from the dashboard instead).
6. **Repository permissions**: **Actions → Read and write**, **Metadata → Read** (required); all other repository permissions: No access. No organization/user permissions required.
7. **Where can this GitHub App be installed?** Select **Only on this account**. Register.
8. Go to app settings → **Install App**, choose owner `fdlryaignogn`, choose **Only select repositories**, select **Qullamaggie-Breakout-Cloud**. Do not install on all your repos.
9. Copy your **Client ID** (not App ID). Generate a **Client Secret** from GitHub App settings. The secret is highly sensitive; never paste it in ChatGPT, public repository, or screenshots.

**No GitHub App private key is needed**: this gateway uses a user's OAuth access token with Actions write permissions, never impersonates the app installation.

## Step 3 — Set runtime secrets on the Worker

In Cloudflare **Workers & Pages → qullamaggie-review-auth → Settings → Variables and Secrets**, add three **Secret** (encrypted) bindings:

| Secret name | Value |
|---|---|
| `GITHUB_CLIENT_ID` | Client ID shown in GitHub App settings |
| `GITHUB_CLIENT_SECRET` | GitHub App Client Secret (not GitHub password or PAT) |
| `SESSION_KEY` | Random 32-byte base64/base64url key **generated privately** |

On Windows PowerShell, generate a 32-byte key locally with:

```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

Use the output only as the Cloudflare **SESSION_KEY** secret. This is not the GitHub Client Secret. Save/Deploy the updated Worker secrets. Visit your actual `https://...workers.dev/health`, expecting `{"status":"ok","configured":true}`. Never publish or send any of the three secret values.

## Step 4 — Activate dashboard sign-in

Edit `site/auth-config.json` (public file; **no secrets**) to:

```json
{
  "enabled": true,
  "api_base": "https://YOUR-ACTUAL-WORKER-URL.workers.dev"
}
```

Only activate after `/health` succeeds. Ask the assistant to update the exact URL via the GitHub connection; it is fine to share the public **Worker URL** and **Client ID**, but **not** any secret.

GitHub Pages deployment publishes the configuration. Refresh the dashboard:
- **🔒 管理員核准 → 使用 GitHub 登入** redirects to the official GitHub authorization screen.
- Return to the same dashboard as `@fdlryaignogn`, then **Stage 2 → 審核 / 核准**.
- Submit `READY` only after manual chart confirmation and a public review reason.
- Backend verifies GitHub `/user`, **the current collaborator role** (`write` or `admin`, including `maintain` as write), and dispatches the existing GitHub Actions workflow. The workflow validates the actual setup and publishes an update.
- Non-collaborators and read-only users cannot submit.

## Authentication, storage and security behavior

- The Github App Client Secret and raw GitHub user access token remain **inside the Cloudflare Worker**. The browser receives only a **six-hour AES-GCM-encrypted sealed session**, held in localStorage until expiry or user logs out.
- The encrypted session grants authority while unexpired; protect your browser/device, and do not install unknown extensions. A malicious script running on the website could steal it. Use HTTPS exclusively. `SESSION_KEY` must remain secret; changing it immediately invalidates all sessions.
- Session is validated by the Worker on every relevant API call, with **current** GitHub repo permissions checked each time. GitHub App access expires independently, so a 401 can force earlier login.
- OAuth state is signed and linked to a random pending nonce stored in the initiating tab. Login callbacks require nonce match.
- A GitHub redirect URL fragment temporarily carries the sealed session, which is removed immediately by dashboard JS. It never carries the raw GitHub credential.
- The Worker validates Origin, structure, length, and confirmation for dispatched reviews. It cannot override the backend's READY validation.
- Clicking **Sign out** discards the local session, but does not globally revoke an already issued session if copied. Effective maximum lifetime is six hours; rotate SESSION_KEY to invalidate all sessions immediately. For stronger token revocation, a server-side session store would be required.
- **Not a brokerage connection, no order execution, no intraday trigger verification.**
- The PAT method stays available **only while `enabled` is false**. Once activated, the modal switches to GitHub App login.

## Functional test checklist

1. CI `Verify cloud scanner` passes Python, frontend JavaScript and Worker unit tests.
2. `GET /health` returns `configured: true`.
3. A visitor without sign-in cannot access review actions.
4. A signed-in account with no repository write rights receives access denied.
5. `fdlryaignogn` can sign in and see Stage 2 review buttons.
6. Submit test decision `FORMING` on a known tracked setup and confirm GitHub Actions run accepted, then published.
7. Check `READY` confirmation required and setup only becomes `READY` after workflow passes. Watchlist must be EOD WATCH, not automatic order.
8. Sign out, refresh, verify buttons hidden.
9. Test expiry/revocation, and verify no raw GitHub token in public site data, history or browser URL.

Useful docs: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app
and https://developers.cloudflare.com/workers/ci-cd/builds/ .

# Generate Site

Generate Site turns a written request into a working website. You describe the site in
plain words, Claude writes the source code, and the app publishes it and gives you a link.
You can then keep sending requests that change the same site.

It runs as two services on Render: a React page where you type requests, and a Flask API
that calls Claude and does the publishing.

## Contents

- [Using the app](#using-the-app)
- [Where a site is published](#where-a-site-is-published)
- [Publishing to your own GitHub repo](#publishing-to-your-own-github-repo)
- [Limits and cost](#limits-and-cost)
- [Administrator](#administrator)
- [How it works](#how-it-works)
- [Running it locally](#running-it-locally)
- [Deploying to Render](#deploying-to-render)
- [Configuration](#configuration)
- [What is stored](#what-is-stored)
- [Troubleshooting](#troubleshooting)

## Using the app

1. **Sign in** with Google, or with an email address alone. There is no password. A session
   lasts 60 minutes from sign-in; after that you sign in again.
2. **Type a request** in the box, for example:

   ```
   Generate Site with
   - Header
   - NavBar (left side)
   - Footer
   ```

   The **Load a previous request** list holds three built-in requests, numbered 1) to 3),
   that build on each other, followed by the requests you have sent yourself.
3. **Click Generate.** A generation usually takes one to a few minutes. The button shows a
   spinner while it runs.
4. **Open the result.** The page lists the generated files, the link to the source on
   GitHub, the link to the live site, and what the generation cost. In Render mode a preview
   of the site appears on the page once it is live.
5. **Refine it.** Send another request, such as "Add shopping cart to the site". While
   **Continue the previous site** is ticked, the request changes the site you generated
   last. Untick it to start a new site and leave the previous one as it is.

The last site is remembered in your browser, so you can continue it after reloading the
page. Signing out or changing **Publish to** forgets it.

After each generation a summary (request, links and cost) is emailed to the address you
signed in with, if the server has email configured.

## Where a site is published

The settings menu (top right) has a **Publish to** choice. It is saved per user.

| | Render static site (default) | GitHub Pages |
|---|---|---|
| What Claude generates | Plain HTML, CSS and JavaScript | A Vite + React + TypeScript project |
| Build step | None; files are served as they are | `npm install` and `npm run build` in GitHub Actions |
| Where the source goes | `sites/<timestamp>-<name>/` in the GitHub repo | The same folder in the GitHub repo |
| Where the site is served | A new Render static site, `https://<name>.onrender.com` | `https://<owner>.github.io/<repo>/` |
| Preview on the page | Yes, when the deploy finishes | No |

In both modes the source is committed to a GitHub repo, because Render builds a static site
only from a Git repository.

In GitHub Pages mode the repo serves one site at a time: the latest generation replaces
what Pages shows. In Render mode every new site gets its own Render service and address,
and refining a site redeploys its service.

## Publishing to your own GitHub repo

By default sites go to the server's repo (`SlavkoPar/AIGeneratedSite`) using the server's
token. To publish to a repo of your own:

1. Make sure the repo has a `README.md`, and set **Settings > Pages > Source** to
   **GitHub Actions**.
2. Create a fine-grained token at https://github.com/settings/personal-access-tokens.
   Select the repo and set **Contents**, **Workflows** and **Pages** to Read and write. If
   Pages was never enabled on the repo, also set **Administration** to Read and write.
3. Open the settings menu, enter the repo as `owner/repo`, paste the token, and click
   **Save**.

The repo name is remembered in your browser per user. The token is stored on the server,
encrypted, and is never sent back to the browser.

The same instructions are in the app: in the settings menu in Render mode, and behind the
help link in GitHub mode.

## Limits and cost

- Each user can run **3 generations**. The page shows how many are left. Only generations
  that reached Claude are counted, including ones that failed after Claude was called.
- Administrators have no limit, and can reset a user's count.
- Every generation shows its Claude token counts and cost in US dollars. The model is
  Claude Sonnet 5.5.
- Cost follows the amount of code written. A first request writes the whole site. A
  refinement sends the current site to Claude and gets back only the files that changed,
  so a small change to a large site is cheap, and a change that touches every page is not.

## Administrator

Addresses listed in `ADMIN_EMAILS` get an extra **Users** tab showing every registered user
and their generations with costs. From there an administrator can reset a user's
generation count, which lets them run 3 more.

The tab only appears when the administrator signs in with Google. Email-only sign-in does
not prove who is typing the address, so it never grants administrator rights.

## How it works

1. The page posts the request, the publish mode and, when continuing, the previous
   conversation to `POST /api/generate-site`.
2. The API calls Claude with a system prompt for the chosen mode and a JSON schema, so the
   answer is a list of files (`path` and `content`) plus a list of files to delete.
3. For a refinement, the changed files are merged into the previous site. The result is
   checked: allowed file types only, no dotfiles or paths outside the folder, and the
   files a Vite project or a plain site must have.
4. The files are committed to the GitHub repo under `sites/<timestamp>-<name>/`, with a
   `PROMPT.md` recording the requests.
5. The site is published:
   - **GitHub Pages:** the commit also updates `sites/LATEST` and
     `.github/workflows/deploy-generated-site.yml`. The change to `sites/LATEST` starts the
     workflow, which builds that folder and deploys `dist/` to Pages.
   - **Render:** the Render API creates a static site that serves the folder as it is, or
     redeploys the existing one for a refinement. The page polls
     `GET /api/render-status/<id>` and shows the preview when the deploy is live.
6. The generation is recorded with its cost, and the summary email is sent.

Claude's API keeps no memory between calls. The conversation is held in the browser and
sent back with each request: the text of every request so far, and one copy of the site as
it currently is.

### Project layout

| Path | What it is |
|---|---|
| `frontend/` | The React page (Vite). `src/App.jsx` is the main screen. |
| `backend/app.py` | Flask entry point; all routes are under `/api`. |
| `backend/routes/` | `auth.py` (sign-in), `generate.py` (generation), `profile.py` (settings, admin). |
| `backend/services/claude.py` | The Claude call, model and price table. |
| `backend/services/site_generator.py` | System prompts, output schema, validation, merging. |
| `backend/services/github_store.py` | Commits to GitHub and sets up Pages. |
| `backend/services/render_store.py` | Creates and redeploys Render static sites. |
| `backend/services/auth.py` | Sessions, administrators, the generation limit. |
| `backend/services/db.py` | Users and generations (SQLite). |
| `backend/services/mailer.py` | The summary email (SMTP). |
| `render.yaml` | Render Blueprint for both services. |

## Running it locally

You need Python 3.12 (the version Render uses) and a current Node.js LTS.

**API**, from `backend/`:

```
python -m venv ../.venv
../.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: ../.venv/bin/pip
../.venv/Scripts/python app.py
```

It listens on http://localhost:5000. Put the settings in `backend/.env` (see
[Configuration](#configuration)); at minimum `ANTHROPIC_API_KEY`, `GITHUB_TOKEN` and
`SECRET_KEY`.

**Page**, from `frontend/`:

```
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` to the API on port 5000.

## Deploying to Render

[`render.yaml`](./render.yaml) deploys the app itself (not the sites it generates) as two
services:

- **generate-site-api**: the Flask API in `backend/`, run with gunicorn.
- **generate-site-ui**: the React page in `frontend/`, published as a static site.

Push this repository to GitHub, then in Render choose **New > Blueprint**, select the
repository and apply `render.yaml`. Set the secrets when prompted.

If Render gives the API an address other than `https://generate-site-api.onrender.com`
(the name was taken), update `VITE_API_URL` in `render.yaml`.

Changing an environment variable on Render redeploys the API. A generation that is running
at that moment is cut off, and the page reports that it lost the connection.

## Configuration

Environment variables of the API (`backend/.env` locally, the service's Environment page on
Render):

| Variable | Needed | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Calls Claude. |
| `GITHUB_TOKEN` | Yes | Writes to the default repo: Contents, Workflows and Pages set to Read and write. |
| `SECRET_KEY` | Yes | Signs sessions and encrypts saved GitHub tokens. Render generates it. Changing it makes saved tokens unreadable. |
| `GITHUB_REPO` | No | Default repo for generated sites; `SlavkoPar/AIGeneratedSite` if unset. |
| `GITHUB_BRANCH` | No | Branch to commit to; `main` if unset. |
| `GOOGLE_CLIENT_ID` | No | Enables the Google button. Without it only email sign-in is offered. |
| `ADMIN_EMAILS` | No | Comma-separated administrator addresses. |
| `RENDER_API_KEY` | For Render mode | Creates static sites (Render dashboard > Account Settings > API Keys). |
| `RENDER_OWNER_ID` | No | The Render workspace to create sites in; the first one if unset. |
| `SQLITE_PATH` | No | Database file; `backend/data.db` if unset. |
| `SMTP_HOST`, `SMTP_PORT` | For email | Mail server, for example `smtp.gmail.com` and `587`. Port 587 uses STARTTLS, 465 implicit TLS. |
| `SMTP_USER`, `SMTP_PASSWORD` | For email | The login. For Gmail use an app password. |
| `MAIL_FROM` | No | Sender, for example `Generate Site <you@gmail.com>`; `SMTP_USER` if unset. |

The page has one build-time variable, `VITE_API_URL`, the address of the API.

**Google sign-in:** create the client ID in the Google Cloud Console under **APIs &
Services > Credentials > Create credentials > OAuth client ID**, type **Web application**,
and add the page's address to **Authorized JavaScript origins**
(`https://generate-site-ui.onrender.com`, plus `http://localhost:5173` for local work).

**Render mode:** Render must be able to read the GitHub repo. Either the repo is public, or
the Render account's GitHub connection has access to it.

Settings in code: the model and output cap are in `backend/services/claude.py`, the
generation limit and session length in `backend/services/auth.py`.

## What is stored

**On the server** (SQLite): one row per user with their email, name, GitHub repo, GitHub
token (encrypted) and publish mode, and one row per generation with the request, links,
token counts and cost.

On Render the service's filesystem is wiped on every deploy and restart, so users, tokens
and costs are lost unless you attach a persistent disk (paid plans) and point `SQLITE_PATH`
at a file on it, for example `/var/data/data.db`.

**In the browser** (localStorage): the session, your sent requests, the last generated site
and its conversation, and the GitHub repo name per user. The GitHub token is not kept in the
browser.

**Sign-in is not verified for email.** The email option sends no message and checks
nothing: it identifies a user, it does not prove they own the address. Anyone who types
someone else's address gets that user's remaining generations and can publish with their
saved token.

## Troubleshooting

| Message or symptom | Cause and fix |
|---|---|
| "You have used all 3 of your generations." | The limit is reached. An administrator can reset it in the Users tab. |
| "Lost the connection to the server before it answered" | The API restarted during the generation, usually because of a deploy. Try again. |
| "The site is too large to return in one answer" | Claude's answer hit the output cap. Send a narrower request, or untick **Continue the previous site**. |
| "Resource not accessible by personal access token", or "not built or published" | The token cannot add the build workflow. Add the Workflows permission and generate again. The source is still saved to the repo. |
| "Could not switch Pages to deploy from GitHub Actions", or "Could not enable Pages" | The token cannot change the Pages setting. Add the Pages permission, or set **Settings > Pages > Source** to **GitHub Actions** by hand, then re-run the failed "Deploy generated site" run in the Actions tab. Needed once per repo. |
| "Render is not configured on the server (RENDER_API_KEY)" | Set `RENDER_API_KEY` on the API service. |
| No email arrives | Check spam. The result on the page says whether the email was sent. Render's free web services block outbound SMTP, so email needs a paid instance. |
| The Users tab is missing | Sign in with Google using an address listed in `ADMIN_EMAILS`. |
| "Continue the previous site" is missing | It appears only once a site has been generated in this browser, by the same user, in the same publish mode. |

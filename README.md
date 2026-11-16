# Generate Site

## Deploy to Render

The Render Blueprint in [`render.yaml`](./render.yaml) deploys the generator app
itself (not the site it generates) as two services:

- **generate-site-api**: the Flask backend in `backend/`, run with gunicorn.
- **generate-site-ui**: the React frontend in `frontend/`, published as a static
  site. It calls the API directly through `VITE_API_URL` and rewrites other
  routes to `index.html`.

To deploy, push this repository to GitHub, then in Render choose **New > Blueprint**,
select the repository, and apply `render.yaml`. When prompted, set the secrets
`ANTHROPIC_API_KEY` and `GITHUB_TOKEN`.

`GITHUB_TOKEN` must be able to write to the target repo's contents, workflows and
Pages settings (fine-grained: Contents, Workflows and Pages set to Read and write;
classic: the `repo` and `workflow` scopes).

## Sign-in

Generating a site requires signing in, with Google or with an email address alone.
The email option sends no message and checks nothing: it identifies the user, it does
not prove they own the address.

The API needs two environment variables:

- `SECRET_KEY`: signs the sessions. Render generates it from `render.yaml`; locally,
  put any long random string in `backend/.env`. A session is a JWT issued with Authlib
  and ends 60 minutes after sign-in (`SESSION_MINUTES` in `backend/services/auth.py`);
  the user then signs in again.
- `GOOGLE_CLIENT_ID`: enables the Google button. Create it in the Google Cloud Console
  under **APIs & Services > Credentials > Create credentials > OAuth client ID**, type
  **Web application**, and add the UI's address to **Authorized JavaScript origins**
  (`https://generate-site-ui.onrender.com`, plus `http://localhost:5173` for local
  work). Without it only the email option is offered.

## User data and email

Each signed-in user has a row in the database holding their GitHub repo, their GitHub
token (encrypted with `SECRET_KEY`, never sent back to the browser) and one record per
generation with its Claude token counts and cost. Changing `SECRET_KEY` makes the saved
tokens unreadable; users then have to enter them again.

- The database is a SQLite file, `backend/data.db` by default. Set `SQLITE_PATH` to put
  it elsewhere. On Render the service's own filesystem is wiped on every deploy and
  restart, so attach a persistent disk (paid plans) and point `SQLITE_PATH` at a file on
  it, for example `/var/data/data.db`; otherwise users, tokens and costs are lost.
- A summary is emailed to the user after each generation, over SMTP. Without `SMTP_HOST`
  no email is sent and the result says so.
  - `SMTP_HOST`, `SMTP_PORT`: the mail server, for example `smtp.gmail.com` and `587`.
    Port 587 (the default) uses STARTTLS, port 465 implicit TLS.
  - `SMTP_USER`, `SMTP_PASSWORD`: the login. For Gmail the password is an app password
    (https://myaccount.google.com/apppasswords), not the account password.
  - `MAIL_FROM`: sender, for example `Generate Site <you@gmail.com>`; defaults to `SMTP_USER`.
  - Render's free web services block outbound SMTP (ports 25, 465 and 587), so there the
    email fails with a timeout; it needs a paid instance.

## Administrator

Addresses listed in `ADMIN_EMAILS` (comma-separated) get an extra **Users** tab with all
registered users and their generations. It only appears when the administrator signs in
with Google, because the email-only sign-in does not prove who is typing the address.

Every other user may run 2 generations (`GENERATION_LIMIT` in `backend/services/auth.py`);
administrators have no limit. Only generations that reached Claude are counted. In the Users
tab an administrator can reset a user's count, which lets them run 2 more.

## Where a generated site is published

The form has a **Publish to** choice:

- **GitHub Pages** (default): the source is committed to the repo and a GitHub Actions
  workflow builds it and deploys it to Pages, as described below.
- **Render static site**: the source is committed to the same repo (Render cannot take
  source any other way; a static site is always built from a Git repository), then the
  Render API creates a static site that builds that folder (`npm install && npm run build`,
  publishing `dist`). When the build finishes the page shows a preview of the site. Each new site is a new Render service; refining a site redeploys its
  service. Needs `RENDER_API_KEY` (Render dashboard > Account Settings > API Keys), and
  optionally `RENDER_OWNER_ID` to pick the workspace. Render must be able to read the repo:
  it is public, or the Render account's GitHub connection has access to it.

## How a generated site is published

Every generated site is a Vite + React + TypeScript project. It is committed to the
target repo under `sites/<timestamp>-<slug>/`, together with `sites/LATEST` (which
names that folder) and `.github/workflows/deploy-generated-site.yml`. The change to
`sites/LATEST` starts that workflow, which runs `npm install` and `npm run build` in
the folder and deploys `dist/` to GitHub Pages.

If Render gives the API a URL other than `https://generate-site-api.onrender.com`
(the name was taken), update `VITE_API_URL` in `render.yaml`.

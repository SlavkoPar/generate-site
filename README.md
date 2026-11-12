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
  put any long random string in `backend/.env`.
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
- `RESEND_API_KEY`: API key from https://resend.com, used to email the user a summary
  after each generation. Without it no email is sent and the result says so.
- `MAIL_FROM`: sender address on a domain verified in Resend, for example
  `Generate Site <noreply@example.com>`. Without it Resend's test sender is used, which
  only delivers to the Resend account owner's own address.

## How a generated site is published

Every generated site is a Vite + React + TypeScript project. It is committed to the
target repo under `sites/<timestamp>-<slug>/`, together with `sites/LATEST` (which
names that folder) and `.github/workflows/deploy-generated-site.yml`. The change to
`sites/LATEST` starts that workflow, which runs `npm install` and `npm run build` in
the folder and deploys `dist/` to GitHub Pages.

If Render gives the API a URL other than `https://generate-site-api.onrender.com`
(the name was taken), update `VITE_API_URL` in `render.yaml`.

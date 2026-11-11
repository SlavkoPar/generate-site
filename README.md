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

## How a generated site is published

Every generated site is a Vite + React + TypeScript project. It is committed to the
target repo under `sites/<timestamp>-<slug>/`, together with `sites/LATEST` (which
names that folder) and `.github/workflows/deploy-generated-site.yml`. The change to
`sites/LATEST` starts that workflow, which runs `npm install` and `npm run build` in
the folder and deploys `dist/` to GitHub Pages.

If Render gives the API a URL other than `https://generate-site-api.onrender.com`
(the name was taken), update `VITE_API_URL` in `render.yaml`.

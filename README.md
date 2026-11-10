# Generate Site

## Deploy to Render

The Render Blueprint in [`render.yaml`](./render.yaml) deploys the generator app
itself (not the site it generates) as two services:

- **generate-site-api**: the Flask backend in `backend/`, run with gunicorn.
- **generate-site-ui**: the React frontend in `frontend/`, published as a static
  site. It rewrites `/api/*` to the API service and other routes to `index.html`.

To deploy, push this repository to GitHub, then in Render choose **New > Blueprint**,
select the repository, and apply `render.yaml`. When prompted, set the secrets
`ANTHROPIC_API_KEY` and `GITHUB_TOKEN`.

If Render gives the API a URL other than `https://generate-site-api.onrender.com`
(the name was taken), update the `/api/*` rewrite destination in `render.yaml`.

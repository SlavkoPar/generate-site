# Generate Site

## Deploy to Render

The Render Blueprint in [`render.yaml`](./render.yaml) deploys the TypeScript site
from `site/` as a static site. It runs the locked dependency install and production
build, publishes `site/dist`, and rewrites client-side routes to `index.html`.
The Render build overrides Vite's base path to `/`; the default build configuration
continues to use `/generate-site/` for GitHub Pages.

To deploy, push this repository to GitHub, then in Render choose **New > Blueprint**,
select the repository, and apply the `render.yaml` Blueprint.

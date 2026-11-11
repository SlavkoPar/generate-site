import base64
import os
import re
from datetime import datetime, timezone

import requests

REPO = os.environ.get("GITHUB_REPO", "SlavkoPar/AIGeneratedSite")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")
API = f"https://api.github.com/repos/{REPO}/contents"


class GitHubStoreError(Exception):
    pass


def is_configured(token: str | None = None) -> bool:
    return bool(token or os.environ.get("GITHUB_TOKEN"))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "untitled"


def _headers(token: str | None = None) -> dict:
    return {
        "Authorization": f"Bearer {token or os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }


def _existing_sha(path: str, api: str = API, token: str | None = None) -> str | None:
    """Return the blob sha if the file already exists (needed to overwrite it)."""
    resp = requests.get(f"{api}/{path}", headers=_headers(token), params={"ref": BRANCH}, timeout=20)
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise GitHubStoreError(f"GitHub returned {resp.status_code}: {resp.json().get('message', '')}")
    return resp.json()["sha"]


def _put_file(path: str, content: str, message: str, overwrite: bool = False, api: str = API,
              token: str | None = None) -> str:
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if overwrite:
        sha = _existing_sha(path, api, token)
        if sha:
            payload["sha"] = sha
    resp = requests.put(f"{api}/{path}", headers=_headers(token), json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        raise GitHubStoreError(f"GitHub returned {resp.status_code}: {resp.json().get('message', '')}")
    return resp.json()["content"]["html_url"]


def _render_blueprint(folder: str, name: str, header: str | None = None) -> str:
    header = header or f"""# Render Blueprint for this generation.
# Deploy: Render dashboard -> New -> Blueprint -> pick this repo, and set
# "Blueprint file path" to {folder}/render.yaml.
# The code must listen on 0.0.0.0:$PORT to pass Render's health check."""
    return f"""{header}
services:
  - type: web
    name: {name}-py
    runtime: python
    plan: free
    rootDir: {folder}
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
  - type: web
    name: {name}-js
    runtime: node
    plan: free
    rootDir: {folder}
    buildCommand: npm install
    startCommand: node main.js
"""


_PACKAGE_JSON = """{
  "name": "generated-app",
  "version": "1.0.0",
  "private": true,
  "main": "main.js",
  "scripts": { "start": "node main.js" }
}
"""


def store_generation(prompt: str, code: dict) -> str:
    """Commit the generated files to the repo under generations/<timestamp>-<slug>/.

    Returns the GitHub URL of the folder.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = f"generations/{stamp}-{_slug(prompt)}"
    message = f"Add generated code: {prompt[:60]}"

    _put_file(f"{folder}/PROMPT.md", f"# Prompt\n\n{prompt}\n", message)
    _put_file(f"{folder}/main.py", code["python"], message)
    _put_file(f"{folder}/main.js", code["javascript"], message)
    requirements = code.get("python_requirements", "").strip()
    _put_file(f"{folder}/requirements.txt", requirements + "\n", message)
    _put_file(f"{folder}/package.json", _PACKAGE_JSON, message)
    # Render service names: lowercase letters, digits, hyphens; keep unique per generation.
    name = f"{_slug(prompt)[:24].strip('-')}-{stamp.replace('-', '')}"
    _put_file(f"{folder}/render.yaml", _render_blueprint(folder, name), message)

    # Root blueprint always points at the newest generation. The fixed service names
    # make Render update the same two services instead of creating new ones.
    root_header = f"""# Render Blueprint (auto-updated on every generation) - deploys the latest one:
# {folder}
# Deploy: Render dashboard -> New -> Blueprint -> pick this repo (default path render.yaml).
# The code must listen on 0.0.0.0:$PORT to pass Render's health check."""
    _put_file(
        "render.yaml",
        _render_blueprint(folder, "latest", root_header),
        f"Point root render.yaml at {folder}",
        overwrite=True,
    )
    return f"https://github.com/{REPO}/tree/{BRANCH}/{folder}"


_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


SITE_FOLDER_RE = re.compile(r"^sites/\d{8}-\d{6}-[a-z0-9-]{0,40}$")


WORKFLOW_PATH = ".github/workflows/deploy-generated-site.yml"
LATEST_PATH = "sites/LATEST"  # first line: folder of the site the workflow builds

# Builds the Vite project named in sites/LATEST and deploys its dist/ to GitHub Pages.
# Only a change to that pointer triggers it, so each generation builds exactly once.
_WORKFLOW = """name: Deploy generated site
on:
  push:
    branches: [__BRANCH__]
    paths: [sites/LATEST]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - id: site
        run: echo "folder=$(head -n 1 sites/LATEST)" >> "$GITHUB_OUTPUT"
      - name: Build
        working-directory: ${{ steps.site.outputs.folder }}
        run: |
          npm install
          npm run build
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ${{ steps.site.outputs.folder }}/dist
      - id: deployment
        uses: actions/deploy-pages@v4
""".replace("__BRANCH__", BRANCH)


def _gh(method: str, repo_full: str, path: str, token: str | None, **kwargs) -> requests.Response:
    return requests.request(
        method, f"https://api.github.com/repos/{repo_full}/{path}",
        headers=_headers(token), timeout=30, **kwargs,
    )


def _check(resp: requests.Response, what: str) -> dict:
    if resp.status_code not in (200, 201):
        raise GitHubStoreError(f"{what}: GitHub returned {resp.status_code}: {resp.json().get('message', '')}")
    return resp.json()


def _file_text(repo_full: str, path: str, token: str | None) -> str | None:
    resp = _gh("GET", repo_full, f"contents/{path}", token, params={"ref": BRANCH})
    if resp.status_code != 200:
        return None
    return base64.b64decode(resp.json()["content"]).decode("utf-8")


def _commit(repo_full: str, token: str | None, message: str, files: dict[str, str],
            replace_folder: str | None = None) -> None:
    """Add `files` (repo path -> content) to the branch in a single commit.

    With `replace_folder`, files already under that folder that are not in `files` are deleted.
    """
    ref = _gh("GET", repo_full, f"git/ref/heads/{BRANCH}", token)
    if ref.status_code in (404, 409):
        raise GitHubStoreError(
            f"Repository {repo_full} has no '{BRANCH}' branch (or the token cannot see it). "
            "Create the repo with a README first")
    parent = _check(ref, f"reading {BRANCH}")["object"]["sha"]
    base_tree = _check(_gh("GET", repo_full, f"git/commits/{parent}", token), "reading commit")["tree"]["sha"]

    entries = [{"path": p, "mode": "100644", "type": "blob", "content": c} for p, c in files.items()]
    if replace_folder:
        listing = _gh("GET", repo_full, f"git/trees/{base_tree}", token, params={"recursive": "1"})
        if listing.status_code == 200:  # best effort: leftovers are harmless compared to losing the update
            prefix = f"{replace_folder}/"
            entries += [
                {"path": item["path"], "mode": "100644", "type": "blob", "sha": None}
                for item in listing.json().get("tree", [])
                if item["type"] == "blob" and item["path"].startswith(prefix) and item["path"] not in files
            ]

    tree = _check(_gh("POST", repo_full, "git/trees", token,
                      json={"base_tree": base_tree, "tree": entries}), "creating tree")
    commit = _check(_gh("POST", repo_full, "git/commits", token,
                        json={"message": message, "tree": tree["sha"], "parents": [parent]}),
                    "creating commit")
    _check(_gh("PATCH", repo_full, f"git/refs/heads/{BRANCH}", token, json={"sha": commit["sha"]}),
           f"updating {BRANCH}")


def store_site(prompt: str, files: list[dict], repo: str | None = None,
               token: str | None = None, folder: str | None = None) -> dict:
    """Commit a Vite project under sites/<timestamp>-<slug>/ and trigger its build.

    `repo` ("owner/name") overrides the GITHUB_REPO default. Pass the `folder` returned by
    an earlier call to overwrite that site (a refinement) instead of creating a new one.
    The commit also updates sites/LATEST, which starts the workflow that builds the project
    and deploys it to GitHub Pages. Returns the folder, Pages and Actions URLs.
    """
    repo_full = repo or REPO
    if not _REPO_RE.match(repo_full):
        raise GitHubStoreError(f"Invalid repository '{repo_full}', expected owner/repo")
    if folder is not None and not SITE_FOLDER_RE.match(folder):
        raise GitHubStoreError(f"Invalid site folder '{folder}'")

    refine = folder is not None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if not refine:
        folder = f"sites/{stamp}-{_slug(prompt)}"
    message = f"{'Update' if refine else 'Add'} generated site: {prompt[:60]}"

    if refine:
        previous = (_file_text(repo_full, f"{folder}/PROMPT.md", token) or "").rstrip()
        prompt_log = (previous + "\n\n" if previous else "") + "# Refinement\n\n" + prompt + "\n"
    else:
        prompt_log = "# Prompt\n\n" + prompt + "\n"

    tree = {f"{folder}/{f['path']}": f["content"] for f in files}
    tree[f"{folder}/PROMPT.md"] = prompt_log
    # The timestamp makes the pointer change on a refinement too, so the workflow runs again.
    tree[LATEST_PATH] = f"{folder}\n{stamp}\n"
    # Writing a workflow needs an extra token permission, so only do it when it is not there yet.
    adds_workflow = _file_text(repo_full, WORKFLOW_PATH, token) != _WORKFLOW
    if adds_workflow:
        tree[WORKFLOW_PATH] = _WORKFLOW

    # Pages must be on before the push, or the workflow's deploy step has nothing to deploy to.
    pages_warning = _ensure_pages_source(repo_full, token)
    try:
        _commit(repo_full, token, message, tree, replace_folder=folder if refine else None)
    except GitHubStoreError as e:
        if adds_workflow:
            raise GitHubStoreError(
                f"{e}. This push adds {WORKFLOW_PATH}, so the token also needs the Workflows "
                "permission (fine-grained) or the workflow scope (classic)") from e
        raise

    owner, name = repo_full.split("/", 1)
    result = {
        "github_url": f"https://github.com/{repo_full}/tree/{BRANCH}/{folder}",
        "pages_url": f"https://{owner.lower()}.github.io/{name}/",
        "actions_url": f"https://github.com/{repo_full}/actions/workflows/{WORKFLOW_PATH.rsplit('/', 1)[1]}",
        "folder": folder,
    }
    if pages_warning:
        result["pages_error"] = pages_warning
    return result


def _ensure_pages_source(repo_full: str, token: str | None) -> str | None:
    """Make GitHub Pages deploy from GitHub Actions. Returns a warning if it could not."""
    source = {"build_type": "workflow"}
    current = _gh("GET", repo_full, "pages", token)
    if current.status_code == 200:
        if current.json().get("build_type") == "workflow":
            return None
        resp = _gh("PUT", repo_full, "pages", token, json=source)  # switch an existing site
        action = "switch Pages to deploy from GitHub Actions"
    else:
        resp = _gh("POST", repo_full, "pages", token, json=source)  # Pages not enabled yet
        action = "enable Pages"
    if resp.status_code in (200, 201, 204):
        return None
    return (f"Could not {action} (GitHub returned {resp.status_code}), so the deploy will fail "
            "until you set it in the repo: Settings > Pages > Source: GitHub Actions, then re-run "
            "the workflow from the Actions tab.")

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


def _delete_stale(folder: str, keep: set[str], message: str, api: str, repo_full: str,
                  token: str | None) -> None:
    """Remove files under `folder` that are not in `keep` (paths relative to the folder)."""
    resp = requests.get(
        f"https://api.github.com/repos/{repo_full}/git/trees/{BRANCH}",
        headers=_headers(token), params={"recursive": "1"}, timeout=20,
    )
    if resp.status_code != 200:
        return  # best effort: leftover files are harmless compared to losing the update
    prefix = f"{folder}/"
    for item in resp.json().get("tree", []):
        path = item["path"]
        if item["type"] == "blob" and path.startswith(prefix) and path[len(prefix):] not in keep:
            requests.delete(
                f"{api}/{path}", headers=_headers(token), timeout=20,
                json={"message": message, "sha": item["sha"], "branch": BRANCH},
            )


def store_site(prompt: str, files: list[dict], repo: str | None = None,
               token: str | None = None, folder: str | None = None) -> dict:
    """Commit a static site under sites/<timestamp>-<slug>/.

    `repo` ("owner/name") overrides the GITHUB_REPO default. Pass the `folder` returned by
    an earlier call to overwrite that site (a refinement) instead of creating a new one.
    Returns the GitHub folder URL and the GitHub Pages URL (live once Pages is enabled).
    """
    repo_full = repo or REPO
    if not _REPO_RE.match(repo_full):
        raise GitHubStoreError(f"Invalid repository '{repo_full}', expected owner/repo")
    if folder is not None and not SITE_FOLDER_RE.match(folder):
        raise GitHubStoreError(f"Invalid site folder '{folder}'")
    api = f"https://api.github.com/repos/{repo_full}/contents"

    refine = folder is not None
    if not refine:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        folder = f"sites/{stamp}-{_slug(prompt)}"
    message = f"{'Update' if refine else 'Add'} generated site: {prompt[:60]}"

    if refine:
        _put_file(f"{folder}/PROMPT.md", _prompt_log(prompt, api, folder, token), message,
                  overwrite=True, api=api, token=token)
    else:
        _put_file(f"{folder}/PROMPT.md", "# Prompt\n\n" + prompt + "\n", message, api=api, token=token)
    for f in files:
        _put_file(f"{folder}/{f['path']}", f["content"], message, overwrite=refine, api=api, token=token)
    if refine:
        _delete_stale(folder, {"PROMPT.md", *(f["path"] for f in files)}, message, api, repo_full, token)

    owner, name = repo_full.split("/", 1)
    result = {
        "github_url": f"https://github.com/{repo_full}/tree/{BRANCH}/{folder}",
        "pages_url": f"https://{owner.lower()}.github.io/{name}/{folder}/",
        "folder": folder,
    }
    try:
        _publish_gh_pages(files, message, repo_full, token)
        # The gh-pages branch always holds the latest site at the Pages root.
        result["pages_url"] = f"https://{owner.lower()}.github.io/{name}/"
    except (GitHubStoreError, requests.RequestException) as e:
        result["pages_error"] = f"Saved to {folder}, but gh-pages was not updated: {e}"
    return result


PAGES_BRANCH = "gh-pages"


def _gh(method: str, repo_full: str, path: str, token: str | None, **kwargs) -> requests.Response:
    return requests.request(
        method, f"https://api.github.com/repos/{repo_full}/{path}",
        headers=_headers(token), timeout=30, **kwargs,
    )


def _check(resp: requests.Response, what: str) -> dict:
    if resp.status_code not in (200, 201):
        raise GitHubStoreError(f"{what}: GitHub returned {resp.status_code}: {resp.json().get('message', '')}")
    return resp.json()


def _publish_gh_pages(files: list[dict], message: str, repo_full: str, token: str | None) -> None:
    """Replace the whole gh-pages branch with `files` in one commit (creating the branch if needed)."""
    entries = [{"path": f["path"], "mode": "100644", "type": "blob", "content": f["content"]} for f in files]
    # .nojekyll makes Pages serve the files as-is instead of running Jekyll over them.
    entries.append({"path": ".nojekyll", "mode": "100644", "type": "blob", "content": chr(10)})

    ref = _gh("GET", repo_full, f"git/ref/heads/{PAGES_BRANCH}", token)
    if ref.status_code not in (200, 404):
        _check(ref, "reading gh-pages")
    parent = ref.json()["object"]["sha"] if ref.status_code == 200 else None

    # No base_tree: the new tree is exactly the latest site, so files from older sites vanish.
    tree = _check(_gh("POST", repo_full, "git/trees", token, json={"tree": entries}), "creating tree")
    commit = _check(
        _gh("POST", repo_full, "git/commits", token, json={
            "message": message, "tree": tree["sha"], "parents": [parent] if parent else [],
        }),
        "creating commit",
    )
    if parent:
        _check(_gh("PATCH", repo_full, f"git/refs/heads/{PAGES_BRANCH}", token,
                   json={"sha": commit["sha"]}), "updating gh-pages")
    else:
        _check(_gh("POST", repo_full, "git/refs", token,
                   json={"ref": f"refs/heads/{PAGES_BRANCH}", "sha": commit["sha"]}), "creating gh-pages")
        # First time only: turn Pages on for the new branch. Best effort; never changes an existing setup.
        _gh("POST", repo_full, "pages", token,
            json={"source": {"branch": PAGES_BRANCH, "path": "/"}})


def _prompt_log(prompt: str, api: str, folder: str, token: str | None) -> str:
    """Existing PROMPT.md plus this refinement, so the folder keeps its full prompt history."""
    resp = requests.get(f"{api}/{folder}/PROMPT.md", headers=_headers(token),
                        params={"ref": BRANCH}, timeout=20)
    previous = ""
    if resp.status_code == 200:
        previous = base64.b64decode(resp.json()["content"]).decode("utf-8").rstrip() + "\n\n"
    return previous + "# Refinement\n\n" + prompt + "\n"

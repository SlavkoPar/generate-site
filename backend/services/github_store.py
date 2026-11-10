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


def store_site(prompt: str, files: list[dict], repo: str | None = None,
               token: str | None = None) -> dict:
    """Commit a static site under sites/<timestamp>-<slug>/.

    `repo` ("owner/name") overrides the GITHUB_REPO default.
    Returns the GitHub folder URL and the GitHub Pages URL (live once Pages is enabled).
    """
    repo_full = repo or REPO
    if not _REPO_RE.match(repo_full):
        raise GitHubStoreError(f"Invalid repository '{repo_full}', expected owner/repo")
    api = f"https://api.github.com/repos/{repo_full}/contents"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = f"sites/{stamp}-{_slug(prompt)}"
    message = f"Add generated site: {prompt[:60]}"

    _put_file(f"{folder}/PROMPT.md", f"# Prompt\n\n{prompt}\n", message, api=api, token=token)
    for f in files:
        _put_file(f"{folder}/{f['path']}", f["content"], message, api=api, token=token)

    owner, name = repo_full.split("/", 1)
    return {
        "github_url": f"https://github.com/{repo_full}/tree/{BRANCH}/{folder}",
        "pages_url": f"https://{owner.lower()}.github.io/{name}/{folder}/",
    }

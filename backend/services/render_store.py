"""Publishes a generated site as a Render static site, through the Render API.

Render has no API to upload source: a static site is always built from a Git repository. So
the source is committed to GitHub first (github_store.store_site) and the static site created
here builds the site's folder of that repo. Render must be able to read the repo: it is public,
or the Render account's GitHub connection has access to it.

Settings: RENDER_API_KEY, and optionally RENDER_OWNER_ID (the workspace; the key's first
workspace is used when it is not set).
"""
import os
import re

import requests

API = "https://api.render.com/v1"
BUILD_COMMAND = "npm install && npm run build"
PUBLISH_PATH = "dist"


class RenderStoreError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("RENDER_API_KEY", "").strip())


def _call(method: str, path: str, **kwargs) -> requests.Response:
    headers = {"Authorization": f"Bearer {os.environ['RENDER_API_KEY'].strip()}",
               "Accept": "application/json"}
    return requests.request(method, f"{API}{path}", headers=headers, timeout=30, **kwargs)


def _check(resp: requests.Response, what: str, ok=(200, 201)):
    if resp.status_code not in ok:
        try:
            detail = resp.json().get("message", "")
        except (ValueError, AttributeError):
            detail = ""
        raise RenderStoreError(f"{what}: Render returned {resp.status_code}: {detail}".rstrip(": "))
    return resp.json() if resp.content else {}


def _owner_id() -> str:
    owner = os.environ.get("RENDER_OWNER_ID", "").strip()
    if owner:
        return owner
    owners = _check(_call("GET", "/owners", params={"limit": 1}), "reading the workspace")
    if not owners:
        raise RenderStoreError("The Render API key has no workspace")
    return owners[0]["owner"]["id"]


def service_name(folder: str) -> str:
    """sites/20261116-101500-coffee-shop -> coffee-shop-20261116101500 (unique per site)."""
    base = folder.rsplit("/", 1)[-1]  # YYYYMMDD-HHMMSS-slug
    stamp, slug = base[:15].replace("-", ""), base[16:][:30].strip("-")
    return f"{slug or 'site'}-{stamp}"


def _result(service: dict) -> dict:
    return {
        "render_service_id": service.get("id", ""),
        "render_url": service.get("serviceDetails", {}).get("url", ""),
        "render_dashboard_url": service.get("dashboardUrl", ""),
    }


_SERVICE_ID_RE = re.compile(r"^srv-[a-z0-9]+$")
_FAILED = {"build_failed": "the build failed", "update_failed": "the deploy failed",
           "pre_deploy_failed": "the deploy failed", "canceled": "the deploy was canceled",
           "deactivated": "the deploy was replaced by a newer one"}


def deploy_state(service_id: str) -> dict:
    """Where the service's latest deploy stands: {"state": "building" | "live" | "failed"},
    with a "detail" when it failed."""
    if not _SERVICE_ID_RE.match(service_id):
        raise RenderStoreError("Invalid Render service id")
    deploys = _check(_call("GET", f"/services/{service_id}/deploys", params={"limit": 1}),
                     "reading the deploy")
    status = deploys[0]["deploy"]["status"] if deploys else "created"
    if status == "live":
        return {"state": "live"}
    if status in _FAILED:
        return {"state": "failed", "detail": _FAILED[status]}
    return {"state": "building"}


def publish(repo_full: str, branch: str, folder: str) -> dict:
    """Create the static site for `folder` of the repo, or redeploy it if it already exists
    (a refinement). Returns its public URL and its Render dashboard URL."""
    name = service_name(folder)
    found = _check(_call("GET", "/services", params={"name": name, "type": "static_site", "limit": 1}),
                   "looking for the static site")
    if found:
        service = found[0]["service"]
        _check(_call("POST", f"/services/{service['id']}/deploys", json={}),
               "starting the deploy", ok=(200, 201, 202))
        return _result(service)

    created = _check(_call("POST", "/services", json={
        "type": "static_site",
        "name": name,
        "ownerId": _owner_id(),
        "repo": f"https://github.com/{repo_full}",
        "branch": branch,
        "rootDir": folder,
        # Deploys are started here, once per generation, rather than by every push to the repo.
        "autoDeployTrigger": "off",
        "serviceDetails": {"buildCommand": BUILD_COMMAND, "publishPath": PUBLISH_PATH},
    }), "creating the static site")
    return _result(created["service"])

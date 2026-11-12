import re

from flask import g, jsonify, request

from services import db
from services.auth import require_login

from . import api_bp

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@api_bp.route("/profile", methods=["GET"])
@require_login
def get_profile():
    return jsonify(db.profile(g.user["email"]))


@api_bp.route("/profile", methods=["PUT"])
@require_login
def update_profile():
    """Save the user's GitHub repo and/or token. A field that is left out is not changed;
    an empty string clears it. The token is stored encrypted and never returned."""
    body = request.get_json(silent=True) or {}
    repo, token = body.get("github_repo"), body.get("github_token")
    if repo is not None:
        if not isinstance(repo, str) or (repo.strip() and not _REPO_RE.match(repo.strip())):
            return jsonify(error="'github_repo' must look like owner/repo"), 400
        repo = repo.strip()
    if token is not None:
        if not isinstance(token, str) or len(token) > 500:
            return jsonify(error="'github_token' is invalid"), 400
        token = token.strip()
    db.save_github(g.user["email"], repo, token)
    return jsonify(db.profile(g.user["email"]))

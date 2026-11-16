import re

from flask import g, jsonify, request

from services import auth, db
from services.auth import require_login

from . import api_bp

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@api_bp.route("/profile", methods=["GET"])
@require_login
def get_profile():
    return jsonify(_profile())


def _profile() -> dict:
    admin = auth.is_admin(g.user)
    data = db.profile(g.user["email"])
    limit = None if admin else auth.GENERATION_LIMIT
    left = None if admin else max(0, limit - data["generations_used"])
    return {**data, "is_admin": admin, "generation_limit": limit, "generations_left": left}


@api_bp.route("/admin/users", methods=["GET"])
@require_login
def admin_users():
    if not auth.is_admin(g.user):
        return jsonify(error="Only the administrator can see this"), 403
    return _users()


def _users():
    return jsonify(users=db.all_users(), generation_limit=auth.GENERATION_LIMIT)


@api_bp.route("/admin/users/reset-generations", methods=["POST"])
@require_login
def admin_reset_generations():
    """Let a user run their full number of generations again."""
    if not auth.is_admin(g.user):
        return jsonify(error="Only the administrator can do this"), 403
    email = (request.get_json(silent=True) or {}).get("email")
    if not isinstance(email, str) or not db.reset_generations(email):
        return jsonify(error="No such user"), 404
    return _users()


@api_bp.route("/profile", methods=["PUT"])
@require_login
def update_profile():
    """Save the user's GitHub repo, token and/or publish target. A field that is left out is not changed;
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
    target = body.get("publish_target")
    if target is not None and target not in db.PUBLISH_TARGETS:
        return jsonify(error="'publish_target' must be 'render' or 'github'"), 400
    db.save_github(g.user["email"], repo, token, target)
    return jsonify(_profile())

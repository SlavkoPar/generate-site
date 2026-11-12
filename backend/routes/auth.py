from flask import jsonify, request

from services import auth

from . import api_bp


def _login(fn, field: str):
    value = (request.get_json(silent=True) or {}).get(field)
    if not isinstance(value, str) or not value.strip():
        return jsonify(error=f"'{field}' is required"), 400
    try:
        return jsonify(fn(value))
    except auth.AuthError as e:
        return jsonify(error=str(e)), e.status


@api_bp.route("/auth/config", methods=["GET"])
def auth_config():
    """What the sign-in UI needs; the client ID is public by design."""
    return jsonify(google_client_id=auth.google_client_id())


@api_bp.route("/auth/email", methods=["POST"])
def auth_email():
    return _login(auth.login_with_email, "email")


@api_bp.route("/auth/google", methods=["POST"])
def auth_google():
    return _login(auth.login_with_google, "credential")


@api_bp.route("/auth/me", methods=["GET"])
def auth_me():
    try:
        user = auth.current_user()
    except auth.AuthError as e:
        return jsonify(error=str(e)), e.status
    if not user:
        return jsonify(error="Not signed in"), 401
    return jsonify(user=user)

import os
import re
from functools import wraps

import requests
from flask import g, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import db

SESSION_MAX_AGE = 30 * 24 * 3600  # seconds
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def _serializer() -> URLSafeTimedSerializer:
    # Read on each call rather than at import: every gunicorn worker must sign with the same
    # key, so there is no random fallback (a token from one worker would fail on the other).
    secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        raise AuthError("Server has no SECRET_KEY configured", 500)
    return URLSafeTimedSerializer(secret, salt="generate-site-session")


def issue_session(email: str, provider: str, name: str = "") -> dict:
    user = {"email": email, "provider": provider, "name": name}
    db.ensure_user(email, name, provider, login=True)
    return {"token": _serializer().dumps(user), "user": user}


def read_session(token: str) -> dict | None:
    try:
        user = _serializer().loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:  # also covers an expired token
        return None
    return user if isinstance(user, dict) and user.get("email") else None


def login_with_email(email: str) -> dict:
    """Sign in with an address alone. Nothing proves the caller owns it: this identifies
    users, it does not authenticate them."""
    email = email.strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address")
    return issue_session(email, "email")


def login_with_google(credential: str) -> dict:
    """Verify the ID token from Google Identity Services and sign that account in."""
    client_id = google_client_id()
    if not client_id:
        raise AuthError("Google sign-in is not configured on the server (GOOGLE_CLIENT_ID)", 500)
    try:
        resp = requests.get(_GOOGLE_TOKENINFO, params={"id_token": credential}, timeout=15)
    except requests.RequestException as e:
        raise AuthError("Could not reach Google to verify the sign-in", 502) from e
    if resp.status_code != 200:
        raise AuthError("Google did not accept this sign-in", 401)
    info = resp.json()
    # `aud` ties the token to this app; without the check a token issued to any other site would pass.
    if info.get("aud") != client_id or str(info.get("email_verified")).lower() != "true":
        raise AuthError("Google did not accept this sign-in", 401)
    return issue_session(info["email"].lower(), "google", info.get("name", ""))


def is_admin(user: dict | None) -> bool:
    """Admins are the addresses in ADMIN_EMAILS, and only when signed in with Google: an
    email-only sign-in proves nothing, so anyone could type an admin's address."""
    admins = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
    return bool(user) and user.get("provider") == "google" and user.get("email") in admins


def current_user() -> dict | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return read_session(header[len("Bearer "):].strip())


def require_login(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            user = current_user()
        except AuthError as e:
            return jsonify(error=str(e)), e.status
        if not user:
            return jsonify(error="Sign in first"), 401
        # Sessions issued before the database existed have no row yet.
        db.ensure_user(user["email"], user.get("name", ""), user.get("provider", ""))
        g.user = user
        return view(*args, **kwargs)
    return wrapper

from flask import Blueprint

api_bp = Blueprint("api", __name__)

from . import auth, generate, hello, profile  # noqa: E402,F401  (registers routes on api_bp)

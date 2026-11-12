import anthropic
import requests
from flask import current_app, g, jsonify, request

from services import db, github_store, mailer
from services.auth import require_login
from services.claude import GenerationRefused, MissingCredentials, get_usage, reset_usage
from services.code_generator import generate_code
from services.site_generator import InvalidSite, extend_history, generate_site

from . import api_bp

MAX_PROMPT_CHARS = 4000
MAX_HISTORY_CHARS = 1_500_000


def _read_history(body: dict):
    """Validate the conversation the client sent back; returns (messages, error response)."""
    raw = body.get("history")
    if raw in (None, []):
        return [], None
    ok = (
        isinstance(raw, list)
        and len(raw) % 2 == 0
        and all(
            isinstance(m, dict)
            and m.get("role") == ("user" if i % 2 == 0 else "assistant")
            and isinstance(m.get("content"), str)
            for i, m in enumerate(raw)
        )
        and sum(len(m["content"]) for m in raw) <= MAX_HISTORY_CHARS
    )
    if not ok:
        return None, (jsonify(error="'history' is invalid or too large"), 400)
    return [{"role": m["role"], "content": m["content"]} for m in raw], None


def _read_prompt():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return None, (jsonify(error="'prompt' is required"), 400)
    if len(prompt) > MAX_PROMPT_CHARS:
        return None, (jsonify(error=f"'prompt' must be at most {MAX_PROMPT_CHARS} characters"), 400)
    return prompt, None


def _store(result: dict, store, token: str | None = None):
    """Run a GitHub store step; never lose the generated output if it fails."""
    if not github_store.is_configured(token):
        result["github_error"] = (
            "No GitHub token: set GITHUB_TOKEN on the server (Render: generate-site-api > "
            "Environment), or enter a token for a different repo"
        )
        return
    try:
        extra = store()
        result.update(extra if isinstance(extra, dict) else {"github_url": extra})
    except (github_store.GitHubStoreError, requests.RequestException) as e:
        result["github_error"] = str(e)


def _with_usage(result: dict) -> dict:
    usage = get_usage()
    if usage:
        result["usage"] = usage
    return result


def _handle(fn, on_done=None):
    """Run a generation and turn its outcome into a JSON response.

    `on_done(result, usage, error)` runs afterwards whether it worked or not (the Claude call
    may have cost money either way) and may add keys to `result`.
    """
    reset_usage()
    status = 200
    try:
        result = fn()
    except GenerationRefused as e:
        result, status = {"error": str(e)}, 422
    except MissingCredentials as e:
        result, status = {"error": str(e)}, 500
    except anthropic.RateLimitError:
        result, status = {"error": "Rate limited, try again shortly"}, 429
    except anthropic.AuthenticationError:
        result, status = {"error": "Server is missing a valid ANTHROPIC_API_KEY"}, 500
    except anthropic.APIConnectionError:
        result, status = {"error": "Could not reach the Claude API"}, 502
    except anthropic.APIStatusError as e:
        result, status = {"error": f"Claude API error ({e.status_code})"}, 502
    except (InvalidSite, RuntimeError) as e:
        result, status = {"error": str(e)}, 502
    _with_usage(result)
    if on_done:
        try:
            on_done(result, get_usage(), result.get("error", "") if status != 200 else "")
        except Exception:  # bookkeeping must never cost the user their generated site
            current_app.logger.exception("recording the generation failed")
    return jsonify(result), status


@api_bp.route("/generate", methods=["POST"])
@require_login
def generate():
    prompt, err = _read_prompt()
    if err:
        return err

    def run():
        code = generate_code(prompt)
        result = dict(code)
        _store(result, lambda: github_store.store_generation(prompt, code))
        return result

    return _handle(run)


@api_bp.route("/generate-site", methods=["POST"])
@require_login
def generate_site_route():
    prompt, err = _read_prompt()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    history, err = _read_history(body)
    if err:
        return err

    email = g.user["email"]
    stored_repo, stored_token = db.github_settings(email)
    repo = (body.get("repo") or "").strip() or stored_repo or None
    token = (body.get("token") or "").strip() or None
    # The user's saved token is for their own repo; the default repo uses the server's token.
    if not token and repo and repo != github_store.REPO:
        token = stored_token or None
    folder = (body.get("folder") or "").strip() or None

    def run():
        files = generate_site(prompt, history)
        result = {
            "files": [f["path"] for f in files],
            "history": extend_history(history, prompt, files),
        }
        _store(result, lambda: github_store.store_site(prompt, files, repo, token, folder), token)
        return result

    def done(result, usage, error):
        db.record_generation(email, prompt, repo or github_store.REPO, result, usage, error)
        problem = mailer.send_generation_email(email, prompt, result, usage, error)
        if problem:
            result["email_error"] = problem
        else:
            result["email_sent_to"] = email

    return _handle(run, done)

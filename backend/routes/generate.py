import anthropic
import requests
from flask import jsonify, request

from services import github_store
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


def _handle(fn):
    reset_usage()
    try:
        return jsonify(_with_usage(fn()))
    except GenerationRefused as e:
        return jsonify(error=str(e)), 422
    except MissingCredentials as e:
        return jsonify(error=str(e)), 500
    except anthropic.RateLimitError:
        return jsonify(error="Rate limited, try again shortly"), 429
    except anthropic.AuthenticationError:
        return jsonify(error="Server is missing a valid ANTHROPIC_API_KEY"), 500
    except anthropic.APIConnectionError:
        return jsonify(error="Could not reach the Claude API"), 502
    except anthropic.APIStatusError as e:
        return jsonify(error=f"Claude API error ({e.status_code})"), 502
    except (InvalidSite, RuntimeError) as e:
        return jsonify(error=str(e)), 502


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

    def run():
        files = generate_site(prompt, history)
        result = {
            "files": [f["path"] for f in files],
            "history": extend_history(history, prompt, files),
        }
        repo = (body.get("repo") or "").strip() or None
        token = (body.get("token") or "").strip() or None
        folder = (body.get("folder") or "").strip() or None
        _store(result, lambda: github_store.store_site(prompt, files, repo, token, folder), token)
        return result

    return _handle(run)

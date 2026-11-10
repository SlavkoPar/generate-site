import anthropic
import requests
from flask import jsonify, request

from services import github_store
from services.claude import GenerationRefused, MissingCredentials
from services.code_generator import generate_code
from services.site_generator import InvalidSite, generate_site

from . import api_bp

MAX_PROMPT_CHARS = 4000


def _read_prompt():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return None, (jsonify(error="'prompt' is required"), 400)
    if len(prompt) > MAX_PROMPT_CHARS:
        return None, (jsonify(error=f"'prompt' must be at most {MAX_PROMPT_CHARS} characters"), 400)
    return prompt, None


def _store(result: dict, store):
    """Run a GitHub store step; never lose the generated output if it fails."""
    if not github_store.is_configured():
        return
    try:
        extra = store()
        result.update(extra if isinstance(extra, dict) else {"github_url": extra})
    except (github_store.GitHubStoreError, requests.RequestException) as e:
        result["github_error"] = str(e)


def _handle(fn):
    try:
        return jsonify(fn())
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
def generate_site_route():
    prompt, err = _read_prompt()
    if err:
        return err

    def run():
        files = generate_site(prompt)
        index = next(f["content"] for f in files if f["path"] == "index.html")
        result = {"files": [f["path"] for f in files], "preview": index}
        _store(result, lambda: github_store.store_site(prompt, files))
        return result

    return _handle(run)

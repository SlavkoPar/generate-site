import anthropic
import requests
from flask import jsonify, request

from services import github_store
from services.code_generator import GenerationRefused, MissingCredentials, generate_code

from . import api_bp

MAX_PROMPT_CHARS = 4000


@api_bp.route("/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return jsonify(error="'prompt' is required"), 400
    if len(prompt) > MAX_PROMPT_CHARS:
        return jsonify(error=f"'prompt' must be at most {MAX_PROMPT_CHARS} characters"), 400

    try:
        code = generate_code(prompt)
        result = dict(code)
        if github_store.is_configured():
            try:
                result["github_url"] = github_store.store_generation(prompt, code)
            except (github_store.GitHubStoreError, requests.RequestException) as e:
                # Don't lose the generated code if storing fails.
                result["github_error"] = str(e)
        return jsonify(result)
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
    except RuntimeError as e:
        return jsonify(error=str(e)), 502

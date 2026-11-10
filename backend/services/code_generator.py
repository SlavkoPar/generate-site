import json

import anthropic

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = (
    "You are a code generator. Given a task description, write a complete, "
    "idiomatic, runnable solution twice: once in Python 3 and once in modern "
    "JavaScript (Node.js). Return code only, with no markdown fences. "
    "Brief comments inside the code are fine. The code may be deployed to Render "
    "as a web service, so if the task is a service or has a UI, implement it as an "
    "HTTP server listening on the PORT environment variable (default 8000) on 0.0.0.0. "
    "In JavaScript use CommonJS and Node.js built-ins only (no npm packages). "
    "In Python list any third-party packages in python_requirements, one per line "
    "(empty string if only the standard library is used)."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "python": {"type": "string", "description": "Python 3 source code"},
        "javascript": {"type": "string", "description": "JavaScript source code"},
        "python_requirements": {
            "type": "string",
            "description": "requirements.txt contents; empty string if none",
        },
    },
    "required": ["python", "javascript", "python_requirements"],
    "additionalProperties": False,
}

# Reads ANTHROPIC_API_KEY (or an `ant auth login` profile) from the environment.
_client = anthropic.Anthropic()


class MissingCredentials(Exception):
    """No Anthropic API credentials are configured on the server."""


class GenerationRefused(Exception):
    """The model declined to produce code for this request."""


def generate_code(prompt: str) -> dict:
    """Return {"python", "javascript", "python_requirements"} strings for the given task description."""
    try:
        response = _create(prompt)
    except TypeError as e:
        # The SDK raises TypeError (not AuthenticationError) when no credentials are configured.
        if "authentication method" in str(e):
            raise MissingCredentials("Server has no ANTHROPIC_API_KEY configured") from e
        raise

    if response.stop_reason == "refusal":
        raise GenerationRefused("The model declined this request.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Generated code was cut off; try a narrower request.")

    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return {
        "python": data["python"],
        "javascript": data["javascript"],
        "python_requirements": data["python_requirements"],
    }


def _create(prompt: str):
    return _client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # re-run on a fallback model if safety classifiers decline
        system=SYSTEM_PROMPT,
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        messages=[{"role": "user", "content": prompt}],
    )

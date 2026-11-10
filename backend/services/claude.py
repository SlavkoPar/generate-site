import json

import anthropic

MODEL = "claude-opus-5-5"

# Reads ANTHROPIC_API_KEY (or an `ant auth login` profile) from the environment.
_client = anthropic.Anthropic()


class MissingCredentials(Exception):
    """No Anthropic API credentials are configured on the server."""


class GenerationRefused(Exception):
    """The model declined to produce output for this request."""


def ask_json(system: str, prompt: str, schema: dict) -> dict:
    """Call Claude and return the parsed JSON object matching `schema`."""
    try:
        response = _client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # re-run on a fallback model if safety classifiers decline
            system=system,
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": schema},
            },
            messages=[{"role": "user", "content": prompt}],
        )
    except TypeError as e:
        # The SDK raises TypeError (not AuthenticationError) when no credentials are configured.
        if "authentication method" in str(e):
            raise MissingCredentials("Server has no ANTHROPIC_API_KEY configured") from e
        raise

    if response.stop_reason == "refusal":
        raise GenerationRefused("The model declined this request.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Output was cut off; try a narrower request.")

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)

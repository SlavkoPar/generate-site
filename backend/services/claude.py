import contextvars
import json

import anthropic

MODEL = "claude-opus-5-5"
MAX_OUTPUT_TOKENS = 64000

# Reads ANTHROPIC_API_KEY (or an `ant auth login` profile) from the environment.
_client = anthropic.Anthropic()


# USD per million tokens: (input, output, cache read). Cache writes (5 min) are 1.25x input.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-fable-5-1": (10.00, 50.00, 1.00),
}

_usage = contextvars.ContextVar("claude_usage", default=None)


def reset_usage() -> None:
    _usage.set(None)


def get_usage() -> dict | None:
    """Token counts and USD cost of the last ask_json call in this request, if any."""
    return _usage.get()


def _record_usage(response) -> None:
    u = response.usage
    inp = u.input_tokens or 0
    out = u.output_tokens or 0
    cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
    p_in, p_out, p_read = PRICES.get(response.model, PRICES[MODEL])
    cost = (inp * p_in + out * p_out + cache_read * p_read + cache_write * p_in * 1.25) / 1_000_000
    _usage.set({
        "model": response.model,
        "input_tokens": inp + cache_read + cache_write,
        "output_tokens": out,
        "total_tokens": inp + cache_read + cache_write + out,
        "cost_usd": round(cost, 6),
    })


class MissingCredentials(Exception):
    """No Anthropic API credentials are configured on the server."""


class GenerationRefused(Exception):
    """The model declined to produce output for this request."""


def ask_json(system: str, prompt: str, schema: dict, history: list[dict] | None = None) -> dict:
    """Call Claude and return the parsed JSON object matching `schema`.

    `history` is earlier {"role", "content"} messages; the API is stateless, so the
    caller owns the conversation and resends it.
    """
    try:
        # Streaming is required for a large max_tokens (a whole site, rewritten on every
        # refinement, can run to tens of thousands of tokens); we still wait for the full message.
        with _client.beta.messages.stream(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # re-run on a fallback model if safety classifiers decline
            system=system,
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": schema},
            },
            messages=[*(history or []), {"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
    except TypeError as e:
        # The SDK raises TypeError (not AuthenticationError) when no credentials are configured.
        if "authentication method" in str(e):
            raise MissingCredentials("Server has no ANTHROPIC_API_KEY configured") from e
        raise

    _record_usage(response)
    if response.stop_reason == "refusal":
        raise GenerationRefused("The model declined this request.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Output was cut off even at the maximum length; try a narrower request.")

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)

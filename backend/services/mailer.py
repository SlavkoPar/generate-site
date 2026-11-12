"""Emails the user a summary of each generation, through the Resend HTTP API.

An HTTP API rather than SMTP because Render's free web services block outbound SMTP ports.
"""
import os

import requests

_RESEND_URL = "https://api.resend.com/emails"


def is_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def _sender() -> str:
    # Resend's shared test sender; it only delivers to the Resend account owner's own address.
    return os.environ.get("MAIL_FROM", "").strip() or "Generate Site <onboarding@resend.dev>"


def send_generation_email(to: str, prompt: str, result: dict, usage: dict | None, error: str = "") -> str | None:
    """Send the summary. Returns None on success, otherwise why it was not sent."""
    if not is_configured():
        return "Email is not configured on the server (RESEND_API_KEY)"

    lines = ["Your request:", "", prompt, ""]
    if error:
        lines += [f"The generation failed: {error}", ""]
    if result.get("github_url"):
        lines.append(f"Source on GitHub: {result['github_url']}")
    if result.get("pages_url"):
        lines.append(f"Live site (once the build finishes): {result['pages_url']}")
    if result.get("actions_url"):
        lines.append(f"Build progress: {result['actions_url']}")
    for key in ("github_error", "pages_error"):
        if result.get(key):
            lines.append(f"Problem: {result[key]}")
    if usage:
        lines += ["", f"Claude usage: {usage['input_tokens']:,} input + {usage['output_tokens']:,} output "
                      f"tokens, about ${usage['cost_usd']:.4f} USD ({usage['model']})"]

    subject = "Your site generation failed" if error else "Your generated site"
    try:
        resp = requests.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY'].strip()}"},
            json={"from": _sender(), "to": [to], "subject": subject, "text": "\n".join(lines)},
            timeout=15,
        )
    except requests.RequestException as e:
        return f"Could not reach the email service: {e}"
    if resp.status_code not in (200, 201):
        try:
            detail = resp.json().get("message", "")
        except ValueError:
            detail = ""
        return f"The email service returned {resp.status_code}: {detail}".rstrip(": ")
    return None

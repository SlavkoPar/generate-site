"""Emails the user a summary of each generation, over SMTP.

Settings: SMTP_HOST, SMTP_PORT (587 by default; 465 uses implicit TLS, anything else STARTTLS),
SMTP_USER, SMTP_PASSWORD and MAIL_FROM (defaults to SMTP_USER).
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

_TIMEOUT = 10  # seconds; a host that blocks outbound SMTP must not hold up the response for long


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def is_configured() -> bool:
    return bool(_env("SMTP_HOST") and _sender())


def _sender() -> str:
    return _env("MAIL_FROM") or _env("SMTP_USER")


def _send(message: EmailMessage) -> None:
    host, port = _env("SMTP_HOST"), int(_env("SMTP_PORT") or 587)
    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=_TIMEOUT, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=_TIMEOUT)
    with server:
        if port != 465:
            server.starttls(context=context)
        if _env("SMTP_USER"):
            server.login(_env("SMTP_USER"), _env("SMTP_PASSWORD"))
        server.send_message(message)


def send_generation_email(to: str, prompt: str, result: dict, usage: dict | None, error: str = "") -> str | None:
    """Send the summary. Returns None on success, otherwise why it was not sent."""
    if not is_configured():
        return "Email is not configured on the server (SMTP_HOST and MAIL_FROM or SMTP_USER)"

    lines = ["Your request:", "", prompt, ""]
    if error:
        lines += [f"The generation failed: {error}", ""]
    if result.get("github_url"):
        lines.append(f"Source on GitHub: {result['github_url']}")
    if result.get("pages_url"):
        lines.append(f"Live site (once the build finishes): {result['pages_url']}")
    if result.get("render_url"):
        lines.append(f"Live site on Render (once the build finishes): {result['render_url']}")
    if result.get("actions_url"):
        lines.append(f"Build progress: {result['actions_url']}")
    for key in ("github_error", "pages_error", "render_error"):
        if result.get(key):
            lines.append(f"Problem: {result[key]}")
    if usage:
        lines += ["", f"Claude usage: {usage['input_tokens']:,} input + {usage['output_tokens']:,} output "
                      f"tokens, about ${usage['cost_usd']:.4f} USD ({usage['model']})"]

    message = EmailMessage()
    message["Subject"] = "Your site generation failed" if error else "Your generated site"
    message["From"] = _sender()
    message["To"] = to
    message.set_content("\n".join(lines))
    try:
        _send(message)
    except (smtplib.SMTPException, OSError, ValueError) as e:
        return f"Could not send the email over SMTP: {e}"
    return None

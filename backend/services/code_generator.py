from .claude import GenerationRefused, MissingCredentials, ask_json  # noqa: F401  (re-exported)

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


def generate_code(prompt: str) -> dict:
    """Return {"python", "javascript", "python_requirements"} strings for the task."""
    data = ask_json(SYSTEM_PROMPT, prompt, OUTPUT_SCHEMA)
    return {
        "python": data["python"],
        "javascript": data["javascript"],
        "python_requirements": data["python_requirements"],
    }

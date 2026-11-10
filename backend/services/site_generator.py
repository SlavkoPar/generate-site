import posixpath

from .claude import ask_json

SYSTEM_PROMPT = (
    "You are a web designer and front-end developer. Given a description, build a "
    "static website that works when served from a plain file host (GitHub Pages): "
    "no build step, no server, no npm packages. Prefer ONE self-contained index.html "
    "with inline <style> and <script>; add extra files only when clearly needed, and "
    "reference them with relative paths (no leading slash). Make it responsive, "
    "accessible and polished. Do not load external scripts or tracking. "
    "Return every file with its relative path and full content, with no markdown fences."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path, e.g. index.html"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["files"],
    "additionalProperties": False,
}

ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".json", ".svg", ".txt", ".md"}
MAX_FILES = 20
MAX_FILE_BYTES = 500_000


class InvalidSite(RuntimeError):
    pass


def _clean_path(path: str) -> str:
    norm = posixpath.normpath(path.replace("\\", "/").strip())
    if (
        not norm
        or norm.startswith(("/", "../"))
        or norm == ".."
        or any(part.startswith(".") for part in norm.split("/"))
        or posixpath.splitext(norm)[1].lower() not in ALLOWED_EXTENSIONS
    ):
        raise InvalidSite(f"Generated site contained a disallowed file path: {path!r}")
    return norm


def generate_site(prompt: str) -> list[dict]:
    """Return a validated list of {"path", "content"} files; always includes index.html."""
    data = ask_json(SYSTEM_PROMPT, prompt, OUTPUT_SCHEMA)
    files: dict[str, str] = {}
    for f in data["files"][:MAX_FILES]:
        path = _clean_path(f["path"])
        if len(f["content"].encode("utf-8")) > MAX_FILE_BYTES:
            raise InvalidSite(f"{path} is too large")
        files[path] = f["content"]
    if "index.html" not in files:
        raise InvalidSite("Generated site has no index.html")
    return [{"path": p, "content": c} for p, c in files.items()]

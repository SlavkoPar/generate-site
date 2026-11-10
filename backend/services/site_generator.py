import posixpath
import re

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


FAVICON_PATH = "favicon.svg"
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Generated Site">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#14b8a6"/>
      <stop offset="1" stop-color="#3b82f6"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="url(#bg)"/>
  <rect x="9" y="14" width="46" height="38" rx="5" fill="#fff"/>
  <path d="M9 19a5 5 0 0 1 5-5h36a5 5 0 0 1 5 5v5H9z" fill="#d6f3ef"/>
  <circle cx="15" cy="19" r="1.8" fill="#14b8a6"/>
  <circle cx="21" cy="19" r="1.8" fill="#3b82f6"/>
  <circle cx="27" cy="19" r="1.8" fill="#ffb84d"/>
  <rect x="14" y="30" width="20" height="4" rx="2" fill="#b6e3dd"/>
  <rect x="14" y="38" width="14" height="4" rx="2" fill="#b6e3dd"/>
  <rect x="14" y="46" width="18" height="3" rx="1.5" fill="#d3eeea"/>
  <path d="M46 28c1 5.5 2.5 7 8 8-5.5 1-7 2.5-8 8-1-5.5-2.5-7-8-8 5.5-1 7-2.5 8-8z" fill="#ffc933" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>
</svg>
"""
_EXISTING_ICON_RE = re.compile(r"""<link[^>]*rel=["'](?:shortcut )?icon["'][^>]*>\s*""", re.I)
_HEAD_END_RE = re.compile(r"</head>", re.I)
_ICON_LINK = '<link rel="icon" type="image/svg+xml" href="favicon.svg">'


def _add_favicon(files: dict[str, str]) -> None:
    """Give the site a 'Generated Site' icon, replacing any icon the model linked."""
    files[FAVICON_PATH] = FAVICON_SVG
    html = _EXISTING_ICON_RE.sub("", files["index.html"])
    if _HEAD_END_RE.search(html):
        html = _HEAD_END_RE.sub(lambda m: "  " + _ICON_LINK + "\n" + m.group(0), html, count=1)
    else:
        html = _ICON_LINK + "\n" + html
    files["index.html"] = html

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
    _add_favicon(files)
    return [{"path": p, "content": c} for p, c in files.items()]

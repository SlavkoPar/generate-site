import json
import posixpath
import re

from .claude import ask_json

SYSTEM_PROMPT = """\
You are a web designer and front-end developer. Given a description, build a website as a \
Vite + React + TypeScript project. Nobody reviews or edits the project before it ships: a \
GitHub Actions job runs `npm install` and `npm run build` on Node 22 and publishes `dist/` \
to GitHub Pages, so the project has to build cleanly exactly as you return it.

Project layout:
- package.json at the root with "type": "module" and the scripts "dev": "vite", \
"build": "vite build", "preview": "vite preview". Keep the build script as plain \
`vite build`: a type error you cannot check here must not block the deploy. Use these \
versions: react and react-dom ^18.3.1, @types/react ^18.3.5, @types/react-dom ^18.3.0, \
@vitejs/plugin-react ^4.3.1, typescript ^5.5.4, vite ^5.4.3. Add react-router-dom ^6.26.2 \
only if the site has several pages. Avoid other dependencies unless the request needs them, \
since you cannot verify that their APIs match what you remember.
- vite.config.ts with the React plugin and `base: './'`. The site is served from a \
subfolder (https://<owner>.github.io/<repo>/), so every asset URL has to be relative.
- tsconfig.json, index.html at the root that loads /src/main.tsx, and the code under src/ \
as .tsx and .ts files with typed props and data. Put static assets in public/.
- For several pages use HashRouter, because GitHub Pages has no server-side rewrites and a \
BrowserRouter route would 404 on reload.

Do not return dotfiles (such as .gitignore), a lockfile, node_modules, dist, or binary \
files; use inline SVG or CSS for graphics. Do not load external scripts or tracking.

Make the site responsive, accessible and polished. Return every file with its path relative \
to the project root and its full content, with no markdown fences. If the conversation \
already contains a site, apply the user's new request to it, keep everything they did not \
ask to change, and return the complete updated set of files."""

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

ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".svg", ".txt", ".md"}
REQUIRED_FILES = ("index.html", "package.json", "vite.config.ts")
MAX_FILES = 80
MAX_HISTORY_MESSAGES = 6  # last 3 request/response turns
MAX_FILE_BYTES = 500_000


FAVICON_PATH = "public/favicon.svg"  # Vite copies public/ to the site root
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
# A root-absolute href is how Vite refers to public/ files; the build rewrites it with `base`.
_ICON_LINK = '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'


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


def generate_site(prompt: str, history: list[dict] | None = None) -> list[dict]:
    """Return a validated list of {"path", "content"} files making up a Vite project."""
    data = ask_json(SYSTEM_PROMPT, prompt, OUTPUT_SCHEMA, history)
    if len(data["files"]) > MAX_FILES:
        # Dropping files would leave imports dangling and break the build.
        raise InvalidSite(f"Generated site has more than {MAX_FILES} files; try a narrower request")
    files: dict[str, str] = {}
    for f in data["files"]:
        path = _clean_path(f["path"])
        if len(f["content"].encode("utf-8")) > MAX_FILE_BYTES:
            raise InvalidSite(f"{path} is too large")
        files[path] = f["content"]
    missing = [p for p in REQUIRED_FILES if p not in files]
    if missing:
        raise InvalidSite(f"Generated site is not a Vite project, missing: {', '.join(missing)}")
    _add_favicon(files)
    return [{"path": p, "content": c} for p, c in files.items()]


def extend_history(history: list[dict] | None, prompt: str, files: list[dict]) -> list[dict]:
    """History for the next request: previous turns plus this prompt and the site it produced."""
    kept = [f for f in files if f["path"] != FAVICON_PATH]  # re-added on every generation
    turn = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": json.dumps({"files": kept})},
    ]
    return [*(history or []), *turn][-MAX_HISTORY_MESSAGES:]

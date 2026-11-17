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
to the project root and its full content, with no markdown fences. Leave `deleted` empty.

If the conversation already contains a site, apply the user's new request to it and keep \
everything they did not ask to change. Then return only the files you created or changed, \
each with its full content, and list in `deleted` the paths of files to remove. Do not \
return a file whose content is unchanged: every file you leave out is kept exactly as it is."""

# Render mode: plain source that is served exactly as returned, with no build step.
PLAIN_SYSTEM_PROMPT = """\
You are a web designer and front-end developer. Given a description, build a website as \
plain source code: HTML, CSS and JavaScript only. There is no build step and nobody reviews \
or edits the files before they ship: they are served by a static host exactly as you return \
them, so the site has to work as it is.

Rules:
- index.html at the root is the entry page. Put styles in .css files and behaviour in .js \
files that the pages load with relative URLs (for example `css/style.css`, `js/main.js`).
- Write modern JavaScript that browsers run directly. No TypeScript, no JSX, no frameworks, \
no npm packages, no package.json, and no bundler or other tooling.
- Use relative URLs for every link and asset, so the site works from any folder. For several \
pages, use separate .html files linked to each other.
- Write what several pages share (header, navigation, footer) once, in a script such as \
`js/layout.js` that inserts it into every page and marks the current page's link. A page \
file then holds only its own content, and a change to the navigation touches one file. Do \
not use fetch for this, so the site also works when opened from disk.
- When several pages differ only in their data (one per product, article, person), keep the \
data in one .js file and render them from a single page chosen by a URL parameter, such as \
`item.html?id=apple`, unless the request asks for a separate file per item.
- For a site that already exists in the conversation, keep the structure it has.

Do not return dotfiles, or binary files; use inline SVG or CSS for graphics. Do not load \
external scripts or tracking.

Make the site responsive, accessible and polished. Return every file with its path relative \
to the site root and its full content, with no markdown fences. Leave `deleted` empty.

If the conversation already contains a site, apply the user's new request to it and keep \
everything they did not ask to change. Then return only the files you created or changed, \
each with its full content, and list in `deleted` the paths of files to remove. Do not \
return a file whose content is unchanged: every file you leave out is kept exactly as it is."""

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
        },
        "deleted": {
            "type": "array",
            "description": "Paths of files of the previous site to remove; empty for a new site.",
            "items": {"type": "string"},
        },
    },
    "required": ["files", "deleted"],
    "additionalProperties": False,
}

ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".svg", ".txt", ".md"}
REQUIRED_FILES = ("index.html", "package.json", "vite.config.ts")
# What a browser can load without a build; a .ts or .tsx file would be served but never run.
PLAIN_EXTENSIONS = {".html", ".css", ".js", ".json", ".svg", ".txt", ".md"}
PLAIN_FAVICON_PATH = "favicon.svg"  # no build: the file sits next to index.html
MAX_FILES = 80
MAX_FILE_BYTES = 500_000


FAVICON_PATH = "public/favicon.svg"  # Vite copies public/ to the site root
# The Vite logo, as shipped in public/vite.svg by the create-vite templates.
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img" width="31.88" height="32" preserveAspectRatio="xMidYMid meet" viewBox="0 0 256 257"><defs><linearGradient id="vite-a" x1="-.828%" x2="57.636%" y1="7.652%" y2="78.411%"><stop offset="0%" stop-color="#41D1FF"></stop><stop offset="100%" stop-color="#BD34FE"></stop></linearGradient><linearGradient id="vite-b" x1="43.376%" x2="50.316%" y1="2.242%" y2="89.03%"><stop offset="0%" stop-color="#FFEA83"></stop><stop offset="8.333%" stop-color="#FFDD35"></stop><stop offset="100%" stop-color="#FFA800"></stop></linearGradient></defs><path fill="url(#vite-a)" d="M255.153 37.938L134.897 252.976c-2.483 4.44-8.862 4.466-11.382.048L.875 37.958c-2.746-4.814 1.371-10.646 6.827-9.67l120.385 21.517a6.537 6.537 0 0 0 2.322-.004l117.867-21.483c5.438-.991 9.574 4.796 6.877 9.62Z"></path><path fill="url(#vite-b)" d="M185.432.063L96.44 17.501a3.268 3.268 0 0 0-2.634 3.014l-5.474 92.456a3.268 3.268 0 0 0 3.997 3.378l24.777-5.718c2.318-.535 4.413 1.507 3.936 3.838l-7.361 36.047c-.495 2.426 1.782 4.5 4.151 3.78l15.304-4.649c2.372-.72 4.652 1.36 4.15 3.788l-11.698 56.621c-.732 3.542 3.979 5.473 5.943 2.437l1.313-2.028l72.516-144.72c1.215-2.423-.88-5.186-3.54-4.672l-25.505 4.922c-2.396.462-4.435-1.77-3.759-4.114l16.646-57.705c.677-2.35-1.37-4.583-3.769-4.113Z"></path></svg>
"""
_EXISTING_ICON_RE = re.compile(r"""<link[^>]*rel=["'](?:shortcut )?icon["'][^>]*>\s*""", re.I)
_HEAD_END_RE = re.compile(r"</head>", re.I)
# A root-absolute href is how Vite refers to public/ files; the build rewrites it with `base`.
_ICON_LINK = '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'


def _add_favicon(files: dict[str, str], plain: bool = False) -> None:
    """Give the site the Vite logo as its icon, replacing any icon the model linked."""
    files[PLAIN_FAVICON_PATH if plain else FAVICON_PATH] = FAVICON_SVG
    link = _ICON_LINK.replace("/favicon.svg", "favicon.svg") if plain else _ICON_LINK
    html = _EXISTING_ICON_RE.sub("", files["index.html"])
    if _HEAD_END_RE.search(html):
        html = _HEAD_END_RE.sub(lambda m: "  " + link + "\n" + m.group(0), html, count=1)
    else:
        html = link + "\n" + html
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


def _previous_files(history: list[dict] | None) -> dict[str, str]:
    """The site the conversation already contains: the files in its last answer."""
    if not history:
        return {}
    try:
        previous = json.loads(history[-1]["content"])["files"]
        return {_clean_path(f["path"]): f["content"] for f in previous
                if isinstance(f["content"], str)}
    except (ValueError, KeyError, TypeError, AttributeError) as e:  # it comes back from the client
        raise InvalidSite("The previous site could not be read; untick \"Continue the previous "
                          "site\" to start a new one.") from e


def generate_site(prompt: str, history: list[dict] | None = None, plain: bool = False) -> list[dict]:
    """Return a validated list of {"path", "content"} files making up a Vite project, or with
    `plain` a site of plain HTML, CSS and JavaScript that needs no build.

    With `history` the model returns only what it changed, which is merged into the previous
    site here, so the answer stays short however large the site has grown."""
    files = _previous_files(history)
    for path in (PLAIN_FAVICON_PATH, FAVICON_PATH):  # ours, re-added below
        files.pop(path, None)
    data = ask_json(PLAIN_SYSTEM_PROMPT if plain else SYSTEM_PROMPT, prompt, OUTPUT_SCHEMA, history)
    for path in data.get("deleted", []):
        files.pop(posixpath.normpath(path.replace("\\", "/").strip()), None)
    for f in data["files"]:
        path = _clean_path(f["path"])
        if len(f["content"].encode("utf-8")) > MAX_FILE_BYTES:
            raise InvalidSite(f"{path} is too large")
        files[path] = f["content"]
    if len(files) > MAX_FILES:
        # Dropping files would leave imports dangling and break the build.
        raise InvalidSite(f"Generated site has more than {MAX_FILES} files; try a narrower request")
    if plain:
        if "index.html" not in files:
            raise InvalidSite("Generated site has no index.html")
        needs_build = [p for p in files if posixpath.splitext(p)[1].lower() not in PLAIN_EXTENSIONS]
        if needs_build:
            raise InvalidSite(f"Generated site has files a browser cannot run without a build: "
                              f"{', '.join(needs_build[:5])}")
    else:
        missing = [p for p in REQUIRED_FILES if p not in files]
        if missing:
            raise InvalidSite(f"Generated site is not a Vite project, missing: {', '.join(missing)}")
    _add_favicon(files, plain)
    return [{"path": p, "content": c} for p, c in files.items()]


def extend_history(history: list[dict] | None, prompt: str, files: list[dict]) -> list[dict]:
    """History for the next request: every request so far, and the site as it is now.

    Only one copy of the site is kept. Resending each earlier version as well would multiply
    the input cost of every refinement without telling the model anything it needs."""
    kept = [f for f in files if f["path"] not in (FAVICON_PATH, PLAIN_FAVICON_PATH)]  # re-added each time
    requests = [m["content"] for m in (history or []) if m["role"] == "user"]
    return [
        {"role": "user", "content": "\n\n".join([*requests, prompt])},
        {"role": "assistant", "content": json.dumps({"files": kept, "deleted": []})},
    ]

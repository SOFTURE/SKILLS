#!/usr/bin/env python3
"""Run evidence (screenshots, frame grabs, recordings) kept outside git (WORKFLOW.md §11).

    evidence.py name   --change <id> --nn <N> --what <slug> --state before|after --width <px> --theme light|dark
    evidence.py save   <file> --change <id> --what <slug> --state before|after --width <px> --theme light|dark [--nn <N>]
    evidence.py list   --change <id>
    evidence.py render --out <page.html> [--from-dir <dir>] [--from-page <page.html>] [--add <key>=<url> ...] [--title <text>]
    evidence.py check  <path> [<path> ...]
    evidence.py prune  --months <N> [--apply]

Names follow `<change-id>/<NN>-<what>-<before|after>-<width>-<theme>.<ext>`. Images are stored as
WebP at quality 85; PNG only when a side exceeds the WebP limit (16383 px) or no WebP encoder exists.
Recordings keep their format.

The store comes from `context/workflow.json` -> `evidence`:
  {"store": "dir", "path": "~/softure-evidence/<repo>"}             a folder outside the repository
  {"store": "project-files", "path": "<project-slug>/evidence"}     the hosted project's shared files
                                                                    (root: `projectFilesRoot`, default /mnt/project-files)
  {"store": "command", "upload": "<cmd with {file} and {key}>"}     object storage behind a project command;
                                                                    the last stdout line is the link
  {"store": "artifact", "url": "<evidence page>"}                   the asset store of one evidence page;
                                                                    the agent uploads with its artifact tool
No store: the file is kept in ~/.cache/softure-evidence/<repo>/ and reported as not durable.

Exit codes: 0 ok, 1 check found binaries / a command failed, 2 usage or configuration error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

CONFIG_PATH = os.path.join("context", "workflow.json")
STORES = ("dir", "project-files", "command", "artifact")
DEFAULT_PROJECT_FILES_ROOT = "/mnt/project-files"
WEBP_MAX_SIDE = 16383
WEBP_QUALITY = 85
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
BINARY_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
CHANGE_ID = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
KEY_RE = re.compile(
    rf"^(?P<change>{CHANGE_ID})/(?P<nn>\d{{2,}})-(?P<what>{SLUG})-(?P<state>before|after)"
    rf"-(?P<width>\d+)-(?P<theme>light|dark)\.(?P<ext>[a-z0-9]+)$"
)
DATA_BLOCK_RE = re.compile(
    r'<script type="application/json" id="evidence-data">(?P<data>.*?)</script>', re.DOTALL
)


def fail(message: str, code: int = 2) -> None:
    print(f"evidence: {message}", file=sys.stderr)
    sys.exit(code)


def repo_root() -> str:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else os.getcwd()


def load_evidence_config(root: str) -> dict:
    path = os.path.join(root, CONFIG_PATH)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    except json.JSONDecodeError as error:
        fail(f"cannot parse {CONFIG_PATH}: {error}")
    evidence = config.get("evidence") if isinstance(config, dict) else None
    if evidence is None:
        return {}
    if not isinstance(evidence, dict):
        fail(f"{CONFIG_PATH}: evidence must be an object")
    store = evidence.get("store")
    if store is not None and store not in STORES:
        fail(f"{CONFIG_PATH}: unknown evidence.store {store!r} (known: {', '.join(STORES)})")
    return evidence


def store_dir(evidence: dict) -> str | None:
    """Folder of a file-based store, or None for the other stores."""
    store = evidence.get("store")
    if store == "dir":
        if not evidence.get("path"):
            fail("evidence.store is 'dir' but evidence.path is missing")
        return os.path.abspath(os.path.expanduser(evidence["path"]))
    if store == "project-files":
        if not evidence.get("path"):
            fail("evidence.store is 'project-files' but evidence.path is missing")
        root = os.environ.get("SOFTURE_PROJECT_FILES") or evidence.get("projectFilesRoot") or DEFAULT_PROJECT_FILES_ROOT
        return os.path.join(root, evidence["path"])
    return None


def fallback_dir(root: str) -> str:
    return os.path.join(os.path.expanduser("~"), ".cache", "softure-evidence", os.path.basename(root))


def build_key(change: str, nn: int, what: str, state: str, width: int, theme: str, ext: str) -> str:
    key = f"{change}/{nn:02d}-{what}-{state}-{width}-{theme}.{ext}"
    if not KEY_RE.match(key) or len(change) > 40:
        fail(f"invalid evidence name {key!r}: change-id and what are lowercase kebab-case, "
             "state is before|after, theme is light|dark, width is a number")
    return key


def parse_key(key: str) -> dict | None:
    match = KEY_RE.match(key)
    return match.groupdict() if match else None


def next_number(folder: str | None, change: str) -> int:
    if folder is None:
        return 1
    numbers = [int(parsed["nn"]) for parsed in (parse_key(f"{change}/{name}") for name in list_names(folder, change)) if parsed]
    return max(numbers, default=0) + 1


def list_names(folder: str, change: str) -> list[str]:
    path = os.path.join(folder, change)
    if not os.path.isdir(path):
        return []
    return sorted(name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name)))


def convert(source: str, target_stem: str) -> tuple[str, str | None]:
    """Write the stored form of `source` next to `target_stem`; return (path, warning)."""
    ext = os.path.splitext(source)[1].lower()
    if ext in VIDEO_EXTENSIONS or ext == ".webp":
        target = target_stem + ext
        shutil.copyfile(source, target)
        return target, None
    if ext not in IMAGE_EXTENSIONS:
        fail(f"{source}: not an image or a recording ({', '.join(sorted(BINARY_EXTENSIONS))})")
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        Image = None
    if Image is not None:
        with Image.open(source) as image:
            if max(image.size) > WEBP_MAX_SIDE:
                target = target_stem + ".png"
                image.save(target, "PNG", optimize=True)
                return target, f"kept PNG: {image.size[0]}x{image.size[1]} exceeds the WebP limit of {WEBP_MAX_SIDE} px"
            target = target_stem + ".webp"
            image.save(target, "WEBP", quality=WEBP_QUALITY, method=6)
            return target, None
    if shutil.which("cwebp"):
        target = target_stem + ".webp"
        result = subprocess.run(["cwebp", "-quiet", "-q", str(WEBP_QUALITY), source, "-o", target], capture_output=True, text=True)
        if result.returncode == 0:
            return target, None
    target = target_stem + ext
    shutil.copyfile(source, target)
    return target, f"kept {ext[1:].upper()}: no WebP encoder (install Pillow or cwebp)"


def command_save(args: argparse.Namespace) -> None:
    if not os.path.isfile(args.file):
        fail(f"{args.file}: no such file")
    root = repo_root()
    evidence = load_evidence_config(root)
    store = evidence.get("store")
    folder = store_dir(evidence)
    nn = args.nn if args.nn is not None else next_number(folder or fallback_dir(root), args.change)
    build_key(args.change, nn, args.what, args.state, args.width, args.theme, "png")  # validate early
    with tempfile.TemporaryDirectory() as scratch:
        stem = os.path.join(scratch, f"{nn:02d}-{args.what}-{args.state}-{args.width}-{args.theme}")
        converted, warning = convert(args.file, stem)
        ext = os.path.splitext(converted)[1][1:]
        key = build_key(args.change, nn, args.what, args.state, args.width, args.theme, ext)
        result: dict = {"key": key, "store": store, "link": None, "durable": True}
        if warning:
            result["warning"] = warning
        if store in ("dir", "project-files"):
            target = os.path.join(folder, key)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(converted, target)
            result["file"] = target
            result["link"] = target if store == "dir" else f"{evidence['path'].rstrip('/')}/{key}"
            page = os.path.join(folder, "index.html")
            with open(page, "w", encoding="utf-8") as fh:
                fh.write(render_page(entries_from_dir(folder), f"Evidence: {os.path.basename(root)}"))
            result["page"] = page
        elif store == "command":
            template = evidence.get("upload")
            if not template:
                fail("evidence.store is 'command' but evidence.upload is missing")
            command = template.replace("{file}", shlex.quote(converted)).replace("{key}", shlex.quote(key))
            run = subprocess.run(command, shell=True, capture_output=True, text=True)
            if run.returncode != 0:
                fail(f"upload failed ({run.returncode}): {run.stderr.strip() or run.stdout.strip()}", 1)
            lines = [line.strip() for line in run.stdout.splitlines() if line.strip()]
            result["link"] = lines[-1] if lines else None
        else:
            keep = os.path.join(fallback_dir(root), key)
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copyfile(converted, keep)
            result["file"] = keep
            if store == "artifact":
                if not evidence.get("url"):
                    fail("evidence.store is 'artifact' but evidence.url is missing")
                result["next"] = (f"upload {keep} to the asset store of {evidence['url']}, then add it to the page: "
                                  f"evidence.py render --from-page <page> --add {key}=<asset url> --out <page>")
            else:
                result["durable"] = False
                result["next"] = "no evidence.store in context/workflow.json: this copy is lost with the machine; set one (softure-init)"
    print(json.dumps(result))


def command_name(args: argparse.Namespace) -> None:
    print(build_key(args.change, args.nn, args.what, args.state, args.width, args.theme, args.ext))


def command_list(args: argparse.Namespace) -> None:
    evidence = load_evidence_config(repo_root())
    folder = store_dir(evidence)
    if folder is None:
        store = evidence.get("store")
        if store == "artifact":
            print(f"evidence lives on the page {evidence.get('url')}: read it with the artifact tool")
        elif store == "command":
            print("evidence lives in the command store: list it with the store's own tools")
        else:
            print("no evidence.store configured")
        return
    for name in list_names(folder, args.change):
        print(f"{args.change}/{name}")


def entries_from_dir(folder: str) -> list[dict]:
    entries = []
    if not os.path.isdir(folder):
        return entries
    for change in sorted(os.listdir(folder)):
        for name in list_names(folder, change):
            key = f"{change}/{name}"
            if parse_key(key) is None:
                continue
            mtime = os.path.getmtime(os.path.join(folder, change, name))
            entries.append({"key": key, "url": key,
                            "saved": dt.datetime.fromtimestamp(mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    return entries


def entries_from_page(page: str) -> list[dict]:
    with open(page, encoding="utf-8") as fh:
        match = DATA_BLOCK_RE.search(fh.read())
    if not match:
        fail(f"{page}: no evidence-data block (not a page made by evidence.py render)")
    data = json.loads(html.unescape(match.group("data")))
    return data.get("entries", [])


def render_page(entries: list[dict], title: str) -> str:
    by_change: dict[str, list[dict]] = {}
    for entry in entries:
        parsed = parse_key(entry["key"])
        if parsed:
            by_change.setdefault(parsed["change"], []).append({**entry, **parsed})
    changes = sorted(by_change, key=lambda change: max(item.get("saved", "") for item in by_change[change]), reverse=True)
    sections = []
    for change in changes:
        rows: dict[tuple, dict] = {}
        for item in by_change[change]:
            row = rows.setdefault((item["what"], item["width"], item["theme"]), {"nn": int(item["nn"])})
            row["nn"] = min(row["nn"], int(item["nn"]))
            row[item["state"]] = item
        cells = []
        for (what, width, theme), row in sorted(rows.items(), key=lambda pair: pair[1]["nn"]):
            pair = []
            for state in ("before", "after"):
                item = row.get(state)
                if item is None:
                    pair.append(f'<div class="shot empty"><span>{state}: none</span></div>')
                    continue
                url = html.escape(item["url"], quote=True)
                media = (f'<video src="{url}" controls preload="metadata"></video>'
                         if f".{item['ext']}" in VIDEO_EXTENSIONS else
                         f'<img src="{url}" alt="{html.escape(what)} {state}" loading="lazy">')
                pair.append(f'<a class="shot" href="{url}">{media}<span>{state}</span></a>')
            cells.append(f'<figure><figcaption>{html.escape(what)} · {width} px · {theme}</figcaption>'
                         f'<div class="pair">{"".join(pair)}</div></figure>')
        newest = max(item.get("saved", "") for item in by_change[change])[:10]
        sections.append(f'<section><h2>{html.escape(change)} <small>{html.escape(newest)}</small></h2>'
                        f'<div class="grid">{"".join(cells)}</div></section>')
    data = html.escape(json.dumps({"entries": sorted(entries, key=lambda entry: entry["key"])}, indent=1), quote=False)
    body = "".join(sections) or "<p>No evidence yet.</p>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ --bg: #ffffff; --fg: #1d1d1f; --muted: #6e6e73; --line: #e2e2e7; --card: #f6f6f8; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg: #141416; --fg: #f2f2f4; --muted: #9a9aa2; --line: #2c2c31; --card: #1d1d21; }} }}
:root[data-theme="dark"] {{ --bg: #141416; --fg: #f2f2f4; --muted: #9a9aa2; --line: #2c2c31; --card: #1d1d21; }}
body {{ margin: 0; padding: 24px 16px; background: var(--bg); color: var(--fg); font: 15px/1.45 system-ui, sans-serif; }}
main {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 22px; margin: 0 0 20px; }}
h2 {{ font-size: 17px; margin: 28px 0 12px; border-top: 1px solid var(--line); padding-top: 16px; }}
small, figcaption, .shot span {{ color: var(--muted); font-size: 13px; font-weight: normal; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 360px), 1fr)); gap: 16px; }}
figure {{ margin: 0; background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 10px; }}
.pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }}
.shot {{ display: flex; flex-direction: column; gap: 4px; text-decoration: none; }}
.shot img, .shot video {{ width: 100%; height: 220px; object-fit: cover; object-position: top; border-radius: 6px; border: 1px solid var(--line); }}
.empty {{ justify-content: center; align-items: center; min-height: 120px; border: 1px dashed var(--line); border-radius: 6px; }}
</style></head>
<body><main><h1>{html.escape(title)}</h1>{body}</main>
<script type="application/json" id="evidence-data">{data}</script>
</body></html>
"""


def command_render(args: argparse.Namespace) -> None:
    entries: dict[str, dict] = {}
    if args.from_page and os.path.exists(args.from_page):
        entries.update({entry["key"]: entry for entry in entries_from_page(args.from_page)})
    if args.from_dir:
        entries.update({entry["key"]: entry for entry in entries_from_dir(args.from_dir)})
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for pair in args.add or []:
        key, sep, url = pair.partition("=")
        if not sep or parse_key(key) is None:
            fail(f"--add {pair!r}: expected <change-id>/<NN>-<what>-<state>-<width>-<theme>.<ext>=<url>")
        entries[key] = {"key": key, "url": url, "saved": entries.get(key, {}).get("saved", now)}
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(render_page(list(entries.values()), args.title))
    print(f"{args.out}: {len(entries)} files")


def command_check(args: argparse.Namespace) -> None:
    hits = []
    for path in args.paths:
        if os.path.isfile(path):
            candidates = [path]
        else:
            candidates = [os.path.join(base, name) for base, _, names in os.walk(path) for name in names]
        hits.extend(sorted(item for item in candidates if os.path.splitext(item)[1].lower() in BINARY_EXTENSIONS))
    if hits:
        for hit in hits:
            print(f"binary evidence in the repository: {hit}")
        print("move each file to the evidence store (evidence.py save), link it from ## Progress, and delete it here")
        sys.exit(1)
    print("no images or recordings")


def archived_on(root: str, change: str) -> dt.date | None:
    archive = os.path.join(root, "context", "archive")
    if not os.path.isdir(archive):
        return None
    for name in os.listdir(archive):
        if re.fullmatch(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(change)}", name):
            path = os.path.join(archive, name, "change.md")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    match = re.search(r"^archived_at:\s*(\d{4}-\d{2}-\d{2})", fh.read(), re.MULTILINE)
                if match:
                    return dt.date.fromisoformat(match.group(1))
    return None


def command_prune(args: argparse.Namespace) -> None:
    root = repo_root()
    evidence = load_evidence_config(root)
    folder = store_dir(evidence)
    if folder is None:
        fail("prune works on the 'dir' and 'project-files' stores; prune other stores with their own tools")
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    cutoff_month = today.year * 12 + today.month - args.months
    pruned = 0
    for change in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not os.path.isdir(os.path.join(folder, change)):
            continue
        archived = archived_on(root, change)
        if archived is None or archived.year * 12 + archived.month > cutoff_month:
            continue
        pruned += 1
        if args.apply:
            shutil.rmtree(os.path.join(folder, change))
            print(f"pruned {change} (archived {archived})")
        else:
            print(f"would prune {change} (archived {archived})")
    if not args.apply and pruned:
        print("dry run: add --apply to delete")


def add_name_arguments(parser: argparse.ArgumentParser, nn_required: bool) -> None:
    parser.add_argument("--change", required=True)
    parser.add_argument("--nn", type=int, required=nn_required)
    parser.add_argument("--what", required=True)
    parser.add_argument("--state", required=True, choices=("before", "after"))
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--theme", required=True, choices=("light", "dark"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evidence kept outside git (WORKFLOW.md §11)")
    commands = parser.add_subparsers(dest="command", required=True)
    name = commands.add_parser("name", help="print the canonical name")
    add_name_arguments(name, nn_required=True)
    name.add_argument("--ext", default="webp")
    save = commands.add_parser("save", help="convert and store one file")
    save.add_argument("file")
    add_name_arguments(save, nn_required=False)
    listing = commands.add_parser("list", help="list a change's stored files")
    listing.add_argument("--change", required=True)
    render = commands.add_parser("render", help="write the evidence page")
    render.add_argument("--out", required=True)
    render.add_argument("--from-dir")
    render.add_argument("--from-page")
    render.add_argument("--add", action="append")
    render.add_argument("--title", default="Evidence")
    check = commands.add_parser("check", help="fail on images or recordings under the paths")
    check.add_argument("paths", nargs="+")
    prune = commands.add_parser("prune", help="delete evidence of changes archived N months ago or earlier")
    prune.add_argument("--months", required=True, type=int)
    prune.add_argument("--apply", action="store_true")
    prune.add_argument("--today", help=argparse.SUPPRESS)
    args = parser.parse_args()
    {"name": command_name, "save": command_save, "list": command_list, "render": command_render,
     "check": command_check, "prune": command_prune}[args.command](args)


if __name__ == "__main__":
    main()

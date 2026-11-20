#!/usr/bin/env python3
"""softure-skills portfolio: where every adopting project stands, from its context/state.json. Read-only.

    softure-skills portfolio [<repo> ...] [--config <file>] [--owner] [--json] [--source git|api]

Repositories come from the arguments or from a config file outside any project (default
`~/.config/softure/portfolio.json`, or `$SOFTURE_PORTFOLIO`):

    { "projects": [ { "name": "shop", "repo": "acme/shop", "branch": "main" },
                    { "repo": "https://git.example.com/acme/api.git" },
                    { "name": "local", "repo": "~/code/app" } ] }

A repo is `owner/name` (GitHub), a git URL, or a local checkout. Without `branch` the remote's default
branch is read; a local checkout is read at `origin/<mainBranch>` when that ref exists, else at
`<mainBranch>` (no fetch: nothing is written to it).

`--source git` (default) reads `context/` of the main branch through git (a shallow, sparse, blob-less
clone into a temporary folder for a remote), takes `context/state.json`, and runs softure-doctor on the
same tree. A project without `state.json` gets one built in memory and is marked `*`.
`--source api` reads only `context/state.json` through the GitHub API (`gh api`) and runs no doctor: the
doctor column shows the `context-doctor` check run on the main branch's head instead (`ok`, `failing`,
`pending`, or `missing` when the project's CI has no job by that name).

Default output, one row per project:

    project | active roadmap X/N | queued | open changes | owner queue | last release | doctor

Last release comes from the forge when it can: the latest GitHub release through `gh api` (for a GitHub
repository, in both modes; a local checkout counts when its `origin` is on GitHub), else the highest
`v*` tag (git mode), else the value a closed roadmap recorded in `state.json`, labelled `(roadmap)`.
`SOFTURE_GH` names another `gh` binary.

`--owner` prints only the owner queue across all projects, oldest first. `--json` prints the same data
for another tool (`last_release` is the version; `last_release_source` is `release`, `tag` or `roadmap`;
with `--source api`, `doctor_check` is the check run's status and `doctor_check_url` its page). Exit 1 when a project could not be read (its row says why); nothing is ever written
outside a temporary folder.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "softure-doctor", "scripts"))
import context_state  # noqa: E402
import doctor  # noqa: E402

DEFAULT_CONFIG = os.path.join("~", ".config", "softure", "portfolio.json")
GITHUB_RE = re.compile(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$")
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
# The CI job every adopting project runs the doctor in (WORKFLOW.md §12.2); its check run carries this name.
DOCTOR_CHECK = "context-doctor"
PASSING = ("success", "neutral", "skipped")


def git(*args: str, cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check, env=env)


def load_projects(args: list[str], config: str | None) -> list[dict]:
    if args:
        return [{"repo": repo} for repo in args]
    path = os.path.expanduser(config or os.environ.get("SOFTURE_PORTFOLIO") or DEFAULT_CONFIG)
    if not os.path.exists(path):
        sys.exit(f"no repositories: pass them as arguments or list them in {path} (see --help)")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    entries = data.get("projects", data) if isinstance(data, dict) else data
    projects = []
    for entry in entries:
        projects.append({"repo": entry} if isinstance(entry, str) else dict(entry))
    return projects


def project_name(project: dict) -> str:
    if project.get("name"):
        return project["name"]
    repo = project["repo"].rstrip("/")
    return re.sub(r"\.git$", "", repo.rsplit("/", 1)[-1].rsplit(":", 1)[-1])


def is_local(repo: str) -> bool:
    return os.path.isdir(os.path.expanduser(repo))


def remote_url(repo: str) -> str:
    if re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return f"https://github.com/{repo}.git"
    return repo


def gh() -> str:
    return os.environ.get("SOFTURE_GH") or "gh"


def github_slug(repo: str, local_path: str | None = None) -> str | None:
    """`owner/name` of a GitHub repository: from the argument, or the `origin` of a local checkout."""
    if local_path:
        url = git("remote", "get-url", "origin", cwd=local_path, check=False).stdout.strip()
        match = GITHUB_RE.search(url)
        return match.group(1) if match else None
    if re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return repo
    match = GITHUB_RE.search(repo)
    return match.group(1) if match else None


def forge_release(slug: str | None) -> dict | None:
    """The latest GitHub release of `slug` through `gh api`; None without gh, access or a release."""
    if not slug:
        return None
    try:
        shown = subprocess.run([gh(), "api", f"repos/{slug}/releases/latest"], capture_output=True, text=True,
                               timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if shown.returncode != 0:
        return None
    try:
        data = json.loads(shown.stdout)
    except json.JSONDecodeError:
        return None
    if not data.get("tag_name"):
        return None
    return {"version": data["tag_name"], "date": (data.get("published_at") or "")[:10] or None, "source": "release"}


def gh_json(path: str):
    """`gh api <path>` as JSON; None without gh, access or a valid answer."""
    try:
        shown = subprocess.run([gh(), "api", path], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if shown.returncode != 0:
        return None
    try:
        return json.loads(shown.stdout)
    except json.JSONDecodeError:
        return None


def doctor_check(slug: str, branch: str | None) -> dict:
    """The newest `context-doctor` check run on the head of `branch` (else the default branch).

    `status` is `ok`, `failing`, `pending`, `missing` (no check run by that name), or `unknown` (the forge
    could not be asked).
    """
    if not branch:
        branch = (gh_json(f"repos/{slug}") or {}).get("default_branch")
    if not branch:
        return {"status": "unknown", "url": None}
    data = gh_json(f"repos/{slug}/commits/{branch}/check-runs?check_name={DOCTOR_CHECK}&filter=latest")
    if not isinstance(data, dict):
        return {"status": "unknown", "url": None}
    runs = [run for run in data.get("check_runs") or [] if run.get("name") == DOCTOR_CHECK]
    if not runs:
        return {"status": "missing", "url": None}
    run = max(runs, key=lambda run: (run.get("started_at") or "", run.get("id") or 0))
    if run.get("status") != "completed":
        status = "pending"
    else:
        status = "ok" if run.get("conclusion") in PASSING else "failing"
    return {"status": status, "url": run.get("html_url")}


def pick_release(forge: dict | None, tag: dict | None, state: dict | None) -> dict:
    """The forge's release, else the highest tag, else the roadmap-recorded value (labelled as such)."""
    for found in (forge, tag):
        if found and found.get("version"):
            return found
    recorded = (state or {}).get("last_release") or {}
    if recorded.get("version"):
        return {"version": recorded["version"], "date": recorded.get("date"), "source": "roadmap"}
    return {"version": None, "date": None, "source": None}


def highest_tag(tags: list[str]) -> str | None:
    versions = [(tuple(int(n) for n in SEMVER_RE.match(tag).groups()), tag) for tag in tags if SEMVER_RE.match(tag)]
    return max(versions)[1] if versions else None


def local_ref(path: str, branch: str | None) -> str:
    if not branch:
        raw = git("show", "HEAD:context/workflow.json", cwd=path, check=False).stdout
        try:
            branch = json.loads(raw).get("mainBranch") if raw else None
        except json.JSONDecodeError:
            branch = None
    for ref in ([f"origin/{branch}", branch] if branch else []) + ["HEAD"]:
        if git("rev-parse", "--verify", "-q", f"{ref}^{{commit}}", cwd=path, check=False).returncode == 0:
            return ref
    return "HEAD"


def read_git(project: dict) -> dict:
    """State, doctor findings and last release of one project, read through git."""
    repo = project["repo"]
    tmp = None
    try:
        if is_local(repo):
            path = os.path.expanduser(repo)
            ref = local_ref(path, project.get("branch"))
            reader = context_state.GitReader(path, ref)
            tags = git("tag", "-l", "v*", cwd=path, check=False).stdout.split()
            branch = ref
            slug = github_slug(repo, path)
        else:
            tmp = tempfile.mkdtemp(prefix="softure-portfolio-")
            url = remote_url(repo)
            clone = ["clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse"]
            if project.get("branch"):
                clone += ["--branch", project["branch"]]
            result = git(*clone, url, tmp, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()[:200]}")
            git("sparse-checkout", "set", "--no-cone", "/context/", cwd=tmp, check=False)
            reader = context_state.FsReader(tmp)
            branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=tmp, check=False).stdout.strip()
            listed = git("ls-remote", "--tags", "--refs", url, "v*", check=False).stdout
            tags = [line.split("refs/tags/", 1)[1] for line in listed.splitlines() if "refs/tags/" in line]
            slug = github_slug(repo)
        if not reader.exists("context"):
            raise RuntimeError(f"no context/ on {branch}")
        state, source = context_state.load_prior(reader), "stored"
        if state is None:
            state, source = context_state.build_state(reader), "built"
        findings = doctor.run_checks(reader, None)
        failures = [f.as_dict() for f in findings if f.severity == "fail"]
        top = highest_tag(tags)
        release = pick_release(forge_release(slug), {"version": top, "date": None, "source": "tag"} if top else None,
                               state)
        return {"branch": branch, "state": state, "state_source": source, "doctor": failures,
                **release_fields(release)}
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def read_api(project: dict) -> dict:
    """State and last release of one GitHub project, through `gh api`; no doctor."""
    repo = project["repo"]
    slug = github_slug(repo)
    if not slug:
        raise RuntimeError("--source api needs a GitHub repository (owner/name)")
    ref = f"?ref={project['branch']}" if project.get("branch") else ""
    shown = subprocess.run([gh(), "api", "-H", "Accept: application/vnd.github.raw",
                            f"repos/{slug}/contents/context/state.json{ref}"], capture_output=True, text=True)
    state, source = None, "missing"
    if shown.returncode == 0:
        state, source = json.loads(shown.stdout), "stored"
    elif "404" not in shown.stderr and "Not Found" not in shown.stderr:
        raise RuntimeError(f"gh api failed: {shown.stderr.strip()[:200]}")
    release = pick_release(forge_release(slug), None, state)
    check = doctor_check(slug, project.get("branch"))
    return {"branch": project.get("branch") or "default", "state": state, "state_source": source,
            "doctor": None, "doctor_check": check["status"], "doctor_check_url": check["url"],
            **release_fields(release)}


def release_fields(release: dict) -> dict:
    return {"last_release": release["version"], "last_release_date": release["date"],
            "last_release_source": release["source"]}


def release_cell(row: dict) -> str:
    version = row.get("last_release")
    if not version:
        return "—"
    notes = [note for note in ("roadmap" if row.get("last_release_source") == "roadmap" else None,
                               row.get("last_release_date")) if note]
    return version + (f" ({', '.join(notes)})" if notes else "")


def collect(projects: list[dict], source: str) -> list[dict]:
    rows = []
    for project in projects:
        row = {"name": project_name(project), "repo": project["repo"], "error": None}
        try:
            row.update(read_api(project) if source == "api" else read_git(project))
        except (RuntimeError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            row.update({"branch": project.get("branch"), "state": None, "state_source": "missing",
                        "doctor": None, "last_release": None, "last_release_date": None,
                        "last_release_source": None, "error": str(exc)})
        rows.append(row)
    return rows


def check_cell(row: dict) -> str:
    """The doctor column of a row read through the API: the `context-doctor` check run, else `n/a`."""
    check = row.get("doctor_check")
    return check if check and check != "unknown" else "n/a"


def summary_cells(row: dict) -> list[str]:
    name = row["name"] + ("*" if row.get("state_source") == "built" else "")
    if row["error"]:
        return [name, f"error: {row['error']}", "", "", "", "", ""]
    state = row["state"]
    if state is None:
        return [name, "no state.json", "—", "—", "—", release_cell(row), check_cell(row)]
    active = state.get("active_roadmap")
    roadmap = f"{active.get('slug') or '?'} {active['done']}/{active['total']}" if active else "—"
    if row["doctor"] is not None:
        doctor_cell = "ok" if not row["doctor"] else f"{len(row['doctor'])} failing"
    else:
        doctor_cell = check_cell(row)
    return [name, roadmap, str(len(state.get("queued", []))), str(len(state.get("open_changes", []))),
            str(len(state.get("owner_queue", []))), release_cell(row), doctor_cell]


def owner_entries(rows: list[dict]) -> list[dict]:
    entries = []
    for row in rows:
        for entry in (row["state"] or {}).get("owner_queue", []):
            entries.append({"project": row["name"], **entry})
    entries.sort(key=lambda entry: (entry.get("since") or "", entry["project"], entry.get("text", "")))
    return entries


def table(header: list[str], body: list[list[str]]) -> str:
    def clean(cell: str) -> str:
        return str(cell).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(clean(cell) for cell in cells) + " |" for cells in body]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    flags = {flag: flag in args for flag in ("--owner", "--json")}
    args = [arg for arg in args if arg not in flags]
    options = {"--config": None, "--source": "git"}
    for key in options:
        if key in args:
            k = args.index(key)
            options[key] = args[k + 1]
            del args[k:k + 2]
    if options["--source"] not in ("git", "api"):
        print("--source is git or api", file=sys.stderr)
        return 2
    unknown = [arg for arg in args if arg.startswith("--")]
    if unknown:
        print(f"unknown option {unknown[0]} (see --help)", file=sys.stderr)
        return 2
    rows = collect(load_projects(args, options["--config"]), options["--source"])
    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if flags["--json"]:
        if flags["--owner"]:
            print(json.dumps({"generated_at": generated, "owner_queue": owner_entries(rows)}, indent=2,
                             ensure_ascii=False))
        else:
            print(json.dumps({"generated_at": generated, "projects": rows}, indent=2, ensure_ascii=False))
    elif flags["--owner"]:
        entries = owner_entries(rows)
        print(table(["since", "project", "kind", "what", "source"],
                    [[e.get("since") or "—", e["project"], e["kind"], e["text"],
                      e["source"].replace("context/", "")] for e in entries]) if entries else "Nothing waits for the owner.")
    else:
        print(table(["project", "active roadmap X/N", "queued", "open changes", "owner queue", "last release", "doctor"],
                    [summary_cells(row) for row in rows]))
        if any(row.get("state_source") == "built" for row in rows):
            print("\n* no context/state.json on the main branch yet; built from the markdown for this report")
    errors = [row for row in rows if row["error"]]
    for row in errors:
        print(f"{row['name']}: {row['error']}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(context_state.quiet_broken_pipe(main))

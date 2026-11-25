#!/usr/bin/env python3
"""ci_config: check how the project's GitHub workflows run the `context-doctor` job (WORKFLOW.md §12.2).

    ci_config.py [--root <dir>] [--main-branch <name>] [--json]

An outside reader (`portfolio --source api`, an aggregator) looks for the `context-doctor` check run on the main
branch's head. That check run exists only when the job runs on `push` to the main branch; a paths filter or an
`if` on the job leaves heads without it. For every workflow under `.github/workflows/` with a job whose id or
`name:` is `context-doctor`, this lists what keeps the job from running on every push to the main branch:

  - no `push` trigger, or a `push` trigger whose `branches`/`branches-ignore`/`tags` leave the main branch out;
  - a `paths` or `paths-ignore` filter on `push` or `pull_request`;
  - an `if:` on the job.

The main branch is `--main-branch`, else `mainBranch` in `context/workflow.json`, else `main` or `master`.
The doctor reports each problem as `ci-doctor-trigger`; the installer prints the fix. A workflow without the job
is not this module's business (the installer prints the missing job). Exit 1 when a problem is found.

    ci_config.py --protection [--root <dir>] [--main-branch <name>] [--json]

`--protection` asks the forge (through `gh`, read-only) whether the main branch requires the project's CI before a
merge: every job that runs on pull requests is a required status check (classic branch protection or a ruleset), and
nobody bypasses them (administrators included). Each problem is `FAIL main-checks-not-required <branch>: <what>`.
Exit 0 when all of it holds, 1 on a problem, 75 when it cannot tell (no forge, or a token that cannot read branch
protection: that needs admin on the repository). `doctor --protection` runs the same (WORKFLOW.md §12.2).

The YAML reader is a small subset (block mappings and sequences, flow lists, quoted scalars, block scalars): enough
for workflow files, with no dependency. A file it cannot read is skipped, never reported.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # no __pycache__ inside the consumer's .claude/skills

CI_JOB = "context-doctor"
WORKFLOWS_DIR = ".github/workflows"
WORKFLOW_CONFIG = "context/workflow.json"
DEFAULT_MAIN_BRANCHES = ("main", "master")
PATH_FILTERS = ("paths", "paths-ignore")
PR_EVENTS = ("pull_request", "pull_request_target")


class YamlError(ValueError):
    pass


# ---------------------------------------------------------------- a small YAML subset


def _strip_comment(text: str) -> str:
    quote = None
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or text[index - 1].isspace()):
            return text[:index].rstrip()
    return text.rstrip()


def _lines(text: str) -> list[tuple[int, str]]:
    out = []
    for raw in text.replace("\t", "  ").splitlines():
        stripped = _strip_comment(raw)
        if not stripped.strip() or stripped.strip() in ("---", "..."):
            out.append((-1, ""))  # kept as a blank, so block scalars can be skipped by indentation
            continue
        out.append((len(stripped) - len(stripped.lstrip(" ")), stripped.strip()))
    return out


KEY_RE = re.compile(r"""^(?P<key>"[^"]*"|'[^']*'|[^\s"'#\-\[{][^:]*?|-[^\s:][^:]*?)\s*:(?:\s+(?P<value>.*))?$""")
BLOCK_SCALAR_RE = re.compile(r"^[|>][-+0-9]*$")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_flow(body: str) -> list[str]:
    parts, depth, quote, current = [], 0, None, ""
    for char in body:
        if quote:
            current += char
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [_scalar(part) for part in _split_flow(value[1:-1])]
    if value.startswith("{") and value.endswith("}"):
        out = {}
        for part in _split_flow(value[1:-1]):
            key, _, rest = part.partition(":")
            out[_unquote(key.strip())] = _scalar(rest) if rest.strip() else None
        return out
    if value in ("", "~", "null"):
        return None
    return _unquote(value)


class _Parser:
    def __init__(self, text: str) -> None:
        self.lines = _lines(text)
        self.index = 0

    def _skip_blank(self) -> None:
        while self.index < len(self.lines) and self.lines[self.index][0] < 0:
            self.index += 1

    def _peek(self) -> tuple[int, str] | None:
        self._skip_blank()
        return self.lines[self.index] if self.index < len(self.lines) else None

    def _skip_deeper(self, indent: int) -> None:
        """Skips a block scalar (or any continuation): every line deeper than `indent`, blanks included."""
        while self.index < len(self.lines):
            line_indent, _ = self.lines[self.index]
            if line_indent >= 0 and line_indent <= indent:
                return
            self.index += 1

    def parse(self):
        line = self._peek()
        if line is None:
            return None
        return self._block(line[0])

    def _block(self, indent: int):
        line = self._peek()
        if line is None:
            return None
        if line[1] == "-" or line[1].startswith("- "):
            return self._sequence(indent)
        return self._mapping(indent)

    def _value_after_key(self, indent: int, value: str | None):
        if value is None or value == "":
            nxt = self._peek()
            if nxt is None:
                return None
            if nxt[0] > indent:
                return self._block(nxt[0])
            if nxt[0] == indent and (nxt[1] == "-" or nxt[1].startswith("- ")):
                return self._sequence(indent)
            return None
        if BLOCK_SCALAR_RE.match(value):
            self._skip_deeper(indent)
            return ""
        if value[0] in "[{" and not value.endswith(("]", "}")):  # a flow collection over several lines
            parts = [value]
            while self.index < len(self.lines):
                line_indent, text = self.lines[self.index]
                self.index += 1
                if line_indent < 0:
                    continue
                parts.append(text)
                if text.endswith(("]", "}")):
                    break
            value = " ".join(parts)
        self._skip_deeper(indent)  # a plain scalar continued on deeper lines
        return _scalar(value)

    def _mapping(self, indent: int) -> dict:
        out: dict = {}
        while True:
            line = self._peek()
            if line is None or line[0] < indent:
                return out
            if line[0] > indent:
                raise YamlError(f"unexpected indentation: {line[1]!r}")
            if line[1] == "-" or line[1].startswith("- "):
                return out
            found = KEY_RE.match(line[1])
            if not found:
                raise YamlError(f"not a mapping entry: {line[1]!r}")
            self.index += 1
            key = _unquote(found.group("key").strip())
            out[key] = self._value_after_key(indent, found.group("value"))

    def _sequence(self, indent: int) -> list:
        out = []
        while True:
            line = self._peek()
            if line is None or line[0] != indent or not (line[1] == "-" or line[1].startswith("- ")):
                return out
            rest = line[1][1:].strip()
            if not rest:
                self.index += 1
                nxt = self._peek()
                out.append(self._block(nxt[0]) if nxt and nxt[0] > indent else None)
            elif KEY_RE.match(rest):
                inner = indent + (len(line[1]) - len(rest))
                self.lines[self.index] = (inner, rest)
                out.append(self._mapping(inner))
            else:
                self.index += 1
                out.append(self._value_after_key(indent, rest))
        return out


def load(text: str):
    """The document as dicts, lists and strings; raises YamlError on what the subset cannot read."""
    return _Parser(text).parse()


# ---------------------------------------------------------------- the check


def _triggers(on) -> dict:
    if on is None:
        return {}
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {str(item): None for item in on}
    if isinstance(on, dict):
        return on
    return {}


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _matches(branch: str, patterns: list[str]) -> bool:
    return any(pattern in ("*", "**") or fnmatch.fnmatchcase(branch, pattern) for pattern in patterns)


def _push_covers(push, branch: str) -> bool:
    """Whether a `push` trigger's filters let a push to `branch` through."""
    if not isinstance(push, dict):
        return True
    branches, ignored = push.get("branches"), push.get("branches-ignore")
    if branches is None and ignored is None:
        return "tags" not in push and "tags-ignore" not in push  # tags only: no branch push runs it
    if branches is not None:
        included = [pattern for pattern in _as_list(branches) if not pattern.startswith("!")]
        excluded = [pattern[1:] for pattern in _as_list(branches) if pattern.startswith("!")]
        return _matches(branch, included) and not _matches(branch, excluded)
    return not _matches(branch, _as_list(ignored))


def doctor_jobs(document) -> list[tuple[str, dict]]:
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict):
        return []
    return [(job_id, job if isinstance(job, dict) else {}) for job_id, job in jobs.items()
            if job_id == CI_JOB or (isinstance(job, dict) and job.get("name") == CI_JOB)]


def problems(text: str, main_branches: tuple[str, ...]) -> list[str] | None:
    """What keeps the workflow's `context-doctor` job off the main branch's head; None without such a job."""
    try:
        document = load(text)
    except (YamlError, IndexError):
        return None
    jobs = doctor_jobs(document)
    if not jobs:
        return None
    on = document.get("on", document.get("true")) if isinstance(document, dict) else None
    triggers = _triggers(on)
    main = " or ".join(f"`{branch}`" for branch in main_branches)
    found = []
    if "push" not in triggers:
        found.append(f"no `push` trigger, so {main} has no `{CI_JOB}` check run")
    elif not any(_push_covers(triggers["push"], branch) for branch in main_branches):
        found.append(f"the `push` trigger leaves out {main}, so it has no `{CI_JOB}` check run")
    for event in ("push", *PR_EVENTS):
        config = triggers.get(event)
        if isinstance(config, dict):
            for key in PATH_FILTERS:
                if key in config:
                    found.append(f"a `{key}` filter on `{event}`")
    for job_id, job in jobs:
        if "if" in job:
            found.append(f"an `if:` on the job `{job_id}`")
    return found


def main_branches(root: str, explicit: str | None = None) -> tuple[str, ...]:
    if explicit:
        return (explicit,)
    try:
        with open(os.path.join(root, WORKFLOW_CONFIG), encoding="utf-8") as fh:
            branch = json.load(fh).get("mainBranch")
    except (OSError, ValueError, AttributeError):
        branch = None
    return (branch,) if isinstance(branch, str) and branch else DEFAULT_MAIN_BRANCHES


def main_branches_from(reader) -> tuple[str, ...]:
    """The same, through a context_state reader (the doctor's view of the project)."""
    try:
        branch = json.loads(reader.read(WORKFLOW_CONFIG) or "{}").get("mainBranch")
    except (ValueError, AttributeError):
        branch = None
    return (branch,) if isinstance(branch, str) and branch else DEFAULT_MAIN_BRANCHES


def check(reader, branches: tuple[str, ...]) -> list[tuple[str, list[str]]]:
    """(workflow path, problems) for every workflow whose `context-doctor` job has a problem."""
    out = []
    for name, is_dir in reader.listdir(WORKFLOWS_DIR):
        if is_dir or not re.search(r"\.ya?ml$", name):
            continue
        path = f"{WORKFLOWS_DIR}/{name}"
        found = problems(reader.read(path) or "", branches)
        if found:
            out.append((path, found))
    return out


def fix_text(branch: str) -> str:
    return (f"run the job on `pull_request` and on `push` to `{branch}`, with no paths filter and no `if:` "
            f"(WORKFLOW.md §12.2)")


# ---------------------------------------------------------------- required checks on the main branch

PROTECTION_CODE = "main-checks-not-required"
EXPRESSION_RE = re.compile(r"\$\{\{")


def pull_request_jobs(text: str) -> list[str]:
    """The check names of a workflow's jobs that run on pull requests (the job's `name:`, else its id).

    A name built from an expression (`${{ matrix.os }}`) cannot be required by a fixed name and is left out; a
    matrix job's check names carry a ` (<values>)` suffix, which `required_problems` accepts."""
    try:
        document = load(text)
    except (YamlError, IndexError):
        return []
    if not isinstance(document, dict):
        return []
    on = document.get("on", document.get("true"))
    if not any(event in _triggers(on) for event in PR_EVENTS):
        return []
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return []
    names = []
    for job_id, job in jobs.items():
        name = job.get("name") if isinstance(job, dict) and isinstance(job.get("name"), str) else str(job_id)
        if not EXPRESSION_RE.search(name):
            names.append(name)
    return names


def ci_jobs(reader) -> list[str]:
    """Every job of the project's workflows that runs on pull requests, in file order, without repeats."""
    out: list[str] = []
    for name, is_dir in reader.listdir(WORKFLOWS_DIR):
        if is_dir or not re.search(r"\.ya?ml$", name):
            continue
        for job in pull_request_jobs(reader.read(f"{WORKFLOWS_DIR}/{name}") or ""):
            if job not in out:
                out.append(job)
    return out


def _covers(required: set[str], job: str) -> bool:
    return any(context == job or context.startswith(f"{job} (") for context in required)


def required_problems(protection: dict, jobs: list[str], branch: str) -> list[str]:
    """What lets a pull request merge into `branch` with a failing check.

    `protection` is what `read_protection` found: `required` (the required check names, None when nothing on the
    branch requires a check), `admins` (True: nobody bypasses; False: administrators or listed actors bypass;
    None: unknown). Returns one line per problem; empty when every job is required and nobody bypasses."""
    required = protection.get("required")
    if not jobs:
        return [f"no workflow under {WORKFLOWS_DIR}/ runs a job on pull requests, so nothing can be required "
                f"before a merge into `{branch}`"]
    if not required:
        return [f"`{branch}` requires no status checks, so a pull request can merge with a failing check: "
                f"require {', '.join(f'`{job}`' for job in jobs)} (branch protection or a ruleset)"]
    found = []
    missing = [job for job in jobs if not _covers(set(required), job)]
    if missing:
        found.append(f"`{branch}` does not require {', '.join(f'`{job}`' for job in missing)}: add "
                     f"{'it' if len(missing) == 1 else 'them'} to the required status checks")
    if protection.get("admins") is False:
        found.append(f"administrators (or the actors a ruleset lists) can bypass the required checks on "
                     f"`{branch}`: turn on \"Do not allow bypassing the above settings\" (classic protection: "
                     f"include administrators), or empty the ruleset's bypass list")
    return found


def read_protection(api, branch: str | None) -> dict:
    """The main branch's required checks, through `api(path) -> parsed JSON | None` (a `gh api` call).

    Reads classic branch protection (needs admin on the repository) and the rules that rulesets apply to the
    branch (readable with read access). `readable` is False when neither could be read: the token cannot see
    branch protection, so the answer is unknown rather than "nothing required"."""
    repo = api("repos/{owner}/{repo}")
    if not isinstance(repo, dict):
        return {"reachable": False, "readable": False, "required": None, "admins": None, "branch": branch}
    branch = branch or repo.get("default_branch") or DEFAULT_MAIN_BRANCHES[0]
    admin = bool((repo.get("permissions") or {}).get("admin"))
    required: set[str] = set()
    admins: list[bool | None] = []
    readable = admin
    classic = api(f"repos/{{owner}}/{{repo}}/branches/{branch}/protection")
    if isinstance(classic, dict):
        readable = True
        checks = classic.get("required_status_checks") or {}
        names = set(checks.get("contexts") or []) | {c.get("context") for c in checks.get("checks") or []
                                                      if isinstance(c, dict) and c.get("context")}
        if names:
            required |= names
            admins.append(bool((classic.get("enforce_admins") or {}).get("enabled")))
    rules = api(f"repos/{{owner}}/{{repo}}/rules/branches/{branch}")
    if isinstance(rules, list):
        readable = True
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            names = {c.get("context") for c in (rule.get("parameters") or {}).get("required_status_checks") or []
                     if isinstance(c, dict) and c.get("context")}
            if not names:
                continue
            required |= names
            ruleset = api(f"repos/{{owner}}/{{repo}}/rulesets/{rule.get('ruleset_id')}")
            bypass = ruleset.get("bypass_actors") if isinstance(ruleset, dict) else None
            admins.append(None if bypass is None else not bypass)
    verdict = False if False in admins else (None if None in admins or not admins else True)
    return {"reachable": True, "readable": readable, "required": sorted(required) or None, "admins": verdict,
            "branch": branch}


def gh_api(root: str):
    """`gh api <path>` from `root` as a callable (`$SOFTURE_GH` names another binary); None on any failure."""
    import subprocess

    def call(path: str):
        try:
            out = subprocess.run([os.environ.get("SOFTURE_GH", "gh"), "api", path], cwd=root,
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode != 0:
            return None
        try:
            return json.loads(out.stdout)
        except ValueError:
            return None
    return call


def protection_report(reader, api, branch: str | None) -> tuple[int, dict]:
    """(exit code, report): 0 every pull-request job is required and nobody bypasses, 1 problems, 75 unknown.

    `branch` None means the repository's default branch."""
    jobs = ci_jobs(reader)
    protection = read_protection(api, branch)
    branch = protection["branch"] or "the main branch"
    report = {"branch": branch, "jobs": jobs, "required": protection["required"], "admins": protection["admins"],
              "problems": [], "unknown": None}
    if not protection["reachable"]:
        report["unknown"] = "the forge cannot be reached from here (no `gh`, no GitHub remote or no credentials)"
        return 75, report
    if not protection["readable"]:
        report["unknown"] = ("this token cannot read the branch protection (it needs admin on the repository) and "
                             "no ruleset applies required checks; ask someone with admin to run it")
        return 75, report
    report["problems"] = required_problems(protection, jobs, branch)
    if not report["problems"] and protection["admins"] is None:
        report["unknown"] = "who may bypass the ruleset could not be read; check its bypass list"
    return (1 if report["problems"] else 0), report


def protection_main(root: str, branch: str | None, as_json: bool) -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from context_state import FsReader

    code, report = protection_report(FsReader(root), gh_api(root), branch)
    branch = report["branch"]
    if as_json:
        print(json.dumps(report, indent=2))
        return code
    for problem in report["problems"]:
        print(f"FAIL {PROTECTION_CODE} {branch}: {problem}")
    if report["unknown"]:
        print(f"UNKNOWN {PROTECTION_CODE} {branch}: {report['unknown']}")
    if code == 0:
        print(f"required checks on `{branch}`: {', '.join(report['required'] or [])} (every pull-request job; "
              f"no bypass{'' if report['admins'] else ' known'})")
    return code


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    root = args[args.index("--root") + 1] if "--root" in args else os.getcwd()
    explicit = args[args.index("--main-branch") + 1] if "--main-branch" in args else None
    if "--protection" in args:
        configured = main_branches(root, explicit)
        return protection_main(root, configured[0] if len(configured) == 1 else None, as_json)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from context_state import FsReader

    branches = main_branches(root, explicit)
    results = check(FsReader(root), branches)
    if as_json:
        print(json.dumps({"main_branches": list(branches),
                          "workflows": [{"path": path, "problems": found} for path, found in results]}, indent=2))
    else:
        for path, found in results:
            print(f"{path}: {'; '.join(found)}; {fix_text(branches[0])}")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())

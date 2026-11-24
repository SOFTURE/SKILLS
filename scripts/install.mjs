#!/usr/bin/env node
// Installs SOFTURE skills into a consumer project:
//   skills/<name>/      -> <project>/.claude/skills/<name>/
//   rules/AGENTS.md     -> managed block in AGENTS.md (or CLAUDE.md when only that exists)
//   managed block in .gitignore, so installed skills are restored by `npm install`, never committed
//   manifest            -> <project>/.claude/softure-skills.json (drives updates and uninstall)
//
// Flags: --postinstall (never fails the host install), --dry-run, --target <dir>, --no-gitignore
//
// Subcommands (run from the project root; Python 3, like the other scripts):
//   softure-skills doctor [--json]          check the context/ contract (WORKFLOW.md §12); exit 1 on drift
//   softure-skills doctor --fix [--write]   mechanical repairs of history (dry run unless --write)
//   softure-skills doctor --sweep [--json]  worklist of the judgement cases, with evidence (read-only)
//   softure-skills doctor --baseline        last resort: accept today's failures; the file only shrinks
//   softure-skills state [write|print|check] regenerate context/state.json (default: write)
//   softure-skills portfolio [<repo> ...] [--owner] [--json]   read-only table across many repositories
//
// Per-project choices live in context/workflow.json -> "install" (all optional):
//   "gitignore": false              commit the installed skills instead of ignoring them
//   "rules": ["workflow", ...]      rule sections to inject; default: every section in RULE_SECTIONS
// The top-level "mode" ("manual" by default, or "autonomous") picks the one "## Operating mode: <mode>"
// section that is always injected, whatever "rules" says. The "language" section is mandatory too:
// only "allowNonEnglishCode": true (an owner's explicit exception) leaves it out.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PACKAGE = JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, "package.json"), "utf8"));
const MANIFEST_PATH = path.join(".claude", "softure-skills.json");
const BLOCK_BEGIN = "<!-- softure-skills:begin (managed by @softure-ai/skills, do not edit) -->";
const BLOCK_END = "<!-- softure-skills:end -->";
const GITIGNORE_BEGIN = "# softure-skills:begin (managed by @softure-ai/skills)";
const GITIGNORE_END = "# softure-skills:end";
const WORKFLOW_CONFIG_PATH = path.join("context", "workflow.json");
// Section key -> heading prefix in rules/AGENTS.md. The text before the first section always ships.
const RULE_SECTIONS = { language: "## Language", workflow: "## How work flows", conventions: "## Conventions" };
// Mode sections: exactly one of them ships, chosen by workflow.json -> "mode".
const MODE_HEADING = "## Operating mode: ";
const MODES = ["manual", "autonomous"];
const DEFAULT_MODE = "manual";
const DOCTOR_SCRIPTS = path.join(PACKAGE_ROOT, "skills", "softure-doctor", "scripts");
// Subcommand -> [script, default arguments]. Each runs with the caller's working directory.
const SUBCOMMANDS = {
  doctor: [path.join(DOCTOR_SCRIPTS, "doctor.py"), []],
  state: [path.join(DOCTOR_SCRIPTS, "context_state.py"), ["write"]],
  portfolio: [path.join(PACKAGE_ROOT, "scripts", "portfolio.py"), []],
};
const CI_LINE = "npx softure-skills doctor";
// The CI job that runs the doctor has this fixed name, so a reader (portfolio --source api, an aggregator)
// finds its check run on the main branch's head. No paths filter and no condition: it runs on every push.
const CI_JOB = "context-doctor";
const CI_JOB_YAML = (version) => [
  `  ${CI_JOB}:  # keep this name: readers look for the check run "${CI_JOB}"`,
  "    runs-on: ubuntu-latest",
  "    steps:",
  "      - uses: actions/checkout@v4",
  `      - run: npx --yes --package @softure-ai/skills@${version} softure-skills doctor`,
  "        env:",
  "          npm_config_ignore_scripts: \"true\"  # run the doctor only, no install into the checkout",
].join("\n");
// The trigger the workflow that holds the job needs: every pull request, and every push to the main branch (the
// check run on the main branch's head is what readers look for). No paths filter, no condition.
const CI_ON_YAML = (branch) => [
  "on:",
  "  pull_request:",
  "  push:",
  `    branches: [${branch}]`,
].join("\n");
const CI_WORKFLOW_YAML = (version, branch) => [
  "name: context-doctor",
  "",
  CI_ON_YAML(branch),
  "",
  "jobs:",
  CI_JOB_YAML(version),
].join("\n");
const CI_CONFIG_SCRIPT = path.join(DOCTOR_SCRIPTS, "ci_config.py");
// Issues with this label carry an owner decision the coordinator acts on (WORKFLOW.md §8.6).
const OWNER_WORD_LABEL = {
  name: "owner-word",
  color: "5319e7",
  description: "An owner decision the coordinator acts on (SOFTURE workflow)",
};
const LABEL_COMMAND = `gh label create ${OWNER_WORD_LABEL.name} --color ${OWNER_WORD_LABEL.color} --description "${OWNER_WORD_LABEL.description}"`;

// Creates the owner-word label on the project's forge when it can (GitHub through an authenticated gh,
// outside CI, once per checkout). Returns [action line, whether the label is known to exist].
function ensureOwnerWordLabel(projectRoot, previous, options) {
  if ((previous.labels ?? []).includes(OWNER_WORD_LABEL.name)) return [null, true];
  if (options.isDryRun) return [`label ${OWNER_WORD_LABEL.name} (created on the forge when gh can)`, false];
  if (process.env.CI) return [null, false];
  const result = spawnSync("gh", ["label", "create", OWNER_WORD_LABEL.name, "--color", OWNER_WORD_LABEL.color,
    "--description", OWNER_WORD_LABEL.description], { cwd: projectRoot, encoding: "utf8", timeout: 15000 });
  if (result.status === 0) return [`label ${OWNER_WORD_LABEL.name} created on the forge`, true];
  if (/already exists/i.test(result.stderr ?? "")) return [null, true];
  return [`label ${OWNER_WORD_LABEL.name}: not created here; run once in the repository: ${LABEL_COMMAND}`, false];
}

// The one-time setup of the owner-word wake routine (WORKFLOW.md §8.6), printed until an autonomous project
// declares how its owner-word issues wake it. Returns the notice, or null when there is nothing to say.
function ownerWordWakeNotice(workflowConfig) {
  if (workflowConfig.mode !== "autonomous" || "ownerWordWake" in (workflowConfig.autonomy ?? {})) return null;
  return [
    `${WORKFLOW_CONFIG_PATH}: autonomy.ownerWordWake is not set, so an owner-word issue waits until a coordinator is awake.`,
    "To have the project pick it up by itself, set up the owner-word wake routine once:",
    "  1. install the Claude GitHub App on the repository (https://github.com/apps/claude);",
    "  2. paste the setup brief from node_modules/@softure-ai/skills/routines/owner-word-wake.md (\"Setting it up\")",
    "     into the project's main chat; it creates a scheduled task with a GitHub trigger on issues (opened, labeled),",
    "     a fresh session per event. The GitHub trigger can be added only in claude.ai/code/routines or with a tool",
    "     that explicitly supports GitHub event triggers; a cron-or-one-shot task has no trigger and never fires;",
    `  3. once the task shows the GitHub trigger (or you confirmed it in the UI), set`,
    `     "autonomy": { "ownerWordWake": "routine" } in ${WORKFLOW_CONFIG_PATH}; until then set "none";`,
    "  4. test it: open one owner-word issue and check that the routine's run shows up.",
    'Without the routine, declare "heartbeat" (picked up only while a run works) or "none".',
  ].join("\n");
}

function runSubcommand(name, args) {
  const [script, defaults] = SUBCOMMANDS[name];
  const result = spawnSync("python3", [script, ...(args.length > 0 ? args : defaults)], { stdio: "inherit" });
  if (result.error) {
    console.error(`[softure-skills] ${name} needs python3 on PATH: ${result.error.message}`);
    return 1;
  }
  return result.status ?? 1;
}

// Fixes the repository-derived `project` in context/workflow.json the first time it is derived, so
// context/state.json no longer depends on how the checkout was cloned (`owner/REPO` vs `owner/repo`).
// Returns the action line, or null when there is nothing to do (no context/, a named project, no python3).
function pinProject(projectRoot, workflowConfig, options) {
  if (workflowConfig.project || !fs.existsSync(path.join(projectRoot, "context"))) return null;
  if (options.isDryRun) return null;
  const result = spawnSync("python3", [path.join(DOCTOR_SCRIPTS, "context_state.py"), "pin-project", "--root", projectRoot],
    { encoding: "utf8", timeout: 15000 });
  if (result.error || result.status !== 0) return null;
  const line = result.stdout.trim();
  return line ? line : null;
}

// How the project's GitHub workflows run the doctor: "named" (in a job whose id or name is CI_JOB),
// "unnamed" (somewhere else), or "none".
function doctorInCi(projectRoot) {
  const dir = path.join(projectRoot, ".github", "workflows");
  if (!fs.existsSync(dir)) return "none";
  const texts = fs
    .readdirSync(dir)
    .filter((name) => /\.ya?ml$/.test(name))
    .map((name) => fs.readFileSync(path.join(dir, name), "utf8"))
    .filter((text) => text.includes("softure-skills doctor"));
  if (texts.length === 0) return "none";
  return texts.some((text) => hasCiJob(text)) ? "named" : "unnamed";
}

// Workflows whose CI_JOB job does not run on every push to the main branch (ci_config.py: no push trigger for it,
// a paths filter, an `if:`), as [{ path, problems }]; [] when python3 is missing or nothing is wrong.
function ciTriggerProblems(projectRoot, branch) {
  const args = [CI_CONFIG_SCRIPT, "--root", projectRoot, "--json"];
  if (branch) args.push("--main-branch", branch);
  const result = spawnSync("python3", args, { encoding: "utf8", timeout: 15000 });
  if (result.error || (result.status !== 0 && result.status !== 1)) return [];
  try {
    return JSON.parse(result.stdout).workflows ?? [];
  } catch {
    return [];
  }
}

// True when a workflow has a job whose id or `name:` is CI_JOB (the name its check run carries).
function hasCiJob(text) {
  const id = new RegExp(`^\\s+${CI_JOB}:\\s*(#.*)?$`, "m");
  const name = new RegExp(`^\\s+name:\\s*["']?${CI_JOB}["']?\\s*(#.*)?$`, "m");
  return id.test(text) || name.test(text);
}

function parseArgs(argv) {
  const options = { isPostinstall: false, isDryRun: false, target: null, shouldIgnore: true };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--postinstall") options.isPostinstall = true;
    else if (arg === "--dry-run") options.isDryRun = true;
    else if (arg === "--no-gitignore") options.shouldIgnore = false;
    else if (arg === "--target") options.target = argv[++index];
    else throw new Error(`Unknown flag: ${arg}`);
  }
  return options;
}

function resolveProjectRoot(options) {
  if (options.target) return path.resolve(options.target);
  // npm sets INIT_CWD to the directory where `npm install` was run.
  return path.resolve(process.env.INIT_CWD ?? process.cwd());
}

function readManifest(projectRoot) {
  const file = path.join(projectRoot, MANIFEST_PATH);
  if (!fs.existsSync(file)) return { skills: [] };
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function readWorkflowConfig(projectRoot) {
  const file = path.join(projectRoot, WORKFLOW_CONFIG_PATH);
  if (!fs.existsSync(file)) return {};
  try {
    const config = JSON.parse(fs.readFileSync(file, "utf8"));
    return config && typeof config === "object" ? config : {};
  } catch (error) {
    throw new Error(`cannot parse ${WORKFLOW_CONFIG_PATH}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function getInstallConfig(workflowConfig) {
  const { install } = workflowConfig;
  return typeof install === "object" && install !== null ? install : {};
}

function resolveMode(workflowConfig) {
  if (workflowConfig.mode === undefined || workflowConfig.mode === null) return DEFAULT_MODE;
  if (!MODES.includes(workflowConfig.mode)) {
    throw new Error(`${WORKFLOW_CONFIG_PATH}: unknown mode "${workflowConfig.mode}" (known: ${MODES.join(", ")})`);
  }
  return workflowConfig.mode;
}

function resolveRuleSections(installConfig) {
  const isLanguageOptional = installConfig.allowNonEnglishCode === true;
  if (installConfig.rules === undefined) {
    return Object.keys(RULE_SECTIONS).filter((key) => key !== "language" || !isLanguageOptional);
  }
  if (!Array.isArray(installConfig.rules)) throw new Error(`${WORKFLOW_CONFIG_PATH}: install.rules must be an array`);
  const unknown = installConfig.rules.filter((key) => !(key in RULE_SECTIONS));
  if (unknown.length > 0) {
    throw new Error(`${WORKFLOW_CONFIG_PATH}: unknown install.rules ${unknown.join(", ")} (known: ${Object.keys(RULE_SECTIONS).join(", ")})`);
  }
  if (isLanguageOptional || installConfig.rules.includes("language")) return installConfig.rules;
  // English code is not opt-out by omission: the section ships unless the owner set the exception.
  return ["language", ...installConfig.rules];
}

// Keeps the preamble, the "## " sections whose key is selected and the section of the active mode;
// drops the rest.
function selectRuleSections(rules, selectedKeys, mode = DEFAULT_MODE) {
  const parts = rules.split(/\n(?=## )/);
  const kept = parts.filter((part, index) => {
    if (index === 0 && !part.startsWith("## ")) return true;
    if (part.startsWith(MODE_HEADING)) return part.startsWith(`${MODE_HEADING}${mode}`);
    const key = Object.keys(RULE_SECTIONS).find((candidate) => part.startsWith(RULE_SECTIONS[candidate]));
    return key === undefined || selectedKeys.includes(key);
  });
  return kept.join("\n");
}

function listPackageSkills() {
  const skillsDir = path.join(PACKAGE_ROOT, "skills");
  return fs
    .readdirSync(skillsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(skillsDir, entry.name, "SKILL.md")))
    .map((entry) => entry.name)
    .sort();
}

function replaceManagedBlock(content, begin, end, body) {
  const block = body === null ? "" : `${begin}\n${body.trim()}\n${end}`;
  const start = content.indexOf(begin);
  const stop = content.indexOf(end);
  if (start !== -1 && stop > start) {
    const before = content.slice(0, start).trimEnd();
    // Trailing whitespace is dropped too, so a re-install never grows the file by a blank line.
    const after = content.slice(stop + end.length).trim();
    return [before, block, after].filter(Boolean).join("\n\n") + "\n";
  }
  if (body === null) return content;
  return (content.trimEnd() ? content.trimEnd() + "\n\n" : "") + block + "\n";
}

function install(options) {
  const projectRoot = resolveProjectRoot(options);
  if (projectRoot === PACKAGE_ROOT) {
    console.log("[softure-skills] running inside the package itself, nothing to install");
    return;
  }

  const previous = readManifest(projectRoot);
  const workflowConfig = readWorkflowConfig(projectRoot);
  const installConfig = getInstallConfig(workflowConfig);
  const ruleSections = resolveRuleSections(installConfig);
  const mode = resolveMode(workflowConfig);
  const shouldIgnore = options.shouldIgnore && installConfig.gitignore !== false;
  const skills = listPackageSkills();
  const skillsRoot = path.join(projectRoot, ".claude", "skills");
  const actions = [];

  for (const name of skills) {
    const target = path.join(skillsRoot, name);
    const isOurs = previous.skills.includes(name);
    if (fs.existsSync(target) && !isOurs) {
      actions.push(`skip ${name} (folder exists and is not managed by this package)`);
      continue;
    }
    actions.push(`install ${name}`);
    if (!options.isDryRun) {
      fs.rmSync(target, { recursive: true, force: true });
      fs.cpSync(path.join(PACKAGE_ROOT, "skills", name), target, { recursive: true });
    }
  }

  for (const name of previous.skills.filter((skill) => !skills.includes(skill))) {
    actions.push(`remove ${name} (no longer shipped)`);
    if (!options.isDryRun) fs.rmSync(path.join(skillsRoot, name), { recursive: true, force: true });
  }

  const rulesSource = path.join(PACKAGE_ROOT, "rules", "AGENTS.md");
  const agentsFile = path.join(projectRoot, "AGENTS.md");
  const claudeFile = path.join(projectRoot, "CLAUDE.md");
  const rulesTarget = fs.existsSync(agentsFile) || !fs.existsSync(claudeFile) ? agentsFile : claudeFile;
  if (fs.existsSync(rulesSource)) {
    actions.push(`rules block (${ruleSections.join(", ")}; mode: ${mode}) -> ${path.relative(projectRoot, rulesTarget)}`);
    if (!options.isDryRun) {
      const existing = fs.existsSync(rulesTarget) ? fs.readFileSync(rulesTarget, "utf8") : "";
      const rules = selectRuleSections(fs.readFileSync(rulesSource, "utf8"), ruleSections, mode);
      fs.writeFileSync(rulesTarget, replaceManagedBlock(existing, BLOCK_BEGIN, BLOCK_END, rules));
    }
  }

  const installed = skills.filter((name) => !actions.includes(`skip ${name} (folder exists and is not managed by this package)`));
  const gitignore = path.join(projectRoot, ".gitignore");
  if (shouldIgnore) {
    const lines = [...installed.map((name) => `/.claude/skills/${name}/`), `/${MANIFEST_PATH}`].join("\n");
    actions.push("gitignore block (installed skills are restored by npm install)");
    if (!options.isDryRun) {
      const existing = fs.existsSync(gitignore) ? fs.readFileSync(gitignore, "utf8") : "";
      fs.writeFileSync(gitignore, replaceManagedBlock(existing, GITIGNORE_BEGIN, GITIGNORE_END, lines));
    }
  } else if (fs.existsSync(gitignore) && fs.readFileSync(gitignore, "utf8").includes(GITIGNORE_BEGIN)) {
    // The project switched to committing the skills: drop the block an earlier install wrote.
    actions.push("gitignore block removed (skills are committed)");
    if (!options.isDryRun) {
      fs.writeFileSync(gitignore, replaceManagedBlock(fs.readFileSync(gitignore, "utf8"), GITIGNORE_BEGIN, GITIGNORE_END, null));
    }
  }

  const pinAction = pinProject(projectRoot, workflowConfig, options);
  if (pinAction) actions.push(pinAction);

  const [labelAction, hasLabel] = ensureOwnerWordLabel(projectRoot, previous, options);
  if (labelAction) actions.push(labelAction);

  if (!options.isDryRun) {
    fs.mkdirSync(path.join(projectRoot, ".claude"), { recursive: true });
    const manifest = {
      package: PACKAGE.name,
      version: PACKAGE.version,
      installedAt: new Date().toISOString(),
      skills: installed,
      rulesTarget: path.relative(projectRoot, rulesTarget),
      rules: ruleSections,
      mode,
      gitignore: shouldIgnore,
      labels: hasLabel ? [OWNER_WORD_LABEL.name] : [],
    };
    // A re-install that changes nothing keeps the old timestamp, so a committed manifest
    // does not dirty every fresh clone or worktree after `npm ci`.
    const { installedAt: previousAt, ...previousRest } = previous;
    const { installedAt: _ignored, ...currentRest } = manifest;
    if (previousAt && JSON.stringify(previousRest) === JSON.stringify(currentRest)) manifest.installedAt = previousAt;
    fs.writeFileSync(path.join(projectRoot, MANIFEST_PATH), JSON.stringify(manifest, null, 2) + "\n");
  }

  const prefix = options.isDryRun ? "[softure-skills] (dry run)" : "[softure-skills]";
  for (const action of actions) console.log(`${prefix} ${action}`);
  console.log(`${prefix} ${PACKAGE.name}@${PACKAGE.version} -> ${projectRoot}`);
  if (fs.existsSync(path.join(projectRoot, WORKFLOW_CONFIG_PATH)) && !readWorkflowConfig(projectRoot).project) {
    console.log(`${prefix} ${WORKFLOW_CONFIG_PATH}: add "project": "<the name the project calls itself>" (context/state.json takes it from the active roadmap until then; softure-init asks for it)`);
  }
  const wakeNotice = ownerWordWakeNotice(readWorkflowConfig(projectRoot));
  if (wakeNotice) console.log(`${prefix} ${wakeNotice}`);
  const ci = doctorInCi(projectRoot);
  const branch = readWorkflowConfig(projectRoot).mainBranch || null;
  const shownBranch = branch ?? "main";
  if (ci === "none") {
    console.log(`${prefix} CI: once \`${CI_LINE}\` exits 0 (rollout: doctor --fix, doctor --sweep; WORKFLOW.md §12.4), add this workflow under .github/workflows/ (or the job to one with the same \`on:\`): it runs on every pull request and every push to ${shownBranch}, documentation-only changes included:\n${CI_WORKFLOW_YAML(PACKAGE.version, shownBranch)}`);
  } else if (ci === "unnamed") {
    console.log(`${prefix} CI: run the doctor in a job named \`${CI_JOB}\` (no paths filter, no condition), on every pull request and every push to ${shownBranch}, so its check run can be found by that name on ${shownBranch}'s head (WORKFLOW.md §12.2):\n${CI_ON_YAML(shownBranch)}\n\njobs:\n${CI_JOB_YAML(PACKAGE.version)}`);
  } else {
    for (const workflow of ciTriggerProblems(projectRoot, branch)) {
      console.log(`${prefix} CI: the \`${CI_JOB}\` job in ${workflow.path} does not run on every push to ${shownBranch}: ${workflow.problems.join("; ")}. Give the workflow this trigger (no paths filter) and the job no \`if:\`, so ${shownBranch}'s head gets a \`${CI_JOB}\` check run (WORKFLOW.md §12.2):\n${CI_ON_YAML(shownBranch)}`);
    }
  }
}

const [subcommand, ...subcommandArgs] = process.argv.slice(2);
if (subcommand in SUBCOMMANDS) {
  process.exit(runSubcommand(subcommand, subcommandArgs));
}

try {
  install(parseArgs(process.argv.slice(2)));
} catch (error) {
  const isPostinstall = process.argv.includes("--postinstall");
  console.error(`[softure-skills] install failed: ${error instanceof Error ? error.message : String(error)}`);
  // A broken skills copy must never break the host project's `npm install`.
  process.exit(isPostinstall ? 0 : 1);
}

export { CI_JOB, CI_LINE, OWNER_WORD_LABEL, hasCiJob, ownerWordWakeNotice, replaceManagedBlock, selectRuleSections };

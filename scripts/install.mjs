#!/usr/bin/env node
// Installs SOFTURE skills into a consumer project:
//   skills/<name>/      -> <project>/.claude/skills/<name>/
//   rules/AGENTS.md     -> managed block in AGENTS.md (or CLAUDE.md when only that exists)
//   managed block in .gitignore, so installed skills are restored by `npm install`, never committed
//   manifest            -> <project>/.claude/softure-skills.json (drives updates and uninstall)
//
// Flags: --postinstall (never fails the host install), --dry-run, --target <dir>, --no-gitignore
//
// Per-project choices live in context/workflow.json -> "install" (all optional):
//   "gitignore": false              commit the installed skills instead of ignoring them
//   "rules": ["workflow", ...]      rule sections to inject; default: every section in RULE_SECTIONS
// The top-level "mode" ("manual" by default, or "autonomous") picks the one "## Operating mode: <mode>"
// section that is always injected, whatever "rules" says.

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
  if (installConfig.rules === undefined) return Object.keys(RULE_SECTIONS);
  if (!Array.isArray(installConfig.rules)) throw new Error(`${WORKFLOW_CONFIG_PATH}: install.rules must be an array`);
  const unknown = installConfig.rules.filter((key) => !(key in RULE_SECTIONS));
  if (unknown.length > 0) {
    throw new Error(`${WORKFLOW_CONFIG_PATH}: unknown install.rules ${unknown.join(", ")} (known: ${Object.keys(RULE_SECTIONS).join(", ")})`);
  }
  return installConfig.rules;
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
    const after = content.slice(stop + end.length).trimStart();
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
}

try {
  install(parseArgs(process.argv.slice(2)));
} catch (error) {
  const isPostinstall = process.argv.includes("--postinstall");
  console.error(`[softure-skills] install failed: ${error instanceof Error ? error.message : String(error)}`);
  // A broken skills copy must never break the host project's `npm install`.
  process.exit(isPostinstall ? 0 : 1);
}

export { replaceManagedBlock, selectRuleSections };

#!/usr/bin/env node
// Installs SOFTURE skills into a consumer project:
//   skills/<name>/      -> <project>/.claude/skills/<name>/
//   rules/AGENTS.md     -> managed block in AGENTS.md (or CLAUDE.md when only that exists)
//   managed block in .gitignore, so installed skills are restored by `npm install`, never committed
//   manifest            -> <project>/.claude/softure-skills.json (drives updates and uninstall)
//
// Flags: --postinstall (never fails the host install), --dry-run, --target <dir>, --no-gitignore

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
    actions.push(`rules block -> ${path.relative(projectRoot, rulesTarget)}`);
    if (!options.isDryRun) {
      const existing = fs.existsSync(rulesTarget) ? fs.readFileSync(rulesTarget, "utf8") : "";
      const rules = fs.readFileSync(rulesSource, "utf8");
      fs.writeFileSync(rulesTarget, replaceManagedBlock(existing, BLOCK_BEGIN, BLOCK_END, rules));
    }
  }

  const installed = skills.filter((name) => !actions.includes(`skip ${name} (folder exists and is not managed by this package)`));
  if (options.shouldIgnore) {
    const gitignore = path.join(projectRoot, ".gitignore");
    const lines = [...installed.map((name) => `/.claude/skills/${name}/`), `/${MANIFEST_PATH}`].join("\n");
    actions.push("gitignore block (installed skills are restored by npm install)");
    if (!options.isDryRun) {
      const existing = fs.existsSync(gitignore) ? fs.readFileSync(gitignore, "utf8") : "";
      fs.writeFileSync(gitignore, replaceManagedBlock(existing, GITIGNORE_BEGIN, GITIGNORE_END, lines));
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
      gitignore: options.shouldIgnore,
    };
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

export { replaceManagedBlock };

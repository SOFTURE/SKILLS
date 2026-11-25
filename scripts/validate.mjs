#!/usr/bin/env node
// Release gate for the skills package. Fails when:
// - a skill folder has no SKILL.md, or frontmatter `name` differs from the folder name
// - a skill name does not start with "softure-" or has no description
// - any shipped file mentions third-party course branding (this package is original work)
// - any shipped file contains Polish diacritics (everything shipped is English)
// - a mode section of the rules block does not mention the cockpit label of owner-word issues (WORKFLOW.md §8.6)
// - the shared part of the rules block does not point to WORKFLOW.md §14 (infrastructure and deploy work)
// - a routine in routines/ does not carry the hard rules every routine follows (WORKFLOW.md §13)
// - any shipped file tells a coordinator to bind a routine to its own session (routines run in a fresh session)
// - the owner-word wake setup brief lets a task without a verified GitHub trigger count as set up, or the routines
//   README does not say how to test that routine (a cron-or-one-shot tool creates a task that never fires)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FORBIDDEN = [/\b10x[- ]?dev/i, /\b10x-[a-z]/i, /przeprogramowani/i, /brave\.courses/i, /[\u0104-\u0107\u0118\u0119\u0141-\u0144\u00d3\u00f3\u015a\u015b\u0179-\u017c]/];
const errors = [];

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

function readFrontmatter(file) {
  const match = fs.readFileSync(file, "utf8").match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;
  const fields = {};
  for (const line of match[1].split("\n")) {
    const pair = line.match(/^([a-z-]+):\s*(.*)$/);
    if (pair) fields[pair[1]] = pair[2].trim();
  }
  return fields;
}

const skillsDir = path.join(ROOT, "skills");
for (const entry of fs.readdirSync(skillsDir, { withFileTypes: true }).filter((item) => item.isDirectory())) {
  const skillFile = path.join(skillsDir, entry.name, "SKILL.md");
  if (!fs.existsSync(skillFile)) {
    errors.push(`${entry.name}: missing SKILL.md`);
    continue;
  }
  const frontmatter = readFrontmatter(skillFile);
  if (!frontmatter) errors.push(`${entry.name}: missing frontmatter`);
  else {
    if (frontmatter.name !== entry.name) errors.push(`${entry.name}: frontmatter name "${frontmatter.name}" differs from folder`);
    if (!entry.name.startsWith("softure-")) errors.push(`${entry.name}: name must start with "softure-"`);
    if (!frontmatter.description) errors.push(`${entry.name}: missing description`);
  }
}

// A sentence that binds a routine to the coordinator's (or "this") session is allowed only as a prohibition.
const BINDING = /\b(bind|binds|bound|binding)\b[^.;]*\b(coordinator's|this) session/i;
const PROHIBITION = /\b(never|not|no)\b/i;

for (const file of [...walk(skillsDir), ...walk(path.join(ROOT, "rules")), ...walk(path.join(ROOT, "routines")), ...walk(path.join(ROOT, "scripts")).filter((file) => !file.endsWith("validate.mjs")), path.join(ROOT, "README.md"), path.join(ROOT, "WORKFLOW.md"), path.join(ROOT, "ONBOARD.md")]) {
  if (!/\.(md|sh|py|mjs|js|json|txt)$/.test(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  for (const pattern of FORBIDDEN) {
    if (pattern.test(content)) errors.push(`${path.relative(ROOT, file)}: matches forbidden pattern ${pattern}`);
  }
  for (const sentence of content.replace(/\s+/g, " ").split(/(?<=[.;])\s/)) {
    if (BINDING.test(sentence) && !PROHIBITION.test(sentence)) {
      errors.push(`${path.relative(ROOT, file)}: binds a routine to the coordinator's session: "${sentence.slice(0, 120)}"`);
    }
  }
}

const rules = fs.readFileSync(path.join(ROOT, "rules", "AGENTS.md"), "utf8");
for (const mode of ["manual", "autonomous"]) {
  const section = rules.split(/\n(?=## )/).find((part) => part.startsWith(`## Operating mode: ${mode}`)) ?? "";
  if (!section.includes("`cockpit`")) errors.push(`rules/AGENTS.md: "Operating mode: ${mode}" does not mention the \`cockpit\` label`);
}
// Infrastructure and deploy rules bind in both modes, so the pointer lives in the shared part of the block (WORKFLOW.md §14).
const sharedRules = rules.slice(0, rules.indexOf("## Operating mode: "));
if (!/WORKFLOW §14/.test(sharedRules)) errors.push('rules/AGENTS.md: the shared part does not point to WORKFLOW §14 (infrastructure and deploy work)');
if (!/^## 14\. Infrastructure and deploy work$/m.test(fs.readFileSync(path.join(ROOT, "WORKFLOW.md"), "utf8"))) errors.push("WORKFLOW.md: missing section 14, Infrastructure and deploy work");
const startOfRun = rules.slice(rules.indexOf("**Start of a run.**"), rules.indexOf("**Messages to the owner"));
if (!/owner-word/.test(startOfRun)) errors.push('rules/AGENTS.md: "Start of a run" does not act on `owner-word` issues first');

const routinesDir = path.join(ROOT, "routines");
const routinesReadme = fs.readFileSync(path.join(routinesDir, "README.md"), "utf8");
if (!/create_new_session_on_fire/.test(routinesReadme)) errors.push("routines/README.md: does not require a fresh session on every fire");
for (const file of fs.readdirSync(routinesDir).filter((name) => name.endsWith(".md") && name !== "README.md")) {
  const content = fs.readFileSync(path.join(routinesDir, file), "utf8");
  if (!/Never release, tag, publish or deploy/.test(content)) errors.push(`routines/${file}: missing the hard rule "Never release, tag, publish or deploy"`);
  if (!/fresh session/i.test(content)) errors.push(`routines/${file}: does not say it runs in a fresh session`);
  if (!/Never disable, edit or delete this routine/.test(content)) errors.push(`routines/${file}: missing the hard rule "Never disable, edit or delete this routine"`);
  if (!routinesReadme.includes(`(${file})`)) errors.push(`routines/${file}: not listed in routines/README.md`);
}

// The owner-word wake fires only through a GitHub event trigger, which most task-creation tools cannot add.
const wake = fs.readFileSync(path.join(routinesDir, "owner-word-wake.md"), "utf8");
const brief = wake.slice(wake.indexOf("## Setting it up"), wake.indexOf("Routine prompt:"));
const WAKE_BRIEF = [
  [/only in the routines web UI \(claude\.ai\/code\/routines\) or with a tool that\s+explicitly supports GitHub event\s+triggers/, "say the GitHub trigger can be added only in the routines web UI or with a tool that explicitly supports it"],
  [/exact steps to finish it in claude\.ai\/code\/routines/, "hand the owner the exact UI steps when the session cannot add the trigger"],
  [/never reports the routine as set up or working/, "forbid reporting a routine without a trigger as working"],
  [/Verify the trigger[\s\S]*Only then set[\s\S]*"routine"/, "verify the trigger before setting autonomy.ownerWordWake to \"routine\""],
  [/Until the\s+trigger is verified the value is "none"/, "keep autonomy.ownerWordWake at \"none\" until the trigger is verified"],
];
for (const [pattern, what] of WAKE_BRIEF) {
  if (!pattern.test(brief)) errors.push(`routines/owner-word-wake.md: the setup brief does not ${what}`);
}
if (!/## Testing it/.test(wake)) errors.push('routines/owner-word-wake.md: no "Testing it" section');
if (!/To test it, open\s+one `owner-word` issue/.test(routinesReadme)) errors.push("routines/README.md: does not say how to test the owner-word wake routine");

if (errors.length > 0) {
  for (const error of errors) console.error(`✗ ${error}`);
  process.exit(1);
}
console.log("✓ skills package valid");

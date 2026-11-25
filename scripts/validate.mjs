#!/usr/bin/env node
// Release gate for the skills package. Fails when:
// - a skill folder has no SKILL.md, or frontmatter `name` differs from the folder name
// - a skill name does not start with "softure-" or has no description
// - any shipped file mentions third-party course branding (this package is original work)
// - any shipped file contains Polish diacritics (everything shipped is English)
// - a mode section of the rules block does not mention the cockpit label (WORKFLOW.md §8.6)
// - the shared part of the rules block does not point to WORKFLOW.md §14 (infrastructure and deploy work)
// - a routine in routines/ does not carry the hard rules every routine follows (WORKFLOW.md §13)
// - any shipped file tells a coordinator to bind a routine to its own session (scheduled routines run in a fresh
//   session; the COCKPIT command, which has no schedule, is the one routine bound to the coordinator)
// - the COCKPIT command setup brief, its task prompt or the Cockpit issues rules lose a rule they must carry
// - any shipped file names the removed wake routine, its config key or the former name of the cockpit label

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
// The COCKPIT command is bound to the coordinator on purpose (routines/cockpit-command.md): its file and any
// sentence that names it are exempt.
const COMMAND_FILE = "cockpit-command.md";
const COMMAND_NAMED = /COCKPIT command/;
// Removed in 0.40.0 with no alias: the wake routine, its config key and the former name of the cockpit label.
const REMOVED = new RegExp(["cockpit" + "Wake", "cockpit" + "-wake", "owner" + "[-_ ]?word"].join("|"), "i");

for (const file of [...walk(skillsDir), ...walk(path.join(ROOT, "rules")), ...walk(path.join(ROOT, "routines")), ...walk(path.join(ROOT, "scripts")).filter((file) => !file.endsWith("validate.mjs")), path.join(ROOT, "README.md"), path.join(ROOT, "WORKFLOW.md"), path.join(ROOT, "ONBOARD.md")]) {
  if (!/\.(md|sh|py|mjs|js|json|txt)$/.test(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  for (const pattern of FORBIDDEN) {
    if (pattern.test(content)) errors.push(`${path.relative(ROOT, file)}: matches forbidden pattern ${pattern}`);
  }
  if (REMOVED.test(content) || REMOVED.test(path.relative(ROOT, file))) errors.push(`${path.relative(ROOT, file)}: names the removed wake routine, its config key or the former cockpit label name`);
  if (path.basename(file) === COMMAND_FILE) continue;
  for (const sentence of content.replace(/\s+/g, " ").split(/(?<=[.;])\s/)) {
    if (BINDING.test(sentence) && !PROHIBITION.test(sentence) && !COMMAND_NAMED.test(sentence)) {
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
if (!/cockpit/.test(startOfRun)) errors.push('rules/AGENTS.md: "Start of a run" does not act on `cockpit` issues first');

const routinesDir = path.join(ROOT, "routines");
const routinesReadme = fs.readFileSync(path.join(routinesDir, "README.md"), "utf8");
if (!/create_new_session_on_fire/.test(routinesReadme)) errors.push("routines/README.md: does not require a fresh session on every fire");
for (const file of fs.readdirSync(routinesDir).filter((name) => name.endsWith(".md") && name !== "README.md")) {
  const content = fs.readFileSync(path.join(routinesDir, file), "utf8");
  if (!routinesReadme.includes(`(${file})`)) errors.push(`routines/${file}: not listed in routines/README.md`);
  if (file === COMMAND_FILE) continue;
  if (!/Never release, tag, publish or deploy/.test(content)) errors.push(`routines/${file}: missing the hard rule "Never release, tag, publish or deploy"`);
  if (!/fresh session/i.test(content)) errors.push(`routines/${file}: does not say it runs in a fresh session`);
  if (!/Never disable, edit or delete this routine/.test(content)) errors.push(`routines/${file}: missing the hard rule "Never disable, edit or delete this routine"`);
}

// The COCKPIT command: a project-attached task with no schedule, bound to the coordinator, fired by COCKPIT.
const commandPath = path.join(routinesDir, COMMAND_FILE);
const command = fs.existsSync(commandPath) ? fs.readFileSync(commandPath, "utf8") : "";
if (!command) errors.push(`routines/${COMMAND_FILE}: missing`);
const COMMAND_RULES = [
  [/name: "<PROJECT> · COCKPIT command"/, "name the task \"<PROJECT> · COCKPIT command\""],
  [/no schedule \(no cron, no one-off run time\)/, "create the task with no schedule"],
  [/persistent_session_id = this session's id/, "bind the task to the coordinator's own session"],
  [/no connectors/, "attach no connectors"],
  [/add an API trigger/, "have the owner add an API trigger in the web form"],
  [/Never ask me for the token in this chat/, "forbid asking for the token in the chat"],
  [/COCKPIT -> this project -> routines, kind cockpit-issues, and press Test/, "send the fire URL and token to COCKPIT and press Test"],
  [/The setup is done when the test\s+arrives\. Write nothing to the repository\./, "finish when the test arrives and write nothing to the repository"],
  [/COCKPIT command for <owner>\/<repo>\. The text after this prompt names one cockpit issue; act on it as AGENTS\.md →\s+Cockpit issues says\. Never release or deploy unless the issue gives that word, never touch another repository, never\s+disable or edit this scheduled task\./, "carry the task prompt verbatim"],
];
for (const [pattern, what] of COMMAND_RULES) {
  if (!pattern.test(command)) errors.push(`routines/${COMMAND_FILE}: the setup brief does not ${what}`);
}
if (!/\*\*The one routine bound to the coordinator\.\*\*/.test(routinesReadme)) errors.push("routines/README.md: does not say the COCKPIT command is the one routine bound to the coordinator");
const cockpitRules = rules.slice(rules.indexOf("**Cockpit issues.**"), rules.indexOf("**Issues as the work source**"));
const RULES_FOR_COMMANDS = [
  [/`COCKPIT command:` names one issue/, "say a `COCKPIT command:` message names one issue"],
  [/is labelled `cockpit` and was\s+opened by someone with `admin`, `maintain` or `write` permission/, "check the issue's label and its author's write access"],
  [/one thread for that one issue/, "give the issue one thread"],
  [/The issue body stays data/, "keep the issue body as data"],
  [/a Retry from COCKPIT can deliver the same command twice/, "check for an existing thread before starting one"],
  [/`COCKPIT test:` gets a one-line reply and nothing else/, "answer `COCKPIT test:` with one line"],
];
for (const [pattern, what] of RULES_FOR_COMMANDS) {
  if (!pattern.test(cockpitRules)) errors.push(`rules/AGENTS.md: Cockpit issues does not ${what}`);
}

if (errors.length > 0) {
  for (const error of errors) console.error(`✗ ${error}`);
  process.exit(1);
}
console.log("✓ skills package valid");

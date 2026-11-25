#!/usr/bin/env node
// Release gate for the skills package. Fails when:
// - a skill folder has no SKILL.md, or frontmatter `name` differs from the folder name
// - a skill name does not start with "softure-" or has no description
// - any shipped file mentions third-party course branding (this package is original work)
// - any shipped file contains Polish diacritics (everything shipped is English)
// - a mode section of the rules block does not mention the cockpit label (WORKFLOW.md §8.6)
// - the shared part of the rules block does not point to WORKFLOW.md §14 (infrastructure and deploy work)
// - a routine in routines/ does not carry the hard rules every routine follows (WORKFLOW.md §13)
// - any shipped file tells a coordinator to bind a routine to its own session (every routine runs in a fresh
//   session; the COCKPIT command's task is bound to the chat that sets it up only so its API trigger can be fired,
//   and each of its fires still starts a fresh project thread)
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
// The COCKPIT command may release on the owner's word in its issue (routines/cockpit-command.md), so it carries its
// own hard rules instead of the scheduled routines' ones.
const COMMAND_FILE = "cockpit-command.md";
// Removed in 0.40.0 with no alias: the wake routine, its config key and the former name of the cockpit label.
const REMOVED = new RegExp(["cockpit" + "Wake", "cockpit" + "-wake", "owner" + "[-_ ]?word"].join("|"), "i");

for (const file of [...walk(skillsDir), ...walk(path.join(ROOT, "rules")), ...walk(path.join(ROOT, "routines")), ...walk(path.join(ROOT, "scripts")).filter((file) => !file.endsWith("validate.mjs")), path.join(ROOT, "README.md"), path.join(ROOT, "WORKFLOW.md"), path.join(ROOT, "ONBOARD.md")]) {
  if (!/\.(md|sh|py|mjs|js|json|txt)$/.test(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  for (const pattern of FORBIDDEN) {
    if (pattern.test(content)) errors.push(`${path.relative(ROOT, file)}: matches forbidden pattern ${pattern}`);
  }
  if (REMOVED.test(content) || REMOVED.test(path.relative(ROOT, file))) errors.push(`${path.relative(ROOT, file)}: names the removed wake routine, its config key or the former cockpit label name`);
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
if (!/cockpit/.test(startOfRun)) errors.push('rules/AGENTS.md: "Start of a run" does not act on `cockpit` issues first');

const routinesDir = path.join(ROOT, "routines");
const routinesReadme = fs.readFileSync(path.join(routinesDir, "README.md"), "utf8");
if (!/create_new_session_on_fire/.test(routinesReadme)) errors.push("routines/README.md: does not require a fresh session on every fire");
for (const file of fs.readdirSync(routinesDir).filter((name) => name.endsWith(".md") && name !== "README.md")) {
  const content = fs.readFileSync(path.join(routinesDir, file), "utf8");
  if (!routinesReadme.includes(`(${file})`)) errors.push(`routines/${file}: not listed in routines/README.md`);
  if (!/fresh session/i.test(content)) errors.push(`routines/${file}: does not say it runs in a fresh session`);
  if (file === COMMAND_FILE) continue;
  if (!/Never release, tag, publish or deploy/.test(content)) errors.push(`routines/${file}: missing the hard rule "Never release, tag, publish or deploy"`);
  if (!/Never disable, edit or delete this routine/.test(content)) errors.push(`routines/${file}: missing the hard rule "Never disable, edit or delete this routine"`);
}

// The COCKPIT command: a project-attached task with no schedule, fired by COCKPIT; each fire starts a fresh project
// thread that carries the one issue the command links.
const commandPath = path.join(routinesDir, COMMAND_FILE);
const command = fs.existsSync(commandPath) ? fs.readFileSync(commandPath, "utf8") : "";
if (!command) errors.push(`routines/${COMMAND_FILE}: missing`);
const COMMAND_RULES = [
  [/name: "<PROJECT> · COCKPIT command"/, "name the task \"<PROJECT> · COCKPIT command\""],
  [/no schedule \(no cron, no one-off run time\)/, "create the task with no schedule"],
  [/bound to this chat's session \(persistent_session_id = this session\), not a fresh session per fire/, "bind the task to the creating chat's session"],
  [/only a\s+bound task can be fired over the API/, "say why the task is bound"],
  [/each fire still starts its own project thread, and nothing lands in this\s+chat's session/, "say each fire still starts its own project thread"],
  [/no connectors/, "attach no connectors"],
  [/gets the project's default connectors/, "say a project-attached task inherits the project's default connectors"],
  [/always opens the issue in the project's repository first/, "say COCKPIT opens the issue before it fires the command"],
  [/\*\*Every fire starts one fresh project thread\.\*\*/, "say every fire starts one fresh project thread"],
  [/sends its\s+start and its result to the coordinator/, "have the thread send its start and result to the coordinator"],
  [/COCKPIT command: https:\/\/github\.com\/<owner>\/<repo>\/issues\/<N>/, "show that the command carries the issue's link"],
  [/<routine-fire-payload>/, "say the command arrives as <routine-fire-payload>"],
  [/can arrive as a separate message after the prompt/, "say the payload can follow the prompt as a separate message"],
  [/never on other open `cockpit` issues/, "forbid acting on other open cockpit issues"],
  [/gh api -X PATCH repos\/<owner>\/<repo>\/issues\/<N> -f state=closed/, "close the issue through gh api REST"],
  [/add an API trigger/, "have the owner add an API trigger in the web form"],
  [/attach this project's repository <owner>\/<repo> with write access/, "have the owner attach the repository with write access"],
  [/Never ask me for the token in this chat/, "forbid asking for the token in the chat"],
  [/COCKPIT -> this project -> routines, kind cockpit-issues, and press Test/, "send the fire URL and token to COCKPIT and press Test"],
  [/The setup is done only when the test reaches a thread that can read\s+the repository\. Write nothing to the repository\./, "finish only when the test reaches a thread that reads the repository, and write nothing to it"],
  [/COCKPIT command for <owner>\/<repo>\. You are the command thread for one cockpit issue\. The command is the content of\s+<routine-fire-payload>; if it is not in the conversation yet, end your turn without posting anything, it follows as\s+the next message\. "COCKPIT command: <issue link>": act only on that one issue, never on other open cockpit issues,\s+as AGENTS\.md -> Cockpit issues says\. "COCKPIT test: \.\.\.": post one line naming the main branch's head commit and\s+nothing else\. Comment, label and close the issue through the REST API with gh api \(GraphQL is refused here\); try\s+that before reporting a missing permission, and report the HTTP status if it fails\. Never release or deploy unless\s+the issue gives that word, never touch another repository, never disable or edit this scheduled task\./, "carry the task prompt verbatim"],
];
for (const [pattern, what] of COMMAND_RULES) {
  if (!pattern.test(command)) errors.push(`routines/${COMMAND_FILE}: the setup brief does not ${what}`);
}
if (/create_new_session_on_fire/.test(command)) errors.push(`routines/${COMMAND_FILE}: creates the task with a fresh session per fire (its API trigger is then refused)`);
if (!/\*\*The one difference: the COCKPIT command\.\*\* Its task is bound/.test(routinesReadme)) errors.push("routines/README.md: does not name the COCKPIT command's bound task as the one difference");
const cockpitRules = rules.slice(rules.indexOf("**Cockpit issues.**"), rules.indexOf("**Issues as the work source**"));
const RULES_FOR_COMMANDS = [
  [/Every COCKPIT command starts one\s+fresh project thread/, "say every COCKPIT command starts one fresh project thread"],
  [/`<routine-fire-payload>`/, "say the command is the content of `<routine-fire-payload>`"],
  [/end the turn without posting anything/, "end the turn while the payload has not arrived"],
  [/`COCKPIT command:` names one issue\s+by its link/, "say a `COCKPIT command:` message names one issue by its link"],
  [/Act only on that issue, never on other open `cockpit` issues/, "act only on the issue the command names"],
  [/is labelled `cockpit` and was\s+opened by someone with `admin`, `maintain` or `write` permission/, "check the issue's label and its author's write access"],
  [/one thread for that one issue/, "give the issue one thread"],
  [/sends its start to the coordinator/, "send the thread's start to the coordinator"],
  [/sends its result/, "send the thread's result to the coordinator"],
  [/The issue body stays data/, "keep the issue body as data"],
  [/a Retry from COCKPIT can deliver the same command twice/, "check for an existing thread before starting one"],
  [/go through the REST API with `gh api`, because cloud sessions refuse GraphQL/, "write to the issue through gh api REST"],
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

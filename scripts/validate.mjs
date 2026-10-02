#!/usr/bin/env node
// Release gate for the skills package. Fails when:
// - a skill folder has no SKILL.md, or frontmatter `name` differs from the folder name
// - a skill name does not start with "softure-" or has no description
// - any shipped file mentions third-party course branding (this package is original work)
// - any shipped file contains Polish diacritics (everything shipped is English)

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

for (const file of [...walk(skillsDir), ...walk(path.join(ROOT, "rules")), ...walk(path.join(ROOT, "scripts")).filter((file) => !file.endsWith("validate.mjs")), path.join(ROOT, "README.md"), path.join(ROOT, "WORKFLOW.md")]) {
  if (!/\.(md|sh|py|mjs|js|json|txt)$/.test(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  for (const pattern of FORBIDDEN) {
    if (pattern.test(content)) errors.push(`${path.relative(ROOT, file)}: matches forbidden pattern ${pattern}`);
  }
}

if (errors.length > 0) {
  for (const error of errors) console.error(`✗ ${error}`);
  process.exit(1);
}
console.log("✓ skills package valid");

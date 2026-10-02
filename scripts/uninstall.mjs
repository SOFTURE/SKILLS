#!/usr/bin/env node
// Removes everything install.mjs put into a project, driven by .claude/softure-skills.json.
// Usage: node node_modules/@softure-ai/skills/scripts/uninstall.mjs [--target <dir>]

import fs from "node:fs";
import path from "node:path";

const MANIFEST_PATH = path.join(".claude", "softure-skills.json");
const BLOCKS = [
  ["<!-- softure-skills:begin (managed by @softure-ai/skills, do not edit) -->", "<!-- softure-skills:end -->"],
  ["# softure-skills:begin (managed by @softure-ai/skills)", "# softure-skills:end"],
];

function stripBlocks(content) {
  let result = content;
  for (const [begin, end] of BLOCKS) {
    const start = result.indexOf(begin);
    const stop = result.indexOf(end);
    if (start !== -1 && stop > start) {
      result = (result.slice(0, start).trimEnd() + "\n\n" + result.slice(stop + end.length).trimStart()).trim() + "\n";
    }
  }
  return result;
}

const targetIndex = process.argv.indexOf("--target");
const projectRoot = path.resolve(targetIndex !== -1 ? process.argv[targetIndex + 1] : process.env.INIT_CWD ?? process.cwd());
const manifestFile = path.join(projectRoot, MANIFEST_PATH);

if (!fs.existsSync(manifestFile)) {
  console.log(`[softure-skills] no manifest at ${manifestFile}, nothing to remove`);
  process.exit(0);
}

const manifest = JSON.parse(fs.readFileSync(manifestFile, "utf8"));
for (const name of manifest.skills) {
  fs.rmSync(path.join(projectRoot, ".claude", "skills", name), { recursive: true, force: true });
  console.log(`[softure-skills] removed ${name}`);
}
for (const file of [manifest.rulesTarget, ".gitignore"].filter(Boolean)) {
  const full = path.join(projectRoot, file);
  if (!fs.existsSync(full)) continue;
  const stripped = stripBlocks(fs.readFileSync(full, "utf8"));
  // The installer may have created the file; leave no empty husk behind.
  if (stripped.trim() === "") fs.rmSync(full);
  else fs.writeFileSync(full, stripped);
}
fs.rmSync(manifestFile);
console.log("[softure-skills] uninstalled");

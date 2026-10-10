#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

const mode = process.argv[2];
const shellIndex = process.argv.indexOf("--shell");
const shell = shellIndex >= 0 ? process.argv[shellIndex + 1] : "";
const settings = path.join(process.env.CLAUDE_CONFIG_DIR, "settings.json");
const payload = fs.existsSync(settings) ? JSON.parse(fs.readFileSync(settings, "utf8")) : {};
if (mode === "inspect") {
  const command = payload.statusLine?.command || "";
  process.stdout.write(JSON.stringify({existing: command.includes("claude-hud") ? "claude-hud" : command ? "other" : "none", shell}));
} else if (mode === "install") {
  payload.statusLine = {type: "command", command: "node $CLAUDE_CONFIG_DIR/plugins/claude-hud/statusline.mjs"};
  fs.mkdirSync(path.dirname(settings), {recursive: true});
  fs.writeFileSync(settings, JSON.stringify(payload, null, 2) + "\n");
  const launcher = path.join(process.env.CLAUDE_CONFIG_DIR, "plugins", "claude-hud", "statusline.mjs");
  fs.mkdirSync(path.dirname(launcher), {recursive: true});
  fs.copyFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "statusline.mjs"), launcher);
}

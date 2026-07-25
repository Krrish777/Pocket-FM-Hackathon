#!/usr/bin/env node
/**
 * SessionStart hook — harness "clock-in".
 *
 * Implements the methodology's session-start routine: at the start of every session, surface the
 * handoff state so the agent resumes exactly where the last session left off, instead of guessing.
 * It injects (via hookSpecificOutput.additionalContext) a short checklist plus the head of the
 * handoff files and the next unfinished feature. Read-only and fail-silent — never blocks a session.
 *
 * Stacks with (does not replace) the global SessionStart hooks (remember / context-mode).
 */
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();

function head(file, n) {
  try {
    const p = join(root, file);
    if (!existsSync(p)) return null;
    const text = readFileSync(p, "utf8").trim();
    if (!text) return null;
    return text.split(/\r?\n/).slice(0, n).join("\n");
  } catch {
    return null;
  }
}

function nextFeature() {
  try {
    const p = join(root, "feature_list.json");
    if (!existsSync(p)) return null;
    const data = JSON.parse(readFileSync(p, "utf8"));
    const f = (data.features || []).find((x) => x.passes === false);
    return f ? `${f.id} — ${f.description}` : "all features passing 🎉";
  } catch {
    return null;
  }
}

const parts = [
  "🕒 HARNESS CLOCK-IN — do this before touching code:",
  "1) `pwd`  2) read the handoff below  3) pick ONE feature (WIP=1)  4) run `./init.sh` / `make check`.",
];

const handoff = head("session_handoff.md", 25);
if (handoff) parts.push("\n--- session_handoff.md ---\n" + handoff);

const progressNext = head("PROGRESS.md", 40);
if (progressNext) parts.push("\n--- PROGRESS.md (head) ---\n" + progressNext);

const nf = nextFeature();
if (nf) parts.push("\n--- next feature (feature_list.json) ---\n" + nf);

parts.push(
  "\nAt clock-out: `make check` green, update feature_list.json (via verification only), PROGRESS.md, " +
    "and session_handoff.md; then ask before committing."
);

const out = {
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: parts.join("\n"),
  },
};
process.stdout.write(JSON.stringify(out));
process.exit(0);

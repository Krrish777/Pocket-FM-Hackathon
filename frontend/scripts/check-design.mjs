#!/usr/bin/env node
/**
 * Design-system gate.
 *
 * DESIGN.md §9 and FRONTEND_TECH_STACK.md §2 end with checklists a human is
 * supposed to eyeball before calling a screen done. Checklists rot. This turns
 * the mechanical half of them into something that fails a build.
 *
 * It cannot judge taste — it catches the specific, literal violations the specs
 * call out by name. Run with `npm run check:design`.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(ROOT, "src");

/* Vendored shadcn primitives are excluded: they are third-party code we restyle
   at the call site, and `--radius: 2px` structurally neutralises their radii. */
const EXCLUDED_DIRS = new Set(["ui", "node_modules"]);

/** `--state-*` is reserved for Ripple nodes/counters and the Verifier Badge. */
const STATE_COLOR_ALLOWLIST = new Set([
  "components/RippleGraph.tsx",
  "components/RippleCounters.tsx",
  "components/VerifierBadge.tsx",
]);

/**
 * The Shelf screen (2026-07-25 redesign) deliberately supersedes the sharp-
 * corner rule from DESIGN.md §4 — rounded cards/nav pills are the brief for
 * that screen specifically, not a lapse. Everything else in the app still
 * answers to radius-discipline; this allowlist is intentionally narrow.
 */
const ROUNDED_ALLOWLIST = new Set([
  "components/Sidebar.tsx",
  "components/StoryCard.tsx",
  "screens/Shelf.tsx",
]);

const RULES = [
  {
    id: "radius-discipline",
    // rounded-none / rounded-full / rounded-[2px] are the only legal radii.
    pattern: /\brounded-(sm|md|lg|xl|2xl|3xl|4xl)\b/g,
    message:
      "DESIGN.md §4: square corners only. Use rounded-none, rounded-[2px] (buttons/inputs) or rounded-full (ripple nodes, portraits).",
  },
  {
    id: "no-gradients",
    pattern: /\bbg-gradient-|\bbg-linear-|\bfrom-\[|\bvia-\w/g,
    message:
      "FRONTEND_TECH_STACK.md §2: no gradient backgrounds. The cover scrim is an SVG linearGradient, not a utility class.",
  },
  {
    id: "no-glassmorphism",
    pattern: /\bbackdrop-blur\b|\bbackdrop-blur-/g,
    message: "FRONTEND_TECH_STACK.md §2: no glassmorphism.",
  },
  {
    id: "one-shadow",
    pattern: /\bshadow-(sm|md|lg|xl|2xl|inner)\b/g,
    message:
      "DESIGN.md §4: exactly one shadow exists (--shadow-lift), and only on the paper panel.",
  },
  {
    id: "no-emoji-icons",
    // Lucide only. The arrow glyph in CanonButton is punctuation, not an icon.
    pattern: /[\u{1F300}-\u{1FAFF}\u{2700}-\u{27BF}]/gu,
    message: "FRONTEND_TECH_STACK.md §2: emoji are never functional icons — use Lucide.",
  },
];

/**
 * Blank out comment bodies while preserving length and line breaks, so the
 * rules below match real code and not prose describing the rules. Positions
 * stay valid, so reported line numbers still point at the right place.
 */
function stripComments(source, ext) {
  const blank = (text) => text.replace(/[^\n]/g, " ");

  let out = source.replace(/\/\*[\s\S]*?\*\//g, blank);
  if (ext === ".ts" || ext === ".tsx") {
    out = out.replace(/\/\/[^\n]*/g, blank);
  }
  return out;
}

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry)) out.push(...walk(full));
    } else if ([".ts", ".tsx", ".css"].includes(extname(entry))) {
      out.push(full);
    }
  }
  return out;
}

const violations = [];

for (const file of walk(SRC)) {
  const rel = relative(SRC, file).replaceAll("\\", "/");
  // Tests describe violations in prose; they don't render them.
  if (rel.endsWith(".test.ts") || rel.endsWith(".test.tsx")) continue;

  const source = stripComments(readFileSync(file, "utf8"), extname(file));
  const lines = source.split("\n");

  for (const rule of RULES) {
    if (rule.id === "radius-discipline" && ROUNDED_ALLOWLIST.has(rel)) continue;

    lines.forEach((line, i) => {
      for (const match of line.matchAll(rule.pattern)) {
        violations.push({ rel, line: i + 1, rule: rule.id, match: match[0], message: rule.message });
      }
    });
  }

  // globals.css defines the state tokens; that is where they are supposed to live.
  if (!STATE_COLOR_ALLOWLIST.has(rel) && rel !== "app/globals.css") {
    lines.forEach((line, i) => {
      for (const match of line.matchAll(/\b(?:text|bg|border|fill|stroke)-state-(invalid|hold|new)\b/g)) {
        violations.push({
          rel,
          line: i + 1,
          rule: "reserved-state-colors",
          match: match[0],
          message:
            "DESIGN.md §2: --state-* may only appear on Ripple Map nodes/counters and the Verifier Badge.",
        });
      }
    });
  }
}

if (violations.length === 0) {
  console.log("✓ design gate: no violations");
  process.exit(0);
}

console.error(`✗ design gate: ${violations.length} violation(s)\n`);
for (const v of violations) {
  console.error(`  ${v.rel}:${v.line}  [${v.rule}]  "${v.match}"`);
  console.error(`      ${v.message}\n`);
}
process.exit(1);

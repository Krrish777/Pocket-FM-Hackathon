# AGENTS.md — Story Engine (Pocket FM Hackathon)

> **Mirror of `CLAUDE.md`** for non-Claude coding agents (Cursor, Copilot, …). Keep the two in sync —
> if you edit one, edit the other. This is a map, not a manual; detailed rules live in on-demand topic
> docs (see *Topic Docs*).

## Project Overview
AI-powered **generative storytelling engine** (Python 3.12+, hexagonal architecture): writes/adapts/
extends serialized stories, episode generators, interactive plots. LLM at the edges, pure domain core.
- **Problem statement: `TODO`** — the exact hackathon brief is not yet known. Do **not** build features
  on a vague requirement; capture the brief here first, then seed `feature_list.json`.

## Quick Start / Verification
```bash
make setup     # create env + install deps (uv)
./init.sh      # session startup: env check + start dev + quick E2E smoke
make test      # pytest
make check     # FULL gate: ruff check + ruff format --check + mypy + pytest  ← "done" means this passes
```

## Hard Constraints (red lines — never cross)
1. Type-hint every public signature — `list[str]`, `X | None` (never `Optional`/`List`).
2. No bare `except:` / no silent `except: pass` — catch specific, fail loud.
3. No hardcoded secrets — `pydantic-settings` + gitignored `.env` (`SecretStr` for keys).
4. Prompts are versioned assets in `prompts/`, never string literals in code.
5. All LLM calls go through ONE client wrapper — log tokens/cost, always set `max_tokens`.
6. Tests assert schema/invariants (Pydantic), never exact generated text; mock the LLM in unit tests.
7. `src/` layout; vendor SDKs only in `adapters/outbound/` — never in `domain/`/`services/`.
8. Run `make check` before calling anything done. Never `git commit`/push without maintainer permission.

## Session Lifecycle (harness loop — MUST follow)
### Clock in (at session start)
1. `pwd` — confirm working directory.
2. Read **`session_handoff.md`** (last clock-out), **`PROGRESS.md`** (durable state), **`DECISIONS.md`** (why).
3. Read **`feature_list.json`** → pick the single highest-priority feature (`not_started`/`active`). **WIP = 1.**
4. Run `make check` (or `./init.sh`) to confirm the repo is consistent before changing anything.

### Clock out (at session end)
1. Run `make check` — build + all tests pass. **Definition of Done = end-to-end verification passes, not
   "code is written."**
2. Update state: flip a `feature_list.json` entry to `passing` **only** when its `verification` command
   passes; update `PROGRESS.md` (Completed / In Progress / Known Issues / Next Steps) and write
   `session_handoff.md` (what I did / state / next step / how to resume).
3. **Session Exit Checklist:** no debug code/TODOs left · feature list updated · startup path intact · build & tests green.
4. Stage a clean checkpoint and **ask** before committing (never commit without permission).

## Feature List Rules
- `feature_list.json` is the single source of truth for "what needs doing" (JSON so it isn't casually rewritten).
- Every feature is a triple **`{description, verification, passes}`**, initialized `passes:false` — earn each pass.
- **One feature active at a time.** Don't hand-edit `passes` — a passing `verification` command flips it.

## Working Rules
- **WIP = 1**; finish (verified) before starting the next. No "refactor while we're at it" before core passes.
- **Confidence is not evidence** — only a runnable check proves done.
- **Knowledge lives next to code** — put a rule in a topic doc or beside the module it governs, not in this file.
- Every rule carries *source / when-it-applies / when-to-remove*; audit and delete decayed rules.
- **`temp/` is the agent scratchpad** (gitignored) — draft, stage scratch scripts, and keep working notes there; never commit it. Keep `.claude/` for config the agent *uses*; research/provenance lives in top-level `research/`.

## Topic Docs (reveal on demand — read the relevant one before editing)
- Conventions live in `.claude/rules/` — **auto-loaded by file type** (`paths:` frontmatter); `structure.md` is always-on. On-demand deep-dive: `/python-conventions` skill.
- Python → `.claude/rules/python-style.md` + `.claude/rules/python-design.md`; persistence → `.claude/rules/persistence.md`
- Folder layout / architecture → `.claude/rules/structure.md`; LLM/prompts → `.claude/rules/llm-storytelling.md` + `.claude/rules/prompts.md`; testing → `.claude/rules/testing.md`
- External dependency docs to consult (upstream `llms.txt` per tech-stack item) → `reference/llms.txt`
- Research provenance (what the rules were distilled FROM) → `research/README.md`
- Harness methodology → `Harness-Engineering/Harness-Engineering-Hub.md`

## State Files (the session-handoff system)
| File | Role | Written |
|---|---|---|
| `BACKLOG.md` | Human-readable ordered task queue (feeds `feature_list.json`) | as work is planned |
| `feature_list.json` | Machine SSOT of features + verification + pass-state | flipped by verification only |
| `PROGRESS.md` | Durable cumulative state (current/completed/next) | before session end |
| `DECISIONS.md` | Decision log (what / why / rejected alternatives) | when a decision is made |
| `session_handoff.md` | The single per-session clock-out note | at session end |

# Session Handoff

> The single per-session **clock-out** note. Overwrite at the end of each session. At session start, read
> this first, then `PROGRESS.md` and `DECISIONS.md`. Keep it short.

## Last session — 2026-07-24 (session 4, harness restructure → native `.claude/rules/`)

**Framing:** Still pre-event (brief drops **2026-07-25**, theme = Generative Storytelling). User-led review that
questioned whether our conventions were organized the way real Claude-Code projects do it. Evidence-backed
answer: **no — the delivery was over-engineered.** This session executed a full restructure onto Claude Code's
**native `.claude/rules/`**. `make check` stayed GREEN throughout.

**What I did (verified; tracked via task list #1–#8):**
- **Research first (4 agents):** (1) conventions structure — verdict "over-engineered; use native
  `.claude/rules/` with `paths:`, delete the routing hook, drop the speculative frontend tree"; (2) Opus-4.8
  prompt-engineering rule draft; (3) `research/`-reorg + `reference/`-hub design; (4) verified the exact
  `.claude/rules/` format (`paths:` YAML list — NOT Cursor's `globs:`; no-frontmatter = always-on).
- **Migration → `.claude/rules/` (7 rules):** `python-style`, `python-design` (`**/*.py`), `persistence`
  (`**/persistence/**`), `structure` (always-on), `llm-storytelling` (`src/**`,`prompts/**`), `prompts`
  (`prompts/**`), `testing` (`tests/**`,`evals/**`). Deleted `.claude/conventions/` (22 files), the
  `conventions-reminder.mjs` hook + its settings.json registration, the `frontend-conventions` skill. Kept +
  repointed the `python-conventions` skill. Preserved the untracked frontend draft →
  `temp/frontend-conventions-draft/`. Repointed all inbound refs (CLAUDE.md, AGENTS.md, README, prompts/README,
  pyproject, 11 `src/` docstrings).
- **Testing = two tiers:** pytest (code) + DeepEval (LLM quality) — in `.claude/rules/testing.md` + memory.
  Scaffolded `evals/metrics/metrics.py` (skill template) + `evals/README.md`. `deepeval` NOT installed; real
  datasets BLOCKED until the brief.
- **research/ reorganized** by domain (`python`/`structure`/`llm`/`persistence`/`frontend`) + `research/README.md`;
  `research/llms.txt` kept as the external source index. **New `reference/llms.txt`** hub — upstream deps'
  `llms.txt` links (Pydantic/uv/ruff/Claude have them; FastAPI/Typer/SQLModel/pytest/mypy don't). Both wired into
  CLAUDE.md/AGENTS.md (research = learned-from, reference = go-read).

**State:** `make check` **GREEN** (ruff + ruff-format + mypy 45 files + pytest 7). **Nothing committed** — all
changes staged for review, awaiting the user's commit decision (never commit without permission).

**Next step / how to resume:**
1. Get the user's OK to **commit** this restructure (staged, uncommitted).
2. Optional: eyeball the 7 rules in `.claude/rules/` + the parked `temp/frontend-conventions-draft/`.
3. INIT-01 still **blocked on the brief** (drops tomorrow) — capture it in CLAUDE.md at the event.
4. When unblocked: add `deepeval` dep + generate goldens; close the E2E gap (deterministic offline LLM); persist
   `StoryBible` in SQLite.

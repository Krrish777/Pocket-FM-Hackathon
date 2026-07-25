# Decision Log

> What was decided, why, and what was rejected. Append-only. Written when a design decision is made;
> read at session start. (Format from Harness-Engineering-State-Persistence.)
>
> **Path note (session 4):** entries below dated before session 4 reference `.claude/docs/conventions/` or
> `.claude/conventions/` — both **historical**. Conventions now live in **`.claude/rules/`** (see the
> session-4 entry at the end). Old paths are kept as-written for accurate provenance, not as live links.

## 2026-07-24: Conventions as a modular, research-backed doc system (not a monolith)
- **Reason:** Extensible to future domains (API, git, security); avoids the giant-instruction-file trap.
- **Rejected:** A single `python.md` — would rot and not scale.
- **Shape:** One folder per domain, one file per topic, under `.claude/docs/conventions/`; every rule cited
  in `_research/`.

## 2026-07-24: Conventions live under `.claude/docs/` (not repo-root `docs/`)
- **Reason:** User preference — keep project-related docs together under `.claude/`.
- **Trade-off accepted:** Slightly less discoverable to non-Claude agents; mitigated by `AGENTS.md` pointing in.
- **⚠️ SUPERSEDED 2026-07-24 (session 3)** — see the reversal entry below.

## 2026-07-24 (session 3): Conventions moved `.claude/docs/conventions/` → `.claude/conventions/`
- **Reason:** User: coding conventions are **not "docs"** — living under a `docs/` subfolder mislabels them.
  Moving up one level to `.claude/conventions/` drops the wrong label while keeping the earlier "keep project
  config under `.claude/`" preference intact (so this reconciles, not fully reverses, the entry above).
- **Rejected:** top-level `conventions/` (scatters agent config outside `.claude/`, larger reference churn);
  folding conventions into the `*-conventions` skills (loses the always-portable plain-doc form + the
  PreToolUse hook that injects them on every `.py` edit).
- **Blast radius:** 29 files repatched (`.claude/docs/conventions` → `.claude/conventions`, and the bare
  `docs/conventions` provenance refs in `research/`). `.claude/docs/` removed (was empty). This DECISIONS.md
  history above is left as-written (append-only); its old paths are historical, not live links.

## 2026-07-24: Delivery is layered — docs + skill + warn-only hook + AGENTS/CLAUDE pointers
- **Reason:** Only a hook fires on every `.py` edit; only a doc is portable; only a skill gives on-demand depth.
- **Rejected:** Skill-only (not guaranteed to load) and CLAUDE.md-only (bloats context, "lost in the middle").
- **Constraint:** Hooks are **warn-only** (inject context, never block); hook lives on PreToolUse (SessionStart
  is already claimed by the global `remember`/`context-mode` hooks).

## 2026-07-24: Tooling stack = uv + Ruff + Black/ruff-format + mypy (strict-ish) + pytest
- **Reason:** Modern 2025 default; fastest agent ergonomics; single-tool lint/format.
- **Docstrings:** Google style. **Typing:** strict-ish mypy.

## 2026-07-24: Hexagonal (ports & adapters) architecture, `src/` layout
- **Reason:** Swap LLM provider / bump prompts without touching the pure story core; unit-test offline.
- **Constraint:** Vendor SDKs only in `adapters/outbound/`; `domain/`/`services/` import nothing external.

## 2026-07-24: Harness entry file = thin router; `CLAUDE.md` mirrored to `AGENTS.md`
- **Reason:** Instruction-File-Trap — keep the entry file ≤200 lines (overview, quick start, red lines, lifecycle,
  topic-doc map). Teammates may use non-Claude agents, so the two files are kept identical.
- **Rejected:** Restating all conventions in `CLAUDE.md`.

## 2026-07-24: Renamed `DECESION.md` → `DECISIONS.md`
- **Reason:** Match the methodology's clock-in routine (reads `DECISIONS.md`); file was empty. Reversible.

## 2026-07-24: Research lives in top-level `research/`, NOT `.claude/`
- **Reason:** Keep `.claude/` for config the agent *uses* (conventions, skills, hooks); raw cited research
  dumps were bloating it. `research/` holds the artifacts + `llms.txt` source index; conventions link to it.
- **Rejected:** Keeping `_research/` under `.claude/docs/conventions/`.

## 2026-07-24: `temp/` is the agent scratchpad
- **Reason:** User-designated gitignored working area for drafts/scratch scripts. Documented in CLAUDE.md/AGENTS.md.

## 2026-07-24: Cross-cutting code goes in `shared/` (focused modules), not a `utils.py`
- **Reason:** Research is unanimous the catch-all `utils.py` is the "dunghill" anti-pattern. `shared/errors.py`,
  `shared/text.py`, `shared/retry.py` are named/focused; logging lives in `observability/logging.py`.
- **Note:** Errors placed in `shared/errors.py` (HTTP-agnostic) per the user's "one folder for error+util" ask;
  an equally valid alternative is `domain/errors.py`.

## 2026-07-24: Memory = three ports, canon kept deterministic
- **Reason:** Serialized continuity needs authoritative canon (bible/character/threads) separate from fuzzy
  recall. Ports: `StoryBibleRepositoryPort` (canonical), `EpisodeLogRepositoryPort` (append-only episodic),
  `LoreRetrieverPort` (associative/RAG). `CharacterStatus` uses SCORE absorbing states.
- **Rejected:** One god `MemoryPort`; letting mem0's auto-consolidation write canon (heuristic, unsafe for canon).
- **mem0** (installed) is for the associative lane only, in an outbound adapter.

## 2026-07-24: Inbound adapters — FastAPI + Typer; deps added
- **Reason:** User wants both API and CLI. Typer chosen over Click/argparse (type-hint-native, built on Click).
  Added `fastapi`, `uvicorn[standard]`, `typer` to deps; `[project.scripts] story-engine`. Composition root =
  `bootstrap.py` (only module importing outbound adapters). Removed root `main.py` (uv leftover).

## 2026-07-24: Frontend convention domain seeded (future, TS/Next)
- **Reason:** Team will add a Next.js frontend. Modeled on `next-shadcn-dashboard-starter` research → a
  `frontend` domain (7 topic docs + CLAUDE template) marked 🔵 Future, plus a `frontend-conventions` skill.
  Aesthetics deferred to the global `frontend-design` skill (no duplication).

## 2026-07-24: `.claude` config fixes from strict evaluation
- Hook command placeholder → `${CLAUDE_PROJECT_DIR}` (documented form). SessionStart hooks confirmed to STACK
  with global plugin hooks (empirical: remember banner + our clock-in both fired).

## 2026-07-24 (session 2): Harness-hardening pre-event decisions
- **Context:** Real hackathon problem statement drops at the event 2026-07-25; theme (fixed) = Generative
  Storytelling. Today's goal = harden the harness so we code fast tomorrow, NOT build product features.
- **LLM/agent framework DEFERRED to the event.** We will pick LangChain / LangGraph / CrewAI / Pydantic-AI /
  raw SDK based on the brief and what the organizers provide (they supply OpenAI credit). So **no LLM adapter
  or agent wiring built today** — that would be guessing. `StubLLM` stays until then.
- **Dev tools → PEP 735 `[dependency-groups]`** (was a `[project.optional-dependencies]` extra `uv sync`
  skipped). Now plain `uv sync` (= `make setup`) installs ruff/mypy/pytest, so `make check` runs from scratch.
- **`StrEnum`** for all domain enums (was `(str, Enum)`); renders cleaner in LLM/JSON I/O (UP042).
- **Persistence = SQLModel on local SQLite** (not Postgres). Skip Docker/Alembic for the hackathon. Other /
  memory DBs (mem0, vector) deferred. SQLite adapter implements existing repository ports (hexagon preserved:
  SQLModel tables are a persistence detail in `adapters/outbound/`, domain models stay pure Pydantic).
- **Extraction source = tiangolo `full-stack-fastapi-template`.** Adopt its config/app-factory/router/DI
  patterns; DROP its auth/JWT/email/Sentry/Postgres/Docker baggage.

## 2026-07-24 (session 2): Skill discovery via `find-skills` + evaluation matrix
- **Installed the `find-skills` meta-skill** (from `Kiranism/next-shadcn-dashboard-starter/.claude/skills`)
  into `~/.claude/skills/`. It drives `npx skills find <query>` against the skills.sh registry.
- **Evaluation matrix (must ALL hold before installing):** install count (≥1K good, <100 skeptical) ·
  source reputation (official orgs ≫ unknown; GitHub stars) · not old · not duplicated · on-target (READ the
  SKILL.md — a "pydantic" skill that is really Pydantic-AI does not match a Pydantic-modeling need) · beats
  our own `.claude/docs/conventions/`. Standing policy for future stack growth.
- **ADOPTED: `fastapi/fastapi@fastapi`** (official FastAPI, 100.8K★, 6.1K installs, passes 3 security audits,
  covers DI/response-modeling/Pydantic/SQLModel/uv/Ruff). Verified by reading the installed SKILL.md +
  6 reference docs — real content, not a stub. Installed globally.
- **DEFERRED: official `pydantic/skills@*`** — they are Pydantic-AI + Logfire, NOT Pydantic-v2 modeling.
  Only adopt if we choose Pydantic AI as tomorrow's framework.
- **REJECTED (build our own instead):** `sqlmodel` (top hit 144 installs, unknown author), `pytest`
  (`github/awesome-copilot@pytest-coverage` 11.9K but Copilot/coverage-narrow — our conventions cover it),
  `sqlalchemy` (`wispbit-ai@…alembic…` 1.4K — Alembic-focused; we use SQLModel+SQLite, no migrations).
- **Decision:** author our OWN local skills (sqlmodel folding SQLAlchemy essentials; pytest; thin pydantic
  pointer) modeled on the FastAPI skill's structure — NOT a separate sqlalchemy skill (would duplicate).

## 2026-07-24 (session 4): Conventions migrated `.claude/conventions/` → native `.claude/rules/` (path-scoped)
- **Reason:** User questioned whether our 22-file numbered "database" matched how real Claude-Code projects
  organize conventions. Research (Anthropic docs + 85 real repos using `.claude/rules/`) confirmed: the
  *philosophy* (short CLAUDE.md → topic files → load on demand) was right, but the *machinery* was
  over-engineered — a hand-rolled PreToolUse routing hook reinvented Claude Code's native `.claude/rules/` with
  `paths:` frontmatter, and the 22 files were reachable only via prose links (the ONE channel Claude Code never
  auto-loads, so nothing loaded automatically). Verified the exact format (`paths:` YAML list — NOT Cursor's
  `globs:`; no-frontmatter = always-on) from the docs before writing.
- **Shape:** 7 rules in `.claude/rules/` — `python-style` + `python-design` (`paths: **/*.py`), `persistence`
  (`**/persistence/**`), `structure` (always-on), `llm-storytelling` (`src/**`,`prompts/**`), `prompts`
  (`prompts/**`; Opus-4.8 prompt-engineering), `testing` (`tests/**`,`evals/**`; two-tier). Rules now auto-inject
  when a matching file is edited — no voluntary hops.
- **Deleted:** the PreToolUse `conventions-reminder.mjs` hook + its settings.json registration (replaced by
  `paths:` scoping); the speculative `frontend/` convention tree (no app exists — violated WIP=1) — PRESERVED to
  `temp/frontend-conventions-draft/` (it was untracked, so delete was irreversible); the `frontend-conventions`
  skill. KEPT one `python-conventions` skill (repointed to `.claude/rules/`).
- **Rejected:** collapsing to one `python.md` (kept the style/design split); jamming persistence/prompts into
  other rules to hit a "~5 files" count (merging-to-a-number is its own anti-pattern).
- **Supersedes** the three 2026-07-24 entries above (conventions doc-system; layered docs+skill+hook delivery;
  frontend domain seed) and REVIEW-02's `.claude/conventions/` relocation. History left append-only.

## 2026-07-24 (session 4): Two testing tiers — pytest (code) + DeepEval (LLM quality)
- **Reason:** An LLM storytelling product can pass code tests yet produce bad stories. Split verification:
  pytest = code correctness (the existing L1/L2/L3 hierarchy); DeepEval = generated-output quality (`evals/`).
- **Constraint:** goldens must be GENERATED (`deepeval generate`, target 30–50), never hand-fabricated (skill
  mandate). Real dataset creation BLOCKED until the brief defines engine I/O + a deterministic offline LLM path
  exists (`StubLLM` raises). Scaffolded `evals/metrics/metrics.py` (from the skill template) + `evals/README.md`
  only; `deepeval` is NOT yet a dep (add under an eval group when unblocked). Evals stay OUT of `make check`.

## 2026-07-24 (session 4): Two indexes — `research/` (learned-from) vs `reference/` (go-read)
- **Reason:** `research/` reorganized by domain (`python`/`structure`/`llm`/`persistence`/`frontend`) to scale as
  it grows + a `research/README.md` map; a new root **`reference/llms.txt`** hub collects upstream dependencies'
  published `llms.txt` (**link, don't vendor**). Distinct direction/lifecycle — both wired into CLAUDE.md/AGENTS.md.
- **Rejected:** vendoring upstream docs (staleness + repo bloat); a README per research subfolder (kept one index).

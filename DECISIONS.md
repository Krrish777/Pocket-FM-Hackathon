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

## 2026-07-25 (session 5): Installed the Databricks AI Dev Kit, scoped to Claude Code only
- **Reason:** User confirmed a real Databricks workspace they intend to use for the hackathon, and asked for the
  full kit (`--skills-profile all`). Provides the `databricks` MCP server (50+ tools), `databricks-tools-core`,
  and 34 skills (Databricks + MLflow + agent-evaluation).
- **Shape:** installed via `install.ps1 --tools claude --skills-profile all --silent`. Global runtime lives in
  `~/.ai-dev-kit/` (own venv) — **zero new deps in `pyproject.toml`**, so the hexagon is untouched. Project-local
  artifacts: `.claude/skills/` (34 dirs), `.mcp.json`, `.ai-dev-kit/` state.
- **Scoped to `--tools claude`** deliberately: the default writes skill dirs for 8 editors
  (`.cursor/ .github/ .agents/ .gemini/ .windsurf/ .opencode/ .kiro/`). `.agents/` already holds our vendored
  deepeval scaffolding, and we only use Claude Code. Result: `.claude/settings.json` (SessionStart clock-in hook)
  and `.claude/rules/` were **not modified** — verified via `git status`.
- **`make check` fallout:** `ruff check .` linted the vendored skill scripts (78 errors). Fixed by extending the
  existing exclusion — `extend-exclude = [".agents", ".claude/skills"]` — same rationale as `.agents/`
  (vendored, not our code). `make check` GREEN after: ruff + format (146 files) + mypy (45) + 7 tests.
- **Gitignored** `.ai-dev-kit/` and `.mcp.json`: the MCP config hardcodes absolute paths into
  `C:/Users/777kr/.ai-dev-kit/.venv`, so it is machine-local, not portable. Repro command is in `.gitignore`.
- **Rejected:** `databricks aitools install` (built into CLI v1.9.0, sources `databricks/databricks-agent-skills`)
  — it ships skills+plugin only, no MCP server, and the dev kit is a superset that already pulls that repo in;
  running both would double-install the same skills. **Watch item:** the dev-kit installer prints a deprecation
  notice — a future release will delegate skill installation to `databricks aitools`. Revisit then.

---

## 2026-07-25 (session 5): Problem statement selected and narrowed — INIT-01 closed

> Full reasoning, all 13 decisions with rejected alternatives, and the mid-session corrections live in
> **`docs/2026-07-25-product-definition-session.md`**. The product spec itself is **`project_context.md`**
> (single source of truth; it declares its own supersessions in §12). Summarised here for the decision log.

- **The brief is a menu, not a statement.** The official brief lists ~40 statements across 6 tracks
  (P1-P6), so "capture the problem statement" was really a *selection + narrowing* decision. Selected:
  **P1 Story Time Machine** (primary) + **P1 Infinite Story Universe** (secondary, now SHOULD-tier).
- **Root problem = participation, not continuity.** User's framing: serialized fiction is passive by
  construction. Continuity is the enabling constraint, not the problem. **Rejected:** the vault's
  continuity-first framing — it produces a developer tool, not a product.
- **Fan-fiction is the branch oracle** (the load-bearing idea). Interactive fiction has failed exactly
  twice: hand-authored branches are coherent but the authoring cost explodes combinatorially
  (Until Dawn/Bandersnatch); generated branches are affordable but incoherent (AI Dungeon, ~1.5M->350K).
  Fan-fiction is a third path — branches pre-authored by the crowd, free, audience-filtered, and dense at
  exactly the emotionally significant moments. The AI's job becomes *selection and enforcement*, not invention.
- **Hero interaction = playthrough, not a single flip.** Up to 10 compounding choices (ceiling 10,
  rehearsed run >= 5). **Rejected:** the friend-authored PRD's flip-one-decision loop — a diff viewer
  cannot demonstrate compounding, which is the actual claim.
- **Primary user = the Player; creator is a slide.** ⚠ This **overrides** `_PROBLEM VERDICT`'s bolded
  "build for the creator/producer, not the passive listener." Its evidence is not disputed; the artifact is
  judged on demonstrated concept, not revenue proximity. Recorded explicitly so it is not mistaken for an oversight.
- **Corpus = the Dexter novels.** Ordinary reasons: real prose (genuine provenance), novels have endings
  (a known destination makes branch outcomes measurable), deep first-person interiority, dense fan-fic coverage.
  **Decisive reason:** the series' central engine *is* who-knows-what, which makes per-character epistemic
  state — the hardest thing we build — the thing the audience is already watching. **Rejected:** public-domain
  corpus (`PRD-KNOWLEDGE-BASE` A-4, on legal grounds now moot); an original story (no familiarity, small fact
  base); Avengers as a literal corpus (films are not text, so the fact base would be fabricated — this objection
  was independent of the legal one, which the user correctly waived for a hackathon artifact).
- **Per-character epistemic state is a MUST**, in the data model from day one. Retrofitting "who witnessed
  this" onto already-extracted facts means re-extracting everything.
- **Reaction architecture: uniform data model + single narration call per turn.** State transitions are
  deterministic in code; one LLM call renders the scene from the acting character's filtered view.
  **Key rationale:** the epistemic guarantee comes from *what is absent from the assembled context*, not from
  instructing a model to withhold — a fact never placed in the prompt cannot leak. This is simultaneously
  ~6x cheaper and structurally stronger than one-agent-per-character. **Rejected:** all-canon-plus-rules in one
  prompt (leaks invisibly); per-character agents (preserved as an upgrade path — it is a *runtime* change
  requiring no data migration).
- **Protagonist-ness is a rendering choice, not a stored property.** No PC/NPC asymmetry anywhere in storage;
  character state never stored as narrative text; the renderer takes a character as a parameter. This makes
  *Infinite Story Universe* nearly free and unlocks the closing demo beat: replay the same branch as Debra,
  who visibly does not know what the audience just watched happen — proving both headline claims at once.
- **Bounded choices now, free-form later.** 2-4 discrete options; no free text this build. Bounded choices can
  be validated *before* being shown; free text forces generate-then-verify, where failures are visible on stage.
- **Open, carried forward:** OD-1 fork-vs-tier (recommend **fork**; tier mislabels every deliberate divergence
  as an error), OD-2 novel-vs-screen canon mismatch (silent corruption path — decide, don't discover),
  OD-3 EXT-1 scraper contract (highest-risk unknown), OD-4 sparse fan-fic coverage, OD-5 product name, OD-6 rubric.

## 2026-07-25 (session 5): `.claude/worktrees/` excluded from ruff

- **Reason:** parallel sessions run in git worktrees under `.claude/worktrees/`. Those are separate checkouts
  that run their own `make check`; linting them from the parent double-lints and makes **our** gate fail on
  **their** in-progress code (this session: RUF001 in `reddit-fanfic-scraper`).
- **Shape:** `extend-exclude = [".agents", ".claude/skills", ".claude/worktrees"]` — same rationale and pattern
  as the two existing exclusions.
- **Rejected:** fixing the violation in the other session's worktree (not our code, and it would recur on every
  edit they make).
## 2026-07-25 (session 6): Work split across two parallel sessions; KB lives in a worktree
- **Reason:** The KB component spec and the product/problem-statement decisions were interleaving and blocking
  each other. Split them: **this branch owns the Knowledge Base component only**; a parallel session in the main
  directory owns the product track (which problem statement, who the buyer is, corpus, fan-fiction semantics).
- **Shape:** git worktree `.claude/worktrees/knowledge-base`, branch `worktree-knowledge-base`, so the two
  sessions never contend for the working directory.
- **Seeding note:** a worktree starts from the last commit, so `PRD-KNOWLEDGE-BASE.md` (untracked) and main's
  three uncommitted edits (`DECISIONS.md`, `.gitignore`, `pyproject.toml`) were copied across. Without this, a
  later merge would have looked like it was reverting the session-5 Databricks entry.
- **Rejected:** a plain in-place branch — with two live sessions in one directory, branch switching would
  corrupt whichever session wasn't looking.

## 2026-07-25 (session 6): The novelty claim is falsified — reposition from representation to ENFORCEMENT
- **Finding:** [Narrative World Model, arXiv 2607.05577](https://arxiv.org/abs/2607.05577) (submitted
  2026-07-06) is authored **entirely by PocketFM**, including **Vasu Sharma, their Head of AI** — one of the
  named executives behind this hackathon. The vault cited this paper five times without noticing the
  affiliation.
- **Consequence:** NWM already implements all three capabilities `Knowledge-Base/10 - Comparison vs Existing
  Systems` claimed nobody had — character knowledge/unknowns (epistemic scope), plot/promise threads with
  open/closed status and payoff (commitment lifecycle), and a retrieval "causal restriction" to chapters ≤
  checkpoint (chapter-safe/spoiler-safe retrieval). **The sentence "not one row above the Kernel carries a
  single ✅ in those three columns" is false**, and it was the load-bearing sentence of the novelty argument.
- **What survives, from NWM's own limitations section:** *no generation-time enforcement, no verifier,
  conditioned generation remains future work*; English-only; the production backend and internal corpus are
  proprietary; no public code (only a Project Gutenberg benchmark is released).
- **Decision:** reposition. NWM answers questions about **finished** text; the Canon Kernel governs text
  **being written**. Cite NWM as validation — it is far stronger evidence than any of the 24 papers in the
  vault — and quote its limitations as the gap. Adopt its 7 record types rather than re-deriving our own.
- **Rejected:** ignoring it (a judge from their own AI team would raise it first); claiming novelty on
  representation (false, and checkable in one search).

## 2026-07-25 (session 6): The KB operates a CLOSED LOOP, not read-only memory
- **Reason:** follows directly from the entry above — enforcement is the unclaimed half. The KB owns write,
  read, **and check**: assemble scoped canon → generator drafts → verify draft against canon → flag with a
  provenance citation → commit new facts.
- **Consequence:** a larger component boundary than a memory store. The verifier is IN the Knowledge Base,
  not a sibling that consumes it.
- **Rejected:** read-only memory (that is NWM, already built, by them, better).

## 2026-07-25 (session 6): Facts are TRI-temporal — story time, telling time, record time
- **Reason:** two axes cannot express *"true in the world, but the audience has not learned it yet"*, which is
  the entire basis of the spoiler guard. Story time (`valid_from`/`valid_to`) answers "who was alive at
  episode 40"; telling time (`revealed_at`) powers the guard; record time (`recorded_at`/`superseded_at`)
  makes retcons auditable instead of corrupting.
- **Precedent:** NWM separates event order from reveal order; Fowler's bitemporal history supplies record time.
  No single source presents all three together — ⚠ the combination is our synthesis.
- **Rejected:** single timestamp (loses history); bitemporal only (loses telling time, so no spoiler guard).

## 2026-07-25 (session 6): `revealed_at` is populated BY CONSTRUCTION; the real bug is assertion mode
- **Reason (researched):** NWM's method is deflationary — the extractor reads chapter N's accepted prose and
  stamps every emitted record with `revealed_at = N` plus an evidence span. There is no reveal-order
  classifier anywhere in the literature. Redefining the field as *"the first chapter in which the text asserts
  this proposition on-page"* makes first-mention the **definition** rather than a heuristic.
- **Error asymmetry (the deciding argument):** `revealed_at` too LATE is harmless (a usable fact is withheld —
  invisible to the audience); too EARLY is the spoiler leak the feature exists to prevent. Only pay for
  failure modes that push early.
- **The three dangerous cases are one bug:** hearsay, a character lying, and dream/hypothetical content all
  push early because the extractor flattens an *attributed or non-actual* proposition into a bare world fact
  ("Marcus said the vault was empty" → `vault_empty = true`). **Fix is a schema change, not a temporal model:**
  add `assertion_mode: narrated | attributed | non_actual`, `attributed_to`, and `evidence_span`. Cost: three
  fields in one extraction prompt. Bonus: this is also what makes lies and dramatic irony *writable*.
- **Also adopted:** decompose to atomic propositions (handles partial reveals for free); layer a
  position-filtered raw-text retrieval under the fact-level guard so a KB miss cannot leak via raw context.
- **Declared out of scope (each pushes in the safe direction or costs more than it saves):** unreliable
  narration, implied-before-stated, reader-inference modelling.
- **Rejected:** building a reveal-order classifier; CFPG-style multi-verifier rubric filtering (that is
  dataset-curation cost at roughly 4 pairs per book recall).
- ⚠ **Carry forward:** no published work validates reveal-position extraction accuracy — NWM stores the field
  and benchmarks downstream QA but never checks the field itself. Hand-labelling ~50 facts across two chapters
  would give us more validation than the literature has.

## 2026-07-25 (session 6): Component PRD written before any KB code
- **Shape:** `PRD-KNOWLEDGE-BASE.md` — 28 sections; 16 functional + 9 non-functional requirements each with
  priority, rationale, dependencies, acceptance criteria and verification method; 7 numbered assumptions;
  6 open decisions routed to the parallel session; 6 milestones with a stated cut-line; a per-milestone test
  matrix across 10 test types; and an engineering-readiness verdict.
- **Method under unresolved ambiguity:** rather than guess, every open item is a labelled assumption with its
  blast radius, and the one place the schema genuinely forks (fan-fiction as fork vs. tier, OD-1) is specified
  in **both branches** so the parallel session's answer slots in without a rewrite.
- **Readiness verdict:** NOT READY overall; **READY for M0–M2**. The blocker is R-1 — extraction quality caps
  every downstream guarantee — and M1 exists specifically to measure it before anything is built on top.
- ⚠️ **R-1 was DOWNGRADED the same day** — see the extraction-architecture entry below.

## 2026-07-25 (session 6): A-5 resolved — knower_scope is populated by VISIBILITY ROUTES, not by inference
- **Reason (researched, 5 agents):** asking an LLM to track who-knows-what in context does not work and the
  numbers are unambiguous. [FANToM](https://arxiv.org/abs/2310.15421): GPT-4 answers *"does X know this?"* at
  90.3% but **cannot list the knower set (48.2%)**, and is self-consistent across framings only **26.6%** of
  the time. [ExploreToM](https://arxiv.org/abs/2412.12175): 9% on adversarially-found stories. Reasoning
  models do not fix it. What *does* work, across four independent lines (SymbolicToM +38pts, TimeToM +44.7%
  on FANToM, EnigmaToM, PDDL-Mind 80.0% vs 55.3% SOTA): **extract explicit state, then query it.**
- **Adopted mechanism — [REVERIEMEM](https://arxiv.org/abs/2606.25632)'s four visibility routes**, the only
  published existence proof: (1) direct experience, (2) observation/presence in scene, (3) organisational
  propagation, (4) world-level common knowledge. Plus a three-way scene roster —
  **present-active / present-silent / only-referenced** — because co-occurrence is not presence
  (Labatut & Bost's survey is explicit that bystanders and absent-mentions pollute co-occurrence graphs).
  Measured: KBF 73.3%, 68.1% on visible facts, **81.2% on correctly refusing invisible ones**; ablating the
  visibility layer collapses it to 17.8%.
- **Explicit knowledge-transfer events are an OVERRIDE, not the baseline.** Emit
  `KnowledgeTransfer{source, recipients[], fact_id, modality, veracity}` only where the text states or
  strongly implies it — high precision, low recall by design. Most of what a character knows was never the
  subject of a stated transfer, so explicit-only leaves knower sets nearly empty. But it is the only route
  that can carry a **lie**, which presence structurally cannot.
- **Also store NEGATIVE facts** (`X does not know Y`) — refusal is the cheaper and more reliable half.
- **Entity identity comes from a HUMAN-SUPPLIED ROSTER, not automatic coreference.**
  [BOOKCOREF](https://aclanthology.org/2025.acl-long.1197/): 67 CoNLL-F1 on full books vs 82 windowed, and
  "the Stranger = the King" is exactly the long-range deliberately-withheld case that fails. A canonical
  name + alias list turns open clustering into closed-set classification — **and becomes the `enum` for every
  entity field in the extraction schema, making hallucinated entities structurally impossible.** Highest-value
  single trick found.
- **Calibration to hold us honest:** realistic per-fact knower-set accuracy is **65–80%**. Addressee
  extraction — the primitive "who told whom" depends on — tops out at **73.58%** in the only paper that has
  measured it. Anyone claiming 95% is measuring only explicit named in-scene attributions, or not measuring.
- **Rejected:** presence-only (over-attributes bystanders, under-attributes offscreen relay, cannot represent
  lies); explicit-transfer-only (near-empty knower sets); LLM-in-context tracking (48.2%); symbolic planners
  — Sabre's `OBS(a,c)` computed-knower-set idea is worth stealing, but 4 characters / 61 fluents cost
  **6.2 hours / 105M nodes**, so steal the idea and not the machinery.

## 2026-07-25 (session 6): Extraction is PARALLEL per chapter, never chained — and R-1 is downgraded
- **Reason:** the natural design (extract chapter N conditioned on accumulated canon) is wrong on both axes.
  **Cost:** conditioning forfeits the Batch API (asynchronous, no ordering guarantee) *and* ~4.5× the input
  tokens ≈ **~9× the stateless-batched cost**. **Quality:** it is actively worse —
  [self-conditioning](https://arxiv.org/abs/2509.09677) (models err more when context holds their own prior
  errors, and it does not scale away); [multi-turn collapse](https://arxiv.org/abs/2505.06120) (−39% mean,
  but **+112% unreliability** — the mean hides it, so evaluate with repeated runs and variance);
  [BooookScore](https://arxiv.org/abs/2310.00785) measuring incremental < hierarchical across 100 books;
  [ATOM](https://arxiv.org/abs/2510.22590) getting **+33% run-to-run stability** from parallel atomic merge.
- **Shape:** extract each chapter independently against the fixed roster; reconcile in a merge tree. The only
  sequential step is cross-chapter knower propagation, done as a **deterministic graph operation over
  extracted records** — never as an LLM prompt containing prior state.
- **R-1 downgraded from Critical.** NWM re-ingested Graphiti *with their own extractor* and it barely moved
  (0.585 vs 0.574, **p=0.89**). The gap was representational, not extractive. M1's precision gate stays
  useful as calibration but is no longer the project's binding risk.
- ⚠️ **The typed ontology is NOT the differentiator either.** NWM's own ablations: stripping type labels
  scored 0.898 → **0.909** (p=0.62); flattening to prose → **0.926** (p=0.12). What carries the result is
  **atomic decomposition + query-conditioned retrieval** (serializing the same state as a dump scores 0.358
  vs 0.893 querying it, with 83% of misses being "present but past truncation"). Our PRD over-weights the
  schema; **retrieval is where the win is.** The schema still earns its place as the substrate that makes
  deterministic querying possible — it is just not the thing to pitch.
- **Two unclaimed measurement gaps, both cheap (<$5):** no public benchmark of per-fact knower sets over real
  prose; no drift-vs-chapter-count curve for narrative KB construction.

## 2026-07-25 (session 6): Standing commit permission scoped to the KB worktree branch
- **Reason:** subagent-driven development is built on commits — review packages are `git diff BASE..HEAD`
  over commit ranges, the ledger records SHAs, and post-compaction recovery trusts `git log`. The plan's
  no-commit stance made the machinery unusable.
- **Granted (user, 2026-07-25):** implementers may commit **on `worktree-knowledge-base` only**. `main` is
  never touched and nothing is pushed; the maintainer gates the merge instead of each commit.
- **Also ruled:** the plan's `# type: ignore[arg-type]` on the test-builder dict-merge stands as a deliberate
  choice; reviewers are told it is ruled, so the fix loop does not churn on it.

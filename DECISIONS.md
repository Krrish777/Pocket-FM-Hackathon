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

## 2026-07-25 (session 6): `knower_scope` is OPTIONAL — staged, not universal (reverses P3)
- **Reason:** the evidence does not support per-character tracking on every fact, and this reverses a stance
  the vault held on an unsourced claim. Counting the full 19-subtype taxonomy in
  [ConStory](https://arxiv.org/abs/2603.05890): **2 of 19 subtypes are epistemic** (Memory Contradictions,
  Knowledge Contradictions), 3 counting Forgotten Abilities generously — and **zero of 19** cover a premature
  reveal, spoiler, lie, or false belief. Those subtypes live in Characterization, which is **~3.5% of total
  measured error density**; factual and temporal dominate.
- **Storage was never the argument** (3,000 facts × 40 characters = ~24 KB as a bitmask). The real costs are
  **population** — [CHIRON](https://arxiv.org/abs/2406.10190) measured a **32.6% false-extraction rate** on
  character-knowledge statements — and **closure**, since "does C know F at chapter k" is honestly a
  reachability query. Sabre needed 6.2 hours / 105M nodes for 4 characters;
  [SymbolicToM](https://arxiv.org/abs/2306.00924) states memory is exponential in nesting depth.
- **The decisive asymmetry:** a noisy knower graph does not merely fail to catch errors — it produces
  **FALSE BLOCKS on legitimate dialogue**, corrupting generator output. Meanwhile ConStory-Checker, a plain
  LLM judge with no knowledge structure at all, scored **F1 0.742 / precision 0.960 on Character
  Consistency** — its best category, 3.2× professional-human recall.
- **Adopted (staged):** (1) `revealed_at` on EVERY fact — same cost as a boolean, strictly more power, and it
  is the spoiler guard; (2) `knower_scope` populated **only for typed secrets, lies and withheld
  information** — expect dozens to low hundreds in a 200-chapter serial, not thousands; (3) **no** nested
  beliefs, no epistemic closure engine, no belief-space planning. This is TADS/adv3Lite's shipped split —
  a global `<.reveal>` plus a targeted `<.inform>`.
- **Schema consequence:** `Fact.knower_scope` is `frozenset[str] | None`, default `None` = NOT TRACKED, and
  `is_known_by` returns True for untracked facts. An empty frozenset stays invalid — use `None` for untracked.
  The M0 plan was amended before Task 3 was dispatched.
- **Measure before building further:** run the plain checker first and measure our own epistemic error rate.
  If it already catches them, `knower_scope` buys only write-amplification.
- ⚠️ **Correction owed to the research vault (main directory — parallel session's file):**
  `Knowledge-Base/01 - Narrative Knowledge Taxonomy.md` claims a character acting on un-known information is
  "the single most common and immersion-breaking continuity error in AI fiction." **Unsourced and
  contradicted by the best available measurement.** `08 - First Principles.md` P3 ("knower-scope and
  provenance are mandatory columns") rests on it and should be softened to "mandatory for typed secrets,
  optional elsewhere." Provenance stays mandatory — that part is independently justified.
- ⚠️ **Two figures circulating in this space are likely fabricated** and must never be cited: an "Alliance of
  Independent Authors: 34% of one-star craft reviews cite plot holes" statistic, and a "BookBub
  review-language analysis." Both trace only to SEO content blogs.
- **Rejected:** universal `knower_scope` (this design, now reversed); dropping it entirely (it is the only
  route that can represent a lie, and secrets are the demo).

## 2026-07-25 (session 6): Three-layer hybrid — relational canon + thin graph + agent memory
- **User direction:** a three-part hybrid — a better database, a graph-based knowledge base, and agent
  memory — with the technology choices delegated ("I don't care about the texture, I care about the
  product"). Recommendation below accepted.

| Layer | Choice | Role |
|---|---|---|
| 1. Canon store | Delta table (Databricks) with DuckDB/SQLite local fallback | Tri-temporal fact rows = system of record. `VERSION AS OF` gives "canon as of episode N" free. |
| 2. Graph | **Graphiti** over the facts | Multi-hop traversal, relationship diffs, causal chains. **Deliberately thin.** |
| 3. Agent memory | Working-set / session layer | What the current session holds, distinct from what is true. Takeover state lives here. |

- **Graphiti over Neo4j, and NOT via Neo4j.** [Neo4j Community is GPLv3](https://github.com/neo4j/neo4j) —
  fine for a demo, a legal conversation for a product Pocket FM might ship. [Graphiti](https://github.com/getzep/graphiti)
  is Apache-2.0 and supplies the two semantics we would otherwise hand-roll: **bi-temporal edges** and
  **invalidate-not-overwrite** (the "Kael loyal ep 1–180, defected ep 181–" behaviour the Kernel depends on).
  If a backing store is needed underneath, prefer FalkorDB (permissive). **Kuzu is out** — archived 2025-10.
- **The graph layer is deliberately thin, and this is the important part.** NWM's ablations say the graph
  engine is not where the win is: stripping type labels scored 0.898 → 0.909, flattening to prose → 0.926,
  and their margin over Graphiti (0.893 vs 0.496) came from **atomic decomposition + query-conditioned
  retrieval**. So invest in the retrieval router, not the graph. A fat graph layer would be re-deriving the
  thing the evidence says does not matter.
- **Databricks stays at the EDGES** (PRD NF-04): `ai_functions`/`json_schema` for schema-locked extraction,
  Delta time-travel for the canon-at-episode-N projection, MLflow for the with/without harness and lane
  tracing, `synthetic-data-gen` for the planted-contradiction fixtures. The default path must run embedded
  and offline — if a cloud hiccup can sink the demo, the architecture is wrong.
- **Rejected:** Neo4j Community as the graph engine (GPLv3); Kuzu (archived); a graph database as the
  *system of record* (Airbnb ran a typed, provenance-and-confidence-tagged node/edge graph on a relational
  store — you do not need a graph DB to hold a story graph); a thick ontology layer (NWM ablation).
- ⚠️ **Open:** "a better database" was read as layer 1, the tri-temporal canon store. If the user meant a
  vector store for semantic recall or a separate operational DB, this entry needs revisiting.

## 2026-07-25 (session 6): Definition of done for the Kernel = a green E2E memory-storage suite
- **User direction:** "I don't want you to just put the code and think it is done. That's not when it's
  done." This restates the project's own standard (`tests/README.md`: *done = end-to-end verification
  passed; confidence is not evidence*), so it becomes the KB's acceptance gate, not a preference.
- **The evidence that set the bar.** We read the test suite of the closest public analogue, **Graphiti**
  ([getzep/graphiti](https://github.com/getzep/graphiti)): `tests/test_edge_int.py::test_entity_edge`
  constructs an edge carrying `valid_at`/`invalid_at`/`expired_at`, saves, reloads — and asserts only on
  `uuid`. `tests/test_graphiti_int.py::test_graphiti_init` runs a temporal `DateFilter` search with **no
  assertions at all**. Both pass while the temporal semantics — the entire point of the system — go
  unverified. **The bar is therefore higher than the reference implementations, not equal to them.**
- **Adopted standard** (full detail in `tests/README.md` § "Testing the Canon Kernel"; summarised in
  `.claude/rules/testing.md` so it auto-loads when tests are edited):
  - Every load-bearing field must appear on the **left-hand side of an assert after a real
    save-and-reload**. Identity-only or didn't-throw assertions are smoke tests and do not count.
  - **Nine tri-temporal invariants I-1…I-9** — one-live-fact-per-key, atomic + append-only supersession,
    as-of correctness on a **2D grid** (story time × record time, not a line), projection-equals-replay,
    idempotent replay, no-lost-update, monotonic record time.
  - **Durability:** real on-disk SQLite via `tmp_path`, **never `:memory:`**, and the store is **closed and
    reopened** mid-test. Skipping the reopen is how a store that only works while the process is warm
    passes its whole suite.
  - **The spoiler guard is tested as access control** (OWASP WSTG authorization method): **set equality** on
    returned ids, never spot checks — spot checks only catch leaks you already thought of.
  - **Severity asymmetry, encoded in the suite:** a **leak fails the build**; over-withholding is a reported
    metric only. Equal severity would make the suite reject correct-but-conservative behaviour.
  - **Property-based testing** (Hypothesis `RuleBasedStateMachine` + in-memory oracle) on the
    mutation-sequence surface only. Sequence-ordering bugs are combinatorial and unreachable by
    parametrization. Not for schema validation — Pydantic already covers that.
- **Tracked as KB-07 (store adapter) → KB-08 (E2E suite, the definition of done) → KB-09 (invariants).**
  `PROGRESS.md` Known Issues now states plainly: **until KB-08 is green the Kernel is unverified and must
  not be described as working**, however much code exists.
- **Rejected:** mocking the store above unit level; `:memory:` SQLite (cannot catch durability bugs);
  asserting on generated text (already a project red line); testing only the guard's positive case.

## 2026-07-25 (session 6): Harness defects found and fixed during a full state-file audit
- **`ruff format` was reformatting Python code blocks inside prose plans**, turning `make check` red on a
  document. `docs` added to `extend-exclude` — plans quote code that is not yet source, so formatting them
  rewrites the document to match a style the described code does not have yet.
- **`feature_list.json` KB-06 referenced `make eval-kernel`, a target that did not exist** — a verification
  command that cannot run means the feature can never legitimately flip to passing. Target added; it
  invokes `evals/run_kernel_eval.py` and correctly fails until M5 lands.
- **Added `make test-e2e` and `make test-kb`** so the E2E layer and the Kernel suite can be run in isolation.
- **`CLAUDE.md`/`AGENTS.md` still said "Problem statement: TODO"** three hours after the brief arrived, and
  carried no record of the two-track split. Both updated (kept in sync, as their own header requires).

## 2026-07-25 (session 6): `project_context.md` lands and settles three of our open assumptions
- **Source:** the parallel product session produced `project_context.md`, declared the single source of
  truth. Product: a playable branching layer over the Dexter novels — pick one of five characters, play
  forward through choices mined from fan-fiction, with every character knowing only what they actually
  learned. Track: P1 Story Time Machine + Infinite Story Universe.
- **OD-1 SETTLED → FORK** (their §11): *"tier structurally mislabels every deliberate divergence as an
  error, which is fatal for this genre."* Same reasoning we recommended. **KB-05 is unblocked**, and
  `conflicting_active_facts` is already fork-scoped, so their §5.5 distinction between *intentional
  divergence* and *accidental contradiction* is enforced in code today with no change.
- **Superseded in `PRD-KNOWLEDGE-BASE.md`** (their §12, recorded here so nothing builds from the stale
  version): OD-2 "producer or player" → **player**; A-4 public-domain corpus → superseded by SD-5/SD-13
  (Dexter novels; commercial IP accepted as a hackathon artifact, explicitly not revisited); OD-6
  "bounded options or free prose" → **bounded**. Their §12 states the PRD's remaining architecture, data
  model and knowledge-model sections stand.
- ⚠️ **CORRECTION TO OUR OWN CALL — `knower_scope` optionality was reasoned in the wrong frame.**
  We downgraded it from mandatory using evidence about continuity-*error frequency* (2 of ConStory's 19
  subtypes are epistemic, in a ~3.5%-of-density category). That frame is right for a verifier and wrong
  for this product: their SD-7 makes per-character epistemic state a **MUST, in the data model from the
  start**, and their §8.1 closing demo beat is re-rendering a scene from another character's view. The
  schema needs **no rework** — optional means *populatable*, and for this build we populate it for all
  five cast members on every fact — but the emphasis inverts and the earlier entry should be read with
  this correction attached.
- ⚠️ **KNOWN SCHEMA GAP vs their §5.3.** They specify each fact records *who witnessed it, who was told
  it, and who could reasonably infer it* — three channels. Our `knower_scope` is a single set, which
  collapses them. Sufficient for M5 ("a character cannot act on unwitnessed facts"), because the filter
  only answers *does X know this*. Insufficient if the demo needs to narrate *how* a character learned
  something. **Recommendation:** ship the single set; add a channel field additively if needed. Flagged,
  not silently absorbed.
- **Their §4.4 confirms our architecture independently:** *"the epistemic guarantee comes from what is
  absent from the assembled context, not from instructing a model to withhold. A fact that was never
  placed in the prompt cannot leak."* That is precisely why `LoreGraph.from_facts` applies the guard at
  construction rather than leaving it to callers, and why `WorkingMemory` assembles only from
  `store.visible_to(...)`.
## 2026-07-25 (session 5): Fan-fiction corpus source = Wattpad, NOT Reddit
- **Reason:** Measured, not assumed. Fandom subreddits are recommendation/discovery indexes, not prose
  repositories — median selftext **141–620 chars** across r/FanFiction, r/HPfanfiction, r/Dramione,
  r/PercyJacksonfanfic, and r/FanFiction **Rule 1 bans posting fic text** on the front page (excerpts >2
  sentences also barred). Cross-sections are near-empty (r/shortstories + "Percy Jackson" = 6 hits;
  r/redditserials = 0). Reddit-hosted prose is *original* fiction (r/HFY 96% >2k chars), and the prose subs
  ban fanfiction by rule. So the requested artifact is not obtainable from Reddit.
- **What IS reachable (probed live):** Wattpad `api/v3/stories` + `apiv2/storytext` return fandom-tagged
  metadata **and** full chapter prose, keyless — verified 18,227 chars of Witcher fanfic in one call.
  AO3 (`403` Cloudflare "Shields are up!"), fanfiction.net (`403` JS challenge) and fictionpress are walled.
  Also reachable for later: SpaceBattles, SufficientVelocity, RoyalRoad, Wattpad.
- **Rejected:** (a) Reddit as prose source — near-zero yield, and its Data API now requires manual approval
  under the **Responsible Builder Policy** while barring ML-training use, with active litigation against AI
  firms; (b) offsite AO3/FFN scraping via headless browser — fragile, slow, the most likely thing to break on
  stage; (c) pre-built HuggingFace AO3 corpora (`ray0rf1re/AO3-2020`, `midwestern-simulation-active/ao3_random_subset`)
  — kept as a documented fallback, but the best fandom-labelled one states **no licence**.
- **Maintainer override recorded:** presented with the evidence that corpus size is scored by **no** hackathon
  rubric and that judges advise against scraping, the maintainer reaffirmed the scraper as a hard requirement.
  Built as asked; scope held to *scrape + judge relevance + save* with KB wiring deferred to another branch.

## 2026-07-25 (session 5): Relevance is lexical (alias matching), not semantic
- **Reason:** Fandom terms are rare proper nouns ("Anaklusmos", "Nilfgaard", "Kaer Morhen"), the regime where
  exact matching is high-precision and dense embeddings blur the very distinction that carries the signal.
  Wikipedia `prop=redirects` yields those universe terms free — every redirect a human made is a real alias.
  Confirmed in the live run: the kept work matched on `['the witcher', 'nilfgaard']`.
- **Requirement clamped to the available alias surface** (`required_alias_hits`): demanding 2 distinct aliases
  is unsatisfiable when expansion fails and only the fandom name remains — which silently rejected **20/20**
  candidates on the first live run. Strict when it can be, permissive when it cannot.
- **Rejected:** sentence-transformers embeddings (256-token window vs ~13k-char stories; chunk-and-pool is real
  work for no gain here), LLM-as-classifier for the sweep, BM25 as the include/exclude decision.
- **Wikimedia UA policy is load-bearing:** a UA without a contactable URL/email returns **403** (a generic
  browser UA also 403s), which silently disables expansion. Hence `STORY_ENGINE_CONTACT`.

## 2026-07-25 (session 5): Fandom disambiguation must be RESOLVED, not guessed
- **Reason:** Wikipedia disambiguates films by YEAR — the real articles are `Titanic (1997 film)` and
  `The Avengers (2012 film)` — so no fixed suffix list can ever reach them. Measured failures with
  suffix guessing: "Dexter" → `USS Dexter` (a warship), "Titanic" → the ship
  ("Provisioning of the RMS Titanic"), "The Avengers" → the 1960s British spy series
  ("Steed and Mrs. Peel"). Fix: a caller-supplied `kind` (movie/novel/series) drives a Wikipedia
  **search** that resolves the actual article title, with suffixes only as fallback.
- **Result:** aliases became real in-universe entities — Dexter → `Dexter Morgan`,
  `The Bay Harbor Butcher`, `Dark passenger`; Titanic → `Caledon Hockley`, `Heart of the Ocean`,
  `Rose DeWitt Bukater`; Interstellar → `TARS`, `Miller's Planet`, `Gargantua`.
- **Also:** `kind`-qualified titles are tried BEFORE the bare title. Trying bare first satisfied the
  early-exit (the ship has plenty of redirects) and silently ignored the hint.

## 2026-07-25 (session 5): Alias matching is tag-key + word-boundary, never raw substring
- **Reason:** Raw substring matching failed in BOTH directions on live Wattpad data. Too strict:
  hosts strip spaces, so the tag `dextermorgan` never matched the alias "Dexter Morgan" and
  unmistakable fanfic ("Dexter: Blood", tagged `bayharborbutcher`) was rejected. Too loose: "dexter"
  matched inside `dextercharming`, an *Ever After High* character, admitting the wrong fandom.
- **Fix:** tags compared as normalized alphanumeric keys (with a leading-article variant, so
  `bayharborbutcher` satisfies "The Bay Harbor Butcher"); title/description matched on `\b` word
  boundaries with `\W*` between words.
- **Plus an explicit-declaration rule:** a work titled "…: A Dexter Fanfiction" or tagged
  `dexterfanfiction` declares its fandom outright — stronger evidence than a second incidental
  alias, and the count rule alone was rejecting three obvious true positives. Adjacency is required
  so "Dexter ▷ Scott Summers" (an X-Men work) is still rejected.
- **Corpus-quality gates added after reviewing real output:** mature works excluded by default
  (a Titanic result's blurb was explicit); read/vote floors (a 54-read, 0-vote joke fic —
  "FOR THE LOVE OF ONIONS. PICK SOMETHING!!!" — passed every other gate); and sentence-level
  disclaimer stripping, because "I DO NOT OWN TITANIC!" shared a line with prose and the
  line-anchored rule missed it. Verified 0 disclaimer leaks corpus-wide afterwards.

## 2026-07-25 (session 5b): The deliverable is BRANCH STRUCTURE, not prose volume
- **Reason:** `project_context.md` section 5.2 (the SSOT) defines the Branch Oracle: "fan-fiction supplies
  *what the options are*. It is **not quoted, reproduced, or used as generated prose. It is a source of branch
  structure only.**" That inverts the earlier optimization target. A 918-word abandoned fic ("Dexter doesn't
  kill Brian") carries as much branch signal as a 35-chapter saga, so "the stories are too small to ingest"
  stopped being a defect once the unit of value moved from prose to divergence.
- **Shape:** each work gets a `PremiseSignature` with `decision_point` (canon-side) plus `alternate_path`
  (what this work did instead); works sharing a decision point form a `PremiseGroup`; `branch_points()`
  assembles one node per decision point whose `options` are a canon baseline plus every distinct alternate.
  Live proof: Titanic `character_survives:jack` -> 4 options from 3 independent authors.
- **Enforcement, not intention:** option labels are synthesized from the premise taxonomy, and a unit test
  asserts no option label appears in its source blurb. Verbatim snippets live only in `premise.evidence` as
  audit provenance for the section 5.4 citation requirement.
- **Grouping is precedence, not union** - "If Jack lived, years later" must group with the other Jack-lived
  branches rather than key on the time skip, and survival keys on ONE entity so "Jack and Rose, two of the few
  survivors" does not split from "If Jack lived". Union-keying shatters the one group that proves the concept.
- **Rejected:** tuning prose-score weights to force a preferred ranking on a 4-work corpus (overfitting);
  copying author phrasing into option labels (violates section 5.2).

## 2026-07-25 (session 5b): OD-2 is decidable - the wiki carries a machine-readable novel/screen split
- **Reason:** section 6.4 flags "two canons that diverge" as "a silent corruption path". Measured:
  `dexter.fandom.com` keeps novel and screen versions as **separate pages** (`Brian Moser` vs
  `Brian Moser (Novels)`), plus `Category:Characters (Novels)` (74 members) and the wiki's own crosswalk
  `Category:Characters with Television Counterparts`. Over 314 entities:
  **novel 68 / screen 223 / both 9 / unknown 14.**
- **Consequence for the build:** three of the five section 6.3 cast members have DIFFERENT novel names -
  **Debra -> Deborah Morgan, Doakes -> Albert Doakes, LaGuerta -> Migdia LaGuerta** - and Brian's moniker is
  `Ice Truck Killer` (screen) vs `Tamiami Butcher/Slasher` (novel). Section 6.3's warning not to encode
  character facts from memory was correct. Our best Dexter branch (*Set Free*, the killing-table premise) is
  therefore **screen-canon**, so under section 6.1 it references a scene the novels may not have.
- **Deliberately NOT a canon KB:** values are emitted as `attributes` ("observed on page X") with mandatory
  provenance, never as canon assertions; the manifest says `artifact_kind: "wiki_entity_vocabulary"`.
  `canon_basis: screen` is a **review flag, not a verdict** - absence of a novel page is not absence from the
  novels. 14 entities stayed `unknown` rather than being defaulted.
- **Collision avoided:** the parallel `worktree-knowledge-base` branch already owns
  `domain/models/canon.py` (`CanonEntity`/`Presence`/`Scene`/`Commitment`/`Flag`, 29 tests) plus 11 new enums.
  Our work was re-pathed to `domain/models/wiki_index.py` + `adapters/outbound/wiki/`, imports none of their
  unmerged types, and integrates through a **JSON artifact** whose field names map onto `CanonEntity`.
- **Rejected:** `action=parse` HTML (infobox label/value pairing depends on skin CSS, whereas wikitext gives
  named parameters that parse straight into typed relationships); emitting the wiki as the authoritative canon
  KB (section 6.1 says the KB comes from the novels - doing that would BE the corruption path).

## 2026-07-25 (session 6, IV&V): Fix the source during the test phase, rather than pin bugs as `xfail`
- **Context:** An IV&V audit found three defects that were *implementation* bugs, not test bugs. Writing
  tests that encode correct behaviour would turn the suite red, conflicting with "all tests pass
  consistently".
- **Decision (maintainer, explicit):** fix the code and the tests together in the same pass.
- **Rejected:** (a) `xfail(strict=True)` pinning — keeps the suite green and documents the bugs, but ships
  a knowingly corrupting pipeline into the knowledge base; (b) characterization tests asserting current
  behaviour — fastest to green, but *enshrines* known-wrong behaviour, the exact failure the audit brief
  warns about ("a passing suite that validates the wrong behaviour is more dangerous than no tests").

## 2026-07-25 (session 6): A call-to-action needs corroborating evidence, not a line-initial keyword
- **Reason:** every CTA word (`vote`, `comment`, `follow`, `like`, `share`, `rate`, `review`) is also an
  ordinary English verb. Matching any line that merely *starts* with one deleted real narration —
  measured: 5 of 5 realistic prose lines destroyed. Corpus text is the knowledge base's input, so this
  was silent data corruption, not a cosmetic flaw.
- **Shape:** a line is boilerplate only if it opens with `please` + a CTA verb, or opens with a CTA verb
  **and** carries a second reader-directed marker (another CTA verb, `if you`, `this chapter`,
  `for more`, `my story`, `don't forget`). `read on <host>` now needs an explicit continuation object
  (`the rest` / `more` / `the full story`).
- **Rejected:** line-length or trailing-punctuation heuristics — real CTAs and real narration overlap on
  both, so neither separates them.

## 2026-07-25 (session 6): Truncation is DECLARED per record, not left to index-gap inference
- **Reason:** `chapters[].index` gaps cannot be distinguished from an author's own numbering, and
  `num_chapters_reported` counts parts that were never fetched — a different question. A real harvest
  shipped `wattpad:864850` starting at **chapter 2** with nothing saying so.
- **Shape:** corpus schema **1.1 → 1.2**, adding `chapters_dropped {non_prose, duplicate, is_partial}`.
  Additive only, so 1.0/1.1 readers keep working.
- **Also documented (was true but unwritten):** chapter dedup is **run-scoped, not work-scoped** — if
  work B repeats text already seen in work A, the chapter is dropped *from B*.
- **Rejected:** dropping the dedup guarantee (contract §4 promises exact-duplicate removal, and reposts
  are real); making dedup per-work (would re-admit genuine cross-work reposts).

## 2026-07-25 (session 6): A sink must be TOLD the branch-option ceiling, never recompute it
- **Reason:** `JsonlCorpusSink` recomputed branch points with its own default, so `--max-branch-options 2`
  printed 2 options to the console and wrote 3 to disk. The artifact is what the knowledge base ingests,
  so a producer whose output contradicts its own CLI is worse than one that simply lacks the flag.
- **Shape:** `max_branch_options` is now part of `CorpusSinkPort.write(...)` and threaded from the service.
- **Rejected:** passing the ceiling to the sink's constructor — it is a per-run value, not per-sink.

## 2026-07-25 (session 6): Test fixtures must match the SHAPE of real data, not just its type
- **Reason:** the harvest fixtures defaulted to `chapters=1` per work. That single choice made intra-work
  chapter dedup *structurally unobservable* — no assertion could have caught it. Real works are
  multi-chapter (the live Dexter corpus is 43 chapters across 4 works).
- **Rule adopted:** a cap or count assertion uses `==`, never `<=` — `assert len(stories) <= 2` is also
  satisfied by a harvester that returns nothing, and passed for exactly that reason.
- **Consequence:** `PerChapterSource` / `PerWorkSource` doubles now serve distinct text per chapter/work.

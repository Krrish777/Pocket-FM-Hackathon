# Project Progress

> Durable cumulative state. **Read at session start; update before session end.** Per-session notes go in
> `session_handoff.md`; decisions in `DECISIONS.md`; the machine task list is `feature_list.json`.

## Current State
- **Phase:** **PRODUCT** (the brief has landed; harness phase is closed). The problem statement is selected,
  narrowed, and written up — **`project_context.md` is the single source of truth for what we are building
  and why. Read it before building anything.**
- **Product in one line:** a playable branching layer over the **Dexter novels** — pick a character, play
  forward through choices mined from **fan-fiction**, with every character remembering only what they
  actually learned. Track: P1 Story Time Machine + Infinite Story Universe.
- **Runway:** 24–36h, 2–4 people. Parallel sessions are live in `.claude/worktrees/`
  (`reddit-fanfic-scraper` = the EXT-1 ingestion dependency; `knowledge-base`).
- **Verification (knowledge base):** `make check` **GREEN**. An IV&V audit (Session D) reproduced 8
  defects with executable probes *while the gate was green*; the two product blockers (per-knower
  acquisition time, fork lineage) and the CRITICAL guard/write-path defects are fixed with regression
  tests. KB tests **110 → 138**. Remaining findings: `BACKLOG.md` § IV&V AUDIT.
- **Superseded note (kept for history):** `make check` was **GREEN — 110 passing** (70 unit, 40 integration + e2e against REAL
  on-disk SQLite). INIT-01…05 + HARDEN-01…04 pass; HARDEN-05 deferred.
- **🧠 THE KNOWLEDGE BASE IS BUILT AND END-TO-END TESTED** (branch `worktree-knowledge-base`, rebased onto
  main 2026-07-25). Three stores over one tri-temporal fact model: **canon store** (SQLite, atomic
  supersession, as-of queries) · **graph projection** (multi-hop traversal, relationship diff) ·
  **vector store** (semantic recall, guard applied as a PRE-filter) · plus **agent working memory**
  (bounded, deterministic, per-character). Spoiler guard asserted at every layer; durability proven by
  closing and reopening the database twice. `KB-01`, `KB-07`…`KB-12` all `passes:true`, each verification
  command re-run individually.
- **What the KB still owes the product:** it is **EMPTY** (no ingestion — that is EXT-1), and `KB-13`
  (fork write path + deriving `knower_scope` from `Scene.witnesses`) is not started. Those two are the only
  KB items the agent loop actually needs. **Seeding 20–40 hand-authored facts (~1h) unblocks the loop today**
  — the API is stable and tested, so an agent built against seeded data works unchanged when ingestion lands.
- **Product features M1–M8 / S1–S3 remain `passes:false`** — but M5 and M8's *storage substrate* now exists
  and is tested; see their `evidence` fields for exactly what is done and what is not.
- **EXT-1 (scraper branch) STATUS: delivered, INDEPENDENTLY AUDITED, and closed for the hackathon.**
  `FANFIC-01…07` all pass — fandom-targeted scraper, Branch Oracle (canon decision points with 2–4
  options), OD-2 canon discriminator, a written EXT-1 contract, and (session 6) an IV&V pass that found
  and fixed **4 real defects**. Corpus artifact is schema **1.2**. Per `project_context.md` §5.2 its
  deliverable is **branch structure, not prose** — fan fiction supplies *what the options are* and is
  never reproduced. **Do not invest further here**; it produces what the playable layer needs.
- **Worktrees are gone (session 7).** Both parallel branches merged (PR #2, PR #4) and their worktrees
  removed; `main` pulled to `d1952c8`. They had been committed as **mode 160000 gitlinks** — now
  untracked, with `.claude/worktrees/` in `.gitignore` so it cannot recur. All parallel work is on `main`.
- **`demo.md` is the scope fence (session 7).** Nine demo beats, tasks T0–T10, a pre-decided cut ladder,
  and an explicit not-building list. **~18 h of work against ~14 h of runway** — read the cut ladder
  before adding anything.
- **Verification:** `make check` is **GREEN** — exit code 0, **479 passing** (up from 447).
  INIT-01…05 + HARDEN-01…04 + FANFIC-01…07 + KB-01/07/08/09/10/11/12 + **INGEST-01** pass.
  HARDEN-05 deferred (deprioritised below product work).
  **All product features M1–M8 / S1–S3 are still `passes:false`** — the substrate is strong, but nothing
  the player touches exists yet. Nothing in this repo can render a sentence: only `StubLLM` exists and
  `prompts/` is a lone README.

## Completed
### Session 7 (2026-07-25) — worktree cleanup, scope lock, novel PDF ingestion (INGEST-01 ✅)
- [x] **Worktrees cleaned and `main` reconciled.** The tree read dirty after `git worktree remove`
      because the index still held gitlink pointers to directories that had vanished.
- [x] **`demo.md` written** — the scope fence, with the cut ladder decided cold rather than at 3 a.m.
- [x] **INGEST-01 — novel PDF → chapter-addressed citable text.** Adapted from
      `patchy631/ai-engineering-hub/notebook-lm-clone` (**MIT**, verified at the repo root; the prior
      "no license stated" note had only checked the subdirectory, and is now corrected in place).
      **Three upstream defects fixed, each with a regression test:**
      (1) **silent data loss** — `start = max(start + chunk_size - overlap, end)` skips past `end`
      whenever the sentence snap retreats further than the overlap covers; a dropped span is a fact that
      exists in the novel and can never be cited. Trigger condition is `start + chunk_size - overlap >
      end`, so short sentences relative to the window are what make it fire — the first proof fixture
      did *not* trigger it and the test correctly failed until corrected.
      (2) **quote/offset disagreement** — offsets recorded before stripping, so the quote did not match
      its own coordinates.
      (3) **page-relative → chapter-relative offsets** — decisive, because the spoiler guard gates on
      chapter and a page number cannot answer "has this been revealed yet?".
      **Design call:** a PDF with no chapter headings **raises** rather than collapsing to one chapter —
      `chapter=1` everywhere leaves the guard green while making the whole novel visible to everyone.
      **Rejected:** upstream's retrieval path, which applies no epistemic filter and would open a second
      unguarded read path beside `store.visible_to()`.
      E2E proves the full chain: real PDF → PyMuPDF → chunk → `Provenance` → SQLite → **restart** →
      source re-read from disk → offsets still resolve, with the guard still gating by chapter.
- [x] **Reference repos assessed and recorded in `BACKLOG.md`** — `NousResearch/hermes-agent` (MIT;
      `conversation_loop.py` is 6,645 lines, so patterns port and code does not; its "self-improvement
      loop" is skill accretion into `SKILL.md` files, not a model improving itself) and the maintainer's
      GitHub stars, of which **`567-labs/instructor`** is the highest-value item for the next task.


### Session 6 (2026-07-25) — IV&V audit of the scraper (FANFIC-07): 4 defects found and fixed
> Run under "assume the scraper is incorrect until evidence proves otherwise." Verification session, not
> a feature session. Every finding below was proven by **executing** code, not by reading it.

- [x] **Defect 1 — `strip_boilerplate` was deleting real narrative prose.** Every CTA word is also an
      ordinary English verb; patterns matched any line merely *starting* with one. Measured: 5 of 5
      realistic prose lines destroyed (`"Like a knife, the cold cut through him."`). The `read on <host>`
      pattern was unanchored too. **This was corrupting the knowledge base's direct input.** Fixed: a CTA
      now needs `please` or a second reader-directed marker.
- [x] **Defect 2 — chapters silently dropped, works shipped truncated with no marker.** Live evidence:
      `wattpad:864850` shipped **starting at chapter 2**; `390229723` had gaps at 6 and 11. Fixed by
      **corpus schema 1.1 → 1.2**, adding `chapters_dropped {non_prose, duplicate, is_partial}`.
- [x] **Defect 3 — the on-disk manifest contradicted the CLI.** `JsonlCorpusSink` recomputed branch
      points with its own default, ignoring `--max-branch-options`: console showed 2 options, the
      artifact contained 3. Fixed by threading the ceiling through `CorpusSinkPort`.
- [x] **Defect 4 — `<script>`/`<style>` bodies leaked into prose.** Found by a *new* test; tag stripping
      leaves those elements' contents behind as story text. Fixed in `http_util.html_to_text`.
- [x] **Test suite 237 → 286.** New `tests/unit/adapters/test_http_util.py` (22 tests) covers the retry
      engine, which had **zero** tests despite every scraper request passing through it. New classes:
      `TestMultiChapterIntegrity`, `TestMultiSourceResilience`, `TestTruncationProvenance`,
      `TestBoilerplateDoesNotEatProse`.
- [x] **Killed a false-positive test.** `test_respects_max_stories` asserted `len(stories) <= 2` — also
      satisfied by a harvester returning **zero**. Now `== 2`.
- [x] **Root-caused the blind spot:** service fixtures defaulted to `chapters=1` per work, making an
      entire bug class *structurally unreachable*. Real works are multi-chapter (43 chapters / 4 works).
- [x] **Contract doc updated to 1.2**, including the previously-unwritten fact that chapter dedup is
      **run-scoped, not work-scoped** (work B loses a chapter that work A had first).

### Session 5b (2026-07-25) — Branch Oracle + OD-2 discriminator (FANFIC-04..06)
- [x] **Branch Oracle (FANFIC-04)** — `domain/fanfic_premise.py` + `domain/prose_score.py` (pure, stdlib).
      Mines fan fiction into **canon decision points with 2-4 player-facing options**, which is
      `project_context.md` section 4 step 3. Live Titanic: `character_survives:jack` support=3 -> 4 options
      (1 canon baseline + 3 distinct alternates from 3 independently authored works). Option labels are
      synthesized from the taxonomy and **never copied** from author text - a test asserts it (section 5.2).
- [x] **OD-2 discriminator (FANFIC-05)** — wiki ENTITY VOCABULARY, deliberately *not* a canon KB.
      314 Dexter entities: **novel 68 / screen 223 / both 9 / unknown 14**, 561 relationships, 2,785
      attributes. Novel and screen characters are SEPARATE wiki pages, so the split is machine-readable.
- [x] **EXT-1 contract (FANFIC-06)** — `docs/EXT-1-scraper-output-contract.md` closes OD-3.
- [x] **AO3 second source** — `HuggingFaceAO3Source`; AO3 labels distinguish canons
      (`Dexter Series - Jeff Lindsay` vs `Dexter (TV)`), the only source that can.
- [x] **Full chapter depth** — `--max-chapters` default 500. Dexter went 13 -> **43 chapters / 55,769 words**.
- [x] CLI: `harvest` (new flags), **`branches`**, **`wiki-index`**.

### Session 5 (2026-07-25) — in-event: fan-fiction scraper (FANFIC-01, FANFIC-02)
- [x] **Evidence sweep first** (4 parallel research agents + live network probes) established, against
      measurements rather than assumption, that Reddit does not hold fandom fanfic prose and that **Wattpad**
      does and is reachable keyless. Verified: `api/v3/stories` (fandom-searchable metadata + `parts[]`) and
      `apiv2/storytext` (chapter prose). Recorded in `docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md`.
- [x] **Domain (pure, stdlib-only):** `domain/models/fanfic.py` (`FandomQuery`, `StoryRef`, `ChapterRef`,
      `Chapter`, `HarvestedStory`) + `domain/fanfic_quality.py` — prose gate (`words>=500` AND
      `quotes_per_1k>=5`, both empirically measured), alias relevance, boilerplate stripping, SHA-256 dedup.
- [x] **Ports:** `FanficSourcePort` + `AliasExpanderPort` (`ports/fanfic_source.py`), `CorpusSinkPort`
      (`ports/corpus_sink.py`) — so a new host is one adapter file, no pipeline change.
- [x] **Adapters:** `WattpadSource`, `WikipediaAliasExpander` (redirects → aliases incl. universe terms),
      `JsonlCorpusSink` (versioned schema + manifest), shared `http_util` (policy-compliant UA, backoff, HTML→text).
- [x] **Service + CLI:** `services/fanfic_harvest.py` (`FanficHarvester` + `HarvestReport` counting every
      rejection) and `story-engine harvest "<novel or film>"`.
- [x] **37 unit tests** for the feature (44 total). `make check` GREEN; mypy strict clean on 55 files.
- [x] **Live verification:** `harvest "The Witcher"` → 18 aliases, 1 work / 3 chapters / 4,073 words of real
      Witcher prose, written to gitignored `data/raw/fanfic/the-witcher/`.

- [x] **Conventions system** — migrated (session 4) to native **`.claude/rules/`**: 7 path-scoped rules that
      auto-load by file type. Replaced the hand-rolled PreToolUse hook; one `python-conventions` skill kept.
- [x] **Research** (8 cited artifacts) in top-level `research/` + `research/llms.txt` source index (moved OUT
      of `.claude/` to keep it lean).
- [x] **Harness**: `CLAUDE.md` (+ `AGENTS.md` mirror) with clock-in/out loop; SessionStart clock-in hook;
      state files (`BACKLOG`, `PROGRESS`, `DECISIONS`, `session_handoff`, `feature_list.json`).
- [x] **Backend scaffold** (`src/story_engine/`, ~30 modules, all compile): `domain/` (base + enums + models:
      Story/Episode/Character + memory models), `ports/` (llm, prompt_store, 3 memory ports), `services/`
      (episode_generator), `adapters/outbound/` (in-memory repos, stub LLM, file prompt store), `api/` (FastAPI
      factory + router + schemas + error handlers), `cli/` (Typer), `bootstrap.py`, `config/settings.py`,
      `shared/` (errors + text + retry), `observability/logging.py`, `resources/`.
- [x] Config: `pyproject.toml` (deps + tool config + `[project.scripts]`), `.env.example`,
      `.pre-commit-config.yaml`, `.gitignore`. Removed root `main.py`. Documented `temp/` as agent scratchpad.
- [x] Strict evaluation of `.claude` setup; fixed hook placeholder `${CLAUDE_PROJECT_DIR}`.

### Session 2 (2026-07-24) — harness hardening
- [x] **`make check` green from scratch**: fixed packaging (dev tools → PEP 735 `[dependency-groups]` so
      `uv sync` installs them), `StrEnum` (UP042), excluded vendored `.agents/` from ruff, `isinstance`-narrowed
      the FastAPI error handler for mypy. INIT-02…05 now pass.
- [x] **SQLite persistence adapter** (`adapters/outbound/persistence/`, SQLModel): `db.py` (engine +
      `session_scope` + `init_db`), `tables.py` (`EpisodeSummaryRow`, JSON columns), `episode_log_repository.py`
      (`SqliteEpisodeLogRepository` implements `EpisodeLogRepositoryPort`, explicit Row⇄domain mapping,
      `col()` for strict-mypy). Fixed a `DetachedInstanceError` (map inside the session scope). **HARDEN-01.**
- [x] **Enhanced settings** (`config/settings.py`): tiangolo-adapted `project_name`, `api_v1_str`,
      `environment`, CORS `parse_cors` + `all_cors_origins`, `database_url` (SQLite default) — kept our
      `SecretStr` LLM settings + `STORYENGINE_` prefix.
- [x] **Wired bootstrap + app factory**: engine created + schema init at startup; `SqliteEpisodeLogRepository`
      injected; `custom_generate_unique_id`, optional-CORS, router aggregation (`api/main.py`) mounted under
      `api_v1_str`; `create_app(container)` is now test-injectable. Wired `make dev`/`make run` (uvicorn).
- [x] **Validation Hierarchy set up** (L1 static / L2 runtime / L3 e2e) — `tests/{unit,integration,e2e}/`,
      `integration`/`e2e` markers, `make check` runs all three, documented in `tests/README.md` (from the
      Harness-Engineering docs). **HARDEN-02/03.**
- [x] **Skills**: installed `find-skills` meta-skill; verified + installed official **FastAPI skill**
      project-level; recorded the reusable skill-evaluation matrix in `DECISIONS.md` + memory. **HARDEN-04.**

### Session 3 (2026-07-24) — user file-by-file review (REVIEW-01…04)
- [x] **REVIEW-01:** dropped the `STORYENGINE_` env prefix — removed `env_prefix` in `settings.py`, rewrote
      `.env.example` with plain SDK-native names (also fixed a stale `TEMPERATURE` var that never mapped to a field).
- [x] **REVIEW-02:** relocated conventions `.claude/docs/conventions/` → **`.claude/conventions/`** (they aren't
      "docs"); patched all 29 inbound references; left `DECISIONS.md` history intact + appended a reversal entry.
- [x] **REVIEW-03:** researched (3 parallel web agents) + refreshed **all** convention docs. Python: mypy-strict
      redundancy, PEP 695 generics, pytest-9 / Ruff-0.16, Black→`ruff format`, **new `09-persistence.md`**.
      Structure: re-synced all 3 docs to the real tree (bootstrap composition root, `shared/`/`resources/`, split
      ports). Frontend: Next 16 async APIs / React 19.2+Compiler 1.0 / Tailwind v4 / WCAG 2.2 AA / shadcn Base UI
      (framed "verify at creation"). Inline source URLs + provenance appended to 5 `research/` files.
- [x] **REVIEW-04:** aligned live `pyproject.toml` — trimmed mypy to `strict`+`no_implicit_optional`, added `RUF`
      (0 new violations), `minversion=9.0`, `[tool.coverage]`. Doc ⇄ config now in sync.

### Session 4 (2026-07-24) — restructure onto native `.claude/rules/`
- [x] **Researched the question first (3 agents):** confirmed our 22-file conventions "database" was
      over-engineered vs. how real Claude-Code repos work; produced the Opus-4.8 prompt-engineering rule draft
      and the `research/`-reorg + `reference/`-hub design. A 4th agent verified the exact `.claude/rules/` format
      (`paths:` YAML list, not Cursor's `globs:`) before any file was written.
- [x] **Migrated → `.claude/rules/`** (7 rules: `python-style`, `python-design`, `persistence`, `structure`,
      `llm-storytelling`, `prompts`, `testing`). Deleted `.claude/conventions/`, the `conventions-reminder.mjs`
      hook + its settings.json registration, and the `frontend-conventions` skill; preserved the untracked
      frontend draft → `temp/frontend-conventions-draft/`. Repointed CLAUDE.md, AGENTS.md, README, prompts/README,
      pyproject, and 11 `src/` docstrings.
- [x] **Two-tier testing** encoded (`.claude/rules/testing.md` + memory): pytest (code) + DeepEval (LLM quality).
      Scaffolded `evals/metrics/metrics.py` + `evals/README.md`; `deepeval` not yet a dep; datasets blocked on brief.
- [x] **research/ reorganized** by domain + `research/README.md`; **new `reference/llms.txt`** hub of upstream
      dependency docs (link-not-vendor), wired into CLAUDE.md/AGENTS.md (research = learned-from, reference = go-read).

### Session 5 (2026-07-25) — the brief landed; problem statement selected and narrowed (INIT-01 ✅)
- [x] **INIT-01 closed.** Established that the official brief is a **menu** (~40 statements / 6 tracks), so
      "capture the problem statement" was a *selection + narrowing* decision, not a copy-paste. Selected
      **P1 Story Time Machine** + **Infinite Story Universe**.
- [x] **Resolved the repo's central unresolved conflict**: `_PROBLEM VERDICT` said build for the *creator*;
      the friend-authored PRD built for the *listener*. Settled: **the Player is primary, creator is a slide** —
      an explicit override of the vault's own recommendation, recorded as such in `DECISIONS.md`.
- [x] **Wrote `project_context.md`** (13 §, ~390 lines): problem, product, users, exact core loop, glossary,
      corpus, MUST/SHOULD/OUT scope, demo proof, external deps, **17 settled decisions**, **6 open items**
      (each with ID/owner/recommendation/deadline), and explicit **supersessions** of the friend's PRD,
      `_PROBLEM VERDICT`, and parts of `PRD-KNOWLEDGE-BASE.md`.
- [x] **Wrote `docs/2026-07-25-product-definition-session.md`** — decision provenance: 13 decisions each with
      *what was chosen, why, and what was rejected*, plus a corrections table (5 mid-session reversals,
      including two of the assistant's own errors). New top-level `docs/` dir (not yet in `structure.md`).
- [x] **Key product ideas established** (neither doc had them): fan-fiction is the **branch oracle** (a third
      path past the hand-authored-vs-generated dead end); **intentional divergence vs accidental contradiction**;
      **protagonist-ness is a rendering choice, not a stored property** — which makes Infinite Story Universe
      nearly free and unlocks the closing demo beat (replay the same branch as Debra).
- [x] **Patched** `CLAUDE.md` + `AGENTS.md` (mirror kept in sync) to point at `project_context.md`; verified
      INIT-01's own verification command passes.
- [x] **Seeded `feature_list.json` with the product phase** — M1–M8 (MUST) + S1–S3 (SHOULD), each with a
      verification command, all `passes:false`. Build order flagged: **M8 first** (only decision expensive to retrofit).
- [x] **Fixed the gate:** added `.claude/worktrees` to ruff `extend-exclude` — parallel-session worktrees are
      separate checkouts that run their own `make check`; linting them from the parent made our gate fail on
      their in-progress code. `make check` re-verified GREEN (exit 0, 7 passed).
- **No product code written this session** — by design; this was an elicitation session.

## Known Issues
- **⚠ Local corpora are at MIXED schema versions.** `./init.sh` now prints this at session start; as of
  session 6: `dexter` **1.2**, `titanic` **1.1**, `the-witcher` **1.0**. A consumer walking
  `data/raw/fanfic/*` will hit records *without* `chapters_dropped` and must not assume its presence.
  Corpora are **not** migrated in place — re-harvest a fandom to bring it to the current schema.
  (Corpus files are overwritten per run and `data/raw/` is gitignored, so this is cheap.)
- **⚠ Branch points have `support: 1` — the "many humans branched here" claim does NOT hold at this
  corpus scale.** Every `premise_group` in the real Dexter harvest has `size: 1`. The demo is unaffected
  (canon-stands + one alternate is a legal 2-option choice), but **KB code written assuming multi-member
  groups will get empty results.** Tell the KB team explicitly.
- **Prose-gate thresholds are borrowed from the wrong problem (IV&V F-7, open).** `words >= 500` AND
  `quotes_per_1k >= 5` were measured for *Reddit prose-vs-discussion*, then applied per-chapter to
  Wattpad, where that problem does not exist. They rejected 7 chapters across a 4-work harvest (~14%),
  including one work's opening chapter. Now *visible* via `chapters_dropped`, but not changed.
  **Tunable without code:** `--min-words 200 --min-quotes-per-1k 0`. Note this systematically drops
  dialogue-free introspective chapters — which matters for Dexter's first-person interiority.
- **`alias_expander.py` (306 lines) has ZERO tests.** `--kind` disambiguation is load-bearing (see the
  next item) and entirely unverified. Wattpad `search()` round-robin/pagination is also untested.
- **`get_with_retry` ignores `Retry-After` on 429**, and `_pause()` is skipped on the failure path — so a
  run that hits errors is *less* polite to the host than one that succeeds.
- **`--kind` is effectively required for ambiguous titles.** Wikipedia disambiguates films by YEAR, so
  `harvest "Titanic"` without `--kind movie` resolves to the SHIP. Always pass `--kind movie|novel|series`.
- **Yield is fandom-size dependent.** Titanic hit the 10-work cap; Dexter yielded 4 — the Dexter fandom is
  simply smaller on Wattpad. Lower `--min-reads`/`--min-votes` for niche fandoms.
- **Short generic aliases can over-match.** Resolution surfaces character names like `Arthur`, `Mal`,
  `Ranger` (Inception/Interstellar). The 2-distinct-hit rule mostly covers it, but a work naming the fandom
  plus one common first name could slip through. Watch this on fandoms with generic character names.
- **Only exact-duplicate dedup.** SHA-256 on normalized text; near-duplicate reposts are NOT caught yet
  (MinHash is on the backlog).
- **Fan fiction is NOT on Reddit** (measured 2026-07-25, and the reason the scraper targets Wattpad): fandom
  subreddits have a **median selftext of 141–620 chars** and r/FanFiction's Rule 1 bans posting fic text
  outright. AO3 + fanfiction.net are **Cloudflare-blocked** from this machine. Reddit's Data API now needs
  manual approval (Responsible Builder Policy) and bars ML-training use. Do not re-litigate this without new
  measurements — see the spec's evidence tables.
- **Wikimedia UA policy is load-bearing.** A User-Agent without a contactable URL/email gets **403**, silently
  disabling alias expansion (which then guts recall). Set `STORY_ENGINE_CONTACT` to a real contact.
- **L3 E2E is partial**: the full `premise → episode → persist` request path is NOT yet E2E-tested — the LLM
  adapter is deferred to the event brief and `StubLLM.generate` raises by design. Today's E2E proves boot +
  schema init only (tracked in `tests/README.md` + HARDEN-02).
- Domain models/services/adapters are **STARTER stubs** — refine to the brief. `StoryBible` repo is still
  in-memory (only the episode-log is SQLite so far).
- `fastapi.testclient` emits a `StarletteDeprecationWarning` (wants `httpx2`) — harmless, future compat only.
- The project-level FastAPI skill is a **symlink** (`.claude/skills/fastapi` → `.agents/skills/fastapi`);
  confirm git tracks it correctly on Windows before relying on it committed.
- CLAUDE.md/AGENTS.md are manual mirrors (drift risk). Clock-out is prose-only (not enforced).
- **⚠ The git index is shared across parallel sessions.** Session 5 staged 4 files for review; a parallel
  session then ran a commit that swept the whole index into `8d70e1b` "regular updates" (164 files). Staging
  is **not** a safe hold when other sessions are live — only an uncommitted working tree is. Coordinate before
  staging, or expect your work to be committed by someone else under someone else's message.
- **New top-level `docs/` dir** (session 5) is not yet described in `.claude/rules/structure.md`, which is an
  always-on rule and is meant to be an accurate map of the tree. Add it, or move the file.
- **`make check` exit codes:** do not pipe `make check` into `tail`/`head` — the pipeline reports the *filter's*
  exit code, not make's, and a red gate reads as green. Redirect to a file and check `$?` instead.

## Next Steps
> Ordered. WIP = 1. `project_context.md` §7 defines every done-condition; do not re-derive scope from memory.

1. **M8 — the uniform character state schema. BUILD THIS FIRST.** All 5 cast members share one identical
   state structure (knowledge set over one world state + traits + goals); **no PC/NPC asymmetry in storage**;
   character state **never** stored as narrative text; the renderer takes a character as a **parameter**.
   Rationale: it is the only decision in the product that is expensive to retrofit, and M5 + S3 both depend
   on it. Spec: `project_context.md` §4.4.
2. **Resolve OD-1 (fork vs. tier)** before the storage layer is written. Recommendation: **fork** — a tier
   model mislabels every deliberate divergence as an error, which is fatal for fan-fiction.
3. ~~**Get the EXT-1 contract from the scraper session (OD-3)**~~ **DELIVERED** —
   `docs/EXT-1-scraper-output-contract.md` answers all four §9 checkboxes and documents corpus schema 1.1 +
   wiki-index schema 1.0 field-by-field. **Remaining ask on the KB side:** expose a resolvable canon-moment id
   (`(chapter, order_in_chapter)` or a documented `Scene.id`) so branches can cite a SCENE, not just entities.
   That is the largest remaining integration gap — see that doc's §6.
4. **Resolve OD-2 (novel vs. screen canon)** — now DECIDABLE rather than a guess. The scraper branch built a
   discriminator: 314 Dexter wiki entities labelled **novel 68 / screen 223 / both 9 / unknown 14**, and AO3
   labels split canons directly (`Dexter Series - Jeff Lindsay` vs `Dexter (TV)`).
   **Decision-forcing finding: 3 of the 5 §6.3 cast have different NOVEL names — Debra→Deborah Morgan,
   Doakes→Albert Doakes, LaGuerta→Migdia LaGuerta** — and our best Dexter branch (*Set Free*) is screen-canon.
   Pick a canon deliberately; the data is in `data/raw/wiki_index/dexter/`.
5. **M5 — per-character epistemic memory** (depends on M8). Acceptance: a character who did not learn a fact
   at step 4 still does not know it at step N, for all N > 4.
6. Then **M1 → M4 → M2 → M3 → M6 → M7**. Only after every M passes: **S3** (replay-as-Debra, the closing beat),
   then S2, S1.
7. **Deferred / unblocked-by-brief but lower priority than the above:** HARDEN-05 (local sqlmodel/pytest skills);
   the E2E gap (deterministic offline LLM so generate→persist is L3-testable without a key); `StoryBible` in
   SQLite; the `deepeval` eval harness (goldens can now be generated — the brief no longer blocks it);
   re-homing the frontend convention draft from `temp/frontend-conventions-draft/` when a UI actually starts.

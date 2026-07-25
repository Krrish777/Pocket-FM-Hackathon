# Backlog

> Human-readable, ordered task queue. Top = next. As a task becomes concrete and verifiable, promote it into
> `feature_list.json` (with a `verification` command, `passes:false`). `feature_list.json` is the machine
> source of truth; this file is for humans to plan and reorder.

## NOW — Product phase (session 5, 2026-07-25). The brief has landed.

> **Scope lives in `project_context.md` (§7), not here.** This list is the ordered queue only.
> Provenance for every decision: `docs/2026-07-25-product-definition-session.md`.
> Machine SSOT: `feature_list.json` (M1–M8 MUST, S1–S3 SHOULD, all `passes:false`).

1. **M8 — uniform character state schema. FIRST.** The only decision expensive to retrofit; M5 and S3 both
   depend on it. No PC/NPC asymmetry in storage; renderer takes a character as a parameter. (`project_context.md` §4.4)
2. **OD-1 — fork vs. tier**, before storage is written. Recommend **fork**.
3. **OD-3 — get the EXT-1 scraper output contract** from the parallel session. Highest-risk unknown.
4. **OD-2 — novel vs. screen canon**, before any fan-fiction is ingested. Silent corruption path.
5. **M5** — per-character epistemic memory (depends on M8).
6. **M1 → M4 → M2 → M3 → M6 → M7**, then S3 → S2 → S1.
7. **OD-4** — define the degradation path for moments with thin fan-fiction coverage, before the demo script is fixed.
8. **OD-5** — product name ("CANON: Time Machine" no longer describes the product).
9. Housekeeping: add the new top-level `docs/` dir to `.claude/rules/structure.md`.

## Session 3 (2026-07-24) — user file-by-file review (LIVE — being added to as the user reviews)

> The user is walking the repo file by file and raising fixes. Captured here first (persistent list), then
> executed ONE AT A TIME (WIP=1). More items will be appended as the review continues.

- [x] **REVIEW-01 — Simplify env var naming (drop the `STORYENGINE_` prefix).** ✅ DONE (2026-07-24):
      dropped `env_prefix` in `settings.py`, rewrote `.env.example` with plain SDK-native names, fixed the
      stale `TEMPERATURE` var (real fields are `temperature_prose`/`temperature_structured`). Settings load +
      `make check` green (7 tests). Linked 2-file change:
      remove `env_prefix="STORYENGINE_"` in `src/story_engine/config/settings.py:31` **and** rewrite
      `.env.example` with plain names (`ANTHROPIC_API_KEY`, `DEFAULT_MODEL`, `MAX_OUTPUT_TOKENS`, …). Rationale:
      single-app hackathon → the prefix is noise (its only value is collision-avoidance in a shared env); plain
      names also align with SDK-native vars (e.g. `ANTHROPIC_API_KEY` is auto-read by the SDK). Keep
      `.env.example` minimal. Verify: `uv run python -c "from story_engine.config.settings import Settings"`
      still loads + `make check` green.
- [x] **REVIEW-02 — Relocate coding conventions out of `.claude/docs/` (they are not "docs").** ✅ DONE
      (2026-07-24): user chose **`.claude/conventions/`** (out of the `docs/` subfolder, still under `.claude/`).
      Moved the dir (removed the now-empty `.claude/docs/`) and patched all 29 inbound references (CLAUDE.md +
      AGENTS.md topic-doc map, both convention skills, the PreToolUse hook, README/pyproject/prompts, src
      module docstrings, research provenance notes). Left `DECISIONS.md` history intact + appended a reversal
      entry. Hook target resolves; `make check` green.
- [x] **REVIEW-03 — Research + update ALL conventions.** ✅ DONE (2026-07-24): 3 parallel web-research agents
      (python / structure / frontend) → verified findings → I wrote the updates. Python: mypy-strict redundancy,
      PEP 695 generics, pytest-9 / Ruff-0.16, Black→`ruff format`, new `09-persistence.md`. Structure: re-synced
      all 3 docs to the real tree (bootstrap composition root, `shared/`/`resources/`, split ports). Frontend:
      Next 16 async APIs, React Compiler 1.0, Tailwind v4, WCAG 2.2 AA, shadcn Base UI — framed "verify at
      creation". Inline source URLs + provenance appended to 5 `research/` files. `make check` green.
- [x] **REVIEW-04 — Align live `pyproject.toml` with the refreshed tooling conventions.** ✅ DONE (2026-07-24):
      trimmed mypy to `strict` + `no_implicit_optional` (mypy still clean → dropped flags were redundant); added
      `RUF` (0 new violations); `minversion=9.0`; added `[tool.coverage]`. `make check` green. Doc ⇄ config now in sync.
- [ ] _(more incoming — user is still reviewing other files)_

## Done — Initialization phase (INIT-01…05) + Harness hardening s2 (HARDEN-01…04)
- [x] Scaffold, `pyproject.toml`, `make setup`/`make check` green, `init.sh` smoke. (INIT-02…05)
- [x] SQLite persistence adapter (SQLModel) + enhanced settings + wired bootstrap/app factory. (HARDEN-01)
- [x] 3-layer Validation Hierarchy (unit/integration/e2e) wired into `make check` + `tests/README.md`. (HARDEN-02/03)
- [x] `find-skills` + official FastAPI skill installed & verified; skill-evaluation matrix recorded. (HARDEN-04)
- [ ] **INIT-01** — problem statement: BLOCKED until the event (brief revealed 2026-07-25).

## Now — finish hardening (pre-event)
0. **Review session-2 work** (user-led): walk the diff — persistence adapter, validation hierarchy,
   settings/app-factory, skill installs — before committing the first checkpoint.
1. **HARDEN-05 — set up the rest of the tech-stack skills:** author local `sqlmodel` / `pytest` / thin
   `pydantic` skills modeled on the FastAPI skill (SKILL.md + `references/`). NO separate `sqlalchemy` skill
   (folds into `sqlmodel`). Vet any further registry skills against the matrix in `DECISIONS.md`/memory.
   → next session (alongside the review above).
2. Close the E2E gap: deterministic **offline/fake LLM** + persistence-backed route so generate→persist is
   L3-testable without a key; add `prompts/episode_generation/v1.jinja`.
3. Persist the `StoryBible` canonical store in SQLite (mirror the episode-log adapter).

## Next — at/after the event (brief known)
- Capture the brief in `CLAUDE.md` (INIT-01); translate into product features (one-session-sized + `verification`).
- Pick the LLM/agent framework (LangChain/LangGraph/CrewAI/Pydantic-AI/raw) + wire behind `LLMPort` with the
  OpenAI key; single client wrapper logs model id/params/tokens/cost.
- Set up the `prompts/` registry (first template `name/v1.jinja`).

## Fan-fiction corpus (in progress, branch `worktree-reddit-fanfic-scraper`)
- [x] **FANFIC-01** scraper: novel/film in → relevant fan-fiction prose out, saved as KB-ready JSONL. DONE.
- [x] **FANFIC-02** live harvest produces a real non-empty corpus. DONE (The Witcher, 4,073 words).
- [x] **FANFIC-03** yield + precision: round-robin alias search, Wikipedia-search title resolution,
      tag-key/word-boundary matching, explicit-declaration rule, quality floors. DONE.
- [x] **FANFIC-04** Branch Oracle - canon decision points with 2-4 player-facing options. DONE.
- [x] **FANFIC-05** OD-2 novel-vs-screen canon discriminator (wiki entity vocabulary). DONE.
- [x] **FANFIC-06** EXT-1 output contract written down, closing OD-3. DONE.
- [x] **FANFIC-07** IV&V audit — 4 defects found and fixed (prose-deleting boilerplate regex, silent
      chapter truncation, sink/CLI artifact divergence, script/style leakage). Suite 237→286.
      Corpus schema 1.1→1.2. DONE.

### IV&V follow-ups (session 6) — deliberately NOT fixed; scraper is closed for hackathon purposes
> Ordered by risk. None of these block the demo. Do not start any of them before the M-features.

- [ ] **F-7 — prose-gate thresholds are borrowed from the wrong problem.** `words >= 500` AND
      `quotes_per_1k >= 5` were measured for *Reddit prose-vs-discussion*, then applied per-chapter to
      Wattpad, where that problem doesn't exist. Rejected 7 chapters across a 4-work harvest (~14%),
      including one work's opening chapter. **Needs a decision, not a fix** — and it is tunable without
      touching code: `--min-words 200 --min-quotes-per-1k 0`. Note the current gate systematically drops
      dialogue-free introspective chapters, which is a poor fit for Dexter's first-person interiority.
- [ ] **`alias_expander.py` (306 lines) has ZERO tests** — `--kind` disambiguation is load-bearing
      (without it "Dexter" resolves to a warship) and completely unverified.
- [ ] **Wattpad `search()` untested** — round-robin across aliases, pagination exhaustion, and the
      "page returns only already-seen ids" case, which can burn requests without growing the result set.
- [ ] **`get_with_retry` ignores `Retry-After` on 429**, and `_pause()` is skipped on the failure path,
      so a run that hits errors is *less* polite than one that succeeds. Politeness, not correctness.
- [ ] **Tell the KB team about `support: 1`.** Every premise group in the real Dexter harvest has
      `size: 1` — the "N independent humans branched off one canon node" story does not hold at this
      corpus scale. Code assuming multi-member groups will silently get empty results.

- [ ] **Link branches to canon MOMENTS** - blocked on the Canon Kernel exposing a resolvable scene id
      (`(chapter, order_in_chapter)` or a documented `Scene.id`). Largest remaining integration gap; see
      `docs/EXT-1-scraper-output-contract.md` section 6. **NEXT.**
- [ ] **Decide OD-2 for real.** The wiki now proves 3 of the 5 spec cast members have different NOVEL names
      (Debra->Deborah Morgan, Doakes->Albert Doakes, LaGuerta->Migdia LaGuerta), and our best Dexter branch
      (*Set Free*) is screen-canon. Pick novel or screen canon deliberately.
- [ ] Near-duplicate detection beyond exact SHA-256 — `datasketch` MinHash (word-5-gram, `num_perm=128`,
      J=0.85) plus `MinHashLSHEnsemble(0.8)` for the chapter-inside-full-story-repost containment case.
- [ ] Second source adapter behind the existing port (SpaceBattles / SufficientVelocity / RoyalRoad are all
      reachable; XenForo threadmarks give chapter structure). No pipeline change required.
- [ ] Serialized-work reassembly across multi-part posts + language filtering (`ftfy`, `lingua`).
- [ ] **Separate branch:** wire the corpus into the knowledge base (schema contract is
      `CORPUS_SCHEMA_VERSION` in `adapters/outbound/fanfic/jsonl_sink.py`).

## Later
- `evals/` harness (coherence / continuity / on-genre, LLM-as-judge) — non-blocking.
- API + CLI delivery adapters (thin).
- Add `api`, `git`, `security` rules under `.claude/rules/` (`paths:`-scoped `.md` files) as needed.

## Parking lot (ideas, not committed)
- _add here_

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

## 🔴 IV&V AUDIT (session 6, 2026-07-25) — deferred remediation queue

> Source: an independent verification pass over the knowledge-base branch. `make check` was GREEN
> (110 passed) throughout, so **none of this is caught by the gate**. Every KB-* item below was
> reproduced by an executable probe, not inferred by reading. Deferred by maintainer decision on
> 2026-07-25: the priority is a working core product, not audit cleanup. Promote into
> `feature_list.json` when scheduled.

### A. Code defects — CRITICAL (guard breach / data loss)
- [x] **AUD-C1 (FIXED 2026-07-25) — the vector lane ignores `FactStatus`.** `vector_store._is_visible()` re-implements only
      2 of the 3 clauses of `Fact.is_visible_to`; `VectorRow` has no `status` column, so a QUARANTINED
      fact the canon store hides is fully searchable by similarity. Two copies of one security predicate,
      and the copy drifted. Fix: store the guard inputs and call the ONE domain predicate; delete
      `_is_visible`. (~1–2h)
- [x] **AUD-C2 (FIXED 2026-07-25) — `supersede()` bypasses domain validation and can brick a store.** It mutates `FactRow`
      attributes directly, so every `Fact` validator is skipped on write while still enforced on read.
      `closes_at < valid_from` writes fine, then `get()`/`all_facts()` raise `ValidationError` on that
      fork **forever**, with no delete path to repair it. Fix: re-validate through `Fact` before writing.
      (~2h)
- [x] **AUD-C3 (FIXED 2026-07-25) — double supersession leaves two live successors.** No check that the target is still
      ACTIVE; the update is not conditional on "was NULL". Violates documented invariants I-2, I-3 and
      I-8. Fix: raise if `row.status is not ACTIVE`. (~2h)

### B. Code defects — HIGH
- [ ] **AUD-H1 — no canon⇄vector synchronisation.** No shared transaction, and `VectorStorePort` has no
      `remove`/`update`. Every supersession silently desynchronises semantic recall: the retired fact
      still ranks, the replacement is never indexed. Fix: `remove(fact_id)` on the port + a
      `CanonIngestService` owning both writes as one unit of work. (~4h)
- [x] **AUD-H2 (FIXED 2026-07-25) — vector store has no idempotency.** `fact_id` is indexed, not unique; re-ingestion
      produces duplicate rows that consume the `k` budget with identical hits. (~1h)
- [x] **AUD-H3 (FIXED 2026-07-25) — `as_of()` has no tie-break.** `ORDER BY valid_from DESC` is not a total order; with two
      rows sharing `valid_from` an INVALIDATED row can win on arbitrary SQLite row order. Add
      `recorded_at DESC` + prefer ACTIVE. (~1h)
- [x] **AUD-H4 (FIXED 2026-07-25) — `knower_scope` carries no acquisition time.** `is_visible_to` ANDs `is_revealed_by` for
      EVERY knower, so a character can never know anything before the audience does — "Doakes suspects at
      ch5, the audience learns at ch9" is unrepresentable. This is M5's premise. Fix:
      `frozenset[str] | None` → `dict[str, ChapterIndex]` (knower → learned-at). **Cheapest before
      ingestion writes data.** (~1 day, schema-wide)
- [ ] **AUD-H5 — the KB has zero production callers.** `bootstrap.py` wires none of `SqliteCanonStore`,
      `SqliteVectorStore`, `WorkingMemory`, `HashingEmbedder`; `Container` has no field for them; no API
      route or CLI command reaches canon. It is a library beside the app, not a subsystem in it. (~3–4h)
- [x] **AUD-H6 (PARTLY FIXED 2026-07-25 — fork lineage done; entities/scenes/commitments still unpersisted) — fork resolution is documented but does not exist.** `Fork`'s docstring promises
      parent→root shadowing; no code does it, `parent_fork_id` appears only in tests, and there is no
      fork table. Same for `CanonEntity`/`Scene`/`Commitment`/`Flag`/`Source`: zero source consumers,
      zero persistence. Partly covered by KB-13; the ancestry query is untracked.

### C. Code defects — MEDIUM
- [ ] **AUD-M1** — `MemoryPacket.graph` is built from budget-TRUNCATED facts, so `related_within()`
      silently returns a smaller, wrong answer under budget pressure with no signal to the caller.
- [x] **AUD-M2 (FIXED 2026-07-25)** — "deterministic assembly" holds only while `recorded_at` is unique; `all_facts` orders
      by it alone and SQLite tie order is arbitrary. Bulk ingest with one timestamp breaks the guarantee.
- [ ] **AUD-M3** — six `feature_list.json` verification commands use `-m unit`, which is neither a
      registered marker nor carried by any test. They fail correctly today (exit 5) but are
      **permanently unsatisfiable** — writing the test will not make them pass. Register the marker or
      switch to path-based selection.
- [ ] **AUD-M4** — SQLite opened `check_same_thread=False` for ASGI, but no WAL, no `busy_timeout`, no
      pool config: two concurrent writers get an immediate `database is locked`.
- [ ] **AUD-M5** — duplicate `append()` surfaces a raw `IntegrityError` across the port boundary instead
      of a domain error (violates the project's own error-hierarchy rule).
- [ ] **AUD-M6** — every guarded query is a full-fork table scan materialised in Python; `assemble()`
      does two. The `revealed_at`/`status` indexes are never used. Fine at demo scale, undocumented.
- [ ] **AUD-M7** — `withheld_count` counts QUARANTINED rows, inflating the user-facing "what you don't
      know yet" number with never-canon junk.
- [ ] **AUD-M8** — documented invariant I-1 says `valid_to > valid_from`; the code allows `==`.
- [ ] **AUD-M9** — `api/app.py` runs `app = create_app()` at MODULE level, so merely importing it builds
      a container, configures logging and creates `./story_engine.db` relative to the CWD. Confirmed:
      the test suite leaks that file into the repo root. Move behind a factory / `if __name__`.

### D. Test-suite improvements (audited, deferred — the suite passes but over-claims)
- [ ] **AUD-T1** — the flagship leak test's oracle is **tautological**: `expected` re-implements
      `is_revealed_by`, so it compares the implementation to a copy of itself. Replace with hand-written
      literal expected sets per cutoff. (`test_canon_invariants.py:80`)
- [ ] **AUD-T2** — `test_i2_exactly_one_live_fact_per_key_after_supersession` **does not test I-2**: it
      counts ACTIVE rows across the whole fork with two facts present, grouping by nothing and checking
      story time not at all. Rename or make it real, and add the double-supersede case.
- [x] **AUD-T3 (FIXED 2026-07-25)** — vector-store coverage gaps: no status test, **no fork-isolation test at all**, no
      duplicate-`add`, no post-supersede staleness, no `k=0`/`k>n`/empty-store/dimension-mismatch.
- [x] **AUD-T4 (FIXED 2026-07-25)** — no negative tests on the `supersede` write path (invalid `closes_at`, already-
      invalidated target, duplicate id, fork mismatch).
- [ ] **AUD-T5** — the working-memory unit tier makes **zero assertions about `packet.graph`**, though
      KB-11's evidence claims the packet carries its own guarded graph.
- [ ] **AUD-T6** — KB-11's evidence claims focus entities survive the budget "on BOTH fact endpoints";
      only the `subject_id` endpoint is tested. The `object_id` branch is asserted by nothing.
- [ ] **AUD-T7** — `test_assemble_is_deterministic` runs against a fake store that is deterministic by
      construction, so it cannot exhibit the real ordering failure (AUD-M2). Re-test against real SQLite
      with tied `recorded_at`.
- [x] **AUD-T8 (PARTLY FIXED 2026-07-25 — vector ordering now asserts monotonicity; working-memory items remain)** — weak assertions: `test_budget_bounds_the_packet` asserts only the count, not which
      facts; `test_focus_entities_...` asserts membership, not priority; `test_as_of_is_fork_scoped`
      checks one direction only; `test_results_are_ordered_by_descending_similarity` asserts identities
      that are an artifact of the placeholder embedder (assert score monotonicity instead).
- [x] **AUD-T9 (FIXED 2026-07-25)** — vector tests hardcode `knower="audience"` instead of importing the `AUDIENCE`
      sentinel; changing the constant leaves them green while production breaks.
- [ ] **AUD-T10** — add a regression test for the import-time side effect in AUD-M9.
- [ ] **AUD-T11 — DECISION NEEDED.** `related_within`'s docstring says "excluding the start", the code
      includes it when a cycle leads back, and `test_related_within_terminates_on_a_cycle` blesses the
      current behaviour. A test currently validates behaviour that contradicts its own spec. Decide
      which is correct (recommendation: exclude the start — a UI asking "who is Dexter connected to?"
      should not list Dexter), then fix code+test or the docstring.
- [ ] **AUD-T12** — `test_memory_storage_e2e.py` is ≈80% a subset of `test_hybrid_kb_e2e.py`; merge or
      differentiate. `test_visible_and_withheld_partition_the_fact_set` is duplicated near-identically
      across two files.
- [ ] **AUD-T13** — spec debt: **4 of the 9 documented invariants have no test at all** (I-6 projection=
      replay, I-7 idempotent replay, I-8 no lost update, I-9 monotonic record time), and I-5 is tested as
      a line rather than the 2D story-time × record-time grid `tests/README.md` requires. `testing.md`
      also mandates a Hypothesis `RuleBasedStateMachine` over append/supersede/query-as-of, which does
      not exist (`hypothesis` is not even a dependency) — that is precisely the surface AUD-C2/C3 live on.
- [ ] **AUD-T14** — zero performance tests and zero concurrency tests; `shared/retry.py`, `shared/text.py`
      and `cli/main.py` are at 0% coverage.

> **Status 2026-07-25:** the two PRODUCT blockers (AUD-H4 per-knower acquisition time, AUD-H6
> fork lineage) and the CRITICAL guard/write-path defects are FIXED and covered by regression
> tests; `tests/e2e/test_product_flow_e2e.py` walks the whole product scenario. Everything still
> unchecked above remains open. AUD-H1 is now cheap: `VectorStorePort.remove()` exists, so only
> the ingest service that pairs the two writes is left.

> **Coverage note, so it is not misread later:** `canon_store.py` measures 98% line coverage and
> `vector_store.py` 95% while both carry CRITICAL defects. Line coverage says which lines ran, not which
> behaviours were checked. Do not treat the 86% total as evidence of correctness.

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

## 🔵 FUTURE — context-aware RAG over source documents (NOT this session)

> Added 2026-07-25 at the maintainer's request. **Reference, not a dependency.** This session builds the
> memory system only; document-RAG comes later.

**Reference implementation:** [`patchy631/ai-engineering-hub/notebook-lm-clone`](https://github.com/patchy631/ai-engineering-hub/tree/main/notebook-lm-clone)
— an open-source NotebookLM-style document-grounded assistant with citations.

**What it actually is** (fetched and read 2026-07-25, not assumed): PyMuPDF for PDF/TXT/Markdown parsing ·
AssemblyAI for audio with speaker diarization · Firecrawl for web · **Milvus** vector DB · **Zep temporal
knowledge graphs** as the memory layer · Kokoro TTS · Streamlit UI · OpenAI LLM. Chunks are overlapping;
retrieval is top-k semantic with metadata (page numbers, timestamps) carried through for citation. No
reranking. `src/` splits into audio_processing, document_processing, embeddings, generation, memory,
podcast, vector_database, web_scraping.

**TAKE — the genuinely reusable part:**
- **PyMuPDF page-accurate parsing.** This is the piece that matters for us: our `Provenance` requires
  `chapter` + `char_span` + a verbatim fragment, and page-accurate extraction is exactly how a citation
  survives back to the source. Directly serves the receipt (`project_context.md` §5.4).
- **Citation metadata threaded through chunking into retrieval results.** Same discipline we need — a
  retrieved chunk that cannot name where it came from cannot produce a receipt.
- Its module split (`document_processing` / `embeddings` / `vector_database` / `generation`) is a sane
  shape to mirror for an ingestion pipeline.

**LEAVE — and the reasons are already documented, do not relitigate:**
- **Its memory layer (Zep).** We analysed Zep/Graphiti in depth (`Knowledge-Base/03`, `/10`): excellent
  bi-temporal substrate, but **no epistemic scope, no commitment lifecycle, no telling-time bound.** Our
  per-character filtered views are the product's core mechanic and Zep cannot express them. We already
  built the better-fitted layer.
- **Milvus.** We are going to **Databricks Vector Search** — sponsor-aligned, and Delta Sync means the
  index maintains itself off the same Delta table that already backs canon time-travel.
- Streamlit/Kokoro/AssemblyAI/Firecrawl — out of scope; text-first, and audio is SHOULD-tier (S1).

⚠️ **License is NOT stated in the repo.** Do not vendor code from it without checking — default copyright
applies otherwise. The *architecture* is free to learn from; the source is not free to copy. (Same trap
that ruled out SymbolicToM.)

**When this becomes real:** after the memory system is complete and the ingestion pipeline needs to read
actual novel PDFs. Blocked on nothing technical — it is a sequencing choice, not a dependency.

## Later
- `evals/` harness (coherence / continuity / on-genre, LLM-as-judge) — non-blocking.
- API + CLI delivery adapters (thin).
- Add `api`, `git`, `security` rules under `.claude/rules/` (`paths:`-scoped `.md` files) as needed.

## Parking lot (ideas, not committed)
- _add here_

# Backlog

> Human-readable, ordered task queue. Top = next. As a task becomes concrete and verifiable, promote it into
> `feature_list.json` (with a `verification` command, `passes:false`). `feature_list.json` is the machine
> source of truth; this file is for humans to plan and reorder.

## 🔵 POST-DEMO / STRETCH — Databricks agent memory + vector search (added session 8, 2026-07-26)

> **Requested by the maintainer.** Parked here deliberately: it is **not** on the demo path, and
> session 8's plan (`docs/superpowers/plans/demo-path-integration.md`) is a closed fence. Do not start
> this before the P0 integration tasks are green.

**Why it is plausible:** the maintainer has a real Databricks workspace for this hackathon (AI Dev Kit
installed 2026-07-25), so this is a sponsor-visible integration with the infrastructure already
provisioned — Vector Search endpoints + indexes, and Unity Catalog / Lakebase for durable agent state.

**Why it must NOT be a swap of what exists:**

- **The canon store stays the source of truth.** `project_context.md` §4.4 and this repo's one
  architectural rule allow **one store and two derived lanes** — a graph projection and a vector
  index. Databricks Vector Search would be a **replacement implementation of the existing
  `VectorStorePort`**, not a new lane, and not a second home for facts.
- **The spoiler guard is non-negotiable and must stay a PRE-filter.** `SqliteVectorStore` applies
  `domain.models.canon.is_visible` *before* similarity, so a withheld fact is never a candidate. A
  hosted index that filters *after* retrieval — or worse, returns text the guard never saw — is an
  unguarded fourth read path and a spoiler side-channel. Any Databricks adapter must push the
  epistemic filter down into the query (`filters=` on the index) **and** re-assert `is_visible` on the
  way out. Belt and braces, because a leak is a hard build failure.
- **Per-character memory is NOT per-agent storage.** Do not reach for a hosted "agent memory" product
  that gives each character its own bucket. Character memory here is a *filtered view* over one world
  state (`Fact.knower_scope` + `store.visible_to()`), which is exactly what makes `replay_as` a
  parameter change rather than a rewrite. Five separate memories would turn the closing demo beat into
  a rebuild and violate §4.4's uniform state schema.
- **Offline must survive.** The demo's stage guarantee is that it runs with no network and no API key.
  A Databricks lane must be *selectable* (like `llm_provider`), never mandatory — the same shape as
  `LLM_PROVIDER=scripted`.

**Shape of the work, if it is picked up:**

| Step | Thing | Note |
|---|---|---|
| 1 | `DatabricksVectorStore` implementing the existing `VectorStorePort` (`add`/`remove`/`search`/`ids`) | one adapter file; no pipeline change — that is what the port is for |
| 2 | A real embedder behind `EmbedderPort` (Databricks serving endpoint, or `fastembed` locally) | `HashingEmbedder` is near-random on natural language; already on this backlog |
| 3 | `vector_provider: Literal["sqlite","databricks"]` in settings, wired in `bootstrap.py` only | composition root is the only place adapters are chosen |
| 4 | Guard-parity test suite run against BOTH implementations | the leak suite must pass identically, or the adapter does not ship |
| 5 | Optional: Lakebase/UC for durable playthrough state, replacing the SQLite run repository | only after the API path is proven; same port, same tests |

**Acceptance:** the existing spoiler-guard leak tests pass **unchanged** against the Databricks
adapter, and `LLM_PROVIDER=scripted` + `VECTOR_PROVIDER=sqlite` still runs the whole demo offline.
**If the guard cannot be pushed into the hosted query, stop and report it** — do not ship a lane that
filters after retrieval.

**Est.** 3–4 h for steps 1–4, and it buys nothing the judge can see beyond the sponsor logo, which is
why it sits below every demo-path item.

---

## 🟢 NOW — what is left after the demo shipped (end of session 7, 2026-07-25)

> **The demo runs:** `uv run story-engine play --auto --turns 5 --replay-as deborah` — no API key.
> `make check` green, **497 tests**, **33/40 features**. `demo.md` remains the scope fence; its cut
> ladder (§5) is still the answer if the runway tightens.
>
> **Done this session:** T1 (superseded — see note), T2, T3, T4, T7, T8, T10, and M6.

| # | Task | Est. | Why it matters |
|---|---|---|---|
| **T0 + T5 → M4** | **Bind the Branch Oracle to real mined fan fiction.** ⚠ **THE HONESTY GAP.** `project_context.md` §5.2 and the pitch both say choices come from divergences fan fiction actually wrote. They come from an authored table in `resources/dexter_demo.py` — only the `source_work_id` values are genuine. **Step one is data:** `data/` is empty (the corpus lived in the deleted worktree), so re-run `story-engine harvest "Dexter" --kind novel --show-branches` + `wiki-index "Dexter"` — **needs network**. Anything that stays authored must keep `source_work_id=None` so the distinction stays auditable. | 2.5 h | a true claim beats a pretty one |
| M8 | **Traits and goals on the character record.** The uniform-schema half is done; this is the disposition half, and it closes a MUST cheaply. | 1 h | closes M8 |
| M7 | **The verifier (§5.5).** Separate *intentional divergence* (a consequence the player chose — expected) from *accidental contradiction* (drift nobody chose — an error). A verifier that flagged every divergence would be useless here, because deliberately breaking canon is the entire genre. | 1.5 h | closes M7 |
| T6 | **Free-form intent router (snap-to-branch).** Embed the player's typed intent, match it to a mined branch, route to the pre-validated branch; below threshold, generate a candidate and verify *before* applying (also closes OD-4's degradation path). **Blocked on M4** — there is nothing real to snap to yet. | 2 h | beats 4, 5 |
| T9 | **API + frontend rewire.** The demo is terminal-only. The frontend's `CanonClient` still targets the superseded single-flip contract (`getMoments`/`postDivergence`/`postRegenerate`) while the backend now serves a turn loop. Keep the mock alive as the stage fallback. | 3 h | presentability |
| — | **A real embedder behind `EmbedderPort`.** Measured on the full novel: verbatim recall@5 **8/8**, but natural-language retrieval is near-random — exactly as `HashingEmbedder`'s own docstring predicts. The guard held perfectly (**0 leaked** of 20 hits at ch3). `fastembed` (ONNX, offline, no torch) is the fit; it is also what `notebook-lm-clone` used. | 1 h | retrieval quality |

**Note on T1.** Superseded rather than done: the maintainer established that **Claude Code is the
model** for this project, so scenes are authored in-session and replayed deterministically via
`ScriptedLLM` — which is also the demo-safe choice, since a stage run cannot then die to a timeout, a
rate limit, or an unlucky sample. `prompts/render_scene/` v1 **and** v2 exist as versioned assets. A
live provider adapter remains a one-file swap behind `LLMPort` if a key ever lands.

**Still-open decisions** (`demo.md` §7): **D-2** snap-to-branch vs true free-form (recommend
snap-to-branch) · **D-3** novel vs screen canon (OD-2) — **this bites the moment M4 starts**, because
our canon is novel-based and fan fiction is predominantly screen-based. **D-1 is closed** (the PDF is
at `data/external/Darkly-Dreaming-Dexter-1.pdf`).

⚠ **`research/Pocket FM Hack/` is a nested git repo.** Leave it untracked. `git add`-ing it creates a
mode-160000 gitlink — precisely the mess this session had to unpick for the two worktrees.

## Product phase ordering (session 5, 2026-07-25) — superseded in ordering by the queue above

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

✅ **License: MIT** (© 2024 patchy631), verified 2026-07-25 by cloning the repo and reading `LICENSE` at
its **root**. An earlier note here claimed no license was stated — that check had only looked inside the
`notebook-lm-clone/` subdirectory. Vendoring is fine; retain the copyright notice.

**STATUS: DONE (session 7, 2026-07-25).** Absorbed into `domain/chunking.py` +
`adapters/outbound/ingestion/pdf_document_source.py`. Three upstream behaviours were deliberately
changed — each is documented in the module docstring with a regression test:
1. **Silent data loss.** `start = max(start + chunk_size - overlap, end)` skips past `end` whenever the
   sentence snap retreats further than the overlap covers, dropping those characters entirely. A dropped
   span is a fact that exists in the novel and can never be cited.
2. **Quote/offset disagreement.** Upstream stripped the chunk text but kept the unstripped offsets, so
   `text[char_start:char_end] != quote`. A citation that cannot resolve to its own coordinates is not one.
3. **Page-relative offsets → chapter-relative.** Decisive, not cosmetic: the spoiler guard gates on
   *chapter* (`visible_to(fork, knower, chapter)`), and a page number cannot answer "has this been
   revealed yet?".

Its **retrieval path was rejected**: `vector_db.search(query_vector, limit=top_k)` applies no epistemic
filter, so wiring it in would create a second, unguarded read path beside `store.visible_to()` — exactly
the spoiler side-channel `.claude/rules` warns about. Its citation-discipline *prompt* is still worth
lifting into `prompts/` when T7 (the receipt surface) is built.
## 🔵 FUTURE — absorb the agent harness (NOT this session; queued at the maintainer's request)

**Reference:** [`NousResearch/hermes-agent`](https://github.com/nousresearch/hermes-agent) — **MIT,
© 2025 Nous Research** (verified 2026-07-25 by cloning and reading `LICENSE`). Requested for its tool
abstraction, agent loop, and self-improvement loop.

**Scale check, measured not guessed.** `agent/` holds 100+ modules and `tools/` holds 102.
`agent/conversation_loop.py` is **6,645 lines**; `agent/tool_executor.py` is **1,827**. This is a
shipped desktop product, not a snippet source — **the patterns port, the code does not.** Budget for
reading and re-implementing, never for pasting.

**Correction worth carrying forward:** its "self-improvement loop" is *not* a model improving itself.
`agent/learn_prompt.py` is explicit — `/learn` builds **one prompt** instructing the agent to author a
reusable `SKILL.md` with tools it already has, with *"no separate distillation engine and no model-tool
footprint."* Improvement is **skill accretion into files**, across sessions. It therefore cannot help a
single five-minute demo, which is why it sits here rather than in the NOW queue.

**TAKE (as patterns, when the turn loop exists):**
- `agent/conversation_loop.py` — turn structure: model call → tool dispatch → retry/fallback →
  compression → post-turn hooks. Our `PlaythroughService` (T4) is the same shape, much smaller.
- `agent/tool_executor.py` + `tools/` — the tool-registry abstraction and sequential-vs-concurrent
  dispatch.
- `agent/context_engine.py`, `context_compressor.py` — bounded context assembly. Compare against our
  `services/working_memory.py`, which already does the epistemic version of this.
- `agent/verification_evidence.py`, `verify_hooks.py`, `verification_stop.py` — evidence-gated stopping.
- `agent/learning_graph.py`, `learning_mutations.py`, `learn_prompt.py` — the skill-accretion loop.

**LEAVE:** its provider adapters (we have `LLMPort`), billing/credits/rate-limit machinery, browser and
computer-use tools, TUI/desktop/web surfaces, MCP plumbing — all irrelevant to a text playthrough.

**Sequencing:** blocked on T4. Absorbing an agent loop before we have a turn loop to absorb it *into*
would be building the harness for a product that does not exist yet.

### Also starred, and relevant (assessed 2026-07-25 from the maintainer's GitHub stars)
- **[`567-labs/instructor`](https://github.com/567-labs/instructor)** — structured outputs for LLMs.
  **Highest-value item for T1.** `pyproject.toml` already carries the placeholder
  `# Structured output: "instructor>=1"`, and `.claude/rules/llm-storytelling.md` §5 requires model
  output to be validated at the boundary with Pydantic before it reaches the core. Pull this in with
  the LLM adapter rather than hand-rolling parse-and-validate.
- **[`opendatalab/MinerU`](https://github.com/opendatalab/MinerU)** — PDF/Office → LLM-ready
  markdown/JSON. A stronger extractor than raw PyMuPDF for real novel layouts (columns, headers,
  footnotes). Costs ML model weights and startup time. **Upgrade path for T2 only if PyMuPDF's output
  on the actual Dexter PDF proves too noisy to chapter-split** — measure before adopting.
- **[`activeloopai/hivemind`](https://github.com/activeloopai/hivemind)** — "turns your traces into
  reusable skills across agents". The same skill-accretion idea as hermes `/learn`, at a fraction of
  the size. Prefer it as the reference if the self-improvement loop is ever built.
- **[`promptfoo/promptfoo`](https://github.com/promptfoo/promptfoo)** — prompt/RAG testing. Overlaps
  our Tier-2 eval lane (`evals/`, DeepEval per `.claude/rules/testing.md`). **Do not adopt a second
  eval framework** without re-running the skill-vetting matrix; one is already chosen.

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

## 🔴 KNOWN GAP (session 8, 2026-07-26) — the graph lane is empty on the DEMO fork

Found by the full-scenario e2e (`tests/e2e/test_full_scenario_e2e.py`), reported rather than papered over.

**What:** every fact in the demo's authored canon (`resources/dexter_demo.py` anchors, and the
consequences `PlaythroughService._fact_for` writes) is stored with `object_literal` and never
`object_id`. `LoreGraph.from_facts` only projects an edge for a fact carrying `object_id` — per
`domain/graph.py`, *"a literal-valued fact is an attribute, not a relation: no second endpoint."*
So the graph projection is **structurally empty for the entire Dexter demo, no matter how many turns
are taken**, and the "graph updates" step of the acceptance scenario is not exercised on that fork.

**How narrow it is (this matters):** the graph lane itself is **not** broken. Task 7's guard-parity
test drives it against **ingested novel** facts and includes a passing positive control at ch3. It is
specifically the four authored demo anchors that cannot produce edges.

**Why it was not fixed in session 8:** it is a property of the authored demo *data*, not of the graph
code; the lane is proven on real ingested data; and S2 (the ripple visualisation), which is the only
surface that would show a judge an empty graph, is an unbuilt SHOULD.

**If picked up:** give the demo anchors genuine `object_id` relations (e.g. `dexter --knows--> brian`
rather than a literal string) so the demo fork projects real edges. Check `PlaythroughService._fact_for`
too — it writes `object_literal` unconditionally. Then assert a non-empty `LoreGraph.edges` in the
scenario test, replacing the current honest `== ()` assertion.

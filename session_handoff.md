# Session Handoff

> The single per-session **clock-out** note. Overwrite at the end of each session. At session start, read
> this first, then `PROGRESS.md` and `DECISIONS.md`. Keep it short.

## Last session — 2026-07-25 (session 6, IN-HACK): the Knowledge Base, built and E2E tested

**Branch:** `worktree-knowledge-base` (worktree `.claude/worktrees/knowledge-base`), **rebased onto main**.
Safety refs if anything looks wrong: `backup/kb-pre-rebase` (`ae31f13`), `backup/kb-pre-integrate`.

**Gate: `make check` GREEN — 110 passing** (70 unit · 40 integration + e2e against real on-disk SQLite).

### What was built
Three stores over ONE tri-temporal fact model — **story time** (true in the world) · **telling time**
(the audience learned it) · **record time** (this store learned it):

| Layer | What it does | Feature |
|---|---|---|
| Canon store | SQLite; as-of queries; **atomic** supersession (close window + insert replacement in one txn) | `KB-07` |
| Graph projection | Derived adjacency, cycle-safe multi-hop, relationship diff. **No graph DB** — a service dependency breaks the offline constraint | `KB-10` |
| Vector store | Semantic recall, guard as a **pre-filter**; dependency-free embedder behind `EmbedderPort` | `KB-12` |
| Working memory | Bounded, deterministic per-character packets | `KB-11` |
| Schema + invariants | Facts, forks, entities, scenes, commitments, flags, 6 pure predicates | `KB-01` |
| Leak suite + E2E | Set-equality leak tests; two restarts; guard asserted at every layer | `KB-09`, `KB-08` |

### The one thing to understand about the design
**The epistemic guarantee comes from what is ABSENT from the assembled context, not from instructing a
model to withhold.** A fact never placed in the prompt cannot leak. That is why the guard is applied at
*construction* in `LoreGraph.from_facts`, why `WorkingMemory` reads only from `store.visible_to()`, and why
the vector store filters *before* ranking (a post-filter on top-k silently returns fewer than k and hides
the leak in the gap). `project_context.md` §4.4 reached the same conclusion independently.

### Six real bugs the tests caught — all in the plan I wrote and self-reviewed
mypy-unsafe `Provenance(**dict)` · SQLite silently dropping `tzinfo` · `as_of` hiding superseded facts from
their own valid window · `conflicting_active_facts` ignoring `assertion_mode` (would have flagged a
character's LIE as a canon contradiction, at BLOCKING severity) · focus-sort checking only one fact
endpoint · superseded facts invisible at *every* chapter. **None were visible from inside the plan.** They
surfaced because the tests assert stated properties rather than written code.

## Next step / how to resume

1. **UNBLOCK THE AGENT LOOP FIRST (~1h): seed 20–40 hand-authored facts** over one scene slice + the 5 cast
   members. The API is stable and tested, so an agent built against seeded data works unchanged when real
   ingestion lands. Do NOT wait for extraction — it is the largest, least predictable chunk, and sequencing
   it first puts the riskiest integration last.
2. **`KB-13` (~half a day):** fork write path + derive `knower_scope` from `Scene.witnesses`. These are the
   only KB items the loop genuinely needs — M5's compounding condition (§4.2) and M6 both depend on them.
   OD-1 is settled as **FORK**, so it is unblocked.
3. Then: verifier + citations (M7), and ingestion (M1 / EXT-1).

## Carry forward — things that will bite if forgotten

- ⚠️ **`project_context.md` §5.3 wants THREE knowledge channels** (witnessed / told / inferred); we store
  one `knower_scope` set. Enough for M5's guarantee (the filter only answers *does X know this*), not enough
  to narrate *how* someone learned something. Additive to fix — cheap now, awkward after ingestion runs.
- ⚠️ **Shared worktree + shared git index bit THREE times this session** (mine once, a subagent once, the
  parallel session once — its commit swept 164 files). `git commit` commits the whole INDEX, not the paths
  you just added. Use `git commit -- <pathspec>`, and never `git add` while another agent is live.
- ⚠️ **Implementer self-reports are not evidence.** Three of five overstated what they had verified — a
  hedged gate claim, a report file claimed but never written, a test count that needed checking. Every
  shipped line was still correct, but only because reviewers were told to RUN the gate rather than read
  about it. Keep that instruction in every review dispatch.
- **Databricks Vector Search** plugs in as a second adapter behind the existing `VectorStorePort` — Delta
  Sync, HYBRID (vector + BM25) search, and server-side filters so the guard runs at the index. The offline
  embedder stays as demo insurance. Open question: `knower_scope` is a set, which is awkward as a
  server-side filter — recommend denormalising to one index row per fact per knower (5 rows, trivial at
  this scale) so the whole guard stays server-side.

# Session Handoff

> The single per-session **clock-out** note. Overwrite at the end of each session. At session start, read
> this first, then `PROGRESS.md` and `DECISIONS.md`. Keep it short.

## Last session — 2026-07-25 (session 6, IV&V AUDIT → two product blockers fixed)

**Branch:** `worktree-knowledge-base` (worktree `.claude/worktrees/knowledge-base`).
**Framing:** an independent verification pass over the knowledge base, then remediation of the
defects that blocked the product. `make check` is GREEN — **138 passed** (was 110).

### The one thing to read next
**`tests/e2e/test_product_flow_e2e.py`** — it walks the whole product scenario (character select →
per-character memory → citation receipt → guarded semantic recall → player choice forks the story →
replay as another character → restart) against a real on-disk database. Fastest way to see what the
KB can and cannot currently carry. It is written against `project_context.md`, not against the
implementation — which is why it found things the 110 green tests did not.

### What I did
1. **Audited the KB and reproduced 8 defects with executable probes** while the gate was green.
   All findings are in `BACKLOG.md` § "🔴 IV&V AUDIT", with fixed items checked off.
2. **Fixed the two PRODUCT blockers:**
   - **Per-knower acquisition time.** `Fact.knower_scope` was a timeless `frozenset[str]`, and
     `is_visible_to` gated EVERY knower on the audience's `revealed_at`. A character could not know
     anything before the audience did, so all five cast members received identical packets and M5/S3
     were unbuildable. Now `tuple[Awareness, ...]` — knower + the chapter they learned it — with
     `AUDIENCE` as an ordinary knower. Call sites accept a `{knower: chapter}` mapping.
   - **Fork lineage.** `fork_id` was an opaque partition key, so a player's branch contained their
     one choice and none of the novels. Added the `canon_fork` table plus
     `register_fork`/`get_fork`/`lineage`; `all_facts` resolves fork → parent → … → root with a
     divergence cap and nearer-fork shadowing.
3. **Fixed the CRITICAL defects in the same code paths:**
   - the vector lane ignored `FactStatus`, so a QUARANTINED fact was searchable — the guard is now
     ONE function, `domain.models.canon.is_visible`, called by both `Fact` and the vector store;
   - `supersede()` skipped every domain validator and could write a row that made the whole fork
     permanently unreadable — it re-validates through `Fact` now;
   - double supersession left two live successors (I-2/I-8) — rejected;
   - `as_of()` had no tie-break on equal `valid_from` — now a total order;
   - vector `add()` was not idempotent, and `remove()` did not exist.
4. **Regression tests for every one of the above**, plus `tests/integration/test_fork_lineage.py`.

### State
- `make check` GREEN: ruff + `ruff format --check` + mypy (56 files) + **138 tests**.
- Suite re-run several times, consistent; no flakiness observed.

### Next step
**`AUD-H5` is the highest-value open item: the KB still has zero production callers.**
`bootstrap.py` wires none of `SqliteCanonStore` / `SqliteVectorStore` / `WorkingMemory` /
`HashingEmbedder`, and no API route or CLI command reaches canon. `AUD-H1` (canon⇄vector sync) is
now cheap because `VectorStorePort.remove()` exists; only the ingest service pairing the two writes
is missing.

### Known gaps, stated plainly
- `CanonEntity` / `Scene` / `Presence` / `Commitment` / `Flag` / `Source` still have no persistence
  and no source consumers.
- `knower_scope` is still populated by hand; nothing derives it from `Scene.witnesses` yet (KB-13's
  propagation half), so knowledge does not compound across turns on its own.
- Test-quality items `AUD-T1`, `AUD-T2`, `AUD-T5`, `AUD-T7`, `AUD-T11`, `AUD-T13` are deferred, not
  done — notably the flagship leak test still uses a tautological oracle, and 4 of the 9 documented
  invariants (I-6, I-7, I-8, I-9) have no test.

# Tests — the Validation Hierarchy (Definition of Done)

> **Done = end-to-end verification passed, not "code is written." Confidence is not evidence.**
> Sourced from `Harness-Engineering/Harness-Engineering-Preventing-Premature-Victory.md` and
> `...-Beyond-Unit-Tests-E2E.md`. This is *how we verify an implementation is actually implemented.*

Three layers. **A layer must pass before the next is trusted** — don't advance on a red layer, and
never self-grade ("it looks right") in place of a command that exits zero.

| Layer | Proves | Command | Lives in |
|---|---|---|---|
| **L1 — Syntax & Static** | It's spelled right; types hold | `make lint` + `make fmt-check` + `make typecheck` | `ruff`, `mypy` |
| **L2 — Runtime Behavior** | It runs; critical paths + **side effects (DB writes)** are correct | `make test` | `tests/unit/` (mocked), `tests/integration/` (real SQLite in `tmp_path`) |
| **L3 — System-Level / E2E** | Wired together, it boots and is correct | `make test` | `tests/e2e/` (app boots via `TestClient`, schema initializes) |

`make check` runs **all three** in order (L1 → L2 → L3) and is THE gate. `pytest` discovers everything
under `tests/`, so one `make test` runs unit + integration + e2e.

## Layout & markers
- `tests/unit/` — fast, mocked, mirrors the package. No real IO.
- `tests/integration/` — `@pytest.mark.integration`. Real adapter against a real (temp) resource.
- `tests/e2e/` — `@pytest.mark.e2e`. The whole app, exercised as a system.

Run a single layer: `uv run pytest -m integration` · `make test-e2e` · `uv run pytest tests/unit`.
Run every Canon Kernel test: `make test-kb`.

## Rules (from the harness docs)
1. **Assert schema/invariants, never exact generated text.** Mock the LLM in unit tests.
2. **Cross-component changes require an L3 check** (e.g. the SQLite persistence adapter → the app-boot + schema E2E).
3. **No "refactor while we're at it"** before the core path is verified — refactoring moves the verified/unverified boundary.
4. Capture runtime signals: does the app reach a ready state? are DB writes correct? are temp resources cleaned up?

---

# Testing the Canon Kernel (memory storage)

The Kernel is a **tri-temporal store**, and that makes most ordinary test instincts insufficient. What
follows is the standard for it. Research-backed 2026-07-25; see `DECISIONS.md`.

## The anti-pattern we are explicitly avoiding

We read the test suites of the closest public analogue, **Graphiti** (`getzep/graphiti`), and found the
failure mode this section exists to prevent:

- `tests/test_edge_int.py::test_entity_edge` **constructs** an edge carrying `valid_at` / `invalid_at` /
  `expired_at`, saves it, reloads it — and then asserts only on `uuid`. **The temporal fields, which are
  the entire point of the system, are never asserted after round-trip.**
- `tests/test_graphiti_int.py::test_graphiti_init` builds a temporal `DateFilter` search and **has no
  assertions on the results at all.** It proves the call doesn't raise.

Both pass. Both would pass while the store silently corrupted every temporal field it holds.

> **The rule that follows from this:** every field the domain model treats as load-bearing must appear on
> the **left-hand side of an assert after a real save-and-reload**. A test that only checks identity, or
> only checks "it didn't throw," is a smoke test. Smoke tests do not count toward done.

## The invariants a tri-temporal store must assert

Three axes: **story time** (`valid_from`/`valid_to` — true in the world), **telling time**
(`revealed_at` — the audience learned it), **record time** (`recorded_at`/`superseded_at` — the store
learned it).

| # | Invariant | Why it bites |
|---|---|---|
| I-1 | `valid_to` is null or `> valid_from`; `superseded_at` is null or `>= recorded_at` | Inverted windows silently match nothing, so queries return empty instead of failing |
| I-2 | **At most ONE live fact** per (fork, subject, predicate) at any single story time | The core bitemporal correctness property. Two live contradicting rows = corrupt canon |
| I-3 | Supersession is **atomic**: no window where both old and new are live, and none where neither is | A half-applied supersede loses a fact entirely |
| I-4 | Supersession **never mutates** the old row's `valid_from`/`recorded_at`/`revealed_at` — only closes `valid_to`/`superseded_at` | Append-only is what makes history auditable; an in-place edit destroys the audit trail |
| I-5 | `as_of` returns exactly the row whose window contains `t`, using the latest non-superseded record | The headline query. Test it as a **2D grid** (story time × record time), not a line |
| I-6 | **Projection equals replay** — rebuilding from the log in `recorded_at` order equals live state | Catches divergence between the write path and the read path |
| I-7 | **Replay is idempotent** — replaying a log twice, or an overlapping prefix+suffix, yields the same state | Catches a supersede that isn't keyed on "was NULL" and corrupts a second row on re-apply |
| I-8 | **No lost update** — two concurrent supersessions of one fact leave exactly one live successor | Never zero, never two |
| I-9 | `recorded_at` is non-decreasing in insert order | Record time is the log's sequence number; out-of-order breaks replay |

**Boundary testing is a grid, not a line.** For as-of correctness, cross
`{before, at, after} valid_from` × `{before, at, after} valid_to` × `{before, at, after} superseded_at`.
Off-by-one at a window edge is the characteristic bug of this whole class of system.

## The spoiler guard is an access-control problem

Test it the way authorization is tested (OWASP WSTG, Authorization Testing), because that is what it is:
proving a fact is unreachable by *any* path, not just the front door.

**Encode the asymmetry — this is the part that shapes the assertions:**

| Failure | Severity | How the suite treats it |
|---|---|---|
| **Leak** — a fact with `revealed_at > telling_time` appears in a packet | **Hard failure** | Must fail the build. This is the guarantee's whole purpose |
| **Over-withholding** — a legitimately revealable fact is withheld | Warning | Reported as a metric, not a build failure. The writer loses a detail; the audience never sees it |

Testing both directions at equal severity would make the suite reject correct-but-conservative behaviour.

**Assert set equality, never spot checks.** After seeding N facts with known `revealed_at`, query at
cutoff `T` and assert the returned id set equals `{f.id for f in facts if f.revealed_at <= T}`. Spot
checks ("assert fact X is absent") only catch leaks you already thought of; set equality catches the
ones you didn't.

## Durability: the store must survive a restart

- **Never `sqlite3.connect(":memory:")`** for these tests. It never touches disk, so it cannot catch
  WAL/journal bugs, uncommitted-transaction bugs, or file-locking bugs.
- Use a **real file** via `tmp_path` — unique per test function, auto-isolated, no manual cleanup.
- The pattern: write → **close the connection** → construct a *fresh* store against the same path →
  assert the data and the projection are intact. Skipping the close-and-reopen is how a store that only
  works while the process is warm passes its tests.

```python
def test_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "canon.db"
    store = CanonStore(db)
    store.append(fact)
    store.close()  # simulate process exit

    reopened = CanonStore(db)  # fresh connection, same file
    assert reopened.as_of("kael", "loyal_to", story_time=1) == fact
    assert reopened.replay() == reopened.projection()
```

## Where property-based testing pays, and where it doesn't

Use Hypothesis's `RuleBasedStateMachine` for the **mutation-sequence surface only** — append / supersede /
query-as-of — with an in-memory oracle model and `@invariant()` methods asserting I-2, I-5 and I-6 after
*every* step. Sequence-ordering bugs are combinatorial and cannot be reached by parametrization; when it
finds one, Hypothesis shrinks it to a minimal repro you paste back as a permanent regression test.

**Don't** reach for it for schema validation (Pydantic already covers that) or single-call query logic —
those are clearer as named `@pytest.mark.parametrize` boundary cases that a human can read in a diff.

Keep named, readable sequence tests too (`test_correction_after_reveal_does_not_retroactively_leak`).
They document the tri-temporal contract in a way a fuzzer's minimal repro never will.

## Anti-patterns (each observed in a real suite, not hypothetical)

- Constructing temporal fields and asserting only on identity after round-trip *(Graphiti)*.
- Exercising a query path with no assertion on its results *(Graphiti)*.
- Mocking the store in anything above unit level — the integration and E2E tiers use the **real** adapter.
- `:memory:` SQLite standing in for the real store — cannot catch durability bugs.
- Fixtures that only ever insert in convenient order (always chronological, never two facts about one
  key at once). Real bugs live in unusual orderings.
- Testing only the guard's positive case; the leak case must be equally weighted and equally frequent.

## Known E2E gaps (tracked, not hidden)

1. **LLM path** — a full `premise → episode → persist` request path is not yet E2E-testable: the LLM
   adapter is deferred and `StubLLM` raises by design. Closing it needs a deterministic offline LLM.
2. **Canon store** — the store itself does not exist yet (M0 is schema only). KB-07 adds the adapter,
   KB-08 the E2E suite above, KB-09 the invariant/property tests. Until KB-08 is green, **the Kernel is
   unverified and must not be described as working.**

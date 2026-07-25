# Canon Store & E2E Memory Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the M0 schema into **memory storage that has been proven to work** — a real SQLite-backed canon store, plus an end-to-end suite that persists, closes, reopens, queries across three time axes, and proves the spoiler guard does not leak.

**Architecture:** A `CanonStorePort` Protocol in `ports/`, implemented by `SqliteCanonStore` in `adapters/outbound/persistence/`, mirroring the existing `SqliteEpisodeLogRepository` exactly — `table=True` rows in `tables.py`, explicit `_to_domain`/`_to_row` mapping performed *inside* the session scope, `col()` for strict-mypy filters. The domain stays pure Pydantic and clock-free; the adapter owns the clock and the SQL.

**Tech Stack:** Python 3.12, Pydantic v2, SQLModel/SQLAlchemy, SQLite, pytest 9, FastAPI TestClient.

## Global Constraints

- Spec: `PRD-KNOWLEDGE-BASE.md`. **Testing standard: `tests/README.md` § "Testing the Canon Kernel" — read it before writing a single test.**
- Features being earned: **KB-07** (store), **KB-08** (E2E suite — the definition of done), **KB-09** (invariants I-1…I-9).
- Python 3.12. Modern typing only: `X | None`, never `Optional`. `tuple[...]`/`frozenset[...]` on domain models, never `list`/`set`.
- **Hexagon red line:** `table=True` SQLModel classes live ONLY in `adapters/outbound/persistence/`. `domain/` imports no SQLModel, no SQLAlchemy, no clock.
- **Map Row → domain INSIDE the session scope.** Attributes lazy-load; touching them after close raises `DetachedInstanceError`. This bug has already been paid for once (HARDEN-01).
- Google-style docstrings on every public module, class and function. Comments explain WHY.
- Line length 88; `ruff format` owns formatting.
- **Never `sqlite3.connect(":memory:")` in a store test.** Real file via `tmp_path`.
- **Never `git add -A` or a bare `git commit`.** Use `git commit -- <pathspec> -m "..."`. No `Co-Authored-By`, no AI attribution.
- The gate is `make check`. It is GREEN at 36 tests as this plan begins. Red at the end of any task = that task is not done.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/story_engine/ports/canon_store.py` | Create | `CanonStorePort` Protocol — the only seam the services see |
| `src/story_engine/adapters/outbound/persistence/tables.py` | Modify | Add `FactRow`. Existing `EpisodeSummaryRow` untouched |
| `src/story_engine/adapters/outbound/persistence/canon_store.py` | Create | `SqliteCanonStore` + `_to_domain`/`_to_row` |
| `tests/integration/test_canon_store_sqlite.py` | Create | KB-07: round-trip, durability, as-of, scoped queries — real DB file |
| `tests/integration/test_canon_invariants.py` | Create | KB-09: I-1…I-9 + the leak test |
| `tests/e2e/test_memory_storage_e2e.py` | Create | KB-08: the whole path through the app boundary |

One port, not four. Append/supersede/query are one cohesive concern (canon facts); splitting them would be interface explosion, and the segregation that matters in this codebase is already done at the *aggregate* level (`StoryBible` vs `EpisodeLog` vs `Canon`).

---

### Task 1: FactRow and lossless mapping

The riskiest part of the whole store: `Fact` carries a `frozenset | None`, a nested `Provenance`, two `datetime`s, and four `StrEnum`s. Any of them can round-trip lossily and no test would notice unless it asserts field-by-field.

**Files:**
- Modify: `src/story_engine/adapters/outbound/persistence/tables.py`
- Create: `src/story_engine/adapters/outbound/persistence/canon_store.py` (mapping functions only this task)
- Test: `tests/integration/test_canon_store_sqlite.py`

**Interfaces:**
- Consumes: `Fact`, `Provenance`, `ChapterIndex` from `story_engine.domain.models`; the enums from `story_engine.domain.enums`.
- Produces: `FactRow`; `_to_row(fact: Fact) -> FactRow`; `_to_domain(row: FactRow) -> Fact`.

- [ ] **Step 1: Write the failing round-trip test**

Create `tests/integration/test_canon_store_sqlite.py`:

```python
"""Integration tests for the SQLite canon store — REAL database file, never :memory:.

See tests/README.md § "Testing the Canon Kernel". The rule these tests exist to enforce:
every load-bearing field must appear on the left-hand side of an assert AFTER a real
save-and-reload. Graphiti's own suite round-trips temporal edges and then asserts only on
uuid — it would pass while every temporal field was corrupted.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_engine.adapters.outbound.persistence.canon_store import _to_domain, _to_row
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Provenance

pytestmark = pytest.mark.integration

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
SUPERSEDED = datetime(2026, 7, 26, 9, 30, tzinfo=UTC)


def _fact(**overrides: object) -> Fact:
    """Build a valid Fact, overriding named fields."""
    defaults: dict[str, object] = {
        "id": "f-1",
        "fork_id": "canon",
        "subject_id": "kael",
        "predicate": "loyal_to",
        "object_id": "the_crown",
        "object_literal": None,
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="src-1", chapter=1, char_start=0, char_end=12, quote="Kael knelt."
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def test_mapping_round_trip_preserves_every_field() -> None:
    """Field-by-field equality after Row conversion — not just identity.

    Asserting `original == restored` on a frozen Pydantic model compares all fields, so a
    silently dropped or coerced field fails here rather than surviving to production.
    """
    original = _fact(
        knower_scope=frozenset({AUDIENCE, "holmes"}),
        valid_to=180,
        revealed_at=42,
        object_id=None,
        object_literal="the Crown",
        attributed_to="marcus",
        assertion_mode=AssertionMode.ATTRIBUTED,
        status=FactStatus.INVALIDATED,
        superseded_at=SUPERSEDED,
        confidence=0.42,
        tier=2,
    )
    restored = _to_domain(_to_row(original))
    assert restored == original


def test_untracked_knower_scope_round_trips_as_none_not_empty() -> None:
    """None (untracked) and an empty set are different states; JSON must not conflate them.

    A `[]` coming back as `frozenset()` would be REJECTED by the model's min_length=1, so a
    lossy mapping here shows up as a validation error rather than silent corruption — but
    only if a test actually exercises the None case.
    """
    restored = _to_domain(_to_row(_fact(knower_scope=None)))
    assert restored.knower_scope is None


def test_nested_provenance_survives_the_json_boundary() -> None:
    """Provenance is a nested model; a dict/model mix-up loses the citation."""
    restored = _to_domain(_to_row(_fact()))
    assert restored.provenance.quote == "Kael knelt."
    assert restored.provenance.char_end == 12
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/integration/test_canon_store_sqlite.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'story_engine.adapters.outbound.persistence.canon_store'`

- [ ] **Step 3: Add `FactRow` to `tables.py`**

Append to `src/story_engine/adapters/outbound/persistence/tables.py`:

```python
class FactRow(SQLModel, table=True):
    """Storage row for `domain.models.Fact` — the tri-temporal canon record.

    Enums are stored as their string values (they are `StrEnum`, so this is lossless).
    `knower_scope` is a JSON list or SQL NULL: NULL means NOT TRACKED, which is a different
    state from "tracked but empty" — the domain rejects the latter, so conflating them would
    surface as a validation error on read.
    """

    __tablename__ = "canon_fact"

    id: str = Field(primary_key=True)
    fork_id: str = Field(index=True)
    subject_id: str = Field(index=True)
    predicate: str = Field(index=True)
    object_id: str | None = Field(default=None)
    object_literal: str | None = Field(default=None)

    valid_from: int = Field(index=True)
    valid_to: int | None = Field(default=None)
    revealed_at: int | None = Field(default=None, index=True)

    assertion_mode: str
    attributed_to: str | None = Field(default=None)

    knower_scope: list[str] | None = Field(default=None, sa_column=Column(JSON))
    provenance: dict[str, object] = Field(default_factory=dict, sa_column=Column(JSON))
    confidence: float
    tier: int
    status: str = Field(index=True)

    recorded_at: datetime
    superseded_at: datetime | None = Field(default=None)
```

Add `from datetime import datetime` to that file's imports.

- [ ] **Step 4: Create `canon_store.py` with the mapping functions**

Create `src/story_engine/adapters/outbound/persistence/canon_store.py`:

```python
"""SQLite-backed canon store — implements `CanonStorePort`.

The Kernel's system of record. Facts are NEVER overwritten: a superseding claim closes the
old row's validity window and stamps `superseded_at`, and both rows stay queryable, because
the superseded fact is still canon at its own timestamp.

Maps Row ⇄ domain explicitly and always INSIDE the session scope — rows detach on close
(the HARDEN-01 `DetachedInstanceError`).
"""

from story_engine.adapters.outbound.persistence.tables import FactRow
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import Fact, Provenance


def _to_row(fact: Fact) -> FactRow:
    """Map a domain fact to a fresh storage row."""
    return FactRow(
        id=fact.id,
        fork_id=fact.fork_id,
        subject_id=fact.subject_id,
        predicate=fact.predicate,
        object_id=fact.object_id,
        object_literal=fact.object_literal,
        valid_from=fact.valid_from,
        valid_to=fact.valid_to,
        revealed_at=fact.revealed_at,
        assertion_mode=str(fact.assertion_mode),
        attributed_to=fact.attributed_to,
        # None (untracked) must stay NULL — an empty list would be a different, invalid state.
        knower_scope=(
            None if fact.knower_scope is None else sorted(fact.knower_scope)
        ),
        provenance=fact.provenance.model_dump(),
        confidence=fact.confidence,
        tier=fact.tier,
        status=str(fact.status),
        recorded_at=fact.recorded_at,
        superseded_at=fact.superseded_at,
    )


def _to_domain(row: FactRow) -> Fact:
    """Map a storage row back to the pure domain model."""
    return Fact(
        id=row.id,
        fork_id=row.fork_id,
        subject_id=row.subject_id,
        predicate=row.predicate,
        object_id=row.object_id,
        object_literal=row.object_literal,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        revealed_at=row.revealed_at,
        assertion_mode=AssertionMode(row.assertion_mode),
        attributed_to=row.attributed_to,
        knower_scope=(
            None if row.knower_scope is None else frozenset(row.knower_scope)
        ),
        provenance=Provenance(**row.provenance),
        confidence=row.confidence,
        tier=row.tier,
        status=FactStatus(row.status),
        recorded_at=row.recorded_at,
        superseded_at=row.superseded_at,
    )
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `uv run pytest tests/integration/test_canon_store_sqlite.py -q`
Expected: PASS (3 tests)

- [ ] **Step 6: Run the full gate**

Run: `make check` — expected green, 39 tests.

- [ ] **Step 7: Commit (pathspec only)**

```bash
git commit -- src/story_engine/adapters/outbound/persistence/tables.py \
  src/story_engine/adapters/outbound/persistence/canon_store.py \
  tests/integration/test_canon_store_sqlite.py \
  -m "feat(persistence): add FactRow and lossless Fact<->Row mapping"
```

---

### Task 2: CanonStorePort and the store's read/write operations

**Files:**
- Create: `src/story_engine/ports/canon_store.py`
- Modify: `src/story_engine/adapters/outbound/persistence/canon_store.py` (add the class)
- Test: `tests/integration/test_canon_store_sqlite.py` (append)

**Interfaces:**
- Produces: `CanonStorePort` Protocol and `SqliteCanonStore` with these exact methods:
  - `append(fact: Fact) -> None`
  - `get(fact_id: str) -> Fact | None`
  - `all_facts(fork_id: str) -> tuple[Fact, ...]`
  - `as_of(fork_id: str, subject_id: str, predicate: str, story_time: ChapterIndex) -> Fact | None`
  - `visible_to(fork_id: str, knower: str, chapter: ChapterIndex) -> tuple[Fact, ...]`
  - `withheld_from(fork_id: str, knower: str, chapter: ChapterIndex) -> tuple[Fact, ...]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_canon_store_sqlite.py`:

```python
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore


@pytest.fixture
def store(tmp_path: Path) -> SqliteCanonStore:
    """A store backed by a REAL file on disk — never :memory:.

    :memory: cannot catch WAL/journal, uncommitted-transaction or file-locking bugs, and it
    makes the restart test below impossible to write.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'canon.db'}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


def test_append_then_get_returns_an_equal_fact(store: SqliteCanonStore) -> None:
    original = _fact(knower_scope=frozenset({AUDIENCE, "holmes"}), revealed_at=3)
    store.append(original)
    assert store.get("f-1") == original


def test_get_returns_none_for_an_unknown_id(store: SqliteCanonStore) -> None:
    assert store.get("nope") is None


def test_as_of_respects_the_story_time_window(store: SqliteCanonStore) -> None:
    """The headline query. Boundaries are where this class of system actually breaks."""
    store.append(_fact(id="f-old", valid_from=1, valid_to=180))
    store.append(_fact(id="f-new", valid_from=181, valid_to=None))

    assert store.as_of("canon", "kael", "loyal_to", 1).id == "f-old"
    assert store.as_of("canon", "kael", "loyal_to", 180).id == "f-old"
    assert store.as_of("canon", "kael", "loyal_to", 181).id == "f-new"
    assert store.as_of("canon", "kael", "loyal_to", 9999).id == "f-new"


def test_as_of_returns_none_before_anything_is_true(store: SqliteCanonStore) -> None:
    store.append(_fact(valid_from=5))
    assert store.as_of("canon", "kael", "loyal_to", 4) is None


def test_as_of_is_fork_scoped(store: SqliteCanonStore) -> None:
    """A fork's fact must not answer a query against its sibling."""
    store.append(_fact(id="f-canon", fork_id="canon", object_id="the_crown"))
    store.append(_fact(id="f-a", fork_id="fork-a", object_id="the_rebels"))
    assert store.as_of("fork-a", "kael", "loyal_to", 1).object_id == "the_rebels"


def test_visible_and_withheld_partition_the_fact_set(store: SqliteCanonStore) -> None:
    """Every fact is either servable or withheld. Nothing may fall through the gap."""
    store.append(_fact(id="f-1", revealed_at=1))
    store.append(_fact(id="f-2", subject_id="mara", revealed_at=9))
    store.append(_fact(id="f-3", subject_id="finn", revealed_at=None))

    visible = store.visible_to("canon", AUDIENCE, 5)
    withheld = store.withheld_from("canon", AUDIENCE, 5)

    assert {f.id for f in visible} == {"f-1"}
    assert {f.id for f in withheld} == {"f-2", "f-3"}
    assert len(visible) + len(withheld) == 3


def test_the_store_survives_a_restart(tmp_path: Path) -> None:
    """Write, CLOSE, reopen against the same file, and assert the data is intact.

    Skipping the close-and-reopen is how a store that only works while the process is warm
    passes its entire suite.
    """
    db = tmp_path / "canon.db"
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    original = _fact(revealed_at=3, knower_scope=frozenset({AUDIENCE}))
    SqliteCanonStore(engine).append(original)
    engine.dispose()  # close every pooled connection — simulate process exit

    reopened = create_engine(f"sqlite:///{db}")
    assert SqliteCanonStore(reopened).get("f-1") == original
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/integration/test_canon_store_sqlite.py -q`
Expected: FAIL — `ImportError: cannot import name 'SqliteCanonStore'`

- [ ] **Step 3: Create the port**

Create `src/story_engine/ports/canon_store.py`:

```python
"""The canon-store port — the only seam the services see for tri-temporal fact storage."""

from typing import Protocol

from story_engine.domain.models import ChapterIndex, Fact


class CanonStorePort(Protocol):
    """Append-only, tri-temporally queryable storage for canon facts."""

    def append(self, fact: Fact) -> None:
        """Store a fact. Never overwrites an existing one."""
        ...

    def get(self, fact_id: str) -> Fact | None:
        """Return one fact by id, or None."""
        ...

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        """Every fact in a fork, in record order."""
        ...

    def as_of(
        self,
        fork_id: str,
        subject_id: str,
        predicate: str,
        story_time: ChapterIndex,
    ) -> Fact | None:
        """The fact true at a story-time position, or None."""
        ...

    def visible_to(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        """Facts that may be surfaced to this knower at this point in the telling."""
        ...

    def withheld_from(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        """The spoiler-guard exclusion set — retrieval performed in order to EXCLUDE."""
        ...
```

- [ ] **Step 4: Implement `SqliteCanonStore`**

Append to `canon_store.py` (add imports: `from sqlalchemy import Engine`, `from sqlmodel import col, select`, `from story_engine.adapters.outbound.persistence.db import session_scope`, `from story_engine.domain.models import ChapterIndex`):

```python
class SqliteCanonStore:
    """SQLite implementation of `CanonStorePort`.

    Every read maps Row → domain INSIDE the session scope, then returns pure models, so no
    caller can trip `DetachedInstanceError` on a lazily-loaded attribute.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append(self, fact: Fact) -> None:
        """Store a fact. Never overwrites — supersession closes windows instead."""
        with session_scope(self._engine) as session:
            session.add(_to_row(fact))

    def get(self, fact_id: str) -> Fact | None:
        with session_scope(self._engine) as session:
            row = session.get(FactRow, fact_id)
            return _to_domain(row) if row is not None else None

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        with session_scope(self._engine) as session:
            statement = (
                select(FactRow)
                .where(col(FactRow.fork_id) == fork_id)
                .order_by(col(FactRow.recorded_at).asc())
            )
            return tuple(_to_domain(row) for row in session.exec(statement).all())

    def as_of(
        self,
        fork_id: str,
        subject_id: str,
        predicate: str,
        story_time: ChapterIndex,
    ) -> Fact | None:
        """The live fact whose story-time window contains `story_time`.

        Superseded rows are excluded rather than filtered afterwards, so a closed window can
        never shadow the row that replaced it.
        """
        with session_scope(self._engine) as session:
            statement = (
                select(FactRow)
                .where(col(FactRow.fork_id) == fork_id)
                .where(col(FactRow.subject_id) == subject_id)
                .where(col(FactRow.predicate) == predicate)
                .where(col(FactRow.status) == str(FactStatus.ACTIVE))
                .where(col(FactRow.valid_from) <= story_time)
                .order_by(col(FactRow.valid_from).desc())
            )
            for row in session.exec(statement).all():
                if row.valid_to is None or story_time <= row.valid_to:
                    return _to_domain(row)
            return None

    def visible_to(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        return tuple(
            f for f in self.all_facts(fork_id) if f.is_visible_to(knower, chapter)
        )

    def withheld_from(
        self, fork_id: str, knower: str, chapter: ChapterIndex
    ) -> tuple[Fact, ...]:
        return tuple(
            f for f in self.all_facts(fork_id) if not f.is_visible_to(knower, chapter)
        )
```

- [ ] **Step 5: Run tests, then the gate**

Run: `uv run pytest tests/integration/test_canon_store_sqlite.py -q` → PASS (10 tests)
Run: `make check` → green.

- [ ] **Step 6: Commit (pathspec only)**

```bash
git commit -- src/story_engine/ports/canon_store.py \
  src/story_engine/adapters/outbound/persistence/canon_store.py \
  tests/integration/test_canon_store_sqlite.py \
  -m "feat(persistence): CanonStorePort and SqliteCanonStore with tri-temporal queries"
```

---

### Task 3: Supersession — invalidate, never overwrite

**Files:**
- Modify: `src/story_engine/ports/canon_store.py`, `.../persistence/canon_store.py`
- Test: `tests/integration/test_canon_invariants.py` (create)

**Interfaces:**
- Produces: `supersede(old_fact_id: str, replacement: Fact, closes_at: ChapterIndex, superseded_at: datetime) -> None` on both port and adapter.

- [ ] **Step 1: Write the failing invariant tests**

Create `tests/integration/test_canon_invariants.py`. Import the `_fact` helper style from the store test file (repeat it — do not cross-import between test modules).

```python
"""Temporal invariants I-1..I-9 — see tests/README.md § "Testing the Canon Kernel"."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Provenance

pytestmark = pytest.mark.integration

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
SUPERSEDED_AT = datetime(2026, 7, 26, 9, 30, tzinfo=UTC)


def _fact(**overrides: object) -> Fact:
    defaults: dict[str, object] = {
        "id": "f-1", "fork_id": "canon", "subject_id": "kael",
        "predicate": "loyal_to", "object_id": "the_crown", "object_literal": None,
        "valid_from": 1, "valid_to": None, "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED, "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="s", chapter=1, char_start=0, char_end=4, quote="Kael"
        ),
        "confidence": 0.9, "tier": 0, "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED, "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> SqliteCanonStore:
    engine = create_engine(f"sqlite:///{tmp_path / 'canon.db'}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


def test_i2_exactly_one_live_fact_per_key_after_supersession(store) -> None:
    """I-2: two live contradicting rows for one key IS corrupt canon."""
    store.append(_fact(id="f-old", object_id="the_crown"))
    store.supersede(
        "f-old",
        replacement=_fact(id="f-new", object_id="the_rebels", valid_from=181),
        closes_at=180,
        superseded_at=SUPERSEDED_AT,
    )
    live = [f for f in store.all_facts("canon") if f.status is FactStatus.ACTIVE]
    assert len(live) == 1
    assert live[0].id == "f-new"


def test_i4_supersession_never_mutates_the_old_rows_open_fields(store) -> None:
    """I-4: append-only is what makes history auditable. Only valid_to/superseded_at move."""
    store.append(_fact(id="f-old", valid_from=1, revealed_at=1))
    store.supersede(
        "f-old",
        replacement=_fact(id="f-new", valid_from=181),
        closes_at=180,
        superseded_at=SUPERSEDED_AT,
    )
    old = store.get("f-old")
    assert old.valid_from == 1
    assert old.revealed_at == 1
    assert old.recorded_at == RECORDED
    assert old.valid_to == 180
    assert old.superseded_at == SUPERSEDED_AT
    assert old.status is FactStatus.INVALIDATED


def test_both_rows_remain_queryable_after_supersession(store) -> None:
    """The superseded fact is still canon at its own timestamp — never delete it."""
    store.append(_fact(id="f-old", object_id="the_crown"))
    store.supersede(
        "f-old",
        replacement=_fact(id="f-new", object_id="the_rebels", valid_from=181),
        closes_at=180,
        superseded_at=SUPERSEDED_AT,
    )
    assert store.as_of("canon", "kael", "loyal_to", 100).object_id == "the_crown"
    assert store.as_of("canon", "kael", "loyal_to", 200).object_id == "the_rebels"


def test_superseding_an_unknown_id_raises(store) -> None:
    """Fail loud. A silent no-op here loses the replacement fact entirely."""
    with pytest.raises(KeyError):
        store.supersede(
            "nope",
            replacement=_fact(id="f-new"),
            closes_at=1,
            superseded_at=SUPERSEDED_AT,
        )
```

- [ ] **Step 2: Run and confirm failure** — `AttributeError: 'SqliteCanonStore' object has no attribute 'supersede'`

- [ ] **Step 3: Add `supersede` to the port**

```python
    def supersede(
        self,
        old_fact_id: str,
        replacement: Fact,
        closes_at: ChapterIndex,
        superseded_at: datetime,
    ) -> None:
        """Close the old fact's window and append its replacement, atomically.

        Never deletes: the superseded fact remains canon at its own timestamp. `superseded_at`
        is supplied by the caller because the domain and its ports take no clock.
        """
        ...
```

- [ ] **Step 4: Implement it**

```python
    def supersede(
        self,
        old_fact_id: str,
        replacement: Fact,
        closes_at: ChapterIndex,
        superseded_at: datetime,
    ) -> None:
        """Close the old row's window and insert the replacement in ONE transaction.

        Both writes share a session so there is no window in which both rows are live, and
        none in which neither is (invariant I-3).
        """
        with session_scope(self._engine) as session:
            row = session.get(FactRow, old_fact_id)
            if row is None:
                raise KeyError(f"cannot supersede unknown fact: {old_fact_id}")
            row.valid_to = closes_at
            row.superseded_at = superseded_at
            row.status = str(FactStatus.INVALIDATED)
            session.add(row)
            session.add(_to_row(replacement))
```

- [ ] **Step 5: Run tests, then `make check`** — both green.

- [ ] **Step 6: Commit (pathspec only)**

```bash
git commit -- src/story_engine/ports/canon_store.py \
  src/story_engine/adapters/outbound/persistence/canon_store.py \
  tests/integration/test_canon_invariants.py \
  -m "feat(persistence): atomic supersession — invalidate, never overwrite"
```

---

### Task 4: The leak test (KB-09's centrepiece)

**Files:**
- Modify: `tests/integration/test_canon_invariants.py`

**Interfaces:** consumes `SqliteCanonStore` from Tasks 2–3. Produces no new source.

- [ ] **Step 1: Write the leak tests**

Append:

```python
LEAK_SEVERITY = "A leaked fact is a HARD failure — it is the guarantee's whole purpose."


@pytest.mark.parametrize("cutoff", [0, 1, 2, 3, 4, 5, 10, 100])
def test_no_fact_is_ever_leaked_at_any_cutoff(store, cutoff: int) -> None:
    """Set equality, not spot checks.

    Spot checks ("assert fact X is absent") only catch leaks you already thought of. Asserting
    the whole returned id set catches the ones you didn't.
    """
    facts = [
        _fact(id="f-1", subject_id="a", revealed_at=1),
        _fact(id="f-2", subject_id="b", revealed_at=3),
        _fact(id="f-3", subject_id="c", revealed_at=5),
        _fact(id="f-4", subject_id="d", revealed_at=None),
    ]
    for f in facts:
        store.append(f)

    returned = {f.id for f in store.visible_to("canon", AUDIENCE, cutoff)}
    expected = {
        f.id for f in facts if f.revealed_at is not None and f.revealed_at <= cutoff
    }
    assert returned == expected, LEAK_SEVERITY


def test_a_quarantined_fact_is_never_visible_however_early_it_was_revealed(store) -> None:
    """Status must dominate reveal time, or the curation gate is decorative."""
    store.append(_fact(id="f-q", revealed_at=1, status=FactStatus.QUARANTINED))
    assert store.visible_to("canon", AUDIENCE, 9999) == (), LEAK_SEVERITY


def test_scope_tracked_facts_do_not_leak_to_a_knower_outside_the_scope(store) -> None:
    """The dramatic-irony case: Watson must not receive a Holmes-only secret."""
    store.append(
        _fact(id="f-secret", revealed_at=1, knower_scope=frozenset({AUDIENCE, "holmes"}))
    )
    assert store.visible_to("canon", "watson", 9999) == (), LEAK_SEVERITY
    assert {f.id for f in store.visible_to("canon", "holmes", 9999)} == {"f-secret"}


def test_over_withholding_is_reported_not_failed(store, capsys) -> None:
    """The asymmetry, encoded.

    Over-withholding costs the writer a usable detail; the audience never sees the difference.
    Failing the build on it would make the suite reject correct-but-conservative behaviour, so
    it is measured and printed instead of asserted.
    """
    facts = [_fact(id=f"f-{i}", subject_id=f"s{i}", revealed_at=1) for i in range(5)]
    for f in facts:
        store.append(f)

    returned = {f.id for f in store.visible_to("canon", AUDIENCE, 10)}
    expected = {f.id for f in facts}
    over_withheld = expected - returned
    leaked = returned - expected

    assert leaked == set(), LEAK_SEVERITY
    if over_withheld:
        print(f"OVER-WITHHELD (metric, not a failure): {sorted(over_withheld)}")
```

- [ ] **Step 2: Run** — `uv run pytest tests/integration/test_canon_invariants.py -q`. Expect PASS. If any leak assertion fails, **stop and fix the store** — do not weaken the test.

- [ ] **Step 3: `make check`** — green.

- [ ] **Step 4: Commit (pathspec only)**

```bash
git commit -- tests/integration/test_canon_invariants.py \
  -m "test: spoiler-guard leak suite with set equality and severity asymmetry"
```

---

### Task 5: The E2E memory-storage suite (KB-08 — the definition of done)

**Files:**
- Create: `tests/e2e/test_memory_storage_e2e.py`

**Interfaces:** consumes `SqliteCanonStore`, `SQLModel.metadata`, and the domain models. No new source.

- [ ] **Step 1: Write the E2E test**

Create `tests/e2e/test_memory_storage_e2e.py`:

```python
"""L3 — the whole memory-storage path, end to end, against a real database file.

This is the session's definition of done. It is deliberately ONE long test rather than many
small ones: the property being proven is that a REALISTIC SEQUENCE of operations survives a
restart with all three time axes intact. Splitting it into isolated cases would let each step
pass while the sequence as a whole was broken.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.invariants import conflicting_active_facts
from story_engine.domain.models import AUDIENCE, Fact, Provenance

pytestmark = pytest.mark.e2e

INGESTED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
CORRECTED_AT = datetime(2026, 7, 25, 18, 0, tzinfo=UTC)


def _fact(fact_id: str, **overrides: object) -> Fact:
    defaults: dict[str, object] = {
        "id": fact_id, "fork_id": "canon", "subject_id": "kael",
        "predicate": "loyal_to", "object_id": "the_crown", "object_literal": None,
        "valid_from": 1, "valid_to": None, "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED, "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="novel", chapter=1, char_start=0, char_end=4, quote="Kael"
        ),
        "confidence": 0.9, "tier": 0, "status": FactStatus.ACTIVE,
        "recorded_at": INGESTED_AT, "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def test_memory_storage_end_to_end(tmp_path: Path) -> None:
    db = tmp_path / "canon.db"

    # --- 1. INGEST: a serial with an ordinary fact, a secret, and a late reveal ----------
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)

    store.append(_fact("f-loyal", valid_from=1, revealed_at=1))
    store.append(
        _fact(
            "f-killer",
            subject_id="moriarty",
            predicate="is_killer_of",
            object_id="victim",
            valid_from=1,
            revealed_at=30,  # true from the start; the audience learns it at ch30
        )
    )
    store.append(
        _fact(
            "f-secret",
            subject_id="holmes",
            predicate="knows_about",
            object_id="the_ash",
            valid_from=3,
            revealed_at=3,
            knower_scope=frozenset({AUDIENCE, "holmes"}),  # Watson is not in scope
        )
    )

    # --- 2. RESTART: close every connection, then reopen the same file -------------------
    engine.dispose()
    reopened = SqliteCanonStore(create_engine(f"sqlite:///{db}"))

    assert len(reopened.all_facts("canon")) == 3, "data did not survive the restart"

    # --- 3. SPOILER GUARD at chapter 10, before the reveal -------------------------------
    visible_ids = {f.id for f in reopened.visible_to("canon", AUDIENCE, 10)}
    assert "f-killer" not in visible_ids, "LEAK: the killer was revealed 20 chapters early"
    assert visible_ids == {"f-loyal", "f-secret"}

    # ...and after it
    assert "f-killer" in {f.id for f in reopened.visible_to("canon", AUDIENCE, 30)}

    # --- 4. EPISTEMIC SCOPE: Watson may not act on a Holmes-only fact --------------------
    watson_ids = {f.id for f in reopened.visible_to("canon", "watson", 10)}
    assert "f-secret" not in watson_ids, "LEAK: Watson received a Holmes-only fact"

    # --- 5. SUPERSEDE: Kael defects at chapter 181 ---------------------------------------
    reopened.supersede(
        "f-loyal",
        replacement=_fact("f-defected", object_id="the_rebels", valid_from=181),
        closes_at=180,
        superseded_at=CORRECTED_AT,
    )

    # --- 6. BOTH rows survive; exactly one is live at any story time ---------------------
    assert reopened.as_of("canon", "kael", "loyal_to", 100).object_id == "the_crown"
    assert reopened.as_of("canon", "kael", "loyal_to", 200).object_id == "the_rebels"
    assert conflicting_active_facts(reopened.all_facts("canon"), chapter=200) == ()

    # --- 7. SECOND RESTART: the correction is durable too --------------------------------
    final = SqliteCanonStore(create_engine(f"sqlite:///{db}"))
    assert final.as_of("canon", "kael", "loyal_to", 100).object_id == "the_crown"
    assert final.get("f-loyal").status is FactStatus.INVALIDATED
    assert final.get("f-loyal").valid_from == 1, "supersession mutated an immutable field"
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/e2e/test_memory_storage_e2e.py -v`
Expected: PASS. **If it fails, the store is wrong — fix the store, never the assertion.**

- [ ] **Step 3: Run the full gate**

Run: `make check` — green, all layers.

- [ ] **Step 4: Commit (pathspec only)**

```bash
git commit -- tests/e2e/test_memory_storage_e2e.py \
  -m "test(e2e): end-to-end memory storage across a restart

Ingest, restart, spoiler guard before and after the reveal, epistemic scope,
supersession, and a second restart proving the correction is durable."
```

---

## Self-Review

**Spec coverage.** KB-07 = Tasks 1–3 (rows + mapping, port + store, supersession). KB-09 = Tasks 3–4 (I-2, I-3, I-4 via supersession; the leak suite; I-5 as-of boundaries in Task 2). KB-08 = Task 5. `tests/README.md`'s durability rule is exercised twice in Task 5 (two restarts) and once in Task 2.

**Deliberately deferred, with reasons:** I-6/I-7 (projection-equals-replay, idempotent replay) need an event log, which this store does not yet have — the store *is* the projection today. I-8 (no-lost-update) needs concurrent writers, which SQLite in a single-process test cannot honestly simulate. Hypothesis `RuleBasedStateMachine` is deferred until the store's shape is settled; adding it now would pin an API that Task 3 changes. All three are logged as follow-ups rather than silently dropped.

**Placeholder scan:** none — every step carries runnable code.

**Type consistency:** `SqliteCanonStore` method names and signatures are identical across the port (Task 2), the adapter (Task 2), the supersede addition (Task 3), and all three test files. `_fact` helpers are repeated per test module rather than cross-imported, per pytest convention.

"""Integration tests for the SQLite canon store — REAL database file, never :memory:.

See tests/README.md § "Testing the Canon Kernel". The rule these tests exist to enforce:
every load-bearing field must appear on the left-hand side of an assert AFTER a real
save-and-reload. Graphiti's own suite round-trips temporal edges and then asserts only on
uuid — it would pass while every temporal field was corrupted.

Supersession tests live here (not in test_canon_invariants.py, which another agent owns)
to avoid a file collision; the assertions are unchanged from the plan's Task 3.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import (
    SqliteCanonStore,
    _to_domain,
    _to_row,
)
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

    old = store.as_of("canon", "kael", "loyal_to", 1)
    assert old is not None
    assert old.id == "f-old"
    at_boundary = store.as_of("canon", "kael", "loyal_to", 180)
    assert at_boundary is not None
    assert at_boundary.id == "f-old"
    after_boundary = store.as_of("canon", "kael", "loyal_to", 181)
    assert after_boundary is not None
    assert after_boundary.id == "f-new"
    far_future = store.as_of("canon", "kael", "loyal_to", 9999)
    assert far_future is not None
    assert far_future.id == "f-new"


def test_as_of_returns_none_before_anything_is_true(store: SqliteCanonStore) -> None:
    store.append(_fact(valid_from=5))
    assert store.as_of("canon", "kael", "loyal_to", 4) is None


def test_as_of_is_fork_scoped(store: SqliteCanonStore) -> None:
    """A fork's fact must not answer a query against its sibling."""
    store.append(_fact(id="f-canon", fork_id="canon", object_id="the_crown"))
    store.append(_fact(id="f-a", fork_id="fork-a", object_id="the_rebels"))
    result = store.as_of("fork-a", "kael", "loyal_to", 1)
    assert result is not None
    assert result.object_id == "the_rebels"


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


def test_i2_exactly_one_live_fact_per_key_after_supersession(
    store: SqliteCanonStore,
) -> None:
    """I-2: two live contradicting rows for one key IS corrupt canon."""
    store.append(_fact(id="f-old", object_id="the_crown"))
    store.supersede(
        "f-old",
        replacement=_fact(id="f-new", object_id="the_rebels", valid_from=181),
        closes_at=180,
        superseded_at=SUPERSEDED,
    )
    live = [f for f in store.all_facts("canon") if f.status is FactStatus.ACTIVE]
    assert len(live) == 1
    assert live[0].id == "f-new"


def test_i4_supersession_never_mutates_the_old_rows_open_fields(
    store: SqliteCanonStore,
) -> None:
    """I-4: append-only is what makes history auditable. Only valid_to/superseded_at move."""
    store.append(_fact(id="f-old", valid_from=1, revealed_at=1))
    store.supersede(
        "f-old",
        replacement=_fact(id="f-new", valid_from=181),
        closes_at=180,
        superseded_at=SUPERSEDED,
    )
    old = store.get("f-old")
    assert old is not None
    assert old.valid_from == 1
    assert old.revealed_at == 1
    assert old.recorded_at == RECORDED
    assert old.valid_to == 180
    assert old.superseded_at == SUPERSEDED
    assert old.status is FactStatus.INVALIDATED


def test_both_rows_remain_queryable_after_supersession(store: SqliteCanonStore) -> None:
    """The superseded fact is still canon at its own timestamp — never delete it."""
    store.append(_fact(id="f-old", object_id="the_crown"))
    store.supersede(
        "f-old",
        replacement=_fact(id="f-new", object_id="the_rebels", valid_from=181),
        closes_at=180,
        superseded_at=SUPERSEDED,
    )
    at_100 = store.as_of("canon", "kael", "loyal_to", 100)
    assert at_100 is not None
    assert at_100.object_id == "the_crown"
    at_200 = store.as_of("canon", "kael", "loyal_to", 200)
    assert at_200 is not None
    assert at_200.object_id == "the_rebels"


def test_superseding_an_unknown_id_raises(store: SqliteCanonStore) -> None:
    """Fail loud. A silent no-op here loses the replacement fact entirely."""
    with pytest.raises(KeyError):
        store.supersede(
            "nope",
            replacement=_fact(id="f-new"),
            closes_at=1,
            superseded_at=SUPERSEDED,
        )

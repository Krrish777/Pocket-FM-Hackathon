"""Temporal invariants I-1..I-9 — see tests/README.md § "Testing the Canon Kernel".

This module owns the spoiler-guard leak suite (KB-09's centrepiece). Supersession
invariants (I-2, I-4) live in `test_canon_store_sqlite.py` — a concurrent agent claimed
that file first, and this project bans cross-importing `_fact` helpers between test
modules, so the helper below is a deliberate, standard-following duplicate.
"""

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

LEAK_SEVERITY = "A leaked fact is a HARD failure — it is the guarantee's whole purpose."


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
            source_id="s", chapter=1, char_start=0, char_end=4, quote="Kael"
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> SqliteCanonStore:
    """A store backed by a REAL file on disk — never :memory:."""
    engine = create_engine(f"sqlite:///{tmp_path / 'canon.db'}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


@pytest.mark.parametrize("cutoff", [0, 1, 2, 3, 4, 5, 10, 100])
def test_no_fact_is_ever_leaked_at_any_cutoff(
    store: SqliteCanonStore, cutoff: int
) -> None:
    """Set equality, not spot checks.

    Spot checks ("assert fact X is absent") only catch leaks you already thought of.
    Asserting the whole returned id set catches the ones you didn't.
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


def test_a_quarantined_fact_is_never_visible_however_early_it_was_revealed(
    store: SqliteCanonStore,
) -> None:
    """Status must dominate reveal time, or the curation gate is decorative."""
    store.append(_fact(id="f-q", revealed_at=1, status=FactStatus.QUARANTINED))
    assert store.visible_to("canon", AUDIENCE, 9999) == (), LEAK_SEVERITY


def test_scope_tracked_facts_do_not_leak_to_a_knower_outside_the_scope(
    store: SqliteCanonStore,
) -> None:
    """The dramatic-irony case: Watson must not receive a Holmes-only secret."""
    store.append(
        _fact(
            id="f-secret", revealed_at=1, knower_scope=frozenset({AUDIENCE, "holmes"})
        )
    )
    assert store.visible_to("canon", "watson", 9999) == (), LEAK_SEVERITY
    assert {f.id for f in store.visible_to("canon", "holmes", 9999)} == {"f-secret"}


def test_an_invalidated_fact_stays_in_the_spoiler_guard_but_not_current_truth(
    store: SqliteCanonStore,
) -> None:
    """`visible_to` is a pure spoiler guard; it is not a currency check.

    CORRECTED: this test previously asserted that `store.visible_to` excludes an
    INVALIDATED fact at any chapter after its supersession — treating "was this told"
    and "is this still true" as one question. They are not. `is_visible_to` excludes
    only QUARANTINED (never-canon); a superseded fact that was told is still knowable,
    which is what makes the replay mechanic work. The store-level guard therefore
    returns BOTH rows here — currency (excluding a stale fact from a CURRENT-chapter
    packet) is `is_valid_at`'s job, applied by `WorkingMemory.assemble`, not the store.
    """
    store.append(_fact(id="f-old", revealed_at=1))
    store.supersede(
        "f-old",
        replacement=_fact(
            id="f-new", object_id="the_rebels", valid_from=181, revealed_at=181
        ),
        closes_at=180,
        superseded_at=SUPERSEDED_AT,
    )
    visible_ids = {f.id for f in store.visible_to("canon", AUDIENCE, 9999)}
    assert visible_ids == {"f-old", "f-new"}

    # The currency check: at chapter 9999, only f-new is still TRUE, even though both
    # facts remain in the spoiler-guard's visible set above.
    facts_by_id = {f.id: f for f in store.all_facts("canon")}
    current_ids = {
        fact_id
        for fact_id, fact in facts_by_id.items()
        if fact_id in visible_ids and fact.is_valid_at(9999)
    }
    assert current_ids == {"f-new"}


def test_over_withholding_is_reported_not_failed(
    store: SqliteCanonStore, capsys: pytest.CaptureFixture[str]
) -> None:
    """The asymmetry, encoded.

    Over-withholding costs the writer a usable detail; the audience never sees the
    difference. Failing the build on it would make the suite reject
    correct-but-conservative behaviour, so it is measured and printed instead of
    asserted.
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

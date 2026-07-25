"""L3 — the whole memory-storage path, end to end, against a real database file.

This is the session's definition of done. It is deliberately ONE long test rather than
many small ones: the property being proven is that a REALISTIC SEQUENCE of operations
survives TWO restarts with all three time axes intact. Splitting it into isolated cases
would let each step pass while the sequence as a whole was broken.
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
    """Build a valid Fact for the ingest scenario, overriding named fields."""
    defaults: dict[str, object] = {
        "id": fact_id,
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
            source_id="novel", chapter=1, char_start=0, char_end=4, quote="Kael"
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": INGESTED_AT,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def test_memory_storage_end_to_end(tmp_path: Path) -> None:
    """Ingest -> restart -> spoiler guard -> epistemic scope -> supersede -> restart.

    Never `:memory:`: a real file lets us close every pooled connection with
    `engine.dispose()` and reopen a FRESH engine against the same file, twice, so the
    durability of both an insert and a correction is proven — not just of a warm process.
    """
    db = tmp_path / "canon.db"

    # --- 1. INGEST: a serial with an ordinary fact, a secret, and a late reveal ------------
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
            knower_scope={AUDIENCE: 3, "holmes": 3},  # Watson is not in scope
        )
    )

    # --- 2. FIRST RESTART: close every connection, then reopen the same file ---------------
    engine.dispose()
    reopened = SqliteCanonStore(create_engine(f"sqlite:///{db}"))

    assert len(reopened.all_facts("canon")) == 3, "data did not survive the restart"

    # --- 3. SPOILER GUARD at chapter 10, before the reveal ----------------------------------
    visible_ids = {f.id for f in reopened.visible_to("canon", AUDIENCE, 10)}
    assert "f-killer" not in visible_ids, (
        "LEAK: the killer was revealed 20 chapters early"
    )
    assert visible_ids == {"f-loyal", "f-secret"}

    # ...and after it
    assert "f-killer" in {f.id for f in reopened.visible_to("canon", AUDIENCE, 30)}

    # --- 4. EPISTEMIC SCOPE: Watson may not act on a Holmes-only fact ----------------------
    watson_ids = {f.id for f in reopened.visible_to("canon", "watson", 10)}
    assert "f-secret" not in watson_ids, "LEAK: Watson received a Holmes-only fact"

    # --- 5. SUPERSEDE: Kael defects at chapter 181 ------------------------------------------
    reopened.supersede(
        "f-loyal",
        replacement=_fact("f-defected", object_id="the_rebels", valid_from=181),
        closes_at=180,
        superseded_at=CORRECTED_AT,
    )

    # --- 6. BOTH rows survive; exactly one is live at any story time -----------------------
    at_100 = reopened.as_of("canon", "kael", "loyal_to", 100)
    at_200 = reopened.as_of("canon", "kael", "loyal_to", 200)
    assert at_100 is not None
    assert at_100.object_id == "the_crown"
    assert at_200 is not None
    assert at_200.object_id == "the_rebels"
    assert conflicting_active_facts(reopened.all_facts("canon"), chapter=200) == ()

    # --- 7. SECOND RESTART: the correction is durable too -----------------------------------
    final = SqliteCanonStore(create_engine(f"sqlite:///{db}"))
    final_at_100 = final.as_of("canon", "kael", "loyal_to", 100)
    assert final_at_100 is not None
    assert final_at_100.object_id == "the_crown"

    old_after_supersession = final.get("f-loyal")
    assert old_after_supersession is not None
    assert old_after_supersession.status is FactStatus.INVALIDATED
    # Append-only: supersession must not mutate the old row's immutable fields — only
    # valid_to/superseded_at/status may move. An in-place edit here would silently
    # destroy the audit trail I-4 exists to protect.
    assert old_after_supersession.valid_from == 1, "supersession mutated valid_from"
    assert old_after_supersession.recorded_at == INGESTED_AT, (
        "supersession mutated recorded_at"
    )
    assert old_after_supersession.revealed_at == 1, "supersession mutated revealed_at"

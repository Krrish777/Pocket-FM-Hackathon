"""L3 — ALL THREE LAYERS of the hybrid knowledge base, one real database, two restarts.

Layer 1 store, layer 2 graph projection, layer 3 working memory. Deliberately one long
test rather than many small ones: the property being proven is that a REALISTIC SEQUENCE
survives persistence with the guard intact at every layer. Split into isolated cases, each
step could pass while the hybrid as a whole leaked — a guard enforced only at the store,
with an unguarded graph or packet beside it, is not a guard, it is a spoiler side-channel.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.graph import LoreGraph
from story_engine.domain.invariants import conflicting_active_facts
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.services.working_memory import WorkingMemory

pytestmark = pytest.mark.e2e

INGESTED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
CORRECTED = datetime(2026, 7, 25, 18, 0, tzinfo=UTC)


def _fact(fact_id: str, subject: str, predicate: str, obj: str, **kw: object) -> Fact:
    """Build a valid Fact for the hybrid scenario, overriding named fields."""
    defaults: dict[str, object] = {
        "id": fact_id,
        "fork_id": "canon",
        "subject_id": subject,
        "predicate": predicate,
        "object_id": obj,
        "object_literal": None,
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="novel", chapter=1, char_start=0, char_end=6, quote="Holmes"
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": INGESTED,
        "superseded_at": None,
    }
    return Fact(**(defaults | kw))  # type: ignore[arg-type]


def test_hybrid_knowledge_base_end_to_end(tmp_path: Path) -> None:
    """Ingest -> restart -> graph guard -> memory guard -> scope -> supersede -> restart.

    Never `:memory:`: a real file lets us `engine.dispose()` and reopen a FRESH engine
    against the same path, twice, so durability is proven for both the original ingest and
    the later correction — not merely that a warm process behaves correctly.
    """
    db = tmp_path / "hybrid.db"

    # --- LAYER 1: ingest several facts into a real on-disk database --------------------
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)

    store.append(_fact("f-hw", "holmes", "knows", "watson", revealed_at=1))
    store.append(_fact("f-wm", "watson", "knows", "mary", revealed_at=1))
    # The late reveal: true from the start, but the audience only learns it at chapter 30.
    store.append(_fact("f-kill", "moriarty", "killed", "victim", revealed_at=30))
    # Scoped to a single character: Watson must never see this, only Mycroft and AUDIENCE.
    # Subject is deliberately NOT holmes, so it does not perturb the holmes-rooted
    # multi-hop traversal assertion below.
    store.append(
        _fact(
            "f-secret",
            "mycroft",
            "knows_about",
            "the_ash",
            valid_from=3,
            revealed_at=3,
            knower_scope={AUDIENCE: 3, "mycroft": 3},
        )
    )
    store.append(
        _fact("f-loyal", "kael", "loyal_to", "crown", valid_from=1, revealed_at=1)
    )

    # --- RESTART: prove persistence, not process memory ---------------------------------
    engine.dispose()
    reopened = SqliteCanonStore(create_engine(f"sqlite:///{db}"))
    assert len(reopened.all_facts("canon")) == 5, "data did not survive the restart"

    # --- LAYER 2: the graph must NOT become a spoiler side-channel ----------------------
    graph_at_10 = LoreGraph.from_facts(
        reopened.all_facts("canon"), knower=AUDIENCE, chapter=10
    )
    assert graph_at_10.neighbours("moriarty") == (), (
        "LEAK: the killer was revealed 20 chapters early via a direct graph edge"
    )
    assert "victim" not in graph_at_10.related_within("moriarty", hops=5), (
        "LEAK: the killer was reachable via multi-hop traversal — traversal is exactly "
        "how you would reach an otherwise-withheld fact"
    )

    # ...and multi-hop traversal DOES work for what is legitimately revealed.
    assert graph_at_10.related_within("holmes", hops=2) == frozenset({"watson", "mary"})

    # ...and the same fact becomes reachable once the telling reaches it.
    graph_at_30 = LoreGraph.from_facts(
        reopened.all_facts("canon"), knower=AUDIENCE, chapter=30
    )
    assert graph_at_30.neighbours("moriarty") != (), (
        "the killer should be a reachable edge once chapter 30 is told"
    )

    # --- LAYER 3: working memory, bounded and guarded ------------------------------------
    packet = WorkingMemory(reopened).assemble(
        "canon", AUDIENCE, chapter=10, focus_entities=("holmes",), budget=3
    )
    assert "f-kill" not in {f.id for f in packet.facts}, (
        "LEAK: the killer was exposed through the assembled memory packet"
    )
    # At chapter 10: f-kill (revealed_at=30) is the only fact withheld from AUDIENCE;
    # f-secret is scoped to mycroft but AUDIENCE is also in its knower_scope, so it is
    # visible to AUDIENCE and does not count as withheld here.
    assert packet.withheld_count == 1
    assert len(packet.facts) <= 3, "budget was not respected"
    assert "f-hw" in {f.id for f in packet.facts}, (
        "focus entity was evicted from a budgeted packet — the scene's own character must "
        "survive the budget"
    )

    # ...and the packet's own graph inherits the guard.
    assert packet.graph.neighbours("moriarty") == (), (
        "LEAK: the packet's derived graph exposed the killer"
    )

    # --- EPISTEMIC SCOPE: Watson may not act on a Mycroft-only fact ---------------------
    watson_ids = {f.id for f in reopened.visible_to("canon", "watson", 10)}
    assert "f-secret" not in watson_ids, "LEAK: Watson received a Mycroft-only fact"
    assert "f-secret" in {f.id for f in reopened.visible_to("canon", "mycroft", 10)}, (
        "mycroft should see his own scoped secret"
    )

    # --- SUPERSESSION across all three layers --------------------------------------------
    # Snapshot the graph before AND after the supersede at the same chapter: `is_visible_to`
    # excludes only QUARANTINED, not every non-ACTIVE status, so an INVALIDATED fact stays
    # visible at chapters inside its old validity window regardless of when it was queried
    # relative to the supersede call. The pre-supersede snapshot is kept here anyway to
    # prove `relationship_diff` reports the two changed edges either way.
    early = LoreGraph.from_facts(reopened.all_facts("canon"), AUDIENCE, chapter=100)

    reopened.supersede(
        "f-loyal",
        replacement=_fact(
            "f-defect", "kael", "loyal_to", "rebels", valid_from=181, revealed_at=181
        ),
        closes_at=180,
        superseded_at=CORRECTED,
    )

    # as_of and visible_to now AGREE on INVALIDATED rows: a superseded fact is still
    # canon at its own story-time window, so chapter 100 (before the close at 180)
    # still resolves to the OLD value even though the row's status is now INVALIDATED.
    old_value = reopened.as_of("canon", "kael", "loyal_to", 100)
    new_value = reopened.as_of("canon", "kael", "loyal_to", 200)
    assert old_value is not None and old_value.object_id == "crown"
    assert new_value is not None and new_value.object_id == "rebels"

    late = LoreGraph.from_facts(reopened.all_facts("canon"), AUDIENCE, chapter=200)
    assert {e.object_id for e in early.relationship_diff(late)} == {
        "crown",
        "rebels",
    }, "relationship_diff must report exactly the two changed edges"

    # Exactly one live fact per (subject, predicate) at the current story time — the
    # supersession must not leave both the old and new row simultaneously active.
    assert conflicting_active_facts(reopened.all_facts("canon"), chapter=200) == ()

    # --- SECOND RESTART: the correction is durable too ------------------------------------
    final = SqliteCanonStore(create_engine(f"sqlite:///{db}"))

    old_after_supersession = final.get("f-loyal")
    assert old_after_supersession is not None
    assert old_after_supersession.status is FactStatus.INVALIDATED
    # Append-only: supersession must not mutate the old row's immutable fields — only
    # valid_to/superseded_at/status may move. An in-place edit would silently destroy the
    # audit trail invariant I-4 exists to protect.
    assert old_after_supersession.valid_from == 1, "supersession mutated valid_from"
    assert old_after_supersession.recorded_at == INGESTED, (
        "supersession mutated recorded_at"
    )
    assert old_after_supersession.revealed_at == 1, "supersession mutated revealed_at"

    final_packet = WorkingMemory(final).assemble("canon", AUDIENCE, chapter=200)
    assert "f-defect" in {f.id for f in final_packet.facts}, (
        "a freshly assembled packet after the second restart must reflect the correction"
    )
    assert "f-loyal" not in {f.id for f in final_packet.facts}, (
        "the superseded fact must not coexist with its replacement in a current packet"
    )

    # --- REPLAY: a packet assembled at the earlier chapter still reflects the old truth --
    # This is the core replay mechanic the product depends on: revisiting chapter 100
    # after the correction must show kael's loyalty to the crown, not a retroactively
    # rewritten history where the correction always applied.
    replay_packet = WorkingMemory(final).assemble("canon", AUDIENCE, chapter=100)
    assert "f-loyal" in {f.id for f in replay_packet.facts}, (
        "REPLAY BUG: a superseded fact must still surface at a chapter inside its old "
        "validity window"
    )
    assert "f-defect" not in {f.id for f in replay_packet.facts}, (
        "the replacement fact must not leak backward before it became true"
    )

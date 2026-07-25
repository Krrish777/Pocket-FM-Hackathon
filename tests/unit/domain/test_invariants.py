"""Unit tests for the pure invariant predicates (domain/invariants.py)."""

from datetime import UTC, datetime

from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    CommitmentType,
    EntityStatus,
    EntityType,
    FactStatus,
)
from story_engine.domain.invariants import (
    conflicting_active_facts,
    entities_acting_while_incapacitated,
    epistemic_violations,
    open_commitments,
    visible_facts,
    withheld_facts,
)
from story_engine.domain.models.canon import (
    AUDIENCE,
    CanonEntity,
    Commitment,
    Fact,
    Provenance,
)

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
PROV = Provenance(source_id="src-1", chapter=1, char_start=0, char_end=5, quote="Kael")


def _fact(fact_id: str, **overrides: object) -> Fact:
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
        "knower_scope": frozenset({AUDIENCE}),
        "provenance": PROV,
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def test_visible_and_withheld_partition_the_fact_set() -> None:
    """Every fact is either servable or withheld — nothing may fall through."""
    facts = (
        _fact("f-1", revealed_at=1),
        _fact("f-2", revealed_at=9),
        _fact("f-3", revealed_at=None),
    )
    visible = visible_facts(facts, AUDIENCE, chapter=5)
    withheld = withheld_facts(facts, AUDIENCE, chapter=5)

    assert {f.id for f in visible} == {"f-1"}
    assert {f.id for f in withheld} == {"f-2", "f-3"}
    assert len(visible) + len(withheld) == len(facts)


def test_epistemic_violations_catch_acting_on_unknown_information() -> None:
    """Watson may not act on a fact only Holmes knows."""
    facts = (
        _fact("f-1", knower_scope=frozenset({AUDIENCE, "holmes"})),
        _fact("f-2", knower_scope=frozenset({AUDIENCE, "watson"})),
    )
    violations = epistemic_violations(
        used_fact_ids=("f-1", "f-2"), facts=facts, knower="watson", chapter=5
    )
    assert {f.id for f in violations} == {"f-1"}


def test_epistemic_violations_ignore_unknown_fact_ids() -> None:
    """An id with no matching fact is not this predicate's problem."""
    facts = (_fact("f-1"),)
    assert epistemic_violations(("f-404",), facts, AUDIENCE, chapter=5) == ()


def test_conflicting_active_facts_detect_two_current_values() -> None:
    """A single-valued predicate must not hold two values at one story time."""
    facts = (
        _fact("f-1", predicate="located_in", object_id="london", valid_from=1),
        _fact("f-2", predicate="located_in", object_id="paris", valid_from=1),
    )
    conflicts = conflicting_active_facts(facts, chapter=3)
    assert len(conflicts) == 1
    assert {conflicts[0][0].id, conflicts[0][1].id} == {"f-1", "f-2"}


def test_superseded_facts_do_not_conflict() -> None:
    """Invalidate-not-overwrite means both rows exist; only one is current."""
    facts = (
        _fact(
            "f-1", predicate="located_in", object_id="london", valid_from=1, valid_to=2
        ),
        _fact("f-2", predicate="located_in", object_id="paris", valid_from=3),
    )
    assert conflicting_active_facts(facts, chapter=5) == ()


def test_facts_in_different_forks_do_not_conflict() -> None:
    """Contradicting canon is legal inside a fork — that is what a fork is for."""
    facts = (
        _fact("f-1", predicate="located_in", object_id="london"),
        _fact("f-2", fork_id="fork-a", predicate="located_in", object_id="paris"),
    )
    assert conflicting_active_facts(facts, chapter=3) == ()


def test_open_commitments_exclude_discharged_ones() -> None:
    prov = PROV
    commitments = (
        Commitment(
            id="c-1",
            fork_id="canon",
            type=CommitmentType.FORESHADOW,
            planted_at=3,
            state=CommitmentState.PLANTED,
            payoff_at=None,
            entity_ids=(),
            provenance=prov,
        ),
        Commitment(
            id="c-2",
            fork_id="canon",
            type=CommitmentType.SECRET,
            planted_at=3,
            state=CommitmentState.PAID_OFF,
            payoff_at=40,
            entity_ids=(),
            provenance=prov,
        ),
    )
    assert {c.id for c in open_commitments(commitments)} == {"c-1"}


def test_dead_and_imprisoned_entities_cannot_act_freely() -> None:
    entities = (
        CanonEntity(
            id="kael",
            fork_id="canon",
            type=EntityType.CHARACTER,
            canonical_name="Kael",
            aliases=(),
            status=EntityStatus.DEAD,
        ),
        CanonEntity(
            id="mara",
            fork_id="canon",
            type=EntityType.CHARACTER,
            canonical_name="Mara",
            aliases=(),
            status=EntityStatus.IMPRISONED,
        ),
        CanonEntity(
            id="finn",
            fork_id="canon",
            type=EntityType.CHARACTER,
            canonical_name="Finn",
            aliases=(),
            status=EntityStatus.ACTIVE,
        ),
    )
    offenders = entities_acting_while_incapacitated(
        acting_entity_ids=("kael", "mara", "finn"), entities=entities
    )
    assert {e.id for e in offenders} == {"kael", "mara"}

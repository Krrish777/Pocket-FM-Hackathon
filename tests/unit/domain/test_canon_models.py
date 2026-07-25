"""Unit tests for the Canon Kernel schema (domain/models/canon.py)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    CommitmentType,
    EntityStatus,
    EntityType,
    FactStatus,
    FlagSeverity,
    InvariantKind,
    PresenceGrade,
    SourceType,
    VerificationLane,
)
from story_engine.domain.models.canon import (
    AUDIENCE,
    CanonEntity,
    Commitment,
    Fact,
    Flag,
    Fork,
    Presence,
    Provenance,
    Scene,
    Source,
)


def test_kernel_enums_are_str_enums() -> None:
    """Kernel enums render as plain strings across the LLM/JSON boundary."""
    # StrEnum members ARE strings at runtime; mypy strict mode doesn't recognize this.
    assert AssertionMode.ATTRIBUTED == "attributed"  # type: ignore
    assert FactStatus.QUARANTINED == "quarantined"  # type: ignore
    assert EntityStatus.DEAD == "dead"  # type: ignore
    assert CommitmentState.PAID_OFF == "paid_off"  # type: ignore
    assert PresenceGrade.SILENT == "silent"  # type: ignore


def test_provenance_requires_a_forward_span() -> None:
    """char_end must come after char_start — a zero-width span cites nothing."""
    with pytest.raises(ValidationError):
        Provenance(
            source_id="src-1", chapter=3, char_start=100, char_end=100, quote="x"
        )


def test_provenance_accepts_a_valid_span() -> None:
    """Accept a valid character span."""
    prov = Provenance(
        source_id="src-1",
        chapter=3,
        char_start=100,
        char_end=118,
        quote="the vault was empty",
    )
    assert prov.chapter == 3


def test_root_fork_has_no_parent_and_no_divergence() -> None:
    """Root forks are base canon without a parent or divergence point."""
    root = Fork(
        id="canon",
        parent_fork_id=None,
        divergence_at=None,
        source_id="src-1",
        label="base novel",
    )
    assert root.is_root is True


def test_non_root_fork_must_declare_a_divergence_point() -> None:
    """A branch without a divergence point cannot be resolved against its parent."""
    with pytest.raises(ValidationError):
        Fork(
            id="fork-a",
            parent_fork_id="canon",
            divergence_at=None,
            source_id="src-2",
            label="what if Kael never defects",
        )


def test_root_fork_may_not_declare_a_divergence_point() -> None:
    """Root forks cannot declare a divergence point."""
    with pytest.raises(ValidationError):
        Fork(
            id="canon",
            parent_fork_id=None,
            divergence_at=12,
            source_id="src-1",
            label="base novel",
        )


def test_source_carries_an_authority_tier() -> None:
    """Sources have an authority tier for conflict resolution."""
    source = Source(
        id="src-2",
        type=SourceType.FANFIC,
        tier=2,
        title="A Study in Anything",
        url=None,
        license_note=None,
    )
    assert source.tier == 2


RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


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
        "knower_scope": frozenset({AUDIENCE, "kael"}),
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


def test_fact_requires_exactly_one_object() -> None:
    """A fact points at an entity or a literal, never both and never neither."""
    with pytest.raises(ValidationError):
        _fact(object_id="the_crown", object_literal="the Crown")
    with pytest.raises(ValidationError):
        _fact(object_id=None, object_literal=None)


def test_attributed_fact_must_name_its_speaker() -> None:
    """ATTRIBUTED without attributed_to is the bug that leaks reveals and stores lies."""
    with pytest.raises(ValidationError):
        _fact(assertion_mode=AssertionMode.ATTRIBUTED, attributed_to=None)


def test_narrated_fact_must_not_name_a_speaker() -> None:
    with pytest.raises(ValidationError):
        _fact(assertion_mode=AssertionMode.NARRATED, attributed_to="marcus")


def test_untracked_knower_scope_falls_back_to_audience_reveal() -> None:
    """Most facts never need per-character scope; None means "not tracked".

    Evidence: only 2 of ConStory's 19 consistency-error subtypes are epistemic, and they
    sit in a category worth ~3.5% of measured error density. Universal knower tracking
    buys little and costs a 32.6% false-extraction rate (CHIRON), whose failure mode is
    FALSE BLOCKS on legitimate dialogue. Scope is populated only for typed secrets/lies.
    """
    fact = _fact(knower_scope=None, revealed_at=3)
    assert fact.is_visible_to("anyone_at_all", 5) is True
    assert fact.is_visible_to("anyone_at_all", 2) is False


def test_tracked_knower_scope_must_not_be_empty() -> None:
    """If scope IS tracked, an empty set is a bug — use None to mean untracked."""
    with pytest.raises(ValidationError):
        _fact(knower_scope=frozenset())


def test_validity_window_must_not_close_before_it_opens() -> None:
    with pytest.raises(ValidationError):
        _fact(valid_from=10, valid_to=4)


def test_invalidated_fact_must_record_when_it_was_superseded() -> None:
    with pytest.raises(ValidationError):
        _fact(status=FactStatus.INVALIDATED, superseded_at=None)


def test_is_valid_at_respects_the_story_time_window() -> None:
    fact = _fact(valid_from=5, valid_to=10)
    assert fact.is_valid_at(4) is False
    assert fact.is_valid_at(5) is True
    assert fact.is_valid_at(10) is True
    assert fact.is_valid_at(11) is False


def test_open_validity_window_never_closes() -> None:
    fact = _fact(valid_from=5, valid_to=None)
    assert fact.is_valid_at(9999) is True


def test_is_revealed_by_respects_telling_time() -> None:
    fact = _fact(revealed_at=7)
    assert fact.is_revealed_by(6) is False
    assert fact.is_revealed_by(7) is True


def test_unrevealed_fact_is_never_revealed() -> None:
    """revealed_at=None means the audience has not earned it at any point yet."""
    fact = _fact(revealed_at=None)
    assert fact.is_revealed_by(9999) is False


def test_is_visible_to_combines_status_reveal_and_scope() -> None:
    fact = _fact(revealed_at=3, knower_scope=frozenset({AUDIENCE, "holmes"}))
    assert fact.is_visible_to("holmes", 5) is True
    assert fact.is_visible_to("watson", 5) is False  # not in scope
    assert fact.is_visible_to("holmes", 2) is False  # not yet revealed


def test_quarantined_fact_is_visible_to_nobody() -> None:
    fact = _fact(status=FactStatus.QUARANTINED)
    assert fact.is_visible_to(AUDIENCE, 9999) is False


def test_foreshadowed_fact_is_revealed_before_it_is_true() -> None:
    """Legal, not an error — this is what foreshadowing IS."""
    assert _fact(revealed_at=2, valid_from=40).is_foreshadowed is True
    assert _fact(revealed_at=40, valid_from=40).is_foreshadowed is False


def test_entity_matches_any_of_its_aliases_case_insensitively() -> None:
    """One node per identity: "the Stranger" and "the King" must resolve together."""
    entity = CanonEntity(
        id="e-1",
        fork_id="canon",
        type=EntityType.CHARACTER,
        canonical_name="Aldric",
        aliases=("the Stranger", "the King"),
        status=EntityStatus.ACTIVE,
    )
    assert entity.matches_name("aldric") is True
    assert entity.matches_name("The Stranger") is True
    assert entity.matches_name("Moriarty") is False


def test_scene_witnesses_exclude_merely_referenced_entities() -> None:
    """Being talked about is not being present — it must not confer knowledge."""
    scene = Scene(
        id="s-1",
        fork_id="canon",
        chapter=3,
        order_in_chapter=1,
        summary="Holmes examines the ash while Watson watches.",
        roster=(
            Presence(entity_id="holmes", grade=PresenceGrade.ACTIVE),
            Presence(entity_id="watson", grade=PresenceGrade.SILENT),
            Presence(entity_id="moriarty", grade=PresenceGrade.REFERENCED),
        ),
    )
    assert scene.witnesses == frozenset({"holmes", "watson"})


def _commitment(**overrides: object) -> Commitment:
    defaults: dict[str, object] = {
        "id": "c-1",
        "fork_id": "canon",
        "type": CommitmentType.FORESHADOW,
        "planted_at": 3,
        "state": CommitmentState.PLANTED,
        "payoff_at": None,
        "entity_ids": ("holmes",),
        "provenance": Provenance(
            source_id="src-1", chapter=3, char_start=0, char_end=9, quote="a scratch"
        ),
    }
    return Commitment(**(defaults | overrides))  # type: ignore[arg-type]


def test_commitment_allows_only_forward_transitions() -> None:
    planted = _commitment(state=CommitmentState.PLANTED)
    assert planted.can_transition_to(CommitmentState.TRIGGERED) is True
    assert planted.can_transition_to(CommitmentState.BROKEN) is True
    assert planted.can_transition_to(CommitmentState.PAID_OFF) is False


def test_paid_off_commitment_is_terminal() -> None:
    paid = _commitment(state=CommitmentState.PAID_OFF, payoff_at=40)
    assert paid.can_transition_to(CommitmentState.TRIGGERED) is False
    assert paid.is_open is False


def test_paid_off_commitment_must_record_where_it_paid_off() -> None:
    with pytest.raises(ValidationError):
        _commitment(state=CommitmentState.PAID_OFF, payoff_at=None)


def test_payoff_must_not_precede_planting() -> None:
    with pytest.raises(ValidationError):
        _commitment(state=CommitmentState.PAID_OFF, planted_at=10, payoff_at=4)


def test_hard_lane_flag_must_cite_at_least_one_fact() -> None:
    """An uncited flag is an opinion; a cited flag is evidence."""
    with pytest.raises(ValidationError):
        Flag(
            id="fl-1",
            invariant=InvariantKind.MORTALITY,
            severity=FlagSeverity.BLOCKING,
            lane=VerificationLane.HARD,
            draft_span="Kael spoke again.",
            cited_fact_ids=(),
            citation_text="draft says Kael speaks; canon: died @ ep 181",
            suggested_action=None,
        )


def test_flag_renders_a_citation() -> None:
    flag = Flag(
        id="fl-2",
        invariant=InvariantKind.MORTALITY,
        severity=FlagSeverity.BLOCKING,
        lane=VerificationLane.HARD,
        draft_span="Kael spoke again.",
        cited_fact_ids=("f-9",),
        citation_text="draft says Kael speaks; canon: died @ ep 181 s3",
        suggested_action="invalidate or depict a resurrection",
    )
    assert "ep 181" in flag.citation_text

"""Knowledge propagation must only ever add knowers — never remove one, never delay one.

The monotonicity invariant is asserted as a property over generated combinations rather than in a
handful of examples, because the failure it guards against is silent: a fact that quietly stops
being visible to someone still renders a perfectly readable scene, just one where a character has
forgotten something the audience watched them learn.
"""

from datetime import UTC, datetime

import pytest

from story_engine.domain.enums import AssertionMode, FactStatus, PresenceGrade
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.domain.models.canon import Awareness, Presence, Scene
from story_engine.domain.propagation import (
    merge_awareness,
    start_tracking,
    told,
    witnesses_learn,
)

RECORDED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(**overrides: object) -> Fact:
    defaults: dict[str, object] = {
        "id": "f-secret",
        "fork_id": "canon",
        "subject_id": "dexter",
        "predicate": "is_killer_of",
        "object_id": "the-priest",
        "valid_from": 1,
        # None, not 1: this is a typed secret Dexter holds and the audience has NOT been told.
        # The domain enforces the coupling — a fact with revealed_at set and a tracked scope
        # must list AUDIENCE, because the audience learning it IS a reveal.
        "revealed_at": None,
        "assertion_mode": AssertionMode.NARRATED,
        "knower_scope": (Awareness(knower="dexter", learned_at=1),),
        "provenance": Provenance(
            source_id="ddd", chapter=1, char_start=0, char_end=6, quote="Dexter"
        ),
        "confidence": 1.0,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED_AT,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def _scene(chapter: int, roster: dict[str, PresenceGrade]) -> Scene:
    return Scene(
        id=f"sc-{chapter}",
        fork_id="canon",
        chapter=chapter,
        order_in_chapter=0,
        summary="a scene",
        roster=tuple(
            Presence(entity_id=entity, grade=grade) for entity, grade in roster.items()
        ),
    )


# --- merge_awareness ------------------------------------------------------------------------


def test_merge_keeps_the_earliest_acquisition_per_knower() -> None:
    """Being present again later must not move a knower's clock forward.

    Otherwise re-deriving knowledge from a later scene would show a character ignorant of
    something they already knew, and a replay would contradict what the audience watched.
    """
    merged = merge_awareness(
        (Awareness(knower="deb", learned_at=3),),
        (Awareness(knower="deb", learned_at=7),),
    )

    assert merged == (Awareness(knower="deb", learned_at=3),)


def test_merge_moves_an_acquisition_earlier_when_new_evidence_is_earlier() -> None:
    merged = merge_awareness(
        (Awareness(knower="doakes", learned_at=20),),
        (Awareness(knower="doakes", learned_at=6),),
    )

    assert merged == (Awareness(knower="doakes", learned_at=6),)


def test_merge_never_drops_a_knower() -> None:
    merged = merge_awareness(
        (Awareness(knower="dexter", learned_at=1),),
        (Awareness(knower="deb", learned_at=4),),
    )

    assert {a.knower for a in merged} == {"dexter", "deb"}


def test_merge_output_is_sorted_so_equal_knowledge_compares_equal() -> None:
    """`Fact` is frozen and hashable; an order that varied by input order would break equality."""
    one = merge_awareness(
        (Awareness(knower="rita", learned_at=2), Awareness(knower="deb", learned_at=4)),
        (),
    )
    other = merge_awareness(
        (Awareness(knower="deb", learned_at=4), Awareness(knower="rita", learned_at=2)),
        (),
    )

    assert (
        one
        == other
        == (
            Awareness(knower="deb", learned_at=4),
            Awareness(knower="rita", learned_at=2),
        )
    )


# --- witnesses_learn ------------------------------------------------------------------------


def test_everyone_present_learns_the_fact_at_that_chapter() -> None:
    fact = _fact()

    updated = witnesses_learn(
        fact,
        _scene(6, {"dexter": PresenceGrade.ACTIVE, "doakes": PresenceGrade.SILENT}),
    )

    assert updated.knower_scope is not None
    assert {a.knower: a.learned_at for a in updated.knower_scope} == {
        "dexter": 1,
        "doakes": 6,
    }


def test_a_merely_referenced_character_does_not_learn() -> None:
    """Presence confers knowledge; being talked about does not. This is the whole mechanic."""
    updated = witnesses_learn(
        _fact(),
        _scene(6, {"dexter": PresenceGrade.ACTIVE, "deb": PresenceGrade.REFERENCED}),
    )

    assert updated.knower_scope is not None
    assert "deb" not in {a.knower for a in updated.knower_scope}


def test_an_absent_character_still_does_not_know_at_a_much_later_chapter() -> None:
    """project_context.md 4.2, stated exactly: absent at step 4 means ignorant at step N."""
    fact = witnesses_learn(_fact(), _scene(4, {"dexter": PresenceGrade.ACTIVE}))

    assert "deb" not in {a.knower for a in fact.knower_scope or ()}


def test_an_untracked_fact_is_left_untouched() -> None:
    """The inverse-of-learning trap.

    `is_visible` reads `knower_scope is None` as "visible to everyone once revealed". Attaching a
    scene's witnesses would restrict it to those witnesses — narrowing visibility in the name of
    spreading knowledge.
    """
    fact = _fact(knower_scope=None)

    updated = witnesses_learn(
        fact, _scene(6, {"dexter": PresenceGrade.ACTIVE, "deb": PresenceGrade.ACTIVE})
    )

    assert updated is fact
    assert updated.knower_scope is None


def test_a_scene_that_teaches_nobody_new_returns_the_same_object() -> None:
    """Callers use identity to decide whether a write is needed; a no-op must be detectable."""
    fact = _fact()

    updated = witnesses_learn(fact, _scene(9, {"dexter": PresenceGrade.ACTIVE}))

    assert updated is fact


def test_knowledge_compounds_across_a_sequence_of_scenes() -> None:
    """The butterfly effect, mechanically: each turn adds knowers and never loses one."""
    fact = _fact()

    fact = witnesses_learn(fact, _scene(2, {"deb": PresenceGrade.ACTIVE}))
    fact = witnesses_learn(fact, _scene(5, {"doakes": PresenceGrade.SILENT}))
    fact = witnesses_learn(fact, _scene(9, {"rita": PresenceGrade.ACTIVE}))

    assert fact.knower_scope is not None
    assert {a.knower: a.learned_at for a in fact.knower_scope} == {
        "dexter": 1,
        "deb": 2,
        "doakes": 5,
        "rita": 9,
    }


@pytest.mark.parametrize("chapters", [(2, 5, 9), (9, 5, 2), (5, 9, 2)])
def test_propagation_is_monotonic_whatever_order_scenes_arrive_in(
    chapters: tuple[int, int, int],
) -> None:
    """No ordering of scenes may remove a knower or delay one that is already recorded."""
    fact = _fact()
    known_before = {a.knower for a in fact.knower_scope or ()}

    for chapter in chapters:
        previous = {a.knower: a.learned_at for a in fact.knower_scope or ()}
        fact = witnesses_learn(fact, _scene(chapter, {"deb": PresenceGrade.ACTIVE}))
        current = {a.knower: a.learned_at for a in fact.knower_scope or ()}

        assert set(previous) <= set(current), "a knower was removed"
        for knower, learned_at in previous.items():
            assert current[knower] <= learned_at, "a knower's acquisition was delayed"

    assert known_before <= {a.knower for a in fact.knower_scope or ()}
    assert {a.knower: a.learned_at for a in fact.knower_scope or ()}["deb"] == min(
        chapters
    )


# --- told -----------------------------------------------------------------------------------


def test_being_told_records_knowledge_without_presence() -> None:
    """ "Doakes suspects at 6, the audience finds out at 20" is the sentence this enables."""
    updated = told(_fact(), AUDIENCE, 20)

    assert updated.knower_scope is not None
    assert {a.knower: a.learned_at for a in updated.knower_scope}[AUDIENCE] == 20


def test_telling_someone_about_an_untracked_fact_fails_loudly() -> None:
    """Silently restricting a public fact to one knower would be a spoiler guard inversion."""
    with pytest.raises(ValueError, match="untracked"):
        told(_fact(knower_scope=None), "deb", 5)


# --- start_tracking -------------------------------------------------------------------------


def test_start_tracking_turns_a_public_fact_into_a_secret() -> None:
    fact = _fact(knower_scope=None)

    secret = start_tracking(fact, (Awareness(knower="dexter", learned_at=1),))

    assert secret.knower_scope == (Awareness(knower="dexter", learned_at=1),)


def test_start_tracking_refuses_an_already_tracked_fact() -> None:
    with pytest.raises(ValueError, match="already tracked"):
        start_tracking(_fact(), (Awareness(knower="deb", learned_at=2),))


def test_start_tracking_refuses_an_empty_knower_set() -> None:
    """A fact nobody can ever see is not a secret, it is a deletion."""
    with pytest.raises(ValueError, match="no knowers"):
        start_tracking(_fact(knower_scope=None), ())

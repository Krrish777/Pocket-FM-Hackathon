"""Derived directives must describe what others are missing without ever leaking a third party.

The safety property is structural, not instructional: a directive is `actor_facts - their_facts`,
so it can only ever name facts the actor already knows. There is no path by which Doakes's private
knowledge reaches a prompt rendered for Deborah, because the subtraction never reads it. That is
worth a test, because the alternative design — describing each character's own state — would look
almost identical and would leak.
"""

from datetime import UTC, datetime

from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import Fact, Provenance
from story_engine.domain.models.canon import Awareness
from story_engine.domain.reactions import MAX_BLIND_SPOTS, derive_directives

RECORDED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(fact_id: str, subject: str = "dexter", predicate: str = "did") -> Fact:
    return Fact(
        id=fact_id,
        fork_id="canon",
        subject_id=subject,
        predicate=predicate,
        object_literal=f"thing-{fact_id}",
        valid_from=1,
        revealed_at=None,
        assertion_mode=AssertionMode.NARRATED,
        knower_scope=(Awareness(knower=subject, learned_at=1),),
        provenance=Provenance(
            source_id="ddd", chapter=1, char_start=0, char_end=6, quote="Dexter"
        ),
        confidence=1.0,
        tier=0,
        status=FactStatus.ACTIVE,
        recorded_at=RECORDED_AT,
    )


def test_a_directive_names_only_what_the_actor_already_knows() -> None:
    """The structural anti-leak property.

    Doakes holds a fact the actor has never seen. It must not appear in any directive, because a
    directive is a subtraction FROM the actor's view and never a read OF someone else's.
    """
    actor_facts = (_fact("f1"), _fact("f2"))
    doakes_private = _fact("f-doakes-only", subject="doakes")

    directives = derive_directives(
        actor="dexter",
        actor_facts=actor_facts,
        others={"doakes": ("Sergeant Doakes", (doakes_private,))},
    )

    everything_said = " ".join(
        spot for directive in directives for spot in directive.blind_spots
    )
    assert "f-doakes-only" not in everything_said
    assert "doakes" not in everything_said.replace("Sergeant Doakes", "")


def test_someone_who_was_not_there_is_marked_as_not_knowing() -> None:
    directives = derive_directives(
        actor="dexter",
        actor_facts=(_fact("f1"), _fact("f2")),
        others={"deborah": ("Deborah Morgan", ())},
    )

    assert len(directives) == 1
    assert len(directives[0].blind_spots) == 2
    assert directives[0].tension == 5, "she is missing everything"


def test_someone_who_shares_the_actors_view_has_no_blind_spots() -> None:
    shared = (_fact("f1"), _fact("f2"))

    directives = derive_directives(
        actor="dexter", actor_facts=shared, others={"doakes": ("Doakes", shared)}
    )

    assert directives[0].blind_spots == ()
    assert directives[0].tension == 0


def test_the_actor_is_never_given_a_directive_about_themselves() -> None:
    directives = derive_directives(
        actor="dexter",
        actor_facts=(_fact("f1"),),
        others={"dexter": ("Dexter Morgan", ()), "rita": ("Rita", ())},
    )

    assert [directive.character_id for directive in directives] == ["rita"]


def test_blind_spots_are_capped_so_a_directive_stays_a_nudge() -> None:
    """A dossier would crowd out the scene and push the model into reciting the difference."""
    directives = derive_directives(
        actor="dexter",
        actor_facts=tuple(_fact(f"f{i}") for i in range(10)),
        others={"rita": ("Rita", ())},
    )

    assert len(directives[0].blind_spots) == MAX_BLIND_SPOTS


def test_nothing_established_means_no_tension_rather_than_a_default() -> None:
    """Zero facts to compare on is not a divide-by-zero and not a middling 3."""
    directives = derive_directives(
        actor="dexter", actor_facts=(), others={"rita": ("Rita", ())}
    )

    assert directives[0].tension == 0
    assert directives[0].blind_spots == ()


def test_directives_are_ordered_stably() -> None:
    """Prompt text must not reshuffle between runs, or nothing downstream is reproducible."""
    others = {
        "rita": ("Rita", ()),
        "deborah": ("Deborah", ()),
        "doakes": ("Doakes", ()),
    }

    first = derive_directives(actor="dexter", actor_facts=(_fact("f1"),), others=others)
    second = derive_directives(
        actor="dexter", actor_facts=(_fact("f1"),), others=others
    )

    assert [d.character_id for d in first] == [d.character_id for d in second]
    assert [d.character_id for d in first] == ["deborah", "doakes", "rita"]

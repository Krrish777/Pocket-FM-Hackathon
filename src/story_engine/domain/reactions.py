"""Derived directives: what each other character is missing, computed fresh every turn.

`project_context.md` §4.4 is explicit that these are **computed at render time and never a stored
asymmetry**. The distinction is not stylistic. If we stored rich state for the protagonist and thin
directives for everyone else, we would hardcode a hierarchy into the data model, and replaying the
story as a "side" character (§8.1, the closing beat) would become a rewrite instead of a parameter
change. Deriving them means the fifth character gets the same treatment as the first, automatically.

A directive is a *subtraction*: what the acting character can see, minus what the other one can.
That has a useful safety property — the result can only ever contain facts the acting character
already knows, so a directive cannot smuggle a third party's secret into the prompt. It is
structurally incapable of leaking, rather than merely instructed not to.
"""

from story_engine.domain.base import DomainModel
from story_engine.domain.models.canon import Fact

MAX_TENSION = 5
MAX_BLIND_SPOTS = 3
"""A directive is a behavioural nudge, not a dossier. Listing every gap would crowd out the scene
and push the model toward reciting the difference rather than playing it."""


class CharacterDirective(DomainModel):
    """One other character, as the renderer needs to see them for a single beat."""

    character_id: str
    name: str
    blind_spots: tuple[str, ...]
    tension: int


def describe(fact: Fact) -> str:
    """Render a fact as the short clause a directive can carry."""
    obj = fact.object_literal or fact.object_id or ""
    return f"{fact.subject_id} {fact.predicate.replace('_', ' ')} {obj}".strip()


def derive_directives(
    *,
    actor: str,
    actor_facts: tuple[Fact, ...],
    others: dict[str, tuple[str, tuple[Fact, ...]]],
) -> tuple[CharacterDirective, ...]:
    """Compute what each other character is missing relative to `actor`.

    Args:
        actor: The character whose view is being rendered.
        actor_facts: What the actor can see — already guarded.
        others: `{character_id: (display_name, their_guarded_facts)}`. Every entry must come from
            the same guarded query the actor's did, so the subtraction compares like with like.

    Returns:
        One directive per other character, in a stable order, excluding `actor`.
    """
    actor_ids = {fact.id for fact in actor_facts}
    directives: list[CharacterDirective] = []

    for character_id, (name, their_facts) in sorted(others.items()):
        if character_id == actor:
            continue
        theirs = {fact.id for fact in their_facts}
        missing = [fact for fact in actor_facts if fact.id not in theirs]
        directives.append(
            CharacterDirective(
                character_id=character_id,
                name=name,
                blind_spots=tuple(describe(fact) for fact in missing[:MAX_BLIND_SPOTS]),
                tension=_tension(len(missing), len(actor_ids)),
            )
        )

    return tuple(directives)


def _tension(missing: int, total: int) -> int:
    """How far this character is from the actor's picture, on a 0-5 scale.

    Deliberately a *derived* number rather than an authored personality stat. An authored value
    would be a stored asymmetry by another name, and it would not move when the story does — the
    whole point is that a choice which puts someone in the room should change how they read on the
    next turn, without anyone editing a character sheet.

    Zero facts to compare on means zero tension, not a divide-by-zero and not a default of 3: with
    nothing established, there is nothing to be in the dark about.
    """
    if total <= 0:
        return 0
    return min(MAX_TENSION, round(MAX_TENSION * missing / total))

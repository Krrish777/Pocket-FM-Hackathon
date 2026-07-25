"""How knowledge spreads: presence at a scene becomes per-character knowledge.

This is the step that makes `project_context.md` §4.2 hold — *"at every step N the world state
must correctly reflect choices 1 through N-1, and a character who did not learn a fact at step 4
must still not know it at step N"*. Without it, `knower_scope` is only ever whatever ingestion
wrote, so nothing a player does can change who knows what, and the ripple, the butterfly effect,
per-character memory, and the replay-as-another-character beat all collapse into set dressing.

Pure and deterministic by design: **no model decides who learned what.** `project_context.md` §4.4
requires state transitions to be computed in code, because the epistemic guarantee comes from what
is absent from an assembled context, not from asking a model to withhold.

## The one invariant everything here protects

**Propagation is monotonic.** It may add a knower, and it may move an acquisition *earlier*. It may
never remove a knower and never push one *later*. Two consequences that are easy to get wrong:

* **An untracked fact stays untracked.** `is_visible` treats `knower_scope is None` as "governed by
  `revealed_at`" — visible to *everyone* once the audience learns it. A populated scope means
  "**only** these knowers". So attaching a scene's witnesses to an untracked fact would take it from
  visible-to-all down to visible-to-three: the exact inverse of learning. `witnesses_learn` is
  therefore a **no-op** on untracked facts, and `start_tracking` exists for the deliberate case.
* **Earliest acquisition wins.** Someone who learned a secret in chapter 3 does not un-learn and
  re-learn it by being present in chapter 7. Re-deriving from a later scene must not move their
  clock forward, or a replay would show them ignorant of something they already knew.
"""

from story_engine.domain.models.canon import Awareness, ChapterIndex, Fact, Scene


def merge_awareness(
    existing: tuple[Awareness, ...], incoming: tuple[Awareness, ...]
) -> tuple[Awareness, ...]:
    """Combine two knowledge sets, keeping each knower's *earliest* acquisition.

    Args:
        existing: What is already recorded.
        incoming: Newly derived acquisitions.

    Returns:
        One entry per knower, sorted by knower name so the result is stable across runs —
        `Fact` is a frozen, hashable value object, and an order that varied by input order would
        make two equal knowledge sets compare unequal.
    """
    earliest: dict[str, ChapterIndex] = {}
    for awareness in (*existing, *incoming):
        current = earliest.get(awareness.knower)
        if current is None or awareness.learned_at < current:
            earliest[awareness.knower] = awareness.learned_at
    return tuple(
        Awareness(knower=knower, learned_at=chapter)
        for knower, chapter in sorted(earliest.items())
    )


def witnesses_learn(fact: Fact, scene: Scene) -> Fact:
    """Record everyone present at `scene` as knowing `fact` from that scene's chapter.

    Presence confers knowledge; being merely mentioned does not. `Scene.witnesses` already applies
    that rule by excluding `PresenceGrade.REFERENCED`, so a character discussed in absentia does
    not learn what was said about them.

    Args:
        fact: The claim disclosed in the scene.
        scene: The scene where it was disclosed; its roster decides who learned it.

    Returns:
        The fact with the scene's witnesses merged into its `knower_scope`, or the fact unchanged
        when it is untracked (see the module docstring) or when nobody new learned anything.
        Returning the original object on a no-op keeps identity checks meaningful for callers
        deciding whether a write is needed.
    """
    if fact.knower_scope is None:
        return fact  # untracked: adding a scope would NARROW visibility, not widen it

    incoming = tuple(
        Awareness(knower=witness, learned_at=scene.chapter)
        for witness in sorted(scene.witnesses)
    )
    merged = merge_awareness(fact.knower_scope, incoming)
    if merged == fact.knower_scope:
        return fact
    return fact.model_copy(update={"knower_scope": merged})


def told(fact: Fact, knower: str, chapter: ChapterIndex) -> Fact:
    """Record that `knower` was told `fact` at `chapter`, without having witnessed it.

    The second of the three channels named in `project_context.md` §5.3 — witnessed, told, inferred.
    Kept separate from `witnesses_learn` because being told is an explicit narrative act with its
    own timing, not something derivable from a roster: Deborah can be told in chapter 20 about a
    scene she was absent from in chapter 6.

    Raises:
        ValueError: If `fact` is untracked. Telling one person about an untracked fact cannot be
            expressed by adding them to a scope, because that would hide the fact from everyone
            else. Call `start_tracking` first if the fact really is a secret.
    """
    if fact.knower_scope is None:
        raise ValueError(
            f"cannot record telling {knower!r} about untracked fact {fact.id!r}: adding a "
            f"knower_scope would restrict this fact to that one knower. Use start_tracking() "
            f"first if it is meant to be a secret."
        )
    merged = merge_awareness(
        fact.knower_scope, (Awareness(knower=knower, learned_at=chapter),)
    )
    if merged == fact.knower_scope:
        return fact
    return fact.model_copy(update={"knower_scope": merged})


def start_tracking(fact: Fact, knowers: tuple[Awareness, ...]) -> Fact:
    """Convert an untracked fact into a tracked secret known only by `knowers`.

    The one operation here that deliberately *narrows* visibility, which is why it is named for
    what it does and kept off the propagation path. Use it when a fact becomes a secret — not as a
    convenience for making `witnesses_learn` apply.

    Raises:
        ValueError: If `fact` is already tracked (use `witnesses_learn` or `told`), or if `knowers`
            is empty — an empty scope is a fact nobody can ever see, which `Fact` rejects anyway.
    """
    if fact.knower_scope is not None:
        raise ValueError(
            f"fact {fact.id!r} is already tracked; use witnesses_learn() or told() to add knowers"
        )
    if not knowers:
        raise ValueError(
            f"cannot start tracking {fact.id!r} with no knowers: the fact would be invisible to "
            f"everyone, forever"
        )
    return fact.model_copy(update={"knower_scope": merge_awareness((), knowers)})

"""Pure narrative invariant predicates over Canon Kernel collections.

Free functions, no state, no IO — every one is a deterministic function of the models it
is handed, so the whole module is unit-testable offline and costs no model calls. This is
the HARD lane's vocabulary: the checks that are decidable by boolean logic over typed
state. Semantic checks (motivation, tone) belong to the soft lane and are not here.

See PRD-KNOWLEDGE-BASE.md §11 KB-F-12 and the invariant catalog in the research vault.
"""

from collections.abc import Iterable

from story_engine.domain.enums import EntityStatus, FactStatus
from story_engine.domain.models.canon import (
    CanonEntity,
    ChapterIndex,
    Commitment,
    Fact,
)

_INCAPACITATED = frozenset(
    {EntityStatus.DEAD, EntityStatus.DESTROYED, EntityStatus.IMPRISONED}
)


def visible_facts(
    facts: Iterable[Fact], knower: str, chapter: ChapterIndex
) -> tuple[Fact, ...]:
    """Facts that may be surfaced to `knower` at this point in the telling."""
    return tuple(f for f in facts if f.is_visible_to(knower, chapter))


def withheld_facts(
    facts: Iterable[Fact], knower: str, chapter: ChapterIndex
) -> tuple[Fact, ...]:
    """The spoiler-guard exclusion set — retrieval performed in order to EXCLUDE.

    Exposed rather than merely applied, because being able to *show* what was withheld is
    what makes the guarantee demonstrable instead of merely asserted.
    """
    return tuple(f for f in facts if not f.is_visible_to(knower, chapter))


def epistemic_violations(
    used_fact_ids: Iterable[str],
    facts: Iterable[Fact],
    knower: str,
    chapter: ChapterIndex,
) -> tuple[Fact, ...]:
    """Facts a draft used that `knower` could not have known.

    The most common AI-fiction tell: a character acting on information no scene gave them.
    Ids with no matching fact are ignored — resolving them is the caller's job.
    """
    by_id = {f.id: f for f in facts}
    offenders = []
    for fact_id in used_fact_ids:
        fact = by_id.get(fact_id)
        if fact is not None and not fact.is_visible_to(knower, chapter):
            offenders.append(fact)
    return tuple(offenders)


def conflicting_active_facts(
    facts: Iterable[Fact], chapter: ChapterIndex
) -> tuple[tuple[Fact, Fact], ...]:
    """Pairs asserting different values for one subject+predicate at one story time.

    Scoped to a single fork: contradicting an ancestor is legal inside a branch, so
    cross-fork pairs are not conflicts. Superseded facts fall out naturally because a
    closed validity window fails `is_valid_at`.
    """
    current = [
        f for f in facts if f.status is FactStatus.ACTIVE and f.is_valid_at(chapter)
    ]
    conflicts: list[tuple[Fact, Fact]] = []
    for index, left in enumerate(current):
        for right in current[index + 1 :]:
            if left.fork_id != right.fork_id:
                continue
            if left.subject_id != right.subject_id:
                continue
            if left.predicate != right.predicate:
                continue
            same_object = (
                left.object_id == right.object_id
                and left.object_literal == right.object_literal
            )
            if not same_object:
                conflicts.append((left, right))
    return tuple(conflicts)


def open_commitments(commitments: Iterable[Commitment]) -> tuple[Commitment, ...]:
    """Narrative debts the story still owes — the unfired Chekhov's guns."""
    return tuple(c for c in commitments if c.is_open)


def entities_acting_while_incapacitated(
    acting_entity_ids: Iterable[str], entities: Iterable[CanonEntity]
) -> tuple[CanonEntity, ...]:
    """Entities that acted despite being dead, destroyed or imprisoned.

    Resurrection is not hardcoded as impossible — a world rule may permit it — but it must
    be depicted, so an undepicted status change surfaces here for the caller to adjudicate.
    """
    acting = set(acting_entity_ids)
    return tuple(e for e in entities if e.id in acting and e.status in _INCAPACITATED)

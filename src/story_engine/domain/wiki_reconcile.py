"""Pure rules for reconciling one entity observed under two canons.

A fandom wiki gives the novel and screen versions of the same character **separate pages** — verified
live 2026-07-25 on `dexter.fandom.com`: "Brian Moser" is the screen page and "Brian Moser (Novels)" the
novel one. For a vocabulary that is exactly one entity with two provenances, and merging them is what
turns a page list into the novel-vs-screen discriminator `project_context.md` §11 OD-2 needs.

No IO and no wiki-format knowledge: the adapter has already normalized page titles to canonical names
and stamped each observation with its basis. These rules only combine.
"""

from story_engine.domain.models.wiki_index import (
    WikiAttribute,
    WikiCanonBasis,
    WikiEntity,
    WikiEntityKind,
    WikiLifeStatus,
    WikiRelationship,
    WikiSourcePage,
)


def combine_basis(left: WikiCanonBasis, right: WikiCanonBasis) -> WikiCanonBasis:
    """Combine two canon-basis observations of the same entity.

    Disagreement is evidence of presence in both canons, never a conflict to resolve: `NOVEL` seen
    alongside `SCREEN` means the entity exists in both. `UNKNOWN` is absorbed rather than propagated,
    because one unlabelled page must not erase a labelled one.
    """
    if left is right:
        return left
    if left is WikiCanonBasis.UNKNOWN:
        return right
    if right is WikiCanonBasis.UNKNOWN:
        return left
    return WikiCanonBasis.BOTH


def merge_entities(entities: tuple[WikiEntity, ...]) -> tuple[WikiEntity, ...]:
    """Merge entities that share a canonical name, most prominent representative first.

    Ordering is by descending prominence so a caller truncating the index keeps the leads. Within a
    merge the *longest* summary wins: a wiki's novel stubs are far thinner than its screen articles,
    and a short summary is worse for entity recognition than a screen-biased one — provenance on the
    surviving summary's page records which canon it came from.
    """
    grouped: dict[str, list[WikiEntity]] = {}
    for entity in entities:
        grouped.setdefault(entity.canonical_name.strip().lower(), []).append(entity)
    merged = [_merge_group(tuple(group)) for group in grouped.values()]
    merged.sort(key=lambda e: (-e.prominence, e.canonical_name))
    return tuple(merged)


def _merge_group(group: tuple[WikiEntity, ...]) -> WikiEntity:
    """Fold a group of same-named entities into one, unioning every observation."""
    if len(group) == 1:
        return group[0]

    richest = max(group, key=lambda e: (len(e.summary), e.prominence))
    basis = WikiCanonBasis.UNKNOWN
    kind = WikiEntityKind.OTHER
    life_status = WikiLifeStatus.UNKNOWN
    for entity in group:
        basis = combine_basis(basis, entity.canon_basis)
        if kind is WikiEntityKind.OTHER:
            kind = entity.kind
        if life_status is WikiLifeStatus.UNKNOWN:
            life_status = entity.life_status

    return WikiEntity(
        canonical_name=richest.canonical_name,
        kind=kind,
        canon_basis=basis,
        aliases=_dedupe_aliases(group),
        summary=richest.summary,
        life_status=life_status,
        relationships=_dedupe_relationships(group),
        attributes=_dedupe_attributes(group),
        sources=_dedupe_sources(group),
        prominence=max(entity.prominence for entity in group),
    )


def _dedupe_aliases(group: tuple[WikiEntity, ...]) -> tuple[str, ...]:
    """Union aliases case-insensitively, excluding whichever name became canonical."""
    canonical = max(group, key=lambda e: (len(e.summary), e.prominence)).canonical_name
    excluded = canonical.strip().lower()
    seen: dict[str, str] = {}
    for entity in group:
        for alias in (entity.canonical_name, *entity.aliases):
            key = alias.strip().lower()
            if key and key != excluded:
                seen.setdefault(key, alias)
    return tuple(seen.values())


def _dedupe_relationships(
    group: tuple[WikiEntity, ...],
) -> tuple[WikiRelationship, ...]:
    """Union relationships, combining the basis of duplicates rather than keeping both rows."""
    merged: dict[tuple[str, str], WikiRelationship] = {}
    for entity in group:
        for relationship in entity.relationships:
            key = (relationship.target.strip().lower(), relationship.kind.lower())
            existing = merged.get(key)
            if existing is None:
                merged[key] = relationship
                continue
            merged[key] = existing.model_copy(
                update={
                    "canon_basis": combine_basis(
                        existing.canon_basis, relationship.canon_basis
                    )
                }
            )
    return tuple(merged.values())


def _dedupe_attributes(group: tuple[WikiEntity, ...]) -> tuple[WikiAttribute, ...]:
    """Union attributes, keeping novel and screen values of the same predicate side by side.

    Two different values for `status` under two canons is exactly the divergence this index exists to
    expose, so they must NOT be collapsed into one.
    """
    merged: dict[tuple[str, str], WikiAttribute] = {}
    for entity in group:
        for attribute in entity.attributes:
            key = (attribute.predicate, attribute.value.lower())
            existing = merged.get(key)
            if existing is None:
                merged[key] = attribute
                continue
            merged[key] = existing.model_copy(
                update={
                    "canon_basis": combine_basis(
                        existing.canon_basis, attribute.canon_basis
                    )
                }
            )
    return tuple(merged.values())


def _dedupe_sources(group: tuple[WikiEntity, ...]) -> tuple[WikiSourcePage, ...]:
    """Union provenance records, keyed by page. Provenance is never dropped in a merge."""
    merged: dict[str, WikiSourcePage] = {}
    for entity in group:
        for source in entity.sources:
            merged.setdefault(source.page_title.lower(), source)
    return tuple(merged.values())

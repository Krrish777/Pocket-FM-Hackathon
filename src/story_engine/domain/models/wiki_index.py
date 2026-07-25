"""Wiki entity index models — a *vocabulary* of canon entities, not a canon knowledge base.

Read this before using anything here. `project_context.md` §6.1 fixes the canon knowledge base on the
Dexter **novels** by Jeff Lindsay, and §6.4 records the hazard that fan fiction is predominantly
**screen**-based. A fandom wiki is overwhelmingly screen canon, so treating a wiki scrape as canon
truth is precisely the silent corruption path §6.4 warns about.

So this module deliberately models something weaker and safer:

1. **A name vocabulary** — which canonical entities exist and what they are called, so a fan-fiction
   blurb can be matched against them. Vocabulary is allowed to be screen-biased; it only has to be
   recognizable, not true.
2. **A novel-vs-screen discriminator** — every entity, relationship, and attribute is stamped with the
   `WikiCanonBasis` it was observed under. This is what lets the branch oracle flag a fan fiction that
   references screen-only entities (`project_context.md` §11 OD-2).

Nothing here is a canon *fact*: values are `WikiAttribute`s — observations attributed to a page, never
assertions. Per §5.1 provenance is mandatory, so every entity carries the pages it was built from with
a retrieval timestamp. These types are private to this feature and are NOT the integration contract —
the contract is the versioned JSONL artifact written by the sink.
"""

from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from pydantic import Field, computed_field

from story_engine.domain.base import DomainModel


class WikiEntityKind(StrEnum):
    """What sort of thing a wiki entity is."""

    CHARACTER = "character"
    LOCATION = "location"
    EVENT = "event"
    ORGANIZATION = "organization"
    OTHER = "other"


class WikiCanonBasis(StrEnum):
    """Which canon an observation was made under.

    `UNKNOWN` is the default on purpose: an unlabelled observation must never be silently promoted to
    novel canon, because that is how screen facts leak into a novel-based knowledge base.
    """

    NOVEL = "novel"
    SCREEN = "screen"
    BOTH = "both"
    UNKNOWN = "unknown"


class WikiLifeStatus(StrEnum):
    """Whether the source page says the entity is still alive."""

    ALIVE = "alive"
    DECEASED = "deceased"
    UNKNOWN = "unknown"


class WikiSourcePage(DomainModel):
    """Provenance for one source page: where an observation came from and when."""

    source_name: str = Field(min_length=1, max_length=80)
    wiki_url: str = Field(default="", max_length=500)
    page_title: str = Field(min_length=1, max_length=300)
    page_id: str = Field(default="", max_length=40)
    page_url: str = Field(default="", max_length=800)
    canon_basis: WikiCanonBasis = WikiCanonBasis.UNKNOWN
    basis_evidence: tuple[str, ...] = Field(
        default=(),
        description="The category names the basis was inferred from, so the call is auditable.",
    )
    retrieved_at: datetime


class WikiAttribute(DomainModel):
    """One observed `(predicate, value)` pair about an entity, stamped with its canon basis.

    Named "attribute" rather than "fact" deliberately: a wiki statement is an observation of a page,
    not a verified canon fact, and the distinction is load-bearing (`project_context.md` §6.3).
    """

    predicate: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=2000)
    canon_basis: WikiCanonBasis = WikiCanonBasis.UNKNOWN
    source_url: str = Field(default="", max_length=800)


class WikiRelationship(DomainModel):
    """A directed, named link from one entity to another, stamped with its canon basis.

    `target` is the other entity's name as the wiki writes it, not a resolved reference: an index is
    harvested breadth-first, so a target may never have been fetched. Unresolved targets are counted,
    not dropped — a link out of the index is itself a coverage signal.
    """

    target: str = Field(min_length=1, max_length=200)
    kind: str = Field(
        default="",
        max_length=120,
        description="Relationship as the wiki words it: 'younger brother', 'ex-wife'.",
    )
    field: str = Field(
        default="", max_length=60, description="Infobox field the link came from."
    )
    canon_basis: WikiCanonBasis = WikiCanonBasis.UNKNOWN
    source_url: str = Field(default="", max_length=800)


class WikiEntity(DomainModel):
    """One entity in the vocabulary: its names, what canon it belongs to, and where that was read."""

    canonical_name: str = Field(min_length=1, max_length=200)
    kind: WikiEntityKind = WikiEntityKind.OTHER
    canon_basis: WikiCanonBasis = WikiCanonBasis.UNKNOWN
    aliases: tuple[str, ...] = ()
    summary: str = Field(default="", max_length=8000)
    life_status: WikiLifeStatus = WikiLifeStatus.UNKNOWN
    relationships: tuple[WikiRelationship, ...] = ()
    attributes: tuple[WikiAttribute, ...] = ()
    sources: tuple[WikiSourcePage, ...] = Field(
        default=(),
        description="Mandatory provenance — every page this entity was built from.",
    )
    prominence: int = Field(
        default=0,
        ge=0,
        description="How much the wiki has written about this entity (page bytes). Ranks leads "
        "above walk-ons without needing an LLM.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def match_names(self) -> tuple[str, ...]:
        """Distinct lowercased canonical name + aliases, for matching the entity in prose."""
        seen: dict[str, None] = {}
        for candidate in (self.canonical_name, *self.aliases):
            cleaned = candidate.strip().lower()
            if cleaned:
                seen.setdefault(cleaned, None)
        return tuple(seen)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary_words(self) -> int:
        """Number of whitespace-separated words in the summary."""
        return len(self.summary.split())

    def matches_name(self, name: str) -> bool:
        """Return True if `name` is this entity's canonical name or one of its aliases."""
        return name.strip().lower() in self.match_names


class WikiPageRef(DomainModel):
    """A handle to a source page that may become a `WikiEntity`.

    Discovery and content-fetching are separate round-trips on a wiki API, so a caller can rank and
    cap candidates before paying to read prose.
    """

    title: str = Field(min_length=1, max_length=300)
    kind: WikiEntityKind = WikiEntityKind.OTHER
    page_id: str = Field(default="", max_length=40)
    page_url: str = Field(default="", max_length=800)
    prominence: int = Field(default=0, ge=0)


class WikiEntityIndex(DomainModel):
    """The entity vocabulary of one fandom, harvested from one wiki."""

    fandom: str = Field(min_length=1, max_length=200)
    source_name: str = Field(min_length=1, max_length=80)
    wiki_url: str = Field(default="", max_length=500)
    retrieved_at: datetime
    entities: tuple[WikiEntity, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def relationship_count(self) -> int:
        return sum(len(entity.relationships) for entity in self.entities)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def attribute_count(self) -> int:
        return sum(len(entity.attributes) for entity in self.entities)

    def counts_by_kind(self) -> dict[str, int]:
        """Return how many entities were harvested per kind."""
        return _tally(str(entity.kind) for entity in self.entities)

    def counts_by_basis(self) -> dict[str, int]:
        """Return how many entities fall under each canon basis — the OD-2 headline number."""
        return _tally(str(entity.canon_basis) for entity in self.entities)

    def names_with_basis(self, basis: WikiCanonBasis) -> tuple[str, ...]:
        """Return the canonical names classified under `basis`.

        `SCREEN` is the set a novel-based knowledge base has never heard of: a fan fiction naming any
        of them is screen canon and must be flagged rather than ingested.
        """
        return tuple(e.canonical_name for e in self.entities if e.canon_basis is basis)

    def name_index(self) -> dict[str, WikiEntity]:
        """Return a lowercased name/alias -> entity lookup. First writer of a name wins."""
        index: dict[str, WikiEntity] = {}
        for entity in self.entities:
            for key in entity.match_names:
                index.setdefault(key, entity)
        return index

    def find(self, name: str) -> WikiEntity | None:
        """Return the entity matching `name` or any alias, case-insensitively."""
        needle = name.strip().lower()
        return self.name_index().get(needle) if needle else None

    def unresolved_targets(self) -> tuple[str, ...]:
        """Return relationship targets that no harvested entity accounts for.

        Not an error: it is the signal that the vocabulary needs a deeper harvest before a side
        character's relationships can be relied on.
        """
        index = self.name_index()
        missing: dict[str, None] = {}
        for entity in self.entities:
            for relationship in entity.relationships:
                key = relationship.target.strip().lower()
                if key and key not in index:
                    missing.setdefault(relationship.target, None)
        return tuple(missing)


def _tally(values: Iterable[str]) -> dict[str, int]:
    """Count occurrences of each string, preserving first-seen order."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts

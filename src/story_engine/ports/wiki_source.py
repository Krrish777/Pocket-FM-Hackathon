"""Wiki source port — the seam between vocabulary-building and any particular wiki.

Three capabilities in one cohesive port because no consumer needs one without the others: resolve
which wiki serves a fandom, enumerate its entity pages, then read chosen pages into typed entities.
HTTP and markup parsing live only in `adapters/outbound/wiki/`.

`fandom` is passed to every method rather than fixed at construction so one adapter instance serves
many fandoms; adapters are expected to memoize the resolution that implies.
"""

from typing import Protocol

from story_engine.domain.models.wiki_index import (
    WikiEntity,
    WikiEntityKind,
    WikiPageRef,
)


class WikiSourcePort(Protocol):
    """Discover and read canon entity pages for a fandom."""

    source_name: str
    """The reference this adapter serves, stamped onto every provenance record."""

    def resolve(self, fandom: str) -> str | None:
        """Return the wiki base URL serving `fandom`, or None if none is reachable."""
        ...

    def discover(
        self,
        fandom: str,
        *,
        kinds: tuple[WikiEntityKind, ...],
        limit_per_kind: int,
    ) -> tuple[WikiPageRef, ...]:
        """Return candidate pages per requested kind, most prominent first.

        Returns an empty tuple when the fandom has no reachable wiki — a caller reports that rather
        than crashing, because a missing wiki is a coverage fact, not a bug.
        """
        ...

    def fetch_entities(
        self, fandom: str, refs: tuple[WikiPageRef, ...]
    ) -> tuple[WikiEntity, ...]:
        """Return typed entities for `refs`, skipping any page that cannot be parsed."""
        ...

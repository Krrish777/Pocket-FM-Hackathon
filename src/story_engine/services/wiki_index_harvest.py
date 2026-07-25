"""Wiki index harvest use-case: fandom name in, entity vocabulary out.

Orchestrates ports only — the reconciliation of a novel page with its screen counterpart delegates to
the pure rules in `domain/wiki_reconcile.py`, so the policy is testable without a network. Pipeline:

    resolve wiki -> discover category members -> rank by prominence -> read wikitext
                 -> classify canon basis -> merge duplicates across canons -> sink

Every rejection is counted rather than silently dropped: a thin vocabulary with
"0 kept, 400 empty-page" needs a different fix than "0 kept, 400 unresolved wiki", and the counts are
what tell them apart. `screen_only` is the number that matters most — it is the size of the set a
novel-based knowledge base has never heard of (`project_context.md` §11 OD-2).
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from story_engine.domain.models.wiki_index import (
    WikiCanonBasis,
    WikiEntity,
    WikiEntityIndex,
    WikiEntityKind,
)
from story_engine.domain.wiki_reconcile import merge_entities
from story_engine.ports.wiki_sink import WikiSinkPort
from story_engine.ports.wiki_source import WikiSourcePort

logger = logging.getLogger(__name__)

DEFAULT_KINDS: tuple[WikiEntityKind, ...] = (
    WikiEntityKind.CHARACTER,
    WikiEntityKind.LOCATION,
)


@dataclass(slots=True)
class WikiIndexReport:
    """Mutable tally of what a harvest did — internal, trusted data, so a dataclass not a model."""

    fandom: str
    wiki_url: str = ""
    pages_discovered: int = 0
    pages_unusable: int = 0
    entities_parsed: int = 0
    entities_dropped_thin: int = 0
    entities_after_merge: int = 0
    duplicates_merged: int = 0
    novel_only: int = 0
    screen_only: int = 0
    both_canons: int = 0
    unknown_basis: int = 0
    relationships: int = 0
    attributes: int = 0
    unresolved_targets: int = 0
    counts_by_kind: dict[str, int] = field(default_factory=dict)
    sink_location: str = ""


class WikiIndexHarvester:
    """Build a fandom's entity vocabulary, labelled by which canon each entity belongs to.

    This is explicitly *not* a canon knowledge base — see `domain/models/wiki_index.py`. It answers
    "which entities exist and what are they called", and "is this entity screen canon or book canon".
    """

    def __init__(
        self,
        *,
        source: WikiSourcePort,
        sink: WikiSinkPort | None = None,
    ) -> None:
        """Initialize the harvester.

        Args:
            source: The wiki to read. One source, not a tuple: merging two wikis' opinions of the
                same entity is a distinct problem and not one this build needs.
            sink: Where the vocabulary artifact is written; optional (callers may persist themselves).
        """
        self._source = source
        self._sink = sink

    def harvest(
        self,
        fandom: str,
        *,
        kinds: tuple[WikiEntityKind, ...] = DEFAULT_KINDS,
        limit_per_kind: int = 150,
        min_summary_words: int = 0,
    ) -> tuple[WikiEntityIndex, WikiIndexReport]:
        """Harvest `fandom` and return the vocabulary plus a report of what happened.

        Returns an empty index (not an exception) when the fandom has no reachable wiki, so a caller
        can report the coverage gap. Raises only if the wiki answers and then breaks.

        Args:
            fandom: The work's title, as a user would type it.
            kinds: Entity kinds to harvest.
            limit_per_kind: Cap on ranked pages per kind. Pages from a novel-marked category bypass
                this cap in the adapter, because they are the scarce half of the discriminator.
            min_summary_words: Drop entities whose summary is thinner than this. 0 keeps everything,
                which is right for a *vocabulary*: a name with no prose is still a name to recognize.
        """
        report = WikiIndexReport(fandom=fandom)
        retrieved_at = datetime.now(UTC)

        wiki_url = self._source.resolve(fandom)
        if wiki_url is None:
            logger.warning(
                "no wiki resolved for %r; returning an empty vocabulary", fandom
            )
            return self._empty_index(fandom, retrieved_at), report
        report.wiki_url = wiki_url

        refs = self._source.discover(fandom, kinds=kinds, limit_per_kind=limit_per_kind)
        report.pages_discovered = len(refs)
        if not refs:
            logger.warning(
                "wiki %s exposed no entity categories for %r", wiki_url, fandom
            )
            return self._empty_index(fandom, retrieved_at, wiki_url=wiki_url), report

        parsed = self._source.fetch_entities(fandom, refs)
        report.entities_parsed = len(parsed)
        report.pages_unusable = len(refs) - len(parsed)

        kept = tuple(e for e in parsed if e.summary_words >= min_summary_words)
        report.entities_dropped_thin = len(parsed) - len(kept)

        merged = merge_entities(kept)
        report.duplicates_merged = len(kept) - len(merged)

        index = WikiEntityIndex(
            fandom=fandom,
            source_name=self._source.source_name,
            wiki_url=wiki_url,
            retrieved_at=retrieved_at,
            entities=merged,
        )
        self._fill_report(index, report)

        if self._sink is not None and index.entities:
            report.sink_location = self._sink.write(index)
        logger.info(
            "harvest %r: %s entities (novel=%s screen=%s both=%s unknown=%s)",
            fandom,
            report.entities_after_merge,
            report.novel_only,
            report.screen_only,
            report.both_canons,
            report.unknown_basis,
        )
        return index, report

    def screen_only_vocabulary(self, index: WikiEntityIndex) -> tuple[str, ...]:
        """Return every name (canonical and alias) that appears only in screen canon.

        This is the lookup a fan-fiction filter needs: a blurb naming any of these is screen-based,
        and per `project_context.md` §6.4 must be flagged before it reaches the branch oracle. It is a
        *flag*, not a verdict — absence of a novel wiki page is not absence from the novels.
        """
        names: dict[str, None] = {}
        for entity in index.entities:
            if entity.canon_basis is not WikiCanonBasis.SCREEN:
                continue
            for name in entity.match_names:
                names.setdefault(name, None)
        return tuple(names)

    # --- internals ------------------------------------------------------------------------
    def _empty_index(
        self, fandom: str, retrieved_at: datetime, *, wiki_url: str = ""
    ) -> WikiEntityIndex:
        return WikiEntityIndex(
            fandom=fandom,
            source_name=self._source.source_name,
            wiki_url=wiki_url,
            retrieved_at=retrieved_at,
        )

    def _fill_report(self, index: WikiEntityIndex, report: WikiIndexReport) -> None:
        """Copy the index's derived counts onto the report."""
        report.entities_after_merge = index.entity_count
        report.relationships = index.relationship_count
        report.attributes = index.attribute_count
        report.unresolved_targets = len(index.unresolved_targets())
        report.counts_by_kind = index.counts_by_kind()
        basis_counts = index.counts_by_basis()
        report.novel_only = basis_counts.get(str(WikiCanonBasis.NOVEL), 0)
        report.screen_only = basis_counts.get(str(WikiCanonBasis.SCREEN), 0)
        report.both_canons = basis_counts.get(str(WikiCanonBasis.BOTH), 0)
        report.unknown_basis = basis_counts.get(str(WikiCanonBasis.UNKNOWN), 0)


def classify_text(
    index: WikiEntityIndex, text: str
) -> tuple[WikiCanonBasis, tuple[WikiEntity, ...]]:
    """Classify a fan-fiction blurb by the canon basis of the entities it names.

    The direct answer to `project_context.md` §11 OD-2 at the point of use: a work naming a
    screen-only entity is screen canon and must be flagged before it reaches the branch oracle.
    Matching is lexical and whole-name; short aliases are skipped because a two-letter alias matches
    everything. Returns `UNKNOWN` when no canon entity is recognized at all.

    Args:
        index: The harvested vocabulary to match against.
        text: A blurb, title, or description — not full prose; this is a cheap gate, not analysis.

    Returns:
        The combined basis of everything matched, and the matched entities most prominent first.
    """
    lowered = text.lower()
    matched: list[WikiEntity] = []
    for entity in index.entities:
        if any(name in lowered for name in entity.match_names if len(name) >= 4):
            matched.append(entity)
    if not matched:
        return WikiCanonBasis.UNKNOWN, ()

    bases = {entity.canon_basis for entity in matched}
    if WikiCanonBasis.SCREEN in bases:
        # Screen-only presence dominates: one screen-only entity is enough to make the work unusable
        # against novel canon, regardless of how many shared entities it also names.
        basis = WikiCanonBasis.SCREEN
    elif bases == {WikiCanonBasis.UNKNOWN}:
        basis = WikiCanonBasis.UNKNOWN
    elif WikiCanonBasis.NOVEL in bases:
        basis = WikiCanonBasis.NOVEL
    else:
        basis = WikiCanonBasis.BOTH
    matched.sort(key=lambda e: -e.prominence)
    return basis, tuple(matched)


__all__ = [
    "DEFAULT_KINDS",
    "WikiIndexHarvester",
    "WikiIndexReport",
    "classify_text",
]

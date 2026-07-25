"""Fanfic harvest use-case: fandom name in, deduplicated prose corpus out.

Orchestrates ports only — every admission decision delegates to the pure rules in
`domain/fanfic_quality.py`, so the policy is testable without a network. Pipeline:

    expand aliases -> search hosts -> relevance gate -> fetch prose
                   -> strip boilerplate -> prose gate -> dedup
                   -> premise signature -> prose-quality score -> rank -> sink
"""

import logging
from dataclasses import dataclass

from story_engine.domain.fanfic_premise import (
    MAX_BRANCH_OPTIONS,
    branch_points,
    group_by_premise,
    premise_signature_for,
)
from story_engine.domain.fanfic_quality import (
    admit_chapter,
    alias_hits,
    content_fingerprint,
    is_relevant,
    strip_boilerplate,
)
from story_engine.domain.models.fanfic import (
    BranchPoint,
    Chapter,
    FandomQuery,
    HarvestedStory,
    PremiseGroup,
    StoryRef,
)
from story_engine.domain.prose_score import prose_quality
from story_engine.ports.corpus_sink import CorpusSinkPort
from story_engine.ports.fanfic_source import AliasExpanderPort, FanficSourcePort
from story_engine.shared.errors import SourceUnavailableError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HarvestReport:
    """Mutable tally of what a harvest did — internal, trusted data, so a dataclass not a model.

    Every rejection is counted rather than silently dropped, so a thin corpus is diagnosable:
    "0 kept, 400 relevance-rejected" and "0 kept, 400 prose-rejected" call for opposite fixes.
    """

    fandom: str
    aliases_used: int = 0
    candidates_seen: int = 0
    relevance_rejected: int = 0
    prose_rejected: int = 0
    duplicates_dropped: int = 0
    quality_rejected: int = 0
    stories_kept: int = 0
    chapters_kept: int = 0
    total_words: int = 0
    premise_groups: tuple[PremiseGroup, ...] = ()
    branch_points: tuple[BranchPoint, ...] = ()
    prose_quality_scores: tuple[float, ...] = ()
    sink_location: str = ""

    @property
    def premises_detected(self) -> int:
        """Number of premise groups that carry an actual detected divergence."""
        return sum(1 for g in self.premise_groups if g.tropes)


class FanficHarvester:
    """Build a fandom-targeted fan-fiction corpus from one or more hosts."""

    def __init__(
        self,
        *,
        sources: tuple[FanficSourcePort, ...],
        alias_expander: AliasExpanderPort | None = None,
        sink: CorpusSinkPort | None = None,
    ) -> None:
        """Initialize the harvester.

        Args:
            sources: Hosts to harvest, tried in order. More than one is supported so adding a host
                later needs no change to this service.
            alias_expander: Expands the fandom name into its alias surface; optional.
            sink: Where the corpus is written; optional (callers may persist themselves).

        Raises:
            ValueError: If no sources are supplied.
        """
        if not sources:
            raise ValueError("at least one fanfic source is required")
        self._sources = sources
        self._alias_expander = alias_expander
        self._sink = sink

    def harvest(
        self,
        fandom: str,
        *,
        max_stories: int = 25,
        max_chapters_per_story: int = 20,
        min_words: int = 500,
        min_quotes_per_1k: float = 5.0,
        min_alias_hits: int = 2,
        min_reads: int = 0,
        min_votes: int = 0,
        allow_mature: bool = False,
        kind: str = "auto",
        min_prose_quality: float | None = None,
        rank_by_quality: bool = True,
        max_branch_options: int = MAX_BRANCH_OPTIONS,
    ) -> tuple[tuple[HarvestedStory, ...], HarvestReport]:
        """Harvest `fandom` and return the kept works plus a report of what happened.

        `kind` (`movie`/`novel`/`series`/`auto`) disambiguates the title during alias expansion.

        Args:
            fandom: Novel, film, or series to harvest.
            max_stories: Cap on works kept. Applied *before* quality ranking (see Note).
            max_chapters_per_story: Cap on chapters fetched per work.
            min_words: Chapter-level prose-length floor.
            min_quotes_per_1k: Chapter-level dialogue-density floor.
            min_alias_hits: Distinct fandom aliases a work must mention.
            min_reads: Host read-count floor.
            min_votes: Host vote-count floor.
            allow_mature: Keep works the host flags as mature.
            kind: Title disambiguator for alias expansion.
            min_prose_quality: Optional 0-100 floor on `prose_quality.score`. `None` (the default)
                drops nothing — ranking, not filtering, is the intended use.
            rank_by_quality: Return works best-written first. On by default.
            max_branch_options: Ceiling on options per Branch Oracle decision point (2-4).

        Returns:
            The kept works (ranked if `rank_by_quality`) and a report carrying the premise groups
            and Branch Oracle decision points.

        Note:
            `max_stories` truncates the candidate stream before scoring, so ranking orders the works
            that were kept — it does not search deeper for better-written ones. Raise `max_stories`
            to widen the pool the ranking sees.
        """
        aliases = self._expand(fandom, kind=kind)
        query = FandomQuery(
            name=fandom,
            aliases=aliases,
            min_words=min_words,
            min_quotes_per_1k=min_quotes_per_1k,
            min_alias_hits=min_alias_hits,
            min_reads=min_reads,
            min_votes=min_votes,
            allow_mature=allow_mature,
        )
        report = HarvestReport(fandom=fandom, aliases_used=len(aliases))

        candidates = self._search_all(query, limit=max(max_stories * 4, max_stories))
        report.candidates_seen = len(candidates)

        kept: list[HarvestedStory] = []
        seen_fingerprints: set[str] = set()
        for ref in candidates:
            if len(kept) >= max_stories:
                break
            story = self._admit(
                ref,
                query,
                max_chapters=max_chapters_per_story,
                seen_fingerprints=seen_fingerprints,
                report=report,
            )
            if story is not None:
                kept.append(story)

        stories = self._analyze(
            tuple(kept),
            fandom=fandom,
            min_prose_quality=min_prose_quality,
            rank_by_quality=rank_by_quality,
            report=report,
        )
        report.stories_kept = len(stories)
        report.chapters_kept = sum(len(s.chapters) for s in stories)
        report.total_words = sum(s.total_words for s in stories)
        report.premise_groups = group_by_premise(stories)
        report.branch_points = branch_points(stories, max_options=max_branch_options)
        report.prose_quality_scores = tuple(
            s.prose_quality.score for s in stories if s.prose_quality is not None
        )
        if self._sink is not None and stories:
            report.sink_location = self._sink.write(fandom, stories)
        logger.info(
            "harvest %r kept %s works / %s chapters / %s words / %s premise groups / "
            "%s branch points",
            fandom,
            report.stories_kept,
            report.chapters_kept,
            report.total_words,
            len(report.premise_groups),
            len(report.branch_points),
        )
        return stories, report

    # --- internals ------------------------------------------------------------------------
    def _analyze(
        self,
        stories: tuple[HarvestedStory, ...],
        *,
        fandom: str,
        min_prose_quality: float | None,
        rank_by_quality: bool,
        report: HarvestReport,
    ) -> tuple[HarvestedStory, ...]:
        """Attach a premise signature and prose-quality score, then threshold and rank.

        Both are pure domain calculations over text already in memory, so this costs no network
        round-trips and is fully reproducible.
        """
        scored = tuple(
            story.model_copy(
                update={
                    "premise": premise_signature_for(story.ref, fandom=fandom),
                    "prose_quality": prose_quality(story.prose_text),
                }
            )
            for story in stories
        )
        if min_prose_quality is not None:
            admitted = tuple(
                s
                for s in scored
                if s.prose_quality is not None
                and s.prose_quality.score >= min_prose_quality
            )
            report.quality_rejected = len(scored) - len(admitted)
            scored = admitted
        if not rank_by_quality:
            return scored
        # Stable: equal scores keep harvest order, so a re-run cannot reshuffle ties.
        return tuple(
            sorted(
                scored,
                key=lambda s: -(s.prose_quality.score if s.prose_quality else 0.0),
            )
        )

    def _expand(self, fandom: str, *, kind: str) -> tuple[str, ...]:
        if self._alias_expander is None:
            return ()
        return self._alias_expander.expand(fandom, limit=60, kind=kind)

    def _search_all(self, query: FandomQuery, *, limit: int) -> tuple[StoryRef, ...]:
        """Search every configured source, dropping hosts that are down rather than aborting."""
        merged: dict[tuple[str, str], StoryRef] = {}
        for source in self._sources:
            try:
                found = source.search(query, limit=limit)
            except SourceUnavailableError:
                logger.warning(
                    "source %s unavailable; continuing with remaining sources",
                    type(source).__name__,
                    exc_info=True,
                )
                continue
            for ref in found:
                merged.setdefault((str(ref.source), ref.source_id), ref)
        return tuple(merged.values())

    def _admit(
        self,
        ref: StoryRef,
        query: FandomQuery,
        *,
        max_chapters: int,
        seen_fingerprints: set[str],
        report: HarvestReport,
    ) -> HarvestedStory | None:
        """Decide whether one candidate earns a place in the corpus, fetching prose if so."""
        if not is_relevant(ref, query):
            report.relevance_rejected += 1
            return None

        source = self._source_for(ref)
        if source is None:
            logger.warning("no configured source can fetch %s", ref.source_id)
            return None
        try:
            raw_chapters = source.fetch_chapters(ref, max_chapters=max_chapters)
        except SourceUnavailableError:
            logger.warning(
                "could not fetch chapters for %s", ref.source_id, exc_info=True
            )
            return None

        chapters = self._clean_and_gate(
            raw_chapters, query, seen_fingerprints=seen_fingerprints, report=report
        )
        if not chapters:
            return None
        return HarvestedStory(
            ref=ref, chapters=chapters, alias_hits=alias_hits(ref, query)
        )

    def _clean_and_gate(
        self,
        raw_chapters: tuple[Chapter, ...],
        query: FandomQuery,
        *,
        seen_fingerprints: set[str],
        report: HarvestReport,
    ) -> tuple[Chapter, ...]:
        """Strip boilerplate, drop non-prose, and drop exact duplicates."""
        cleaned: list[Chapter] = []
        for chapter in raw_chapters:
            candidate = chapter.model_copy(
                update={"text": strip_boilerplate(chapter.text)}
            )
            if not admit_chapter(candidate, query):
                report.prose_rejected += 1
                continue
            fingerprint = content_fingerprint(candidate.text)
            if fingerprint in seen_fingerprints:
                report.duplicates_dropped += 1
                continue
            seen_fingerprints.add(fingerprint)
            cleaned.append(candidate)
        return tuple(cleaned)

    def _source_for(self, ref: StoryRef) -> FanficSourcePort | None:
        """Return the configured source that owns `ref`, matched on the host it came from."""
        for source in self._sources:
            if source.source_name == str(ref.source):
                return source
        return None

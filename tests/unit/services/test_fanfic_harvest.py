"""Unit tests for the harvest pipeline, driven by in-memory fakes — no network.

Proves the orchestration contract: relevance gating, prose gating, cross-work dedup, resilience to a
dead host, and that the report explains every rejection.
"""

import pytest

from story_engine.domain.models.fanfic import (
    Chapter,
    ChapterRef,
    FandomQuery,
    FanficSource,
    HarvestedStory,
    StoryRef,
)
from story_engine.services.fanfic_harvest import FanficHarvester
from story_engine.shared.errors import SourceUnavailableError

PROSE = (
    '"You came back," Geralt said.\n\n'
    'Ciri watched the treeline. "I had nowhere else to go," she answered.\n\n'
    '"Then sit, and eat." He pushed the bowl toward her across the fire.\n\n'
    "She sat, and the broth burned her tongue, and she did not care at all."
) * 12


def _ref(
    source_id: str, *, title: str = "The Witcher: A Tale", chapters: int = 1
) -> StoryRef:
    return StoryRef(
        source=FanficSource.WATTPAD,
        source_id=source_id,
        title=title,
        description="Geralt and Ciri travel north.",
        tags=("fanfiction", "geralt"),
        chapter_refs=tuple(
            ChapterRef(source_id=f"{source_id}-{i}", index=i, title=f"Chapter {i}")
            for i in range(1, chapters + 1)
        ),
    )


class FakeSource:
    """An in-memory `FanficSourcePort` returning canned refs and prose."""

    source_name = str(FanficSource.WATTPAD)

    def __init__(
        self,
        refs: tuple[StoryRef, ...],
        *,
        text: str = PROSE,
        fail_search: bool = False,
    ) -> None:
        self._refs = refs
        self._text = text
        self._fail_search = fail_search

    def search(self, query: FandomQuery, *, limit: int) -> tuple[StoryRef, ...]:
        if self._fail_search:
            raise SourceUnavailableError("host down")
        return self._refs[:limit]

    def fetch_chapters(
        self, ref: StoryRef, *, max_chapters: int
    ) -> tuple[Chapter, ...]:
        return tuple(
            Chapter(
                index=cr.index, source_id=cr.source_id, title=cr.title, text=self._text
            )
            for cr in ref.chapter_refs[:max_chapters]
        )


class StaticExpander:
    """An `AliasExpanderPort` returning a fixed alias set."""

    def __init__(self, aliases: tuple[str, ...]) -> None:
        self._aliases = aliases

    def expand(self, fandom: str, *, limit: int, kind: str = "auto") -> tuple[str, ...]:
        return self._aliases[:limit]


class RecordingSink:
    """A `CorpusSinkPort` that keeps what it was handed."""

    def __init__(self) -> None:
        self.written: tuple[HarvestedStory, ...] = ()

    def write(self, fandom: str, stories: tuple[HarvestedStory, ...]) -> str:
        self.written = stories
        return f"memory://{fandom}"


class TestHarvest:
    def test_keeps_relevant_prose_and_reports_it(self) -> None:
        sink = RecordingSink()
        harvester = FanficHarvester(
            sources=(FakeSource((_ref("1"),)),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
            sink=sink,
        )
        stories, report = harvester.harvest("The Witcher")

        assert report.stories_kept == 1
        assert report.chapters_kept == 1
        assert report.total_words > 500
        assert report.sink_location == "memory://The Witcher"
        assert sink.written == stories
        assert "geralt" in stories[0].alias_hits

    def test_rejects_work_lacking_two_distinct_aliases(self) -> None:
        off_topic = StoryRef(
            source=FanficSource.WATTPAD,
            source_id="9",
            title="An Original Romance",
            description="No fandom here.",
            chapter_refs=(ChapterRef(source_id="9-1", index=1),),
        )
        harvester = FanficHarvester(
            sources=(FakeSource((off_topic,)),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )
        stories, report = harvester.harvest("The Witcher")

        assert stories == ()
        assert report.relevance_rejected == 1
        assert report.prose_rejected == 0

    def test_rejects_discussion_text_as_non_prose(self) -> None:
        harvester = FanficHarvester(
            sources=(
                FakeSource((_ref("1"),), text="Does anyone remember this fic? " * 300),
            ),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )
        stories, report = harvester.harvest("The Witcher")

        assert stories == ()
        assert report.prose_rejected == 1
        assert report.relevance_rejected == 0

    def test_identical_chapters_across_works_are_deduplicated(self) -> None:
        # Two distinct works serving byte-identical prose: the repost must not be kept twice.
        harvester = FanficHarvester(
            sources=(FakeSource((_ref("1"), _ref("2"))),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )
        stories, report = harvester.harvest("The Witcher")

        assert report.chapters_kept == 1
        assert report.duplicates_dropped == 1
        assert len(stories) == 1

    def test_respects_max_stories(self) -> None:
        refs = tuple(_ref(str(i), title=f"Witcher Tale {i}") for i in range(1, 6))
        # Distinct text per work so dedup does not mask the cap.
        harvester = FanficHarvester(
            sources=(FakeSource(refs),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )
        stories, _ = harvester.harvest("The Witcher", max_stories=2)
        assert len(stories) <= 2

    def test_dead_host_does_not_abort_the_run(self) -> None:
        harvester = FanficHarvester(
            sources=(FakeSource((), fail_search=True),),
            alias_expander=StaticExpander(("Geralt",)),
        )
        stories, report = harvester.harvest("The Witcher")

        assert stories == ()
        assert report.candidates_seen == 0

    def test_runs_without_an_alias_expander(self) -> None:
        harvester = FanficHarvester(sources=(FakeSource((_ref("1"),)),))
        stories, report = harvester.harvest("The Witcher", min_alias_hits=1)

        assert report.aliases_used == 0
        assert len(stories) == 1

    def test_requires_at_least_one_source(self) -> None:
        with pytest.raises(ValueError, match="at least one fanfic source"):
            FanficHarvester(sources=())


# Two works whose blurbs name the SAME canon decision point in different words — the real Dexter
# corpus shape ("Dexter doesn't kill Brian" / the author note's "Dexter letting Brian live").
SPARES_BRIAN_A = (
    "Dexter doesn't kill Brian. They rekindle the brotherly bond that has been lost."
)
SPARES_BRIAN_B = (
    "Geralt and Ciri watch as Dexter lets Brian live, and everything changes."
)

MECHANICAL_PROSE = (
    'I said, "I will be on my way."\n'
    'He said, "Okay."\n'
    'Ciri said, "Oh not him."\n'
    'Geralt said, "I have to go now."\n'
    'She said, "Fine."\n'
) * 30

VIVID_PROSE = (
    "The cold air of the room raised goose bumps on my arms, but I ignored them. Something "
    "twitched inside of me, something that had been dead a long time.\n\n"
    '"You came back," Geralt murmured, and Ciri did not answer at once.\n\n'
    "She watched the treeline where the wolves had been, and the broth burned her tongue, and "
    "she did not care at all.\n\n"
    "Nothing moved. Then it did, and the shadow beyond the fire took a shape she knew.\n\n"
) * 12


def _blurbed(source_id: str, description: str) -> StoryRef:
    return StoryRef(
        source=FanficSource.WATTPAD,
        source_id=source_id,
        title=f"The Witcher: Tale {source_id}",
        description=description,
        tags=("fanfiction", "geralt"),
        chapter_refs=(ChapterRef(source_id=f"{source_id}-1", index=1),),
    )


class TestPremiseClustering:
    def test_works_sharing_a_premise_land_in_one_group(self) -> None:
        harvester = FanficHarvester(
            sources=(FakeSource((_blurbed("1", SPARES_BRIAN_A),), text=VIVID_PROSE),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )
        stories, report = harvester.harvest("The Witcher")

        assert stories[0].premise is not None
        assert stories[0].premise.key == "character_survives:brian"
        assert report.premise_groups[0].key == "character_survives:brian"
        assert report.premises_detected == 1

    def test_report_exposes_branch_points_with_a_canon_option(self) -> None:
        harvester = FanficHarvester(
            sources=(FakeSource((_blurbed("1", SPARES_BRIAN_A),), text=VIVID_PROSE),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )
        _, report = harvester.harvest("The Witcher")

        point = report.branch_points[0]
        assert point.decision_point == "Whether Brian dies, as canon has it"
        assert point.options[0].is_canon
        assert point.option_count >= 2


class PerWorkSource:
    """A `FanficSourcePort` serving different prose per work, so quality can differ across works."""

    source_name = str(FanficSource.WATTPAD)

    def __init__(self, texts: dict[str, str]) -> None:
        self._texts = texts

    def search(self, query: FandomQuery, *, limit: int) -> tuple[StoryRef, ...]:
        return tuple(
            _blurbed(sid, "Geralt and Ciri travel north.") for sid in self._texts
        )

    def fetch_chapters(
        self, ref: StoryRef, *, max_chapters: int
    ) -> tuple[Chapter, ...]:
        return (
            Chapter(
                index=1, source_id=f"{ref.source_id}-1", text=self._texts[ref.source_id]
            ),
        )


class TestProseQualityRanking:
    def _harvester(self) -> FanficHarvester:
        # The well-written work is discovered SECOND, so ranking has to actually move it.
        return FanficHarvester(
            sources=(PerWorkSource({"1": MECHANICAL_PROSE, "2": VIVID_PROSE}),),
            alias_expander=StaticExpander(("Geralt", "Ciri")),
        )

    def test_every_kept_work_is_scored(self) -> None:
        stories, report = self._harvester().harvest("The Witcher")
        assert all(s.prose_quality is not None for s in stories)
        assert len(report.prose_quality_scores) == len(stories)

    def test_best_written_work_is_returned_first(self) -> None:
        stories, _ = self._harvester().harvest("The Witcher")
        assert len(stories) == 2
        assert stories[0].ref.source_id == "2"
        assert stories[0].prose_quality is not None
        assert stories[1].prose_quality is not None
        assert stories[0].prose_quality.score > stories[1].prose_quality.score

    def test_ranking_can_be_disabled(self) -> None:
        stories, _ = self._harvester().harvest("The Witcher", rank_by_quality=False)
        assert [s.ref.source_id for s in stories] == ["1", "2"]

    def test_nothing_is_dropped_without_an_explicit_threshold(self) -> None:
        _, report = self._harvester().harvest("The Witcher")
        assert report.quality_rejected == 0

    def test_threshold_drops_and_counts_the_weak_work(self) -> None:
        stories, report = self._harvester().harvest(
            "The Witcher", min_prose_quality=50.0
        )
        assert [s.ref.source_id for s in stories] == ["2"]
        assert report.quality_rejected == 1

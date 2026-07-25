"""Unit tests for the wiki index harvest use-case — fake port, no network."""

from datetime import UTC, datetime

from story_engine.domain.models.wiki_index import (
    WikiCanonBasis,
    WikiEntity,
    WikiEntityIndex,
    WikiEntityKind,
    WikiPageRef,
    WikiSourcePage,
)
from story_engine.services.wiki_index_harvest import (
    WikiIndexHarvester,
    classify_text,
)

AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _entity(
    name: str,
    basis: WikiCanonBasis,
    *,
    prominence: int = 100,
    aliases: tuple[str, ...] = (),
) -> WikiEntity:
    return WikiEntity(
        canonical_name=name,
        kind=WikiEntityKind.CHARACTER,
        canon_basis=basis,
        aliases=aliases,
        summary=f"{name} is a character.",
        prominence=prominence,
        sources=(
            WikiSourcePage(
                source_name="fake_wiki",
                page_title=name,
                canon_basis=basis,
                retrieved_at=AT,
            ),
        ),
    )


class FakeWikiSource:
    """A `WikiSourcePort` that serves canned entities. Records what it was asked for."""

    source_name = "fake_wiki"

    def __init__(
        self,
        *,
        wiki_url: str | None = "https://fake.test",
        entities: tuple[WikiEntity, ...] = (),
        refs: tuple[WikiPageRef, ...] | None = None,
    ) -> None:
        self._wiki_url = wiki_url
        self._entities = entities
        self._refs = (
            refs
            if refs is not None
            else tuple(WikiPageRef(title=e.canonical_name) for e in entities)
        )
        self.discover_calls: list[int] = []

    def resolve(self, fandom: str) -> str | None:
        return self._wiki_url

    def discover(
        self,
        fandom: str,
        *,
        kinds: tuple[WikiEntityKind, ...],
        limit_per_kind: int,
    ) -> tuple[WikiPageRef, ...]:
        self.discover_calls.append(limit_per_kind)
        return self._refs

    def fetch_entities(
        self, fandom: str, refs: tuple[WikiPageRef, ...]
    ) -> tuple[WikiEntity, ...]:
        return self._entities


class RecordingSink:
    """A `WikiSinkPort` that remembers what it was handed."""

    def __init__(self) -> None:
        self.written: WikiEntityIndex | None = None

    def write(self, index: WikiEntityIndex) -> str:
        self.written = index
        return "/tmp/fake"


class TestHarvest:
    def test_reports_a_missing_wiki_instead_of_raising(self) -> None:
        harvester = WikiIndexHarvester(source=FakeWikiSource(wiki_url=None))
        index, report = harvester.harvest("Nonexistent Fandom")
        assert index.entities == ()
        assert report.wiki_url == ""
        assert report.pages_discovered == 0

    def test_reports_a_wiki_with_no_entity_categories(self) -> None:
        harvester = WikiIndexHarvester(source=FakeWikiSource(entities=()))
        index, report = harvester.harvest("Dexter")
        assert index.entities == ()
        assert report.wiki_url == "https://fake.test"

    def test_counts_entities_by_canon_basis(self) -> None:
        source = FakeWikiSource(
            entities=(
                _entity("Hannah McKay", WikiCanonBasis.SCREEN),
                _entity("Dr. Danco", WikiCanonBasis.NOVEL),
                _entity("Brian Moser", WikiCanonBasis.SCREEN, prominence=900),
                _entity("Brian Moser", WikiCanonBasis.NOVEL, prominence=100),
                _entity("Acupuncturist", WikiCanonBasis.UNKNOWN),
            )
        )
        _, report = WikiIndexHarvester(source=source).harvest("Dexter")
        assert report.entities_parsed == 5
        assert report.duplicates_merged == 1
        assert report.entities_after_merge == 4
        assert (report.screen_only, report.novel_only) == (1, 1)
        assert report.both_canons == 1
        assert report.unknown_basis == 1

    def test_min_summary_words_drops_thin_entities_and_counts_them(self) -> None:
        thin = _entity("Extra", WikiCanonBasis.SCREEN).model_copy(
            update={"summary": ""}
        )
        source = FakeWikiSource(
            entities=(thin, _entity("Hannah McKay", WikiCanonBasis.SCREEN))
        )
        index, report = WikiIndexHarvester(source=source).harvest(
            "Dexter", min_summary_words=2
        )
        assert report.entities_dropped_thin == 1
        assert [e.canonical_name for e in index.entities] == ["Hannah McKay"]

    def test_writes_to_the_sink_and_records_the_location(self) -> None:
        sink = RecordingSink()
        source = FakeWikiSource(entities=(_entity("Dr. Danco", WikiCanonBasis.NOVEL),))
        _, report = WikiIndexHarvester(source=source, sink=sink).harvest("Dexter")
        assert report.sink_location == "/tmp/fake"
        assert sink.written is not None
        assert sink.written.fandom == "Dexter"

    def test_nothing_is_written_when_no_entity_survived(self) -> None:
        sink = RecordingSink()
        _, report = WikiIndexHarvester(
            source=FakeWikiSource(entities=()), sink=sink
        ).harvest("Dexter")
        assert sink.written is None
        assert report.sink_location == ""

    def test_passes_the_limit_through_to_the_source(self) -> None:
        source = FakeWikiSource(entities=())
        WikiIndexHarvester(source=source).harvest("Dexter", limit_per_kind=7)
        assert source.discover_calls == [7]

    def test_screen_only_vocabulary_includes_aliases(self) -> None:
        source = FakeWikiSource(
            entities=(
                _entity(
                    "Hannah McKay", WikiCanonBasis.SCREEN, aliases=("Maggie Randall",)
                ),
                _entity("Dr. Danco", WikiCanonBasis.NOVEL),
            )
        )
        harvester = WikiIndexHarvester(source=source)
        index, _ = harvester.harvest("Dexter")
        vocabulary = harvester.screen_only_vocabulary(index)
        assert set(vocabulary) == {"hannah mckay", "maggie randall"}


def _index(*entities: WikiEntity) -> WikiEntityIndex:
    return WikiEntityIndex(
        fandom="Dexter",
        source_name="fake_wiki",
        wiki_url="https://fake.test",
        retrieved_at=AT,
        entities=entities,
    )


class TestClassifyText:
    def test_a_screen_only_mention_flags_the_whole_work(self) -> None:
        # One screen-only entity is enough to make a work unusable against novel canon (6.4).
        index = _index(
            _entity("Hannah McKay", WikiCanonBasis.SCREEN),
            _entity("Brian Moser", WikiCanonBasis.BOTH),
        )
        basis, matched = classify_text(
            index, "Hannah McKay and Brian Moser leave Miami"
        )
        assert basis is WikiCanonBasis.SCREEN
        assert {e.canonical_name for e in matched} == {"Hannah McKay", "Brian Moser"}

    def test_novel_only_mentions_classify_as_novel(self) -> None:
        index = _index(
            _entity("Dr. Danco", WikiCanonBasis.NOVEL),
            _entity("Hannah McKay", WikiCanonBasis.SCREEN),
        )
        basis, matched = classify_text(index, "Dr. Danco returns")
        assert basis is WikiCanonBasis.NOVEL
        assert [e.canonical_name for e in matched] == ["Dr. Danco"]

    def test_shared_entities_only_classify_as_both(self) -> None:
        index = _index(_entity("Brian Moser", WikiCanonBasis.BOTH))
        basis, _ = classify_text(index, "brian moser is the ice truck killer")
        assert basis is WikiCanonBasis.BOTH

    def test_no_recognized_entity_is_unknown_not_a_guess(self) -> None:
        index = _index(_entity("Hannah McKay", WikiCanonBasis.SCREEN))
        assert classify_text(index, "a story about nobody in particular") == (
            WikiCanonBasis.UNKNOWN,
            (),
        )

    def test_short_aliases_are_not_matched(self) -> None:
        # A three-letter alias would fire on almost any text.
        index = _index(_entity("Bob", WikiCanonBasis.SCREEN, aliases=("Bob",)))
        basis, _ = classify_text(index, "Bobbing along in a boat")
        assert basis is WikiCanonBasis.UNKNOWN

    def test_matches_are_ordered_by_prominence(self) -> None:
        index = _index(
            _entity("Debra Morgan", WikiCanonBasis.SCREEN, prominence=10),
            _entity("Dexter Morgan", WikiCanonBasis.SCREEN, prominence=900),
        )
        _, matched = classify_text(index, "Debra Morgan and Dexter Morgan")
        assert [e.canonical_name for e in matched] == ["Dexter Morgan", "Debra Morgan"]

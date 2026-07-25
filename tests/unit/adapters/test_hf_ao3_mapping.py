"""Unit tests for the HuggingFace AO3 adapter — no network.

Fixtures mirror the real `datasets-server` payload observed 2026-07-25: the row envelope is
`{"rows": [{"row": {id, title, metadata, text}}]}`, `metadata` is a struct whose many fields are
mostly null per row, `Fandom` is sometimes null while `Fandoms` carries a crossover pair, counts
arrive as comma-formatted strings, and some rows have empty `text`.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from story_engine.adapters.outbound.fanfic import http_util
from story_engine.adapters.outbound.fanfic.hf_ao3 import (
    HuggingFaceAO3Source,
    _match_terms,
    _matches,
    _parse_row,
    _to_ref,
)
from story_engine.domain.fanfic_quality import alias_hits, is_relevant
from story_engine.domain.models.fanfic import FandomQuery, FanficSource
from story_engine.shared.errors import SourceUnavailableError

_NULL_METADATA: dict[str, Any] = {
    "Category": None,
    "Character": None,
    "Relationships": None,
    "Series": None,
    "Collections": None,
    "Fandoms": None,
    "Archive Warnings": None,
    "Categories": None,
    "Bookmarks": None,
    "Chapters": None,
    "Comments": None,
    "Completed": None,
    "Hits": None,
    "Kudos": None,
    "Published": None,
    "Words": None,
    "Updated": None,
}

HP_ROW: dict[str, Any] = {
    "id": "83116",
    "title": "The Ring",
    "metadata": {
        **_NULL_METADATA,
        "Archive Warning": "No Archive Warnings Apply",
        "Category": "F/M",
        "Characters": "Harry Potter, Hermione Granger",
        "Fandom": "Harry Potter - J. K. Rowling",
        "Language": "English",
        "Rating": "Teen And Up Audiences",
        "author": "by etspes",
        "chapters": "3/3",
        "completed": "2010-04-27",
        "published": "2010-04-26T00:00:00",
        "words": "10,817",
        "Additional Tags": "Angst, Slow Burn",
        "Relationship": "Harry Potter/Hermione Granger",
        "Hits": "12,345",
        "Kudos": "678",
    },
    "text": '"Hello," she said.\n\nHe said nothing back.',
}

CROSSOVER_ROW: dict[str, Any] = {
    "id": "1800",
    "title": "Between a Waiter and a",
    "metadata": {
        **_NULL_METADATA,
        "Archive Warning": "Major Character Death",
        "Fandom": None,
        "Fandoms": "Angel The Series, The Sandman",
        "Language": "English",
        "Rating": "Explicit",
        "author": "Enigel",
        "chapters": "1/?",
        "completed": "",
        "words": "1,181",
    },
    "text": "Prose here.",
}

EMPTY_TEXT_ROW: dict[str, Any] = {
    "id": "999",
    "title": "Nothing At All",
    "metadata": {**_NULL_METADATA, "Fandom": "Supernatural", "Language": "English"},
    "text": "",
}


class TestParseRow:
    def test_maps_core_fields(self) -> None:
        record = _parse_row(HP_ROW, offset=17)
        assert record is not None
        assert record.offset == 17
        assert record.source_id == "83116"
        assert record.fandom == "Harry Potter - J. K. Rowling"
        assert record.author == "etspes"  # the "by " byline prefix is stripped
        assert record.language == "en"
        assert record.words == 10817  # thousands separator survives coercion
        assert record.hits == 12345
        assert record.kudos == 678
        assert record.completed is True

    def test_reads_plural_fandoms_when_singular_is_null(self) -> None:
        record = _parse_row(CROSSOVER_ROW, offset=0)
        assert record is not None
        assert record.fandom == "Angel The Series, The Sandman"
        assert record.completed is False  # "1/?" is an unfinished work

    def test_drops_rows_with_empty_text(self) -> None:
        assert _parse_row(EMPTY_TEXT_ROW, offset=0) is None

    def test_drops_rows_without_id_or_title(self) -> None:
        assert _parse_row({"title": "No id", "text": "x"}, offset=0) is None
        assert _parse_row({"id": "1", "text": "x"}, offset=0) is None

    def test_tolerates_missing_and_wrong_typed_metadata(self) -> None:
        record = _parse_row(
            {"id": 7, "title": "Bare", "metadata": None, "text": "prose"}, offset=0
        )
        assert record is not None
        assert record.fandom == ""
        assert record.tags == ()
        assert record.hits == 0
        assert record.language == "en"


class TestToRef:
    def test_stamps_the_ao3_source_and_one_chapter_handle(self) -> None:
        record = _parse_row(HP_ROW, offset=0)
        assert record is not None
        ref = _to_ref(record)
        assert ref.source is FanficSource.AO3
        # The dataset has no chapter split, so the ref promises exactly what fetch can deliver.
        assert len(ref.chapter_refs) == 1
        assert ref.num_chapters == 1
        assert ref.chapter_refs[0].source_id == "83116"
        assert ref.url == "https://archiveofourown.org/works/83116"

    def test_carries_hits_and_kudos_into_reads_and_votes(self) -> None:
        record = _parse_row(HP_ROW, offset=0)
        assert record is not None
        ref = _to_ref(record)
        assert (ref.reads, ref.votes) == (12345, 678)

    def test_leaves_reads_and_votes_at_zero_when_absent(self) -> None:
        record = _parse_row(CROSSOVER_ROW, offset=0)
        assert record is not None
        ref = _to_ref(record)
        assert (ref.reads, ref.votes) == (0, 0)

    def test_preserves_the_raw_fandom_and_character_labels_as_tags(self) -> None:
        record = _parse_row(HP_ROW, offset=0)
        assert record is not None
        ref = _to_ref(record)
        # Provenance entries, so downstream code can tell novel canon from screen canon.
        assert "ao3_fandom:Harry Potter - J. K. Rowling" in ref.tags
        assert "ao3_characters:Harry Potter, Hermione Granger" in ref.tags
        assert "ao3_chapters:3/3" in ref.tags
        # Each label is also its own tag, because `alias_hits` matches whole normalized tag keys.
        assert "Harry Potter - J. K. Rowling" in ref.tags
        assert "Hermione Granger" in ref.tags
        assert "Angst" in ref.tags

    def test_is_admitted_by_the_domain_relevance_gate(self) -> None:
        # Regression: with an empty description and one joined tag, `alias_hits` scored 0 and every
        # AO3 work was relevance-rejected end-to-end.
        record = _parse_row(HP_ROW, offset=0)
        assert record is not None
        ref = _to_ref(record)
        query = FandomQuery(name="Harry Potter", aliases=("Hermione Granger",))
        assert set(alias_hits(ref, query)) == {"harry potter", "hermione granger"}
        assert is_relevant(ref, query) is True

    def test_rejected_by_the_relevance_gate_once_a_read_floor_is_set(self) -> None:
        # AO3 Hits/Kudos are absent from most rows, so any nonzero floor rejects the work.
        record = _parse_row(CROSSOVER_ROW, offset=0)
        assert record is not None
        ref = _to_ref(record)
        query = FandomQuery(
            name="The Sandman",
            aliases=("Angel The Series",),
            min_reads=1,
            allow_mature=True,
        )
        assert alias_hits(ref, query)  # relevant on the merits
        assert is_relevant(ref, query) is False  # but the read floor still rejects it

    def test_flags_an_explicit_rating_as_mature(self) -> None:
        record = _parse_row(CROSSOVER_ROW, offset=0)
        assert record is not None
        assert _to_ref(record).mature is True


class TestFandomMatching:
    def test_matches_an_author_attributed_fandom_label(self) -> None:
        record = _parse_row(HP_ROW, offset=0)
        assert record is not None
        assert _matches(record, _match_terms(("harry potter",))) is True

    def test_matches_one_side_of_a_crossover_label(self) -> None:
        record = _parse_row(CROSSOVER_ROW, offset=0)
        assert record is not None
        assert _matches(record, _match_terms(("the sandman",))) is True

    def test_does_not_match_on_a_word_prefix(self) -> None:
        record = _parse_row(
            {**HP_ROW, "metadata": {**HP_ROW["metadata"], "Fandom": "Stargate SG-1"}},
            offset=0,
        )
        assert record is not None
        assert _matches(record, _match_terms(("star",))) is False
        assert _matches(record, _match_terms(("stargate",))) is True

    def test_drops_terms_too_short_to_discriminate(self) -> None:
        assert _match_terms(("au", "x", "dexter")) == ("dexter",)

    def test_a_row_without_a_fandom_label_never_matches(self) -> None:
        record = _parse_row(
            {"id": "5", "title": "Unlabelled", "metadata": {}, "text": "prose"},
            offset=0,
        )
        assert record is not None
        assert _matches(record, _match_terms(("harry potter",))) is False


def _rows_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"rows": [{"row_idx": i, "row": row} for i, row in enumerate(rows)]}


def _stub_client(pages: list[list[dict[str, Any]]]) -> tuple[httpx.Client, list[int]]:
    """Return a client that serves `pages` by offset, plus the list of offsets requested."""
    requested: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        length = int(request.url.params["length"])
        requested.append(offset)
        flat = [row for page in pages for row in page]
        return httpx.Response(200, json=_rows_payload(flat[offset : offset + length]))

    return httpx.Client(transport=httpx.MockTransport(handler)), requested


@pytest.fixture
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the retry sleeps so a rate-limit test costs no wall-clock time."""
    monkeypatch.setattr(http_util.time, "sleep", lambda _seconds: None)


class TestSearchScan:
    @pytest.fixture
    def query(self) -> FandomQuery:
        return FandomQuery(name="Harry Potter", aliases=("Hogwarts",))

    def test_scans_pages_and_returns_matching_works(
        self, tmp_path: Path, query: FandomQuery
    ) -> None:
        client, requested = _stub_client([[CROSSOVER_ROW, HP_ROW, EMPTY_TEXT_ROW]])
        source = HuggingFaceAO3Source(
            client,
            cache_dir=tmp_path,
            max_scan_rows=100,
            page_size=2,
            total_rows=3,
            request_delay=0.0,
        )
        refs = source.search(query, limit=5)
        assert [ref.source_id for ref in refs] == ["83116"]
        assert requested == [0, 2]

    def test_persists_the_scan_offset_and_index_for_resumption(
        self, tmp_path: Path, query: FandomQuery
    ) -> None:
        client, requested = _stub_client([[CROSSOVER_ROW, HP_ROW]])
        source = HuggingFaceAO3Source(
            client,
            cache_dir=tmp_path,
            max_scan_rows=100,
            page_size=2,
            total_rows=2,
            request_delay=0.0,
        )
        source.search(query, limit=5)
        state = json.loads((tmp_path / "scan_state.json").read_text(encoding="utf-8"))
        assert state["rows_scanned"] == 2
        index_lines = (tmp_path / "row_index.jsonl").read_text(encoding="utf-8")
        assert index_lines.count("\n") == 2  # the empty-text row was never indexed

        # A second search re-matches from the index without issuing another request.
        requested.clear()
        refs = HuggingFaceAO3Source(
            client,
            cache_dir=tmp_path,
            max_scan_rows=100,
            page_size=2,
            total_rows=2,
            request_delay=0.0,
        ).search(query, limit=5)
        assert [ref.source_id for ref in refs] == ["83116"]
        assert requested == []

    def test_respects_the_row_budget(self, tmp_path: Path, query: FandomQuery) -> None:
        rows = [EMPTY_TEXT_ROW] * 10
        client, requested = _stub_client([rows])
        source = HuggingFaceAO3Source(
            client,
            cache_dir=tmp_path,
            max_scan_rows=4,
            page_size=2,
            total_rows=10,
            request_delay=0.0,
        )
        assert source.search(query, limit=5) == ()
        assert requested == [0, 2]  # stopped at the 4-row budget, not the 10-row split

    def test_keeps_matches_found_before_the_host_rate_limits(
        self, tmp_path: Path, query: FandomQuery, no_backoff: None
    ) -> None:
        # Sustained paging really does get 429'd, and discarding an already-paid-for page of
        # matches because the *next* page failed would waste the whole scan.
        def handler(request: httpx.Request) -> httpx.Response:
            offset = int(request.url.params["offset"])
            if offset == 0:
                return httpx.Response(200, json=_rows_payload([HP_ROW]))
            return httpx.Response(429, json={"error": "rate limited"})

        source = HuggingFaceAO3Source(
            httpx.Client(transport=httpx.MockTransport(handler)),
            cache_dir=tmp_path,
            max_scan_rows=100,
            page_size=1,
            total_rows=100,
            request_delay=0.0,
        )
        refs = source.search(query, limit=5)
        assert [ref.source_id for ref in refs] == ["83116"]
        state = json.loads((tmp_path / "scan_state.json").read_text(encoding="utf-8"))
        assert state["rows_scanned"] == 1  # the failed page did not advance the offset

    def test_raises_when_the_host_fails_with_nothing_matched(
        self, tmp_path: Path, no_backoff: None
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "rate limited"})

        source = HuggingFaceAO3Source(
            httpx.Client(transport=httpx.MockTransport(handler)),
            cache_dir=tmp_path,
            max_scan_rows=10,
            page_size=1,
            total_rows=10,
            request_delay=0.0,
        )
        with pytest.raises(SourceUnavailableError):
            source.search(FandomQuery(name="Dexter"), limit=5)

    def test_returns_nothing_when_the_query_has_no_usable_terms(
        self, tmp_path: Path
    ) -> None:
        client, requested = _stub_client([[HP_ROW]])
        source = HuggingFaceAO3Source(
            client, cache_dir=tmp_path, total_rows=1, request_delay=0.0
        )
        assert source.search(FandomQuery(name="AU"), limit=5) == ()
        assert requested == []


class TestFetchChapters:
    def test_returns_the_whole_work_as_one_chapter(self, tmp_path: Path) -> None:
        client, _ = _stub_client([[HP_ROW]])
        source = HuggingFaceAO3Source(
            client,
            cache_dir=tmp_path,
            max_scan_rows=10,
            page_size=1,
            total_rows=1,
            request_delay=0.0,
        )
        (ref,) = source.search(FandomQuery(name="Harry Potter"), limit=1)
        chapters = source.fetch_chapters(ref, max_chapters=20)
        assert len(chapters) == 1
        assert chapters[0].index == 1
        assert chapters[0].text == HP_ROW["text"]

    def test_refetches_prose_by_cached_offset_when_the_text_cache_is_missing(
        self, tmp_path: Path
    ) -> None:
        client, requested = _stub_client([[CROSSOVER_ROW, HP_ROW]])
        source = HuggingFaceAO3Source(
            client,
            cache_dir=tmp_path,
            max_scan_rows=10,
            page_size=2,
            total_rows=2,
            request_delay=0.0,
        )
        (ref,) = source.search(FandomQuery(name="Harry Potter"), limit=1)
        (tmp_path / "texts" / "83116.txt").unlink()
        requested.clear()
        chapters = source.fetch_chapters(ref, max_chapters=1)
        assert requested == [1]  # one single-row request, not another scan
        assert chapters[0].text == HP_ROW["text"]

    def test_returns_nothing_for_an_unknown_work(self, tmp_path: Path) -> None:
        client, _ = _stub_client([[HP_ROW]])
        source = HuggingFaceAO3Source(
            client, cache_dir=tmp_path, total_rows=1, request_delay=0.0
        )
        record = _parse_row(HP_ROW, offset=0)
        assert record is not None
        assert source.fetch_chapters(_to_ref(record), max_chapters=1) == ()

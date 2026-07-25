"""Unit tests for Wattpad payload mapping and HTML cleanup — no network.

The fixture mirrors the real API response shape observed 2026-07-25: `language` and `user` are
nested objects, `tags` is a flat list, and `parts[]` carries per-chapter ids and titles.
"""

from typing import Any

from story_engine.adapters.outbound.fanfic.http_util import html_to_text
from story_engine.adapters.outbound.fanfic.wattpad import _parse_story
from story_engine.domain.models.fanfic import FanficSource

STORY_PAYLOAD: dict[str, Any] = {
    "id": "329047365",
    "title": "The Ring: A Percy Jackson Fanfiction",
    "description": "Percy finds a ring at Camp Half-Blood.",
    "user": {"name": "Learn_2_Luv", "fullname": "Luv", "verified": False},
    "language": {"id": 1, "name": "English"},
    "tags": ["annabeth", "demigods", "fanfiction", "percyjackson"],
    "categories": [6, 0],
    "numParts": 17,
    "readCount": 103768,
    "voteCount": 4210,
    "completed": True,
    "mature": False,
    "url": "https://www.wattpad.com/story/329047365",
    "parts": [
        {"id": 924362039, "title": "1. Finding The Ring", "draft": False},
        {"id": 924362040, "title": "2. The Quest", "draft": False},
        {"id": 924362041, "title": "Draft chapter", "draft": True},
    ],
}


class TestParseStory:
    def test_maps_core_fields(self) -> None:
        ref = _parse_story(STORY_PAYLOAD)
        assert ref is not None
        assert ref.source is FanficSource.WATTPAD
        assert ref.source_id == "329047365"
        assert ref.author == "Learn_2_Luv"
        assert ref.reads == 103768
        assert ref.completed is True

    def test_flattens_nested_language_to_a_code(self) -> None:
        ref = _parse_story(STORY_PAYLOAD)
        assert ref is not None
        assert ref.language == "en"

    def test_skips_draft_chapters_and_reindexes(self) -> None:
        ref = _parse_story(STORY_PAYLOAD)
        assert ref is not None
        assert [c.index for c in ref.chapter_refs] == [1, 2]
        assert ref.chapter_refs[0].source_id == "924362039"
        assert ref.chapter_refs[1].title == "2. The Quest"

    def test_rejects_payload_without_id_or_title(self) -> None:
        assert _parse_story({"title": "No id"}) is None
        assert _parse_story({"id": "1"}) is None

    def test_rejects_deleted_work(self) -> None:
        assert _parse_story({**STORY_PAYLOAD, "deleted": True}) is None

    def test_tolerates_missing_and_wrong_typed_fields(self) -> None:
        # Third-party JSON is untrusted; a sparse payload must degrade, not raise.
        ref = _parse_story(
            {"id": 7, "title": "Bare", "tags": None, "readCount": "lots"}
        )
        assert ref is not None
        assert ref.tags == ()
        assert ref.reads == 0
        assert ref.chapter_refs == ()


class TestHtmlToText:
    def test_converts_paragraphs_to_blank_line_separated_text(self) -> None:
        markup = '<p data-p-id="x">First line.</p><p>Second line.</p>'
        assert html_to_text(markup) == "First line.\n\nSecond line."

    def test_unescapes_entities_and_preserves_dialogue_quotes(self) -> None:
        markup = "<p>&ldquo;Hello,&rdquo; she said &amp; smiled.</p>"
        assert html_to_text(markup) == "“Hello,” she said & smiled."

    def test_strips_unknown_tags(self) -> None:
        assert html_to_text("<em>word</em>") == "word"

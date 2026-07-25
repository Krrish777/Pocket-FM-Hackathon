"""Unit tests for Fandom API payload mapping — no network.

Payloads mirror the real `formatversion=2` shapes fetched 2026-07-25: `query.pages[]` rows carrying
`revisions[0].slots.main.content` for wikitext and a `categories[]` list of `{ns, title}`.
"""

from typing import Any

import httpx

from story_engine.adapters.outbound.wiki import canon_basis
from story_engine.adapters.outbound.wiki.fandom_wiki import (
    FandomWikiSource,
    _collect_relationships,
    _is_entity_page,
    _page_url,
    _revision_content,
    _truncate,
)
from story_engine.domain.models.wiki_index import (
    WikiCanonBasis,
    WikiEntityKind,
    WikiLifeStatus,
    WikiPageRef,
)
from tests.unit.adapters.test_wikitext_parsing import BRIAN_WIKITEXT

BRIAN_PAGE: dict[str, Any] = {
    "pageid": 2196,
    "title": "Brian Moser",
    "revisions": [{"slots": {"main": {"content": BRIAN_WIKITEXT}}}],
    "categories": [
        {"ns": 14, "title": "Category:Characters"},
        {"ns": 14, "title": "Category:Season 1 characters"},
        {"ns": 14, "title": "Category:Serial Killers"},
    ],
}

BRIAN_REF = WikiPageRef(
    title="Brian Moser",
    kind=WikiEntityKind.CHARACTER,
    page_id="2196",
    page_url="https://dexter.fandom.com/wiki/Brian_Moser",
    prominence=82058,
)


def _source() -> FandomWikiSource:
    # A client is injected so constructing the adapter performs no IO; no request is ever issued.
    return FandomWikiSource(httpx.Client())


class TestToEntity:
    def _entity(self) -> Any:
        return _source()._to_entity(
            BRIAN_PAGE,
            BRIAN_REF,
            wiki_url="https://dexter.fandom.com",
            rules=canon_basis.BasisRules(),
            work_titles=frozenset({"dexter"}),
        )

    def test_maps_core_vocabulary_fields(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert entity.canonical_name == "Brian Moser"
        assert entity.kind is WikiEntityKind.CHARACTER
        assert entity.life_status is WikiLifeStatus.DECEASED
        assert entity.prominence == 82058

    def test_labels_canon_basis_from_categories(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert entity.canon_basis is WikiCanonBasis.SCREEN

    def test_collects_aliases_from_infobox_and_lead(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert set(entity.aliases) >= {"Rudy Cooper", "The Ice Truck Killer"}
        assert "Brian Moser" not in entity.aliases

    def test_excludes_the_work_title_from_aliases(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert "dexter" not in {alias.lower() for alias in entity.aliases}

    def test_stamps_every_relationship_and_attribute_with_the_basis(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert entity.relationships
        assert entity.attributes
        assert all(r.canon_basis is WikiCanonBasis.SCREEN for r in entity.relationships)
        assert all(a.canon_basis is WikiCanonBasis.SCREEN for a in entity.attributes)

    def test_relationship_fields_do_not_also_become_attributes(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert "relatives" not in {a.predicate for a in entity.attributes}

    def test_presentational_fields_are_never_attributes(self) -> None:
        entity = self._entity()
        assert entity is not None
        predicates = {a.predicate for a in entity.attributes}
        assert "image" not in predicates
        assert "name" not in predicates

    def test_null_valued_fields_are_dropped(self) -> None:
        entity = self._entity()
        assert entity is not None
        # `spouse = '''None'''` must not become a relationship to a character called "None".
        assert "none" not in {r.target.lower() for r in entity.relationships}

    def test_provenance_is_mandatory_and_complete(self) -> None:
        entity = self._entity()
        assert entity is not None
        assert len(entity.sources) == 1
        source = entity.sources[0]
        assert source.source_name == "fandom_wiki"
        assert source.page_title == "Brian Moser"
        assert source.page_id == "2196"
        assert source.page_url.endswith("/wiki/Brian_Moser")
        assert source.retrieved_at.tzinfo is not None
        assert "Category:Season 1 characters" in source.basis_evidence

    def test_a_page_without_wikitext_is_skipped(self) -> None:
        assert (
            _source()._to_entity(
                {"title": "Empty", "categories": []},
                WikiPageRef(title="Empty"),
                wiki_url="https://dexter.fandom.com",
                rules=canon_basis.BasisRules(),
            )
            is None
        )

    def test_an_index_page_is_skipped(self) -> None:
        page = {
            "pageid": 9,
            "title": "Total Deaths",
            "revisions": [
                {
                    "slots": {
                        "main": {"content": "This page lists every death.\n{|\n|x\n|}"}
                    }
                }
            ],
            "categories": [{"ns": 14, "title": "Category:Characters"}],
        }
        assert (
            _source()._to_entity(
                page,
                WikiPageRef(title="Total Deaths", kind=WikiEntityKind.CHARACTER),
                wiki_url="https://dexter.fandom.com",
                rules=canon_basis.BasisRules(),
            )
            is None
        )


class TestSubdomainResolution:
    def test_compacts_and_hyphenates_a_multi_word_name(self) -> None:
        candidates = _source()._candidate_subdomains("Breaking Bad")
        assert candidates[:2] == ("breakingbad", "breaking-bad")

    def test_also_tries_the_name_without_a_leading_article(self) -> None:
        assert "witcher" in _source()._candidate_subdomains("The Witcher")

    def test_an_override_wins_outright(self) -> None:
        source = FandomWikiSource(
            httpx.Client(), subdomain_overrides={"Percy Jackson": "riordan"}
        )
        assert source._candidate_subdomains("percy jackson") == ("riordan",)

    def test_a_nameless_fandom_yields_no_candidates(self) -> None:
        assert _source()._candidate_subdomains("!!!") == ()


class TestHelpers:
    def test_page_url_encodes_spaces_as_underscores(self) -> None:
        assert (
            _page_url("https://dexter.fandom.com/", "Brian Moser (Novels)")
            == "https://dexter.fandom.com/wiki/Brian_Moser_(Novels)"
        )

    def test_revision_content_tolerates_a_missing_slot(self) -> None:
        assert _revision_content({"revisions": [{}]}) == ""
        assert _revision_content({}) == ""

    def test_revision_content_reads_the_main_slot(self) -> None:
        assert (
            _revision_content({"revisions": [{"slots": {"main": {"content": "x"}}}]})
            == "x"
        )

    def test_truncate_cuts_on_a_word_boundary(self) -> None:
        result = _truncate("alpha beta gamma delta", 12)
        assert result.endswith("…")
        assert "gamm" not in result

    def test_truncate_leaves_short_text_alone(self) -> None:
        assert _truncate("short", 50) == "short"

    def test_is_entity_page_accepts_a_stub_that_bolds_its_own_name(self) -> None:
        assert _is_entity_page(
            "Alice", profile=None, lead="'''Alice''' is a neighbour.", relationships=()
        )

    def test_is_entity_page_rejects_a_list_page(self) -> None:
        assert not _is_entity_page(
            "Total Deaths",
            profile=None,
            lead="This page lists deaths.",
            relationships=(),
        )

    def test_collect_relationships_falls_back_to_the_field_name_as_the_kind(
        self,
    ) -> None:
        relationships = _collect_relationships(
            {"spouse": "[[Rita Morgan]]"},
            basis=WikiCanonBasis.SCREEN,
            source_url="https://example.test",
        )
        assert relationships[0].target == "Rita Morgan"
        assert relationships[0].kind == "spouse"
        assert relationships[0].field == "spouse"

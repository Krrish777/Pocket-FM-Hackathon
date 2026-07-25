"""Unit tests for wiki entity reconciliation and index invariants — pure, no network.

The scenario is the real one: `dexter.fandom.com` keeps "Brian Moser" (screen) and
"Brian Moser (Novels)" (book) as separate pages that describe one entity under two canons.
"""

from datetime import UTC, datetime

from story_engine.domain.models.wiki_index import (
    WikiAttribute,
    WikiCanonBasis,
    WikiEntity,
    WikiEntityIndex,
    WikiEntityKind,
    WikiLifeStatus,
    WikiRelationship,
    WikiSourcePage,
)
from story_engine.domain.wiki_reconcile import combine_basis, merge_entities

AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _source(title: str, basis: WikiCanonBasis) -> WikiSourcePage:
    return WikiSourcePage(
        source_name="fandom_wiki",
        wiki_url="https://dexter.fandom.com",
        page_title=title,
        page_id="1",
        page_url=f"https://dexter.fandom.com/wiki/{title.replace(' ', '_')}",
        canon_basis=basis,
        basis_evidence=(f"Category:{basis} marker",),
        retrieved_at=AT,
    )


BRIAN_SCREEN = WikiEntity(
    canonical_name="Brian Moser",
    kind=WikiEntityKind.CHARACTER,
    canon_basis=WikiCanonBasis.SCREEN,
    aliases=("The Ice Truck Killer", "Rudy Cooper"),
    summary="Brian Moser, also known as The Ice Truck Killer, is the antagonist of Season One.",
    life_status=WikiLifeStatus.DECEASED,
    relationships=(
        WikiRelationship(
            target="Dexter Morgan",
            kind="younger brother",
            field="relatives",
            canon_basis=WikiCanonBasis.SCREEN,
        ),
    ),
    attributes=(
        WikiAttribute(
            predicate="moniker",
            value="The Ice Truck Killer",
            canon_basis=WikiCanonBasis.SCREEN,
        ),
    ),
    sources=(_source("Brian Moser", WikiCanonBasis.SCREEN),),
    prominence=82058,
)

BRIAN_NOVEL = WikiEntity(
    canonical_name="Brian Moser",
    kind=WikiEntityKind.CHARACTER,
    canon_basis=WikiCanonBasis.NOVEL,
    aliases=("Tamiami Slasher",),
    summary="Brian Moser is the Tamiami Slasher.",
    life_status=WikiLifeStatus.DECEASED,
    relationships=(
        WikiRelationship(
            target="Dexter Morgan",
            kind="younger brother",
            field="relatives",
            canon_basis=WikiCanonBasis.NOVEL,
        ),
        WikiRelationship(
            target="Lily Anne Morgan",
            kind="niece",
            field="relatives",
            canon_basis=WikiCanonBasis.NOVEL,
        ),
    ),
    attributes=(
        WikiAttribute(
            predicate="moniker",
            value="Tamiami Slasher",
            canon_basis=WikiCanonBasis.NOVEL,
        ),
    ),
    sources=(_source("Brian Moser (Novels)", WikiCanonBasis.NOVEL),),
    prominence=15000,
)

HANNAH = WikiEntity(
    canonical_name="Hannah McKay",
    kind=WikiEntityKind.CHARACTER,
    canon_basis=WikiCanonBasis.SCREEN,
    summary="Hannah McKay is a serial killer.",
    prominence=43648,
    sources=(_source("Hannah McKay", WikiCanonBasis.SCREEN),),
)


class TestCombineBasis:
    def test_novel_and_screen_combine_to_both(self) -> None:
        assert (
            combine_basis(WikiCanonBasis.NOVEL, WikiCanonBasis.SCREEN)
            is WikiCanonBasis.BOTH
        )

    def test_unknown_is_absorbed_not_propagated(self) -> None:
        assert (
            combine_basis(WikiCanonBasis.UNKNOWN, WikiCanonBasis.NOVEL)
            is WikiCanonBasis.NOVEL
        )
        assert (
            combine_basis(WikiCanonBasis.SCREEN, WikiCanonBasis.UNKNOWN)
            is WikiCanonBasis.SCREEN
        )

    def test_identical_bases_are_preserved(self) -> None:
        assert (
            combine_basis(WikiCanonBasis.SCREEN, WikiCanonBasis.SCREEN)
            is WikiCanonBasis.SCREEN
        )


class TestMergeEntities:
    def test_same_name_under_two_canons_merges_to_one_entity_marked_both(self) -> None:
        merged = merge_entities((BRIAN_SCREEN, BRIAN_NOVEL, HANNAH))
        assert len(merged) == 2
        brian = next(e for e in merged if e.canonical_name == "Brian Moser")
        assert brian.canon_basis is WikiCanonBasis.BOTH

    def test_merge_unions_aliases_across_canons(self) -> None:
        brian = merge_entities((BRIAN_SCREEN, BRIAN_NOVEL))[0]
        assert set(brian.aliases) >= {
            "The Ice Truck Killer",
            "Rudy Cooper",
            "Tamiami Slasher",
        }
        assert "Brian Moser" not in brian.aliases

    def test_merge_keeps_diverging_attribute_values_side_by_side(self) -> None:
        # Two monikers under two canons IS the divergence this index exists to expose.
        brian = merge_entities((BRIAN_SCREEN, BRIAN_NOVEL))[0]
        monikers = {a.value: a.canon_basis for a in brian.attributes}
        assert monikers["The Ice Truck Killer"] is WikiCanonBasis.SCREEN
        assert monikers["Tamiami Slasher"] is WikiCanonBasis.NOVEL

    def test_merge_combines_a_duplicated_relationship_rather_than_repeating_it(
        self,
    ) -> None:
        brian = merge_entities((BRIAN_SCREEN, BRIAN_NOVEL))[0]
        brothers = [r for r in brian.relationships if r.target == "Dexter Morgan"]
        assert len(brothers) == 1
        assert brothers[0].canon_basis is WikiCanonBasis.BOTH
        assert any(r.target == "Lily Anne Morgan" for r in brian.relationships)

    def test_merge_never_drops_provenance(self) -> None:
        brian = merge_entities((BRIAN_SCREEN, BRIAN_NOVEL))[0]
        assert {s.page_title for s in brian.sources} == {
            "Brian Moser",
            "Brian Moser (Novels)",
        }

    def test_merge_keeps_the_highest_prominence(self) -> None:
        assert merge_entities((BRIAN_NOVEL, BRIAN_SCREEN))[0].prominence == 82058

    def test_result_is_ordered_by_descending_prominence(self) -> None:
        merged = merge_entities((HANNAH, BRIAN_SCREEN))
        assert [e.canonical_name for e in merged] == ["Brian Moser", "Hannah McKay"]

    def test_a_lone_entity_passes_through_unchanged(self) -> None:
        assert merge_entities((HANNAH,)) == (HANNAH,)


class TestWikiEntityIndex:
    def _index(self) -> WikiEntityIndex:
        return WikiEntityIndex(
            fandom="Dexter",
            source_name="fandom_wiki",
            wiki_url="https://dexter.fandom.com",
            retrieved_at=AT,
            entities=merge_entities((BRIAN_SCREEN, BRIAN_NOVEL, HANNAH)),
        )

    def test_counts_are_derived_not_stored(self) -> None:
        index = self._index()
        assert index.entity_count == 2
        assert index.relationship_count == 2
        assert index.attribute_count == 2

    def test_counts_by_basis_is_the_od2_headline(self) -> None:
        assert self._index().counts_by_basis() == {"both": 1, "screen": 1}

    def test_names_with_basis_lists_the_screen_only_set(self) -> None:
        assert self._index().names_with_basis(WikiCanonBasis.SCREEN) == (
            "Hannah McKay",
        )

    def test_find_matches_an_alias_case_insensitively(self) -> None:
        found = self._index().find("tamiami slasher")
        assert found is not None
        assert found.canonical_name == "Brian Moser"

    def test_find_returns_none_for_an_unknown_name(self) -> None:
        assert self._index().find("Walter White") is None

    def test_unresolved_targets_reports_coverage_gaps_without_dropping_them(
        self,
    ) -> None:
        unresolved = self._index().unresolved_targets()
        assert set(unresolved) == {"Dexter Morgan", "Lily Anne Morgan"}

    def test_matches_name_covers_canonical_name_and_aliases(self) -> None:
        assert HANNAH.matches_name("hannah mckay")
        assert not HANNAH.matches_name("Dexter Morgan")

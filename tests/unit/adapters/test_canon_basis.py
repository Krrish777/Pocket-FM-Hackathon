"""Unit tests for novel-vs-screen classification — no network.

Category names are verbatim from `dexter.fandom.com` as fetched 2026-07-25, because this classifier is
the answer to `project_context.md` §11 OD-2 and a fixture invented from memory would prove nothing.
"""

from story_engine.adapters.outbound.wiki.canon_basis import (
    BasisRules,
    canonical_name,
    classify,
)
from story_engine.domain.models.wiki_index import WikiCanonBasis

# Real category sets observed live.
SCREEN_ONLY = (
    "Category:Characters",
    "Category:Season 7 characters",
    "Category:Season 8 characters",
    "Category:Serial Killers",
)
NOVEL_ONLY = (
    "Category:Characters (Novels)",
    "Category:Dearly Devoted Dexter characters",
    "Category:Deceased (Novels)",
)
BOOK_TITLES = frozenset(
    {"darkly dreaming dexter", "dearly devoted dexter", "dexter is dead"}
)


class TestClassify:
    def test_season_categories_mark_screen_canon(self) -> None:
        basis, evidence = classify("Hannah McKay", SCREEN_ONLY)
        assert basis is WikiCanonBasis.SCREEN
        assert "Category:Season 7 characters" in evidence

    def test_novel_qualifier_in_the_page_title_marks_book_canon(self) -> None:
        basis, evidence = classify("Brian Moser (Novels)", NOVEL_ONLY)
        assert basis is WikiCanonBasis.NOVEL
        assert "Brian Moser (Novels)" in evidence

    def test_a_page_marked_both_ways_is_both(self) -> None:
        basis, _ = classify("Angel Batista (Novels)", (*NOVEL_ONLY, *SCREEN_ONLY))
        assert basis is WikiCanonBasis.BOTH

    def test_unmarked_page_is_unknown_never_novel(self) -> None:
        # Defaulting to novel is the silent corruption path project_context.md 6.4 warns about.
        basis, evidence = classify("Acupuncturist", ("Category:Characters",))
        assert basis is WikiCanonBasis.UNKNOWN
        assert evidence == ()

    def test_per_book_category_is_recognized_via_discovered_titles(self) -> None:
        rules = BasisRules(novel_work_titles=BOOK_TITLES)
        basis, evidence = classify(
            "Dr. Danco", ("Category:Dearly Devoted Dexter characters",), rules
        )
        assert basis is WikiCanonBasis.NOVEL
        assert evidence == ("Category:Dearly Devoted Dexter characters",)

    def test_tolerates_categories_without_the_prefix(self) -> None:
        basis, _ = classify("X", ("Season 1 characters",))
        assert basis is WikiCanonBasis.SCREEN

    def test_ignores_blank_categories(self) -> None:
        basis, _ = classify("X", ("", "   "))
        assert basis is WikiCanonBasis.UNKNOWN


class TestCanonicalName:
    def test_strips_a_media_variant_qualifier(self) -> None:
        assert canonical_name("Brian Moser (Novels)") == "Brian Moser"
        assert canonical_name("Rita Morgan (Novels/Comics)") == "Rita Morgan"
        assert canonical_name("Vince Masuoka (Novels)") == "Vince Masuoka"

    def test_leaves_a_non_media_parenthetical_intact(self) -> None:
        assert canonical_name("Rudy Cooper (Alias)") == "Rudy Cooper (Alias)"

    def test_leaves_an_unqualified_title_untouched(self) -> None:
        assert canonical_name("Debra Morgan") == "Debra Morgan"

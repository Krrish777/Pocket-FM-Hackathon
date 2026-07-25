"""Unit tests for the pure fanfic admission rules.

These encode the empirically measured separation (spec §2.4): real prose runs 23-32 dialogue quotes
per 1k words while discussion posts sit at a median of exactly 0.0.
"""

from story_engine.domain.fanfic_quality import (
    alias_hits,
    content_fingerprint,
    declares_fandom,
    is_prose,
    is_relevant,
    normalize_text,
    quotes_per_1k_words,
    required_alias_hits,
    strip_boilerplate,
)
from story_engine.domain.models.fanfic import FandomQuery, FanficSource, StoryRef

PROSE = (
    '"You came back," Geralt said, sheathing his sword.\n\n'
    "Ciri did not answer at once. She watched the treeline where the wolves had been. "
    '"I had nowhere else to go," she said finally.\n\n'
    '"Then sit. Eat." He pushed the bowl across the fire toward her. '
    '"You are thinner than when you left."\n\n'
    "She sat. The broth burned her tongue and she did not care. "
    "Somewhere beyond the ridge a horn sounded, and Geralt turned his head toward it, listening."
) * 12

# Repeated until it clears the 500-word gate, so the dialogue-density check is what rejects it.
DISCUSSION = (
    "Does anyone remember the fic where Geralt adopts Ciri early and they go to Skellige? "
    "I think it was on AO3 but I cannot find it anymore. Any help appreciated. "
    "I have already checked the recs list and the wiki."
) * 16


def _ref(**overrides: object) -> StoryRef:
    defaults: dict[str, object] = {
        "source": FanficSource.WATTPAD,
        "source_id": "1",
        "title": "A Witcher Tale",
        "description": "Geralt and Ciri travel north.",
        "tags": ("fanfiction", "geralt"),
    }
    return StoryRef(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestProseDetection:
    def test_dialogue_density_separates_prose_from_discussion(self) -> None:
        assert quotes_per_1k_words(PROSE) >= 5.0
        assert quotes_per_1k_words(DISCUSSION) == 0.0

    def test_prose_is_admitted(self) -> None:
        assert is_prose(PROSE, min_words=500, min_quotes_per_1k=5.0)

    def test_discussion_is_rejected_despite_being_long(self) -> None:
        # Long enough to clear a naive length gate, but carries no dialogue.
        assert len(DISCUSSION.split()) > 500
        assert not is_prose(DISCUSSION, min_words=500, min_quotes_per_1k=5.0)

    def test_short_prose_is_rejected(self) -> None:
        assert not is_prose('"Hi," she said.', min_words=500, min_quotes_per_1k=5.0)

    def test_empty_text_does_not_divide_by_zero(self) -> None:
        assert quotes_per_1k_words("") == 0.0
        assert not is_prose("", min_words=1, min_quotes_per_1k=0.0)


class TestBoilerplate:
    def test_strips_author_notes_and_promos(self) -> None:
        raw = (
            "A/N: sorry for the late update!!\n"
            "I don't own The Witcher, CDPR does.\n"
            '"You came back," Geralt said.\n'
            "Please vote and comment if you liked it\n"
            "Read the rest on AO3\n"
        )
        cleaned = strip_boilerplate(raw)
        assert cleaned == '"You came back," Geralt said.'

    def test_keeps_prose_that_merely_mentions_a_keyword(self) -> None:
        # "vote" mid-sentence is dialogue, not a footer — anchoring must protect it.
        line = "The council will vote at dawn, and you will lose."
        assert strip_boilerplate(line) == line


class TestRelevance:
    def test_requires_two_distinct_aliases(self) -> None:
        query = FandomQuery(
            name="The Witcher", aliases=("Geralt", "Ciri"), min_alias_hits=2
        )
        # Title+description+tags mention "geralt" and "witcher" -> two distinct hits.
        assert is_relevant(_ref(), query)

    def test_single_incidental_mention_is_rejected(self) -> None:
        query = FandomQuery(
            name="Percy Jackson",
            aliases=("Anaklusmos", "Camp Half-Blood"),
            min_alias_hits=2,
        )
        ref = _ref(
            title="Percy learns to skate", description="Original story.", tags=()
        )
        assert not is_relevant(ref, query)

    def test_universe_term_counts_as_a_hit(self) -> None:
        query = FandomQuery(
            name="Percy Jackson", aliases=("Anaklusmos",), min_alias_hits=2
        )
        ref = _ref(
            title="Anaklusmos Reforged", description="A Percy Jackson story.", tags=()
        )
        assert sorted(alias_hits(ref, query)) == ["anaklusmos", "percy jackson"]
        assert is_relevant(ref, query)

    def test_read_floor_is_enforced(self) -> None:
        query = FandomQuery(name="The Witcher", aliases=("Geralt",), min_reads=1000)
        assert not is_relevant(_ref(reads=10), query)

    def test_other_languages_are_excluded_by_default(self) -> None:
        query = FandomQuery(name="The Witcher", aliases=("Geralt",))
        assert not is_relevant(_ref(language="es"), query)


class TestAliasMatchingBoundaries:
    """Regression cover for the two misclassifications seen in live Wattpad data."""

    def test_space_stripped_tag_satisfies_a_multiword_alias(self) -> None:
        # Real case: 'Dexter: Blood (fanfiction)' tagged dextermorgan/bayharborbutcher was rejected.
        query = FandomQuery(
            name="Dexter", aliases=("Dexter Morgan", "The Bay Harbor Butcher")
        )
        ref = _ref(
            title="Dexter: Blood (fanfiction)",
            description="",
            tags=("dexter", "dextermorgan", "bayharborbutcher"),
        )
        hits = alias_hits(ref, query)
        assert "dexter morgan" in hits
        assert "the bay harbor butcher" in hits
        assert is_relevant(ref, query)

    def test_alias_does_not_match_inside_a_longer_word(self) -> None:
        # Real case: 'dexter' matched inside 'dextercharming', an Ever After High character.
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",))
        ref = _ref(
            title="Ever After High Raven Queen Is Gone Forever After",
            description="",
            tags=("dextercharming", "ravenqueen", "fanfiction"),
        )
        assert alias_hits(ref, query) == ()
        assert not is_relevant(ref, query)

    def test_multiword_alias_matches_across_a_space_in_prose_text(self) -> None:
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",))
        ref = _ref(title="A Study of Dexter Morgan", description="", tags=())
        assert "dexter morgan" in alias_hits(ref, query)

    def test_numeric_alias_matches(self) -> None:
        query = FandomQuery(name="Inception", aliases=("528491",))
        ref = _ref(title="Inception: 528491", description="", tags=())
        assert sorted(alias_hits(ref, query)) == ["528491", "inception"]


class TestExplicitFandomDeclaration:
    """A work that labels itself "<Fandom> Fanfiction" declares its fandom outright."""

    def test_title_declaring_the_fandom_is_admitted_on_one_hit(self) -> None:
        # Real case: 'Rita Makes Up Her Mind: A Dexter Fanfiction' was rejected on the count rule.
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",), min_alias_hits=2)
        ref = _ref(
            title="Rita Makes Up Her Mind: A Dexter Fanfiction",
            description="",
            tags=(),
        )
        assert declares_fandom(ref, query)
        assert is_relevant(ref, query)

    def test_bracketed_declaration_is_admitted(self) -> None:
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",))
        ref = _ref(
            title="I Love Both of His Sides [Dexter Fanfiction]",
            description="",
            tags=(),
        )
        assert is_relevant(ref, query)

    def test_space_stripped_tag_declaration_is_admitted(self) -> None:
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",))
        ref = _ref(title="Set Free", description="", tags=("dexterfanfiction",))
        assert declares_fandom(ref, query)

    def test_non_adjacent_mention_is_not_a_declaration(self) -> None:
        # 'Dexter ▷ Scott Summers' is an X-Men work with a character named Dexter.
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",))
        ref = _ref(
            title="1 | Dexter - Scott Summers",
            description="An X-Men story.",
            tags=("xmen", "fanfiction"),
        )
        assert not declares_fandom(ref, query)
        assert not is_relevant(ref, query)

    def test_other_fandoms_declaration_is_not_ours(self) -> None:
        query = FandomQuery(name="Dexter", aliases=("Dexter Morgan",))
        ref = _ref(title="Powerpuff girls fanfiction", description="", tags=())
        assert not declares_fandom(ref, query)


class TestRequiredAliasHits:
    """Regression cover for the silent total-recall failure seen on the first live run."""

    def test_clamps_to_the_available_alias_surface(self) -> None:
        # Alias expansion failed, so only the fandom name is searchable.
        query = FandomQuery(name="The Witcher", aliases=(), min_alias_hits=2)
        assert required_alias_hits(query) == 1

    def test_keeps_the_strict_requirement_when_aliases_exist(self) -> None:
        query = FandomQuery(
            name="The Witcher", aliases=("Geralt", "Ciri"), min_alias_hits=2
        )
        assert required_alias_hits(query) == 2

    def test_never_drops_below_one(self) -> None:
        query = FandomQuery(name="The Witcher", min_alias_hits=1)
        assert required_alias_hits(query) >= 1

    def test_name_only_query_still_admits_a_matching_work(self) -> None:
        query = FandomQuery(name="The Witcher", aliases=(), min_alias_hits=2)
        ref = _ref(title="The Witcher: Blood Origin", description="", tags=())
        assert is_relevant(ref, query)

    def test_name_only_query_still_rejects_an_unrelated_work(self) -> None:
        query = FandomQuery(name="The Witcher", aliases=(), min_alias_hits=2)
        ref = _ref(title="An Original Romance", description="", tags=())
        assert not is_relevant(ref, query)


class TestContentAndQualityFloors:
    """Corpus-quality gates found necessary while reviewing real harvested output."""

    def test_mature_work_is_excluded_by_default(self) -> None:
        query = FandomQuery(name="Titanic", aliases=("Jack Dawson",))
        assert not is_relevant(_ref(mature=True), query)

    def test_mature_work_is_kept_when_explicitly_allowed(self) -> None:
        query = FandomQuery(
            name="The Witcher", aliases=("Geralt", "Ciri"), allow_mature=True
        )
        assert is_relevant(_ref(mature=True), query)

    def test_vote_floor_is_enforced(self) -> None:
        # Real case: a 54-read, 0-vote joke fic passed every other gate.
        query = FandomQuery(name="The Witcher", aliases=("Geralt", "Ciri"), min_votes=5)
        assert not is_relevant(_ref(votes=0), query)
        assert is_relevant(_ref(votes=50), query)


class TestDisclaimerStripping:
    def test_removes_a_disclaimer_sharing_a_line_with_prose(self) -> None:
        # Real case: Titanic #7 chapter 1 opened with this exact shape.
        raw = "This is based mainly after the film Titanic by James Cameron. I DO NOT OWN TITANIC! I only own the plot for this story."
        assert strip_boilerplate(raw) == ""

    def test_keeps_the_prose_around_a_stripped_disclaimer(self) -> None:
        raw = 'The ship groaned. I do not own Titanic. "Hold on," he said.'
        cleaned = strip_boilerplate(raw)
        assert "The ship groaned." in cleaned
        assert "do not own" not in cleaned.lower()
        assert '"Hold on," he said.' in cleaned

    def test_removes_a_byline_and_credit_title_page(self) -> None:
        # Real case: Dexter #2's first chapter was a title page, not prose.
        raw = "I love both of his sides\nDexter Fanfiction\nBy: KrissyChan\nI woke up to my ringtone."
        assert (
            strip_boilerplate(raw)
            == "I love both of his sides\nI woke up to my ringtone."
        )


class TestFingerprinting:
    def test_normalization_ignores_case_and_whitespace(self) -> None:
        assert normalize_text("The  WOLF\n\nhowled.") == "the wolf howled."

    def test_reposted_text_shares_a_fingerprint(self) -> None:
        assert content_fingerprint("The wolf howled.") == content_fingerprint(
            "the   WOLF\nhowled."
        )

    def test_different_text_differs(self) -> None:
        assert content_fingerprint("a") != content_fingerprint("b")

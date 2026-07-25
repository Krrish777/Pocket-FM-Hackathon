"""Unit tests for premise detection, clustering, and Branch Oracle assembly.

Every fixture below is REAL text from the harvested corpus on disk
(`data/raw/fanfic/{dexter,titanic}/stories.jsonl`), so the patterns are anchored to observed fandom
phrasing rather than to invented examples.
"""

import pytest

from story_engine.domain.fanfic_premise import (
    MAX_BRANCH_OPTIONS,
    UNCLASSIFIED_KEY,
    branch_points,
    entity_slug,
    group_by_premise,
    premise_signature,
    premise_signature_for,
)
from story_engine.domain.models.fanfic import (
    Chapter,
    FanficSource,
    HarvestedStory,
    PremiseTrope,
    StoryRef,
)

# --- real harvested metadata --------------------------------------------------------------------
SET_FREE_TITLE = "Set Free- A Dexter FanFiction"
SET_FREE_DESC = (
    "Dexter doesn't kill Brian. However instead of 'running off' together, perhaps they can "
    "rekindle the brotherly bond that has been lost. Will Brian's influence on his baby brother "
    "cause him to become darker, or will Dexter's influence make Brian...better?"
)
SET_FREE_TAGS = (
    "biney",
    "brian",
    "brother",
    "cooper",
    "dexter",
    "morgan",
    "moser",
    "rudy",
)

# The same divergence as SET_FREE, phrased the way that work's own author note phrases it.
AUTHOR_NOTE_PHRASING = "There are a lot of Fan Fictions out there with Dexter letting Brian live, and this is mine."

IF_JACK_LIVED_TITLE = "Life After Titanic, If Jack Lived (Titanic Fanfiction)"
IF_JACK_LIVED_DESC = (
    "In this book, you probably already guessed what it's about! If Jack lived, this is Rose's "
    "and Jack's life after Titanic! In this fanfic, Jack and Rose grow old together and have "
    "children! Exactly the ending everyone wanted them to have ;)"
)
IF_JACK_LIVED_TAGS = (
    "ifjacklived",
    "jack",
    "jackandrose",
    "jackdawson",
    "rose",
    "titanic",
)

HEARTS_TITLE = "Hearts Beneath the Waves ~ Titanic FanFiction"
HEARTS_DESC = (
    "Jack and Rose, two of the few survivors of the Titanic, one of the deadliest peacetime "
    "maritime disasters in history, find themselves aboard the Carpathia."
)

ICEBREAKER_TITLE = "Icebreaker--Titanic Fanfiction"
ICEBREAKER_DESC = (
    "Jack wakes up 90 years after the Titanic sinks, and soon learns he has been kept frozen at "
    "the bottom of the sea in a giant ice block. He tries to find Rose, but is she dead?"
)

CROSSOVER_TITLE = "Finally Flying- Disney Descendants/ Titanic FanFiction"
CROSSOVER_DESC = (
    "The Titanic, the greatest ship ever built some say. Ben, son of King Beast and Queen Belle, "
    "went on the ship to become king."
)

READER_TITLE = "Safe & Sound: Officer Lowe x Reader: Titanic Fanfiction"
READER_DESC = (
    "Y/n boards the chance of a lifetime to America on R.M.S Titanic with her bratty-brother Cal "
    "Hockley."
)

NO_PREMISE_TITLE = "I Love Both of His Sides [Dexter Fanfiction]"


class TestSurvivalPremise:
    def test_negated_kill_names_the_spared_character(self) -> None:
        premise = premise_signature(
            SET_FREE_TITLE, SET_FREE_DESC, SET_FREE_TAGS, fandom="Dexter"
        )
        assert premise.key == "character_survives:brian"
        assert PremiseTrope.CHARACTER_SURVIVES in premise.tropes
        assert premise.focal_entities == ("brian",)

    def test_author_note_phrasing_lands_on_the_same_key(self) -> None:
        # "doesn't kill Brian" and "letting Brian live" are one canon decision point. The whole
        # feature is worthless if two renderings of it split into two groups.
        other = premise_signature(
            "A Dexter Fanfiction", AUTHOR_NOTE_PHRASING, fandom="Dexter"
        )
        assert other.key == "character_survives:brian"

    def test_if_x_lived_is_the_same_shape(self) -> None:
        premise = premise_signature(
            IF_JACK_LIVED_TITLE,
            IF_JACK_LIVED_DESC,
            IF_JACK_LIVED_TAGS,
            fandom="Titanic",
        )
        assert premise.key == "character_survives:jack"

    def test_survivors_phrasing_keys_on_the_first_character(self) -> None:
        # "Jack and Rose, two of the few survivors" must not become `survives:jack+rose` — the
        # decision point is ONE character's death.
        premise = premise_signature(HEARTS_TITLE, HEARTS_DESC, fandom="Titanic")
        assert premise.key == "character_survives:jack"

    def test_waking_after_a_year_gap_counts_as_survival(self) -> None:
        premise = premise_signature(ICEBREAKER_TITLE, ICEBREAKER_DESC, fandom="Titanic")
        assert premise.key == "character_survives:jack"
        assert PremiseTrope.TIME_DISPLACEMENT in premise.tropes

    def test_survival_tag_alone_is_enough(self) -> None:
        premise = premise_signature(
            "Untitled", "No blurb.", ("ifjacklived", "titanic"), fandom="Titanic"
        )
        assert premise.key == "character_survives:jack"

    def test_function_words_are_not_mistaken_for_characters(self) -> None:
        # "They survived" is a real blurb shape and names nobody; it must not key on "They".
        premise = premise_signature(
            "A Tale", "They survived the wreck.", fandom="Titanic"
        )
        assert not premise.focal_entities or "they" not in premise.focal_entities


class TestOtherPremises:
    def test_crossover_drops_the_fandoms_own_name(self) -> None:
        premise = premise_signature(
            CROSSOVER_TITLE,
            CROSSOVER_DESC,
            ("disney", "disneydescendants"),
            fandom="Titanic",
        )
        assert premise.key == "crossover:disney-descendants"

    def test_reader_insert_names_the_love_interest(self) -> None:
        premise = premise_signature(
            READER_TITLE,
            READER_DESC,
            ("charecterxreader", "officerlowe"),
            fandom="Titanic",
        )
        assert premise.key == "reader_insert:officer-lowe"

    def test_pairing_is_order_independent(self) -> None:
        left = premise_signature(
            "Titanic fanfiction Jack x Fabrizio", "", fandom="Titanic"
        )
        right = premise_signature(
            "Titanic fanfiction Fabrizio x Jack", "", fandom="Titanic"
        )
        assert left.key == right.key == "pairing:fabrizio+jack"

    def test_blank_blurb_is_unclassified_not_dropped(self) -> None:
        premise = premise_signature(NO_PREMISE_TITLE, "", fandom="Dexter")
        assert premise.key == UNCLASSIFIED_KEY
        assert premise.tropes == ()
        assert "UNVERIFIED" in premise.alternate_path

    def test_signature_is_deterministic(self) -> None:
        first = premise_signature(
            SET_FREE_TITLE, SET_FREE_DESC, SET_FREE_TAGS, fandom="Dexter"
        )
        second = premise_signature(
            SET_FREE_TITLE, SET_FREE_DESC, SET_FREE_TAGS, fandom="Dexter"
        )
        assert first == second

    def test_entity_slug_normalizes_punctuation_and_case(self) -> None:
        assert entity_slug("Officer  Lowe!") == "officer-lowe"


def _story(
    source_id: str, title: str, description: str, tags: tuple[str, ...] = ()
) -> HarvestedStory:
    ref = StoryRef(
        source=FanficSource.WATTPAD,
        source_id=source_id,
        title=title,
        description=description,
        tags=tags,
    )
    return HarvestedStory(
        ref=ref,
        chapters=(Chapter(index=1, source_id=f"{source_id}-1", text="prose"),),
        premise=premise_signature_for(ref, fandom="Titanic"),
    )


JACK_BRANCHES = (
    _story("1", IF_JACK_LIVED_TITLE, IF_JACK_LIVED_DESC, IF_JACK_LIVED_TAGS),
    _story("2", HEARTS_TITLE, HEARTS_DESC),
    _story("3", ICEBREAKER_TITLE, ICEBREAKER_DESC),
    _story("4", NO_PREMISE_TITLE, ""),
)


class TestGrouping:
    def test_three_independent_works_group_on_one_decision_point(self) -> None:
        groups = group_by_premise(JACK_BRANCHES)
        assert groups[0].key == "character_survives:jack"
        assert groups[0].size == 3
        assert groups[0].members == ("wattpad:1", "wattpad:2", "wattpad:3")

    def test_unscored_works_are_skipped_not_bucketed(self) -> None:
        unscored = JACK_BRANCHES[0].model_copy(update={"premise": None})
        assert group_by_premise((unscored,)) == ()


class TestBranchPoints:
    def test_one_decision_point_yields_canon_plus_distinct_alternates(self) -> None:
        points = branch_points(JACK_BRANCHES)
        jack = points[0]
        assert jack.key == "character_survives:jack"
        assert jack.decision_point == "Whether Jack dies, as canon has it"
        assert jack.support == 3
        # Canon-stands plus three distinct alternate paths — exactly the 2-4 choices §4 requires.
        assert 2 <= jack.option_count <= MAX_BRANCH_OPTIONS
        assert jack.options[0].is_canon
        assert jack.options[0].label == "Let canon stand — Jack dies"
        alternates = [o.label for o in jack.options if not o.is_canon]
        assert all(label.startswith("Spare Jack") for label in alternates)
        assert len(set(alternates)) == len(alternates)

    def test_unclassified_works_are_not_offered_as_branches(self) -> None:
        keys = {p.key for p in branch_points(JACK_BRANCHES)}
        assert UNCLASSIFIED_KEY not in keys

    def test_option_labels_never_quote_the_harvested_blurb(self) -> None:
        # project_context.md §5.2: fan fiction supplies WHAT the options are, never the prose.
        for point in branch_points(JACK_BRANCHES):
            for option in point.options:
                assert option.label not in IF_JACK_LIVED_DESC
                assert option.label not in ICEBREAKER_DESC

    def test_option_ceiling_is_enforced(self) -> None:
        points = branch_points(JACK_BRANCHES, max_options=2)
        assert all(p.option_count <= 2 for p in points)

    def test_a_single_option_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_options must be >= 2"):
            branch_points(JACK_BRANCHES, max_options=1)

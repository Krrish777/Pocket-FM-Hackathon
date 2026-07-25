"""Unit tests for the prose-quality score.

Anchored to three REAL harvested passages, so the thresholds are calibrated to observed data:
mechanical tag-first dialogue, vivid interiority, and a joke fic that shouts in ALL CAPS.
"""

from story_engine.domain.prose_score import (
    NEUTRAL,
    dialogue_craft,
    interiority,
    paragraph_structure,
    prose_quality,
    punctuation_discipline,
    sentence_rhythm,
    vocabulary_richness,
)

# Harvested LOW-quality shape: attribution first, flat verbs, no interiority, no description.
MECHANICAL = (
    'I said, "I will be on my way."\n'
    'He said, "Okay."\n'
    'Dexter replied, "Oh not him."\n'
    'I said, "I have to go now."\n'
    'She said, "Fine."\n'
    'He said, "See you."\n'
)

# Harvested HIGH-quality shape: varied syntax, interiority, sensory detail.
VIVID = (
    "The cold air of the refrigerated room caused goose bumps to stand up on my arms, but I "
    "ignored them. Something twitched inside of me, something that had been dead for a long "
    "time.\n\n"
    "I waited. The light above the table hummed, and the smell of the place settled into my "
    "throat. I remembered the first time, and how little I had felt.\n\n"
    "Nothing moved. Then it did."
)

# Harvested joke fic, verbatim.
ONIONS = '"FOR THE LOVE OF ONIONS. PICK SOMETHING!!!!!!!!!!!!"'
# The same register at work-length. Needed because the bare line above is only seven words: most
# components correctly report "not measurable" and fall back to NEUTRAL, so a one-liner cannot be
# ranked. Scoring is a work-level operation.
ONIONS_FIC = (
    'She said, "OMG WHAT?!?!"\n'
    'He said, "FOR THE LOVE OF ONIONS. PICK SOMETHING!!!!!!!!!!!!"\n'
    'She said, "NO WAY!!!!"\n'
    'He said, "YES WAY!!!!!"\n'
    'She said, "OMG STOP IT!!!!!!"\n'
    'He said, "NEVER!!!!!!!!"\n'
) * 4


class TestScoreIsBounded:
    def test_score_stays_in_range_for_every_anchor(self) -> None:
        for text in (MECHANICAL, VIVID, ONIONS, "", "one two three"):
            assert 0.0 <= prose_quality(text).score <= 100.0

    def test_weights_sum_to_one(self) -> None:
        components = prose_quality(VIVID).components
        assert round(sum(c.weight for c in components), 6) == 1.0

    def test_every_component_is_explained(self) -> None:
        for component in prose_quality(VIVID).components:
            assert component.detail, f"{component.name} carries no measurement detail"

    def test_scoring_is_deterministic(self) -> None:
        assert prose_quality(VIVID) == prose_quality(VIVID)


class TestAnchorSeparation:
    def test_vivid_prose_outscores_mechanical_prose(self) -> None:
        low = prose_quality(MECHANICAL).score
        high = prose_quality(VIVID).score
        # Measured separation on these exact passages is ~30 points; 15 leaves headroom for
        # lexicon tuning without letting the ordering silently invert.
        assert high - low >= 15.0, f"low={low} high={high}"

    def test_mechanical_prose_has_no_interiority(self) -> None:
        value, detail = interiority(MECHANICAL)
        assert value == 0.0, detail

    def test_vivid_prose_maxes_interiority(self) -> None:
        value, _ = interiority(VIVID)
        assert value == 1.0

    def test_mechanical_dialogue_is_penalized_for_tag_first_monotony(self) -> None:
        value, detail = dialogue_craft(MECHANICAL)
        assert value <= 0.25, detail
        assert "tag-first lines 100%" in detail

    def test_narration_without_dialogue_is_neutral_not_zero(self) -> None:
        value, detail = dialogue_craft(VIVID)
        assert value == NEUTRAL, detail

    def test_flat_sentence_lengths_score_low(self) -> None:
        value, detail = sentence_rhythm(MECHANICAL)
        assert value <= 0.25, detail


class TestShoutingAbuse:
    def test_all_caps_and_exclamation_runs_bottom_out(self) -> None:
        value, detail = punctuation_discipline(ONIONS)
        assert value == 0.0, detail

    def test_the_joke_fic_ranks_last_of_the_three_anchors(self) -> None:
        joke = prose_quality(ONIONS_FIC).score
        assert joke < prose_quality(MECHANICAL).score
        assert joke < prose_quality(VIVID).score

    def test_a_bare_one_liner_is_reported_as_unmeasurable(self) -> None:
        # Honesty check: a seven-word snippet must NOT be presented as a confident low score —
        # most components say "not measurable" and fall back to NEUTRAL by design.
        unmeasurable = [
            c.name
            for c in prose_quality(ONIONS).components
            if "not measurable" in c.detail
        ]
        assert "dialogue_craft" in unmeasurable
        assert "vocabulary_richness" in unmeasurable

    def test_clean_punctuation_is_not_penalized(self) -> None:
        value, _ = punctuation_discipline(VIVID)
        assert value == 1.0


class TestUnmeasurableInputs:
    def test_short_text_falls_back_to_neutral_rather_than_zero(self) -> None:
        assert vocabulary_richness("Three words only.")[0] == NEUTRAL
        assert sentence_rhythm("Two sentences. That is all.")[0] == NEUTRAL

    def test_empty_text_scores_but_does_not_crash(self) -> None:
        result = prose_quality("")
        assert result.word_count == 0
        assert result.score >= 0.0

    def test_fragment_spam_is_penalized_in_structure(self) -> None:
        fragments = "\n".join(["Yes.", "No.", "Maybe.", "Fine.", "Okay."])
        value, detail = paragraph_structure(fragments)
        assert value <= 0.2, detail

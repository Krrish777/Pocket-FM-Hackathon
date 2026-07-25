"""Pure prose-quality scoring — deterministic, bounded, explainable.

Relevance (`fanfic_quality.is_relevant`) decides whether a work is *about* the fandom. Nothing
decided whether it is *well written*, and the harvested corpus spans the full range. Two real
harvested passages bracket it:

* **Low** — mechanical, tag-first dialogue with no interiority:
  `I said, "I will be on my way." / He said, "Okay." / Dexter replied, "Oh not him."`
* **High** — varied syntax, interiority, sensory detail:
  `The cold air of the refrigerated room caused goose bumps to stand up on my arms, but I ignored
  them. Something twitched inside of me, something that had been dead for a long time.`

The score exists to **rank**, not to filter: under project_context.md §5.2 the prose is never quoted
or reproduced, so quality only decides *which works to trust as branch evidence*. Ranking is the
primary use and no work is dropped unless a caller sets an explicit threshold.

Design constraints, all deliberate:

* **Stdlib only, no model.** Every component is a counting or variance measurement, so a score is
  reproducible across runs and reviewable in a diff.
* **Bounded and weighted.** Each component is normalized to [0, 1] and the weights sum to 1, so the
  total is a weighted mean scaled to [0, 100]. No component can dominate by scale accident.
* **Explainable.** Each component is returned with its value, weight, and raw measurement, so a
  ranking can be defended rather than asserted.
* **Neutral, not zero, when unmeasurable.** A work with no dialogue is not badly written, so the
  dialogue component returns `NEUTRAL` instead of 0 — otherwise the score would punish narration.

Thresholds are anchored to the two passages above and to the joke fic that shouted
`"FOR THE LOVE OF ONIONS. PICK SOMETHING!!!!!!!!!!!!"`, not chosen a priori.
"""

import re
import statistics

from story_engine.domain.models.fanfic import ProseComponent, ProseQuality

NEUTRAL = 0.5
"""Value used when a component cannot be measured — neither credit nor penalty."""

# Component weights — they sum to 1.0, which is what makes the total a weighted mean. Rationale for
# the ordering: rhythm and dialogue craft are the two defects the anchor passages differ on most,
# vocabulary and interiority are the positive signals, structure and punctuation catch abuse.
WEIGHT_SENTENCE_RHYTHM = 0.20
WEIGHT_DIALOGUE_CRAFT = 0.18
WEIGHT_VOCABULARY = 0.18
WEIGHT_INTERIORITY = 0.16
WEIGHT_PARAGRAPHS = 0.14
WEIGHT_PUNCTUATION = 0.14

# Built from code points, not literals: the typographic apostrophe is indistinguishable from the
# ASCII one in source, which is exactly what ruff's RUF001 exists to prevent.
_CURLY_APOSTROPHE = chr(0x2019)
_CURLY_CLOSE_QUOTE = chr(0x201D)
_SENTENCE_SPLIT_RE = re.compile(
    rf"(?<=[.!?…])[\"'{_CURLY_CLOSE_QUOTE}{_CURLY_APOSTROPHE})\]]*\s+"
)
_WORD_RE = re.compile(rf"[A-Za-z][A-Za-z'{_CURLY_APOSTROPHE}]*")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_QUOTE_RE = re.compile(r"[\"“”«»]")
_BANG_RUN_RE = re.compile(r"[!?]{2,}")
_CAPS_WORD_RE = re.compile(r"\b[A-Z]{3,}\b")

# Dialogue attribution verbs. `said`-family separated because said-monotony is the measured defect.
_SAID_VERBS = frozenset({"said", "says", "say"})
_TAG_VERBS = frozenset(
    {
        "said",
        "says",
        "say",
        "asked",
        "asks",
        "replied",
        "answered",
        "whispered",
        "muttered",
        "shouted",
        "yelled",
        "murmured",
        "growled",
        "snapped",
        "breathed",
        "sighed",
        "laughed",
        "added",
        "continued",
        "called",
        "cried",
        "hissed",
        "demanded",
        "offered",
        "admitted",
        "agreed",
        "insisted",
        "told",
        "explained",
        "mused",
        "grumbled",
        "screamed",
        "stammered",
        "repeated",
        "warned",
        "begged",
        "teased",
    }
)
_TAG_VERB_RE = re.compile(r"\b(" + "|".join(sorted(_TAG_VERBS)) + r")\b", re.IGNORECASE)
# "I said, "..."" / "Dexter replied, "..."" — the attribution comes FIRST and carries no action
# beat. This is the exact shape of the low-quality harvested passage.
_TAG_FIRST_RE = re.compile(
    r"^\s*[\"“]?\s*(?:[A-Z][a-z]+|I|He|She|They|We|You)\s+(?:"
    + "|".join(sorted(_TAG_VERBS))
    + r")\s*,?\s*[\"“]",
)

# Interiority and sensory markers: what separates "He said, 'Okay.'" from "Something twitched inside
# of me". A lexicon, not a model — the words are common and the density is the signal.
_INTERIOR_WORDS = frozenset(
    {
        "thought",
        "thoughts",
        "thinking",
        "felt",
        "feel",
        "feeling",
        "wondered",
        "wonder",
        "realized",
        "realised",
        "remembered",
        "remember",
        "knew",
        "hoped",
        "wanted",
        "needed",
        "ashamed",
        "afraid",
        "guilt",
        "ignored",
        "imagined",
        "decided",
        "doubted",
        "regret",
        "ached",
        "dreaded",
        "understood",
        "suspected",
        "hated",
        "loved",
        "inside",
        "something",
        "dead",
    }
)
_SENSORY_WORDS = frozenset(
    {
        "cold",
        "warm",
        "heat",
        "air",
        "skin",
        "breath",
        "breathing",
        "smell",
        "smelled",
        "taste",
        "tasted",
        "light",
        "dark",
        "shadow",
        "sound",
        "silence",
        "blood",
        "hands",
        "arms",
        "throat",
        "chest",
        "goose",
        "bumps",
        "goosebumps",
        "damp",
        "sharp",
        "weight",
        "rain",
        "wind",
        "twitched",
        "trembled",
        "shivered",
        "flinched",
        "burned",
        "ached",
        "sweat",
        "metallic",
        "refrigerated",
    }
)

_TTR_WINDOW = 400
"""Type-token ratio is length-biased — it falls monotonically as a text grows — so it is measured on
fixed windows and averaged. Without this, long works would be punished for being long."""


def _ramp(value: float, low: float, high: float) -> float:
    """Map `value` linearly onto [0, 1], clamped outside `[low, high]`."""
    if high <= low:
        raise ValueError("high must exceed low")
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    return (value - low) / (high - low)


def _sentences(text: str) -> list[str]:
    """Split into sentences on terminal punctuation, keeping only substantive ones."""
    return [s for s in (part.strip() for part in _SENTENCE_SPLIT_RE.split(text)) if s]


def _paragraphs(text: str) -> list[str]:
    """Split into paragraphs on blank lines, falling back to single newlines.

    Harvested hosts are inconsistent: some emit blank-line-separated paragraphs, some a newline per
    paragraph. Without the fallback, a whole chapter reads as one wall and the structure component
    is meaningless.
    """
    blocks = [b.strip() for b in _PARAGRAPH_SPLIT_RE.split(text) if b.strip()]
    if len(blocks) > 1:
        return blocks
    return [line.strip() for line in text.splitlines() if line.strip()]


def sentence_rhythm(text: str) -> tuple[float, str]:
    """Score variation in sentence length — the clearest mark of mechanical prose.

    The low-quality passage is three near-identical seven-word sentences; competent prose mixes a
    four-word beat with a thirty-word one. Population standard deviation of sentence word-counts is
    ramped from 2 words (flat) to 9 words (varied).
    """
    lengths = [len(_WORD_RE.findall(s)) for s in _sentences(text)]
    lengths = [n for n in lengths if n >= 2]
    if len(lengths) < 4:
        return NEUTRAL, "too few sentences to measure"
    spread = statistics.pstdev(lengths)
    return _ramp(spread, 2.0, 9.0), f"sentence-length stdev={spread:.1f} words"


def dialogue_craft(text: str) -> tuple[float, str]:
    """Score dialogue attribution: verb variety, and whether tags carry any action beat.

    Two measured defects, averaged:

    1. **Tag monotony** — the share of attributions using the most frequent verb. `said` is not a
       sin, but three lines running on `said/said/replied` is.
    2. **Tag-first bareness** — the share of dialogue lines shaped `X said, "..."`, i.e. attribution
       first with nothing else in the line. Good prose leads with the speech or an action beat.

    Returns `NEUTRAL` when there are too few attributions to measure, so pure narration is not
    punished.
    """
    quoted_lines = [
        line for line in text.splitlines() if _QUOTE_RE.search(line) and line.strip()
    ]
    verbs = [
        m.group(1).lower() for line in quoted_lines for m in _TAG_VERB_RE.finditer(line)
    ]
    if len(verbs) < 3 or not quoted_lines:
        return NEUTRAL, f"only {len(verbs)} dialogue attributions — not measurable"
    counts: dict[str, int] = {}
    for verb in verbs:
        counts[verb] = counts.get(verb, 0) + 1
    dominant_share = max(counts.values()) / len(verbs)
    said_share = sum(counts.get(v, 0) for v in _SAID_VERBS) / len(verbs)
    bare = sum(1 for line in quoted_lines if _TAG_FIRST_RE.match(line))
    bare_share = bare / len(quoted_lines)
    value = 0.5 * (1.0 - dominant_share) + 0.5 * (1.0 - bare_share)
    detail = (
        f"{len(verbs)} tags, dominant verb {dominant_share:.0%}, "
        f"said-family {said_share:.0%}, tag-first lines {bare_share:.0%}"
    )
    return max(0.0, min(1.0, value)), detail


def vocabulary_richness(text: str) -> tuple[float, str]:
    """Score lexical variety as a windowed type-token ratio, ramped over 0.38-0.62.

    Windowed (400 tokens) because raw TTR falls with length; averaging windows makes a 700-word
    one-shot and a 40,000-word epic comparable.
    """
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if len(words) < 40:
        return NEUTRAL, f"only {len(words)} words — not measurable"
    ratios = [
        len(set(window)) / len(window)
        for window in (
            words[i : i + _TTR_WINDOW] for i in range(0, len(words), _TTR_WINDOW)
        )
        if len(window) >= 40
    ]
    mean_ttr = statistics.fmean(ratios) if ratios else 0.0
    return _ramp(mean_ttr, 0.38, 0.62), (
        f"windowed type-token ratio={mean_ttr:.2f} over {len(ratios)} window(s)"
    )


def interiority(text: str) -> tuple[float, str]:
    """Score interior and sensory density per 1,000 words, ramped over 3-30 hits.

    This is the component that separates the two anchor passages: the mechanical one contains zero
    interior or sensory words, the vivid one is saturated with them.
    """
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return 0.0, "empty text"
    hits = sum(1 for w in words if w in _INTERIOR_WORDS or w in _SENSORY_WORDS)
    density = hits * 1000.0 / len(words)
    return _ramp(density, 3.0, 30.0), (
        f"{hits} interior/sensory words = {density:.0f} per 1k"
    )


def paragraph_structure(text: str) -> tuple[float, str]:
    """Score paragraphing: mean length inside a 20-150 word band, penalizing fragment spam.

    Two failure shapes appear in real harvests: undifferentiated walls (mean far above the band) and
    pure dialogue ping-pong where almost every paragraph is a bare one-liner. The second is scaled
    down hard, because it is the low-quality anchor's exact shape.
    """
    paragraphs = _paragraphs(text)
    if not paragraphs:
        return 0.0, "no paragraphs"
    lengths = [len(_WORD_RE.findall(p)) for p in paragraphs]
    mean_length = statistics.fmean(lengths)
    if mean_length <= 20.0:
        value = _ramp(mean_length, 5.0, 20.0)
    elif mean_length <= 150.0:
        value = 1.0
    else:
        value = 1.0 - _ramp(mean_length, 150.0, 400.0)
    fragment_share = sum(1 for n in lengths if n < 8) / len(lengths)
    if fragment_share > 0.6:
        value *= 0.4
    return max(0.0, min(1.0, value)), (
        f"{len(paragraphs)} paragraphs, mean {mean_length:.0f} words, "
        f"{fragment_share:.0%} under 8 words"
    )


def punctuation_discipline(text: str) -> tuple[float, str]:
    """Score restraint in shouting: ALL-CAPS share, `!!!!` runs, and exclamation rate.

    Penalty-only, starting from 1.0, because correct punctuation earns no credit — only abuse
    costs. Calibrated on the harvested joke fic `"FOR THE LOVE OF ONIONS. PICK SOMETHING!!!!!!!!!!!!"`,
    which must bottom out at 0.
    """
    words = _WORD_RE.findall(text)
    if not words:
        return 0.0, "empty text"
    long_words = [w for w in words if len(w) >= 3]
    caps_share = (
        len(_CAPS_WORD_RE.findall(text)) / len(long_words) if long_words else 0.0
    )
    runs = _BANG_RUN_RE.findall(text)
    max_run = max((len(r) for r in runs), default=0)
    sentence_count = max(len(_sentences(text)), 1)
    bang_rate = text.count("!") / sentence_count
    penalty = (
        0.60 * min(1.0, caps_share / 0.06)
        + 0.25 * (_ramp(float(max_run), 1.0, 5.0) if runs else 0.0)
        + 0.15 * min(1.0, bang_rate / 0.25)
    )
    return max(0.0, 1.0 - penalty), (
        f"ALL-CAPS {caps_share:.0%} of words, longest !?-run {max_run}, "
        f"{bang_rate:.2f} exclamations/sentence"
    )


def prose_quality(text: str) -> ProseQuality:
    """Score `text` for writing quality on a documented, bounded 0-100 scale.

    Args:
        text: Cleaned prose — run `fanfic_quality.strip_boilerplate` first, or author notes and
            disclaimers will be measured as if they were the story.

    Returns:
        A `ProseQuality` carrying the total plus every component's value, weight, and raw
        measurement, so a ranking is explainable rather than asserted.
    """
    measured = (
        ("sentence_rhythm", WEIGHT_SENTENCE_RHYTHM, sentence_rhythm(text)),
        ("dialogue_craft", WEIGHT_DIALOGUE_CRAFT, dialogue_craft(text)),
        ("vocabulary_richness", WEIGHT_VOCABULARY, vocabulary_richness(text)),
        ("interiority", WEIGHT_INTERIORITY, interiority(text)),
        ("paragraph_structure", WEIGHT_PARAGRAPHS, paragraph_structure(text)),
        ("punctuation_discipline", WEIGHT_PUNCTUATION, punctuation_discipline(text)),
    )
    components = tuple(
        ProseComponent(name=name, value=result[0], weight=weight, detail=result[1])
        for name, weight, result in measured
    )
    total = sum(c.value * c.weight for c in components) * 100.0
    return ProseQuality(
        score=round(max(0.0, min(100.0, total)), 2),
        components=components,
        word_count=len(text.split()),
    )

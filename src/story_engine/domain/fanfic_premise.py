"""Pure what-if premise detection and clustering.

Fan fiction is not an unordered pile of works — it clusters around **canon decision points**. The
harvested Dexter corpus contains "Set Free- A Dexter FanFiction", blurbed *"Dexter doesn't kill
Brian…"*, whose author notes *"there are a lot of Fan Fictions out there with Dexter letting Brian
live."* Two different phrasings ("doesn't kill Brian", "letting Brian live") name the *same*
divergence, and independent authors rewrite it independently. Grouping by premise turns the corpus
into "N human-authored branches off one canon decision point".

Detection is deliberately **lexical and deterministic** — no model, no embeddings, no dependency:

* The signal lives in a short, formulaic blurb, not in long prose. Fandom blurbs use a tiny set of
  conventional constructions ("If X lived", "X doesn't kill Y", "Y/n x Character", "A/B crossover"),
  which is exactly the regime where exact patterns beat similarity search.
* A premise key must be **stable across runs and reviewable in a diff**. An embedding cluster id is
  neither.
* Entities are captured *from the matched pattern position* (the capitalized token adjacent to the
  trigger), not by scanning for capitalized words, which in a title-cased title is pure noise.

Kept in its own module rather than appended to `fanfic_quality.py`: that file is the *admission*
policy (is this work in-fandom, is this text prose) and is already ~240 lines. Premise clustering is
a separate concern — it organizes works that have already been admitted.

Precedence, not union, decides the grouping key: a work that is both "Jack lived" and "years later"
belongs with the other Jack-lived branches, so the most specific canon divergence wins and the
remaining facets are retained in `tropes` for looser regrouping.
"""

import re

from story_engine.domain.models.fanfic import (
    BranchOption,
    BranchPoint,
    HarvestedStory,
    PremiseGroup,
    PremiseSignature,
    PremiseTrope,
    StoryRef,
)

# --- entity capture -----------------------------------------------------------------------------
# One or two capitalized tokens, captured only where a trigger word makes the position meaningful.
_NAME = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
_NEG = (
    r"(?:doesn'?t|does\s+not|didn'?t|did\s+not|never|won'?t|will\s+not|refuses\s+to"
    r"|couldn'?t\s+bring\s+himself\s+to|couldn'?t\s+bring\s+herself\s+to)"
)
_LETHAL = (
    r"(?:kill|kills|killing|murder|murders|murdering|shoot|shoots|stab|stabs|drown|drowns"
    r"|execute|executes|behead|beheads)"
)
# Sentence-initial capitals make these look like names; none of them ever is one.
_NOT_A_NAME = frozenset(
    {
        "the",
        "this",
        "that",
        "these",
        "those",
        "he",
        "she",
        "it",
        "they",
        "we",
        "you",
        "i",
        "his",
        "her",
        "their",
        "there",
        "then",
        "when",
        "where",
        "while",
        "if",
        "but",
        "and",
        "so",
        "most",
        "some",
        "many",
        "read",
        "in",
        "on",
        "at",
        "a",
        "an",
        "one",
        "two",
        "everyone",
        "nobody",
        "someone",
        "what",
        "who",
        "now",
        "after",
        "before",
        "instead",
        "however",
        "perhaps",
        "maybe",
    }
)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_WORD_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# --- survival / canon-divergence patterns ------------------------------------------------------
# Each entry is (compiled pattern, 1-based group holding the character who does NOT die).
# The unifying idea: "X doesn't kill Y", "X lets Y live", "if Y lived", and "Y survives" are four
# renderings of ONE canon decision point — Y's death — so they must produce the same key.
_SURVIVAL_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(rf"\b{_NAME}\s+{_NEG}\s+{_LETHAL}\s+{_NAME}\b"), 2),
    (
        re.compile(
            rf"\b(?:lets?|letting|allows?|allowing|spares?|sparing)\s+{_NAME}"
            r"\s+(?:live|survive|go|escape|walk\s+away)\b"
        ),
        1,
    ),
    (re.compile(rf"\b(?:spares?|spared|sparing)\s+{_NAME}\b"), 1),
    (
        re.compile(
            rf"\bif\s+{_NAME}\s+(?:lived|had\s+lived|survived|had\s+survived|lives|survives"
            r"|didn'?t\s+die|hadn'?t\s+died|never\s+died)\b"
        ),
        1,
    ),
    (
        re.compile(
            rf"\b{_NAME}\s+(?:lived|lives|survived|survives|stayed\s+alive|stays\s+alive"
            r"|is\s+alive|doesn'?t\s+die|didn'?t\s+die|never\s+died|is\s+not\s+dead)\b"
        ),
        1,
    ),
    (
        re.compile(
            rf"\b{_NAME}(?:\s+and\s+[A-Z][a-z]+)?\s*,?\s+"
            r"(?:two\s+of\s+the\s+few\s+|one\s+of\s+the\s+(?:few\s+|only\s+)?)?survivors?\s+of\b"
        ),
        1,
    ),
)
# "If <name> lived" also shows up as a bare tag: `ifjacklived` on the real Titanic corpus.
_SURVIVAL_TAG_RE = re.compile(r"^if([a-z]{3,20})(?:lived|survived|hadlived)$")
# "Jack wakes up 90 years after the Titanic sinks" — waking after a multi-year gap only makes sense
# if the character survived the canon event, so this counts as a survival branch (plus a time skip).
_WAKES_RE = re.compile(rf"\b{_NAME}\s+(?:wakes|woke|awakens|awoke)\s+up\b")
_TIME_GAP_RE = re.compile(
    r"\b\d+\s+years\s+(?:after|later)\b|\b(?:decades|centuries|years)\s+later\b"
)

# --- other premise facets -----------------------------------------------------------------------
_CROSSOVER_TITLE_RE = re.compile(
    r"([A-Za-z][A-Za-z' ]{2,40})\s*/\s*([A-Za-z][A-Za-z' ]{2,40}?)\s*fan\W*fiction\b",
    re.IGNORECASE,
)
_CROSSOVER_WORD_RE = re.compile(r"\bcross-?over\b", re.IGNORECASE)
_READER_INSERT_RES = (
    re.compile(r"\bx\s*reader\b", re.IGNORECASE),
    re.compile(r"\breader\s*x\b", re.IGNORECASE),
    re.compile(r"\by\s*/\s*n\b", re.IGNORECASE),
    re.compile(r"\breader\s*[-_]?insert\b", re.IGNORECASE),
)
_READER_TARGET_RES = (
    re.compile(r"([A-Za-z][A-Za-z' ]{2,30}?)\s*x\s*reader\b", re.IGNORECASE),
    re.compile(r"^([a-z]{3,25})x?reader$"),
)
# U+00D7 is written as a code point: as a literal it is indistinguishable from `x` (ruff RUF001).
_MULTIPLICATION_SIGN = chr(0x00D7)
_PAIRING_RE = re.compile(
    rf"\b([A-Z][a-z]{{2,}})\s*[x{_MULTIPLICATION_SIGN}]\s*([A-Z][a-z]{{2,}})\b",
)
_TRANSMIGRATION_RE = re.compile(
    r"\btransmigrat\w*\b|\breincarnat\w*\b|\bisekai\b|\btransported\s+(?:in)?to\b"
    r"|\bfound\s+(?:him|her|them)self\s+(?:transported|in\s+the\s+body)\b"
    r"|\bwakes\s+up\s+(?:as|in\s+the\s+body\s+of)\b|\bself[-\s]?insert\b",
    re.IGNORECASE,
)
_TIME_TRAVEL_RE = re.compile(
    r"\btime[-\s]?travel\w*\b|\bback\s+in\s+time\b|\bfrozen\b|\bcryo\w*\b"
    r"|\b\d+\s+years\s+(?:after|later)\b|\b(?:decades|centuries)\s+later\b",
    re.IGNORECASE,
)
_CONTINUATION_RE = re.compile(
    r"\blife\s+after\b|\bafter\s+the\s+(?:sinking|events|war|finale|show|series)\b"
    r"|\bgrow\s+old\b|\bsequel\b|\bpost[-\s]canon\b|\bwhat\s+happen(?:s|ed)\s+next\b",
    re.IGNORECASE,
)
_LOVE_TRIANGLE_RE = re.compile(r"\blove\s*triangle\b", re.IGNORECASE)
_FOUND_FAMILY_RE = re.compile(
    r"\badopts?\b|\badopted\b|\bevacuee\b|\btake\s+in\b|\bbecome\s+a\s+family\b"
    r"|\bhave\s+children\b|\bpregnan\w*\b|\bbaby\b|\bfoster\b",
    re.IGNORECASE,
)
_ORIGINAL_CHARACTER_RE = re.compile(
    r"\bo\.?c\.?s?\b|\boriginal\s+character\b|\+\s*original\b|\boriginal\s*\)",
    re.IGNORECASE,
)
_ALTERNATE_UNIVERSE_RE = re.compile(
    # `AU` stays case-sensitive: lowercased it collides with ordinary words.
    r"(?i:\balternate\s+universe\b|\bmodern\s+au\b|\bwhat\s+if\b)|\bAU\b",
)
_CHARACTER_DEATH_RE = re.compile(
    r"\bmajor\s+character\s+death\b|\bdeath\s*fic\b|\bcharacter\s+death\b",
    re.IGNORECASE,
)

# Most specific canon divergence first. The FIRST trope to fire owns the grouping key; the rest are
# retained on the signature. Without this ordering a work would key on an incidental facet
# ("alternate universe") instead of the decision point that actually defines it.
_TROPE_PRECEDENCE: tuple[PremiseTrope, ...] = (
    PremiseTrope.CHARACTER_SURVIVES,
    PremiseTrope.TRANSMIGRATION,
    PremiseTrope.CROSSOVER,
    PremiseTrope.READER_INSERT,
    PremiseTrope.PAIRING,
    PremiseTrope.TIME_DISPLACEMENT,
    PremiseTrope.CONTINUATION,
    PremiseTrope.FOUND_FAMILY,
    PremiseTrope.LOVE_TRIANGLE,
    PremiseTrope.ORIGINAL_CHARACTER,
    PremiseTrope.CHARACTER_DEATH,
    PremiseTrope.ALTERNATE_UNIVERSE,
)

UNCLASSIFIED_KEY = "unclassified"
"""Key for works whose blurb states no detectable premise. Kept as an explicit bucket rather than
dropped, so a thin classified set is visible instead of silently implied."""


def entity_slug(value: str) -> str:
    """Return a stable, comparable slug for a character or franchise name."""
    words = _WORD_RE.findall(value.lower())
    return "-".join(words)


def _is_name(value: str) -> bool:
    """Reject sentence-initial function words that a capitalization rule mistakes for names."""
    words = _WORD_RE.findall(value.lower())
    return bool(words) and not any(word in _NOT_A_NAME for word in words)


def _clip(text: str, limit: int = 120) -> str:
    """Trim a matched snippet down to an auditable one-liner."""
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 1] + "…"


class _Detection:
    """Mutable accumulator for one work's fired tropes — internal, never leaves this module."""

    def __init__(self) -> None:
        self.tropes: dict[PremiseTrope, tuple[str, ...]] = {}
        self.evidence: list[str] = []

    def add(
        self, trope: PremiseTrope, *, entities: tuple[str, ...] = (), evidence: str = ""
    ) -> None:
        """Record a trope, merging entities so the first (most specific) match keeps priority."""
        existing = self.tropes.get(trope, ())
        merged = existing + tuple(e for e in entities if e and e not in existing)
        self.tropes[trope] = merged
        snippet = _clip(evidence)
        if snippet and snippet not in self.evidence:
            self.evidence.append(snippet)


def _detect_survival(detection: _Detection, text: str, tags: tuple[str, ...]) -> None:
    """Find the character whose canon death the work undoes."""
    for pattern, group in _SURVIVAL_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(group)
            if _is_name(name):
                detection.add(
                    PremiseTrope.CHARACTER_SURVIVES,
                    entities=(entity_slug(name),),
                    evidence=match.group(0),
                )
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if not _TIME_GAP_RE.search(sentence):
            continue
        wakes = _WAKES_RE.search(sentence)
        if wakes is not None and _is_name(wakes.group(1)):
            detection.add(
                PremiseTrope.CHARACTER_SURVIVES,
                entities=(entity_slug(wakes.group(1)),),
                evidence=sentence,
            )
    for tag in tags:
        tag_match = _SURVIVAL_TAG_RE.match(entity_slug(tag).replace("-", ""))
        if tag_match is not None:
            detection.add(
                PremiseTrope.CHARACTER_SURVIVES,
                entities=(tag_match.group(1),),
                evidence=f"tag:{tag}",
            )


def _detect_crossover(
    detection: _Detection, title: str, text: str, fandom: str
) -> None:
    """Find the *other* franchise a crossover pulls in."""
    own = entity_slug(fandom)
    for match in _CROSSOVER_TITLE_RE.finditer(title):
        others = [
            entity_slug(part)
            for part in (match.group(1), match.group(2))
            if entity_slug(part) and entity_slug(part) != own
        ]
        if others:
            detection.add(
                PremiseTrope.CROSSOVER,
                entities=tuple(others),
                evidence=match.group(0),
            )
    crossover_word = _CROSSOVER_WORD_RE.search(text)
    if crossover_word is not None:
        detection.add(PremiseTrope.CROSSOVER, evidence=crossover_word.group(0))


def _detect_reader_insert(
    detection: _Detection, text: str, tags: tuple[str, ...]
) -> None:
    """Detect a reader-insert (`Y/n`, `Character x Reader`) and who the reader is paired with."""
    if not any(pattern.search(text) for pattern in _READER_INSERT_RES) and not any(
        entity_slug(tag).replace("-", "").endswith("xreader") for tag in tags
    ):
        return
    entities: list[str] = []
    target = _READER_TARGET_RES[0].search(text)
    if target is not None and _is_name(target.group(1)):
        entities.append(entity_slug(target.group(1)))
    for tag in tags:
        flat = entity_slug(tag).replace("-", "")
        if flat.endswith("xreader"):
            name = flat[: -len("xreader")]
            if name and name not in {"charecter", "character"}:
                entities.append(name)
    detection.add(
        PremiseTrope.READER_INSERT,
        entities=tuple(dict.fromkeys(entities)),
        evidence="reader-insert marker",
    )


def _detect_pairing(detection: _Detection, title: str) -> None:
    """Detect an explicit `A x B` ship in the title."""
    match = _PAIRING_RE.search(title)
    if match is None:
        return
    left, right = match.group(1), match.group(2)
    if left.lower() == "reader" or right.lower() == "reader":
        return
    if not (_is_name(left) and _is_name(right)):
        return
    detection.add(
        PremiseTrope.PAIRING,
        entities=tuple(sorted((entity_slug(left), entity_slug(right)))),
        evidence=match.group(0),
    )


def _detect_simple_tropes(detection: _Detection, text: str) -> None:
    """Fire the facets that need no entity — a single regex each."""
    simple: tuple[tuple[PremiseTrope, re.Pattern[str]], ...] = (
        (PremiseTrope.TRANSMIGRATION, _TRANSMIGRATION_RE),
        (PremiseTrope.TIME_DISPLACEMENT, _TIME_TRAVEL_RE),
        (PremiseTrope.CONTINUATION, _CONTINUATION_RE),
        (PremiseTrope.FOUND_FAMILY, _FOUND_FAMILY_RE),
        (PremiseTrope.LOVE_TRIANGLE, _LOVE_TRIANGLE_RE),
        (PremiseTrope.ORIGINAL_CHARACTER, _ORIGINAL_CHARACTER_RE),
        (PremiseTrope.CHARACTER_DEATH, _CHARACTER_DEATH_RE),
        (PremiseTrope.ALTERNATE_UNIVERSE, _ALTERNATE_UNIVERSE_RE),
    )
    for trope, pattern in simple:
        match = pattern.search(text)
        if match is not None:
            detection.add(trope, evidence=match.group(0))


_LABELS: dict[PremiseTrope, str] = {
    PremiseTrope.CHARACTER_SURVIVES: "{entities} survives the canon death",
    PremiseTrope.TRANSMIGRATION: "Outsider transmigrates into the canon world",
    PremiseTrope.CROSSOVER: "Crossover with {entities}",
    PremiseTrope.READER_INSERT: "Reader-insert romance with {entities}",
    PremiseTrope.PAIRING: "Ship: {entities}",
    PremiseTrope.TIME_DISPLACEMENT: "Time displacement / years after canon",
    PremiseTrope.CONTINUATION: "Continuation beyond the canon ending",
    PremiseTrope.FOUND_FAMILY: "Found family / children after canon",
    PremiseTrope.LOVE_TRIANGLE: "Love triangle",
    PremiseTrope.ORIGINAL_CHARACTER: "Original character inserted into canon",
    PremiseTrope.CHARACTER_DEATH: "Major character death added",
    PremiseTrope.ALTERNATE_UNIVERSE: "Unspecified alternate universe",
}


# --- branch-oracle vocabulary -------------------------------------------------------------------
# The Branch Oracle (project_context.md §5.2) needs a PAIR per premise: the canon decision point
# diverged from, and the alternate path taken. Both are synthesized from this taxonomy — never
# copied from a work's blurb, because fan fiction supplies *what the options are* and is not
# reproduced. Every divergence below is an INTENTIONAL divergence (§5.5), never a contradiction.
_DECISION_POINTS: dict[PremiseTrope, str] = {
    PremiseTrope.CHARACTER_SURVIVES: "Whether {entities} dies, as canon has it",
    PremiseTrope.TRANSMIGRATION: "Whether an outsider enters the story's world at all",
    PremiseTrope.CROSSOVER: "Whether the story stays inside its own world",
    PremiseTrope.READER_INSERT: "Whether a newcomer enters {entities}'s life",
    PremiseTrope.PAIRING: "Whether {entities} become involved",
    PremiseTrope.TIME_DISPLACEMENT: "Whether the story stays in its canon timeframe",
    PremiseTrope.CONTINUATION: "Whether the story ends where canon ends",
    PremiseTrope.FOUND_FAMILY: "Whether the characters take on a family",
    PremiseTrope.LOVE_TRIANGLE: "Whether a rival claim on the romance appears",
    PremiseTrope.ORIGINAL_CHARACTER: "Whether an outside character joins the cast",
    PremiseTrope.CHARACTER_DEATH: "Whether a character canon spares is killed",
    PremiseTrope.ALTERNATE_UNIVERSE: "Whether the story's premises hold",
}
_CANON_OPTIONS: dict[PremiseTrope, str] = {
    PremiseTrope.CHARACTER_SURVIVES: "Let canon stand — {entities} dies",
    PremiseTrope.TRANSMIGRATION: "Let canon stand — no outsider arrives",
    PremiseTrope.CROSSOVER: "Let canon stand — the world stays self-contained",
    PremiseTrope.READER_INSERT: "Let canon stand — no newcomer arrives",
    PremiseTrope.PAIRING: "Let canon stand — the pairing does not happen",
    PremiseTrope.TIME_DISPLACEMENT: "Let canon stand — the timeframe holds",
    PremiseTrope.CONTINUATION: "Let canon stand — the story ends where it ends",
    PremiseTrope.FOUND_FAMILY: "Let canon stand — no family is taken on",
    PremiseTrope.LOVE_TRIANGLE: "Let canon stand — no rival claim appears",
    PremiseTrope.ORIGINAL_CHARACTER: "Let canon stand — the cast is unchanged",
    PremiseTrope.CHARACTER_DEATH: "Let canon stand — the character lives",
    PremiseTrope.ALTERNATE_UNIVERSE: "Let canon stand — the premises hold",
}
_ALTERNATE_PATHS: dict[PremiseTrope, str] = {
    PremiseTrope.CHARACTER_SURVIVES: "Spare {entities} — {entities} lives",
    PremiseTrope.TRANSMIGRATION: "An outsider wakes up inside the story",
    PremiseTrope.CROSSOVER: "Pull in {entities} and cross the two worlds",
    PremiseTrope.READER_INSERT: "A newcomer becomes close to {entities}",
    PremiseTrope.PAIRING: "Let {entities} become involved",
    PremiseTrope.TIME_DISPLACEMENT: "Displace the story out of its canon timeframe",
    PremiseTrope.CONTINUATION: "Carry the story past the canon ending",
    PremiseTrope.FOUND_FAMILY: "Have the characters take on a family",
    PremiseTrope.LOVE_TRIANGLE: "Introduce a rival claim on the romance",
    PremiseTrope.ORIGINAL_CHARACTER: "Add an outside character to the cast",
    PremiseTrope.CHARACTER_DEATH: "Kill a character canon spares",
    PremiseTrope.ALTERNATE_UNIVERSE: "Change the story's premises outright",
}
# Appended to an alternate path when a *secondary* trope also fired, which is how one decision point
# yields several distinct options instead of one (e.g. "Jack survives" vs "Jack survives, displaced
# ninety years later"). Capped so an option stays readable as a player-facing choice.
_MODIFIER_CLAUSES: dict[PremiseTrope, str] = {
    PremiseTrope.TIME_DISPLACEMENT: "displaced in time",
    PremiseTrope.CONTINUATION: "carrying on past the canon ending",
    PremiseTrope.FOUND_FAMILY: "building a family",
    PremiseTrope.PAIRING: "as a couple",
    PremiseTrope.LOVE_TRIANGLE: "against a rival claim",
    PremiseTrope.CROSSOVER: "across another world",
    PremiseTrope.TRANSMIGRATION: "with an outsider present",
    PremiseTrope.ORIGINAL_CHARACTER: "alongside a new character",
    PremiseTrope.READER_INSERT: "with a newcomer involved",
    PremiseTrope.CHARACTER_DEATH: "at another character's cost",
    PremiseTrope.ALTERNATE_UNIVERSE: "in a reworked setting",
    PremiseTrope.CHARACTER_SURVIVES: "with a canon death undone",
}
_MAX_MODIFIERS = 2


def _fill(template: str, entities: tuple[str, ...]) -> str:
    """Render a taxonomy template, degrading gracefully when no entity was captured."""
    if "{entities}" not in template:
        return template
    if entities:
        return template.format(entities=_titleize(entities))
    return (
        template.replace("{entities} ", "")
        .replace(" {entities}", "")
        .replace("{entities}", "the character")
        .replace("'s life", " someone's life")
    )


def _titleize(entities: tuple[str, ...]) -> str:
    """Render entity slugs back into a readable list ("jack" -> "Jack")."""
    return " & ".join(
        " ".join(word.capitalize() for word in slug.split("-")) for slug in entities
    )


def _render(trope: PremiseTrope, entities: tuple[str, ...]) -> tuple[str, str]:
    """Return the `(key, label)` pair for the dominant trope and its entities."""
    key = str(trope) if not entities else f"{trope}:{'+'.join(sorted(entities))}"
    template = _LABELS[trope]
    if "{entities}" not in template:
        return key, template
    if not entities:
        return key, template.replace("{entities} ", "").replace(" with {entities}", "")
    return key, template.format(entities=_titleize(entities))


def premise_signature(
    title: str,
    description: str,
    tags: tuple[str, ...] = (),
    *,
    fandom: str = "",
) -> PremiseSignature:
    """Derive a work's premise signature from its blurb, title, and tags.

    Args:
        title: The work's title, as published (often title-cased).
        description: The blurb — the richest premise signal, and usually sentence-cased, which is
            what makes adjacent-capitalization entity capture reliable.
        tags: Host tags; they carry premises the blurb omits (`ifjacklived`, `dexterxreader`).
        fandom: The fandom being harvested. Used only to drop the fandom's own name from a
            crossover pair, so "Descendants/Titanic" keys on `descendants`, not on both.

    Returns:
        A `PremiseSignature` whose `key` groups works branching off the same canon decision point.
        Works with no detectable premise get `key == UNCLASSIFIED_KEY` rather than being dropped.
    """
    text = f"{title}. {description}"
    detection = _Detection()
    _detect_survival(detection, text, tags)
    _detect_crossover(detection, title, text, fandom)
    _detect_reader_insert(detection, text, tags)
    _detect_pairing(detection, title)
    _detect_simple_tropes(detection, text)

    ordered = tuple(t for t in _TROPE_PRECEDENCE if t in detection.tropes)
    if not ordered:
        return PremiseSignature(
            key=UNCLASSIFIED_KEY,
            label="No premise detected in the blurb",
            alternate_path="UNVERIFIED — no divergence detectable from the blurb",
        )
    dominant = ordered[0]
    entities = detection.tropes[dominant]
    if dominant is PremiseTrope.CHARACTER_SURVIVES:
        # A canon decision point is ONE character's death. A blurb naming several survivors
        # ("Jack and Rose, two of the few survivors") must still key on the first — otherwise
        # `survives:jack` and `survives:jack+rose` split branches off the same decision.
        entities = entities[:1]
    key, label = _render(dominant, entities)
    return PremiseSignature(
        key=key,
        label=label,
        tropes=ordered,
        focal_entities=entities,
        evidence=tuple(detection.evidence),
        decision_point=_fill(_DECISION_POINTS[dominant], entities),
        alternate_path=_alternate_path(dominant, entities, ordered[1:]),
    )


def _alternate_path(
    dominant: PremiseTrope,
    entities: tuple[str, ...],
    secondary: tuple[PremiseTrope, ...],
) -> str:
    """Render the path a work takes instead of canon, qualified by its secondary tropes."""
    base = _fill(_ALTERNATE_PATHS[dominant], entities)
    clauses = [_MODIFIER_CLAUSES[t] for t in secondary if t in _MODIFIER_CLAUSES]
    if not clauses:
        return base
    return f"{base}, {', '.join(clauses[:_MAX_MODIFIERS])}"


def premise_signature_for(ref: StoryRef, *, fandom: str = "") -> PremiseSignature:
    """Derive a premise signature from a `StoryRef`'s metadata."""
    return premise_signature(
        ref.title, ref.description, ref.tags, fandom=fandom or ref.title
    )


def group_by_premise(stories: tuple[HarvestedStory, ...]) -> tuple[PremiseGroup, ...]:
    """Group works by `premise.key`, largest group first.

    Works whose `premise` was never computed are skipped rather than lumped into the unclassified
    bucket — "not measured" and "measured, nothing found" are different facts.

    Returns:
        Groups ordered by descending size then key, so the biggest shared canon divergence — the
        interesting one — is first.
    """
    buckets: dict[str, list[HarvestedStory]] = {}
    for story in stories:
        if story.premise is None:
            continue
        buckets.setdefault(story.premise.key, []).append(story)
    groups = [
        PremiseGroup(
            key=key,
            label=members[0].premise.label if members[0].premise else key,
            tropes=members[0].premise.tropes if members[0].premise else (),
            members=tuple(s.handle for s in members),
            member_titles=tuple(s.ref.title for s in members),
        )
        for key, members in buckets.items()
    ]
    return tuple(sorted(groups, key=lambda g: (-g.size, g.key)))


MIN_BRANCH_OPTIONS = 2
MAX_BRANCH_OPTIONS = 4
"""project_context.md §4 step 3: each decision point presents 2-4 discrete choices. The canon-stands
option always counts as one, so a single detected premise already yields a legal branch point."""


def branch_points(
    stories: tuple[HarvestedStory, ...], *, max_options: int = MAX_BRANCH_OPTIONS
) -> tuple[BranchPoint, ...]:
    """Assemble Branch Oracle decision points from harvested works.

    One `BranchPoint` per premise key — i.e. per canon decision point. Its options are the
    canon-stands baseline plus every *distinct* alternate path observed: two works that both spare
    the same character but qualify it differently ("and grow old together" vs "ninety years later")
    become two separate options, which is how one decision point reaches 3-4 choices from real data.

    Args:
        stories: Works whose `premise` has been computed. Works without one, and works whose
            premise is `UNCLASSIFIED_KEY`, are skipped — an undetectable premise is not a branch.
        max_options: Hard ceiling on options per decision point, canon included. Alternates beyond
            the ceiling are dropped lowest-support-first, so the best-evidenced paths survive.

    Returns:
        Decision points ordered by descending supporting-work count, then key.

    Raises:
        ValueError: If `max_options` is below `MIN_BRANCH_OPTIONS` — a decision point with fewer
            than two choices is not a choice.
    """
    if max_options < MIN_BRANCH_OPTIONS:
        raise ValueError(
            f"max_options must be >= {MIN_BRANCH_OPTIONS}, got {max_options}"
        )
    buckets: dict[str, list[tuple[HarvestedStory, PremiseSignature]]] = {}
    for story in stories:
        premise = story.premise
        if premise is None or premise.key == UNCLASSIFIED_KEY or not premise.tropes:
            continue
        buckets.setdefault(premise.key, []).append((story, premise))

    points: list[BranchPoint] = []
    for key, members in buckets.items():
        head = members[0][1]
        by_path: dict[str, list[tuple[HarvestedStory, PremiseSignature]]] = {}
        for pair in members:
            by_path.setdefault(pair[1].alternate_path, []).append(pair)
        alternates = [
            BranchOption(
                label=path,
                detail=f"Taken by {len(group)} harvested work(s).",
                tropes=group[0][1].tropes,
                support=len(group),
                sources=tuple(story.handle for story, _ in group),
                source_titles=tuple(story.ref.title for story, _ in group),
            )
            for path, group in by_path.items()
        ]
        alternates.sort(key=lambda o: (-o.support, o.label))
        canon = BranchOption(
            label=_fill(_CANON_OPTIONS[head.tropes[0]], head.focal_entities),
            detail="The canon baseline. Choosing it is not a divergence.",
            is_canon=True,
        )
        points.append(
            BranchPoint(
                key=key,
                decision_point=head.decision_point or head.label,
                tropes=head.tropes,
                focal_entities=head.focal_entities,
                options=(canon, *alternates[: max_options - 1]),
            )
        )
    return tuple(sorted(points, key=lambda p: (-p.support, p.key)))

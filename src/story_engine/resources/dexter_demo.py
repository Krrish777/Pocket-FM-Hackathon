"""The rehearsed demo, as data: the cast, the secret, and the branches offered at each turn.

Everything here is anchored to *Darkly Dreaming Dexter* by character offset rather than by pasted
text. The seeding service reads the novel, slices those offsets, and uses the result as the quote —
so a citation cannot drift from its source through a transcription slip, and a receipt shown on
stage is the book's own words.

Each anchor carries a `must_contain` word. If the PDF is re-ingested and the offsets move, seeding
fails loudly on the anchor instead of silently citing the wrong paragraph — the failure mode that
matters, because a wrong citation still *looks* like a citation.

The cast is the five from `project_context.md` §6.3. Their **novel** names are used, not the screen
ones: the wiki index (FANFIC-05) established that three of the five differ, and our canon is the
novels (§6.1).
"""

from typing import NamedTuple

SOURCE_ID = "darkly-dreaming-dexter"
FORK_ID = "canon"

DEXTER = "dexter"
DEBORAH = "deborah"
DOAKES = "doakes"
LAGUERTA = "laguerta"
RITA = "rita"

CAST: dict[str, str] = {
    DEXTER: "Dexter Morgan",
    DEBORAH: "Deborah Morgan",
    DOAKES: "Sergeant Doakes",
    LAGUERTA: "Migdia LaGuerta",
    RITA: "Rita Bennett",
}
"""Novel names. Screen canon calls them Debra, James Doakes and Maria LaGuerta; using those here
would cite the novels for claims the novels never made (`project_context.md` §6.4 / OD-2)."""


class Anchor(NamedTuple):
    """A claim, and the exact stretch of novel that supports it."""

    fact_id: str
    subject_id: str
    predicate: str
    object_literal: str
    chapter: int
    char_start: int
    char_end: int
    must_contain: str
    secret: bool
    knowers: tuple[str, ...]
    revealed_at: int | None


THE_SECRET = "f-dark-passenger"

ANCHORS: tuple[Anchor, ...] = (
    Anchor(
        fact_id=THE_SECRET,
        subject_id=DEXTER,
        predicate="hunts_with",
        object_literal="the Dark Passenger",
        chapter=1,
        char_start=1023,
        char_end=1232,
        must_contain="Dark Passenger",
        # The engine's whole reason for existing: true from chapter 1, known to Dexter alone, and
        # never told to the audience. Everything the demo proves hangs off this one row.
        secret=True,
        knowers=(DEXTER,),
        revealed_at=None,
    ),
    Anchor(
        fact_id="f-harry-code",
        subject_id=DEXTER,
        predicate="was_taught_by",
        object_literal="Harry, who made the rules careful and exact",
        chapter=1,
        char_start=1824,
        char_end=2029,
        must_contain="Harry",
        secret=True,
        knowers=(DEXTER,),
        revealed_at=None,
    ),
    Anchor(
        fact_id="f-deborah-sister",
        subject_id=DEBORAH,
        predicate="is_foster_sister_of",
        object_literal="Dexter, and a cop like her father",
        chapter=2,
        char_start=3433,
        char_end=3640,
        must_contain="Deborah Morgan",
        # Public: everyone in the story knows who Deborah is, and so does the reader.
        secret=False,
        knowers=(),
        revealed_at=2,
    ),
    Anchor(
        fact_id="f-rita",
        subject_id=RITA,
        predicate="is_involved_with",
        object_literal="Dexter, and is as badly damaged as he is",
        chapter=6,
        char_start=335,
        char_end=539,
        must_contain="Rita",
        secret=False,
        knowers=(),
        revealed_at=6,
    ),
    Anchor(
        fact_id="f-doakes-hostile",
        subject_id=DOAKES,
        predicate="distrusts",
        object_literal="Dexter, openly and from the start",
        chapter=8,
        char_start=650,
        char_end=856,
        must_contain="Doakes",
        secret=False,
        knowers=(),
        revealed_at=8,
    ),
)


class Branch(NamedTuple):
    """One offered option and what taking it does to the world."""

    id: str
    label: str
    source_work_id: str | None
    present: tuple[str, ...]
    predicate: str
    object_literal: str
    secret: bool
    discloses: tuple[str, ...]


BRANCHES: dict[int, tuple[Branch, ...]] = {
    1: (
        Branch(
            "t1:hunt",
            "Finish what you started with the priest tonight",
            None,
            (DEXTER,),
            "acted_on",
            "the priest, alone, the Harry way",
            True,
            (),
        ),
        Branch(
            "t1:answer-deb",
            "Answer Deborah's message before anything else",
            "wattpad:864850",
            (DEXTER, DEBORAH),
            "chose",
            "Deborah's call over the night's work",
            False,
            (),
        ),
    ),
    2: (
        Branch(
            "t2:take-deb",
            "Take Deborah to the scene with you",
            "wattpad:864850",
            (DEXTER, DEBORAH),
            "brought",
            "Deborah into the investigation",
            False,
            (),
        ),
        Branch(
            "t2:shut-out",
            "Keep Deborah out of it entirely",
            None,
            (DEXTER,),
            "kept",
            "Deborah at arm's length",
            True,
            (),
        ),
    ),
    3: (
        # THE pivotal branch. Taking it puts Doakes in the room when the Passenger surfaces —
        # which is the moment the whole demo is built to show.
        Branch(
            "t3:confront-doakes",
            "Let Doakes follow you, and let him see",
            "wattpad:390229723",
            (DEXTER, DOAKES),
            "was_seen_by",
            "Doakes, in the middle of it",
            True,
            (THE_SECRET,),
        ),
        Branch(
            "t3:lose-doakes",
            "Lose Doakes in traffic and finish clean",
            None,
            (DEXTER,),
            "evaded",
            "Doakes for another night",
            True,
            (),
        ),
    ),
    4: (
        Branch(
            "t4:rita-dinner",
            "Keep the dinner with Rita as if nothing happened",
            None,
            (DEXTER, RITA),
            "performed",
            "an ordinary evening with Rita",
            False,
            (),
        ),
        Branch(
            "t4:laguerta",
            "Go to LaGuerta with a version of the truth",
            "wattpad:390229723",
            (DEXTER, LAGUERTA),
            "told",
            "LaGuerta a shaped version of the night",
            False,
            (),
        ),
    ),
    5: (
        Branch(
            "t5:finish",
            "Finish it on your own terms",
            None,
            (DEXTER,),
            "closed",
            "the account himself",
            True,
            (),
        ),
        Branch(
            "t5:confess",
            "Let Deborah find out what you are",
            "wattpad:864850",
            (DEXTER, DEBORAH),
            "let",
            "Deborah see what he is",
            True,
            (THE_SECRET,),
        ),
    ),
    6: (),
}
"""Five decision points, then the run closes. Options carrying a `source_work_id` came from the
harvested corpus; `None` marks one authored to complete the rehearsed path, so the distinction
stays auditable (`project_context.md` §5.2)."""

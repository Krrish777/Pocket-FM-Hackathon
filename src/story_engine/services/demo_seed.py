"""Seed the demo fork: read the novel, slice the anchored passages, write them as canon.

The quotes are *sliced from the PDF at seed time*, never pasted into source. Two reasons, and the
second is the important one:

1. A pasted quote can drift from the text it claims to come from through a single transcription
   slip, and a drifted citation still looks exactly like a good one.
2. Slicing makes the receipt self-proving. If `Provenance.quote` came out of the same offsets the
   citation displays, then showing the receipt and re-reading the book cannot disagree.

Every anchor carries a `must_contain` sentinel, checked against the slice. Re-ingesting the PDF with
different chunking or a different reader will move offsets; when that happens this fails loudly at
seed time rather than quietly citing the wrong paragraph.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from story_engine.domain.enums import AssertionMode, FactStatus, PresenceGrade
from story_engine.domain.models.canon import Awareness, Fact, Presence, Provenance
from story_engine.domain.models.play import ChoiceOption, Consequence
from story_engine.ports.canon_store import CanonStorePort
from story_engine.ports.document_source import DocumentSourcePort
from story_engine.resources.dexter_demo import (
    ANCHORS,
    BRANCHES,
    FORK_ID,
    SOURCE_ID,
    Anchor,
)
from story_engine.shared.errors import StoryEngineError

logger = logging.getLogger(__name__)

DEFAULT_NOVEL = Path("data/external/Darkly-Dreaming-Dexter-1.pdf")


class DemoSeedError(StoryEngineError):
    """The demo could not be seeded from the source novel."""

    code = "demo_seed_failed"


def seed_canon(
    store: CanonStorePort, reader: DocumentSourcePort, novel: Path = DEFAULT_NOVEL
) -> tuple[Fact, ...]:
    """Write the anchored canon facts into `store`, quoting the novel verbatim.

    Raises:
        DemoSeedError: The novel is missing a chapter an anchor points into, an anchor's offsets
            fall outside that chapter, or the sliced text does not contain its sentinel — all of
            which mean the citation would be wrong rather than merely absent.
    """
    chapters = {chapter.index: chapter.text for chapter in reader.read_chapters(novel)}
    seeded: list[Fact] = []

    for anchor in ANCHORS:
        quote = _slice(chapters, anchor)
        fact = _fact_from(anchor, quote)
        store.append(fact)
        seeded.append(fact)
        logger.info(
            "seeded %s from ch%d [%d:%d]",
            anchor.fact_id,
            anchor.chapter,
            anchor.char_start,
            anchor.char_end,
        )

    return tuple(seeded)


def _slice(chapters: dict[int, str], anchor: Anchor) -> str:
    """Pull the anchored passage out of the novel, refusing anything that has drifted."""
    text = chapters.get(anchor.chapter)
    if text is None:
        raise DemoSeedError(
            f"{anchor.fact_id}: the novel has no chapter {anchor.chapter} "
            f"(found {len(chapters)} chapters)"
        )
    if anchor.char_end > len(text):
        raise DemoSeedError(
            f"{anchor.fact_id}: offsets [{anchor.char_start}:{anchor.char_end}] run past the end "
            f"of chapter {anchor.chapter}, which is {len(text)} characters"
        )

    quote = text[anchor.char_start : anchor.char_end].strip()
    if anchor.must_contain.lower() not in quote.lower():
        raise DemoSeedError(
            f"{anchor.fact_id}: expected {anchor.must_contain!r} in the passage at ch"
            f"{anchor.chapter} [{anchor.char_start}:{anchor.char_end}] but found {quote[:80]!r}. "
            f"The offsets have drifted — re-anchor them rather than citing the wrong passage."
        )
    return quote


def _fact_from(anchor: Anchor, quote: str) -> Fact:
    """Build the canon fact, tracked only when the claim is genuinely a secret."""
    return Fact(
        id=anchor.fact_id,
        fork_id=FORK_ID,
        subject_id=anchor.subject_id,
        predicate=anchor.predicate,
        object_literal=anchor.object_literal,
        valid_from=anchor.chapter,
        revealed_at=anchor.revealed_at,
        assertion_mode=AssertionMode.NARRATED,
        knower_scope=(
            tuple(
                Awareness(knower=knower, learned_at=anchor.chapter)
                for knower in sorted(anchor.knowers)
            )
            if anchor.secret
            else None
        ),
        provenance=Provenance(
            source_id=SOURCE_ID,
            chapter=anchor.chapter,
            char_start=anchor.char_start,
            char_end=anchor.char_start + len(quote),
            quote=quote,
        ),
        confidence=1.0,
        tier=0,  # the novel is base canon; a player's branch is tier 1 and never outranks it
        status=FactStatus.ACTIVE,
        recorded_at=datetime.now(UTC),
    )


def demo_branches() -> dict[int, tuple[ChoiceOption, ...]]:
    """Build the oracle's options from the authored branch table."""
    return {
        chapter: tuple(
            ChoiceOption(
                id=branch.id,
                label=branch.label,
                source_work_id=branch.source_work_id,
                consequence=Consequence(
                    subject_id="dexter",
                    predicate=branch.predicate,
                    object_literal=branch.object_literal,
                    roster=tuple(
                        Presence(entity_id=entity, grade=PresenceGrade.ACTIVE)
                        for entity in branch.present
                    ),
                    secret=branch.secret,
                    discloses=branch.discloses,
                ),
            )
            for branch in branches
        )
        for chapter, branches in BRANCHES.items()
    }

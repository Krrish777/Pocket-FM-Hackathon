"""Agent working memory — layer 3 of the hybrid knowledge base.

The bounded slice of canon one session actually holds, as distinct from everything that is
true. Assembly is DETERMINISTIC and the store's guard is the only path in, so no caller can
construct a packet containing a fact the audience has not earned.
"""

from collections.abc import Sequence

from story_engine.domain.base import DomainModel
from story_engine.domain.graph import LoreGraph
from story_engine.domain.models import ChapterIndex, Fact
from story_engine.ports.canon_store import CanonStorePort

DEFAULT_BUDGET = 40


class MemoryPacket(DomainModel):
    """What one session may see, plus the count of what it may not."""

    knower: str
    chapter: ChapterIndex
    facts: tuple[Fact, ...]
    graph: LoreGraph
    withheld_count: int


class WorkingMemory:
    """Assembles a bounded, guarded memory packet for a single session."""

    def __init__(self, store: CanonStorePort) -> None:
        self._store = store

    def assemble(
        self,
        fork_id: str,
        knower: str,
        chapter: ChapterIndex,
        focus_entities: Sequence[str] = (),
        budget: int = DEFAULT_BUDGET,
    ) -> MemoryPacket:
        """Build the packet for `knower` at `chapter`.

        Facts about the scene's own entities are kept first: under a budget, evicting the
        entities the scene is ABOUT in favour of unrelated canon is the one failure that
        makes the packet useless.

        Raises:
            ValueError: `budget` is less than 1 — a zero-size packet is a silent failure
                that looks identical to "no relevant canon".
        """
        if budget < 1:
            raise ValueError("budget must be at least 1")

        # The guard is the ONLY way in: assemble exclusively from the port's guarded
        # queries, never from an unfiltered read the caller has to filter itself — a
        # second filtering path is a second chance to leak.
        visible = self._store.visible_to(fork_id, knower, chapter)
        withheld = self._store.withheld_from(fork_id, knower, chapter)

        # visible_to answers "may this be told" (spoiler guard); it now correctly
        # includes superseded-but-knowable facts. is_valid_at answers "is this true
        # NOW". A prompt needs both, or a packet could hand the model both a fact and
        # its replacement (e.g. "Kael loyal to Crown" AND "Kael loyal to rebels") as
        # simultaneously true.
        current = tuple(f for f in visible if f.is_valid_at(chapter))

        focus = set(focus_entities)
        # Stable sort on a boolean key: focus facts first, original order preserved within
        # each group, so the packet is reproducible across runs. A focus entity can appear
        # as either endpoint of a fact, so both are checked.
        ordered = sorted(
            current,
            key=lambda f: (
                not (
                    f.subject_id in focus
                    or (f.object_id is not None and f.object_id in focus)
                )
            ),
        )
        kept = tuple(ordered[:budget])

        return MemoryPacket(
            knower=knower,
            chapter=chapter,
            facts=kept,
            graph=LoreGraph.from_facts(kept, knower=knower, chapter=chapter),
            withheld_count=len(withheld),
        )

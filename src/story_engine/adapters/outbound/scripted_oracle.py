"""A `BranchOraclePort` backed by authored options, keyed by chapter.

The real oracle mines divergences out of the harvested fan-fiction corpus and binds them to canon
moments (T5 in `demo.md`, feature M4). That binding does not exist yet — our own EXT-1 contract
records that the harvester cannot cite a canon scene until the Kernel exposes a resolvable moment
id — so this adapter stands in behind the same port.

**It does not pretend to be the oracle.** Every option it serves carries whatever `source_work_id`
the author gave it, including `None`, so `ChoiceOption.is_canon_baseline` and any downstream audit
can still tell a mined divergence from an authored one. The moment the real oracle lands, it
replaces this class and nothing else moves.
"""

from collections.abc import Mapping, Sequence

from story_engine.domain.models.canon import ChapterIndex
from story_engine.domain.models.play import ChoiceOption


class ScriptedBranchOracle:
    """Serves pre-authored options per chapter. Implements `BranchOraclePort`."""

    def __init__(
        self, options_by_chapter: Mapping[ChapterIndex, Sequence[ChoiceOption]]
    ) -> None:
        self._by_chapter = {
            chapter: tuple(options) for chapter, options in options_by_chapter.items()
        }

    def options_at(
        self, *, fork_id: str, chapter: ChapterIndex, protagonist: str
    ) -> tuple[ChoiceOption, ...]:
        """Return the authored options for `chapter`, or none where coverage is thin.

        An unmapped chapter returns an empty tuple rather than raising, mirroring the real
        oracle's honest answer at a moment fan fiction never wrote (`project_context.md` OD-4).
        """
        return self._by_chapter.get(chapter, ())

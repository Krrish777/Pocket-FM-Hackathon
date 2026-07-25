"""The Branch Oracle port — where the options at a decision point come from.

`project_context.md` §5.2: fan fiction supplies *what the options are*, and is never quoted or
reproduced. An implementation therefore returns branch **structure** — a label and its consequence —
never source prose.
"""

from typing import Protocol

from story_engine.domain.models.canon import ChapterIndex
from story_engine.domain.models.play import ChoiceOption


class BranchOraclePort(Protocol):
    """Supplies the 2-4 discrete options offered at a point in the story."""

    def options_at(
        self, *, fork_id: str, chapter: ChapterIndex, protagonist: str
    ) -> tuple[ChoiceOption, ...]:
        """Return the options available to `protagonist` at `chapter`.

        Returns:
            Between 2 and 4 options, or an empty tuple when this moment has no mined divergence.
            An empty result is a legitimate answer, not an error: `project_context.md` OD-4 records
            that fan fiction clusters at famous decision points rather than spreading evenly, so
            callers must handle a thin moment rather than assume coverage everywhere.
        """
        ...

"""Corpus sink port — where a finished harvest is written.

Kept separate from `FanficSourcePort` so the knowledge-base integration (a different branch) can
supply its own sink without touching the harvesting pipeline.
"""

from typing import Protocol

from story_engine.domain.fanfic_premise import MAX_BRANCH_OPTIONS
from story_engine.domain.models.fanfic import HarvestedStory


class CorpusSinkPort(Protocol):
    """Persist harvested works."""

    def write(
        self,
        fandom: str,
        stories: tuple[HarvestedStory, ...],
        *,
        max_branch_options: int = MAX_BRANCH_OPTIONS,
    ) -> str:
        """Persist `stories` for `fandom` and return a human-readable location.

        `max_branch_options` must be threaded through rather than defaulted: a sink that recomputes
        branch points with its own ceiling emits an artifact contradicting what the caller was
        shown, and the artifact is what the knowledge base ingests.
        """
        ...

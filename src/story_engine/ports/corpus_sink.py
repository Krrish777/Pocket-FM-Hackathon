"""Corpus sink port — where a finished harvest is written.

Kept separate from `FanficSourcePort` so the knowledge-base integration (a different branch) can
supply its own sink without touching the harvesting pipeline.
"""

from typing import Protocol

from story_engine.domain.models.fanfic import HarvestedStory


class CorpusSinkPort(Protocol):
    """Persist harvested works."""

    def write(self, fandom: str, stories: tuple[HarvestedStory, ...]) -> str:
        """Persist `stories` for `fandom` and return a human-readable location."""
        ...

"""Episode-log repository port — the APPEND-ONLY episodic record.

Ordered, immutable log of what happened per episode (episodic memory). Never edit past entries;
only append. See research/memory-and-persistence.md.
"""

from typing import Protocol

from story_engine.domain.models import EpisodeSummary


class EpisodeLogRepositoryPort(Protocol):
    """Append and read episode summaries in order."""

    def append_summary(self, summary: EpisodeSummary) -> None:
        """Append one episode summary (append-only — never overwrite)."""
        ...

    def get_recent(self, series_id: str, n: int) -> tuple[EpisodeSummary, ...]:
        """Return the most recent `n` summaries, newest last."""
        ...

    def get_by_episode(
        self, series_id: str, episode_number: int
    ) -> EpisodeSummary | None: ...

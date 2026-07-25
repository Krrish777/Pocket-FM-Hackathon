"""In-memory repository adapters — dev/test defaults implementing the memory ports.

Swap for SQLite/persistent adapters later; these keep the scaffold runnable and are ideal fakes for
unit tests. No vendor SDKs here (none needed).
"""

from story_engine.domain.models import (
    CanonFact,
    CharacterState,
    EpisodeSummary,
    PlotThread,
    StoryBible,
)
from story_engine.shared.errors import StoryNotFoundError


class InMemoryStoryBibleRepository:
    """Dict-backed canonical store implementing `StoryBibleRepositoryPort`."""

    def __init__(self) -> None:
        self._bibles: dict[str, StoryBible] = {}

    def get_bible(self, series_id: str) -> StoryBible:
        bible = self._bibles.get(series_id)
        if bible is None:
            raise StoryNotFoundError(f"no bible for series {series_id!r}")
        return bible

    def put_bible(self, bible: StoryBible) -> None:
        """Seed/replace a whole bible (test/dev helper, not part of the port)."""
        self._bibles[bible.series_id] = bible

    def get_character(self, series_id: str, character_id: str) -> CharacterState | None:
        bible = self._bibles.get(series_id)
        if bible is None:
            return None
        return next(
            (c for c in bible.characters if c.character_id == character_id), None
        )

    def upsert_character(self, series_id: str, character: CharacterState) -> None:
        bible = self.get_bible(series_id)
        others = tuple(
            c for c in bible.characters if c.character_id != character.character_id
        )
        self._bibles[series_id] = bible.model_copy(
            update={"characters": (*others, character)}
        )

    def add_canon_fact(self, series_id: str, fact: CanonFact) -> None:
        bible = self.get_bible(series_id)
        self._bibles[series_id] = bible.model_copy(
            update={"world_rules": (*bible.world_rules, fact)}
        )

    def list_open_threads(self, series_id: str) -> tuple[PlotThread, ...]:
        bible = self.get_bible(series_id)
        return tuple(t for t in bible.open_threads if t.status.value == "open")

    def resolve_thread(self, series_id: str, thread_id: str, *, episode: int) -> None:
        bible = self.get_bible(series_id)
        updated = tuple(
            t.model_copy(update={"status": "resolved", "resolved_episode": episode})
            if t.thread_id == thread_id
            else t
            for t in bible.open_threads
        )
        self._bibles[series_id] = bible.model_copy(update={"open_threads": updated})


class InMemoryEpisodeLogRepository:
    """List-backed append-only log implementing `EpisodeLogRepositoryPort`."""

    def __init__(self) -> None:
        self._log: dict[str, list[EpisodeSummary]] = {}

    def append_summary(self, summary: EpisodeSummary) -> None:
        self._log.setdefault(summary.series_id, []).append(summary)

    def get_recent(self, series_id: str, n: int) -> tuple[EpisodeSummary, ...]:
        return tuple(self._log.get(series_id, [])[-n:])

    def get_by_episode(
        self, series_id: str, episode_number: int
    ) -> EpisodeSummary | None:
        entries = self._log.get(series_id, [])
        return next((e for e in entries if e.episode_number == episode_number), None)

"""Story-bible repository port — the CANONICAL, authoritative story state.

Deterministic, versioned CRUD over the series bible (semantic + entity memory). This is truth you
look up, not fuzzily retrieve — never let an LLM's auto-consolidation write here.
See research/memory-and-persistence.md.
"""

from typing import Protocol

from story_engine.domain.models import CanonFact, CharacterState, PlotThread, StoryBible


class StoryBibleRepositoryPort(Protocol):
    """Authoritative reads/writes of canonical series state."""

    def get_bible(self, series_id: str) -> StoryBible:
        """Return the full canonical bible for a series, or raise `StoryNotFoundError`."""
        ...

    def get_character(
        self, series_id: str, character_id: str
    ) -> CharacterState | None: ...

    def upsert_character(self, series_id: str, character: CharacterState) -> None: ...

    def add_canon_fact(self, series_id: str, fact: CanonFact) -> None: ...

    def list_open_threads(self, series_id: str) -> tuple[PlotThread, ...]: ...

    def resolve_thread(
        self, series_id: str, thread_id: str, *, episode: int
    ) -> None: ...

"""Story-memory models (the continuity backbone).

Separates the three memory lanes (FictionRAG) and the two truth kinds:
- **Canonical / current-truth** (mutable, versioned): `CanonFact`, `CharacterState`, `PlotThread`, `StoryBible`.
- **Episodic / what-happened** (append-only, ordered, immutable): `EpisodeSummary`.
Canon is written deterministically by repositories you control — never by an LLM's auto-consolidation.
See research/memory-and-persistence.md. STARTER models — refine to the brief.
"""

from pydantic import Field

from story_engine.domain.base import DomainModel
from story_engine.domain.enums import CanonScope, ThreadStatus
from story_engine.domain.models.character import CharacterState


class CanonFact(DomainModel):
    """An established, versioned truth about the world/character/plot."""

    fact_id: str
    statement: str = Field(min_length=1)
    scope: CanonScope
    established_episode: int = Field(ge=1)
    supersedes: str | None = Field(
        default=None, description="fact_id this fact revises, if any."
    )


class PlotThread(DomainModel):
    """An unresolved (or resolved) narrative thread to track for payoff."""

    thread_id: str
    description: str = Field(min_length=1)
    status: ThreadStatus = ThreadStatus.OPEN
    opened_episode: int = Field(ge=1)
    resolved_episode: int | None = Field(default=None, ge=1)


class EpisodeSummary(DomainModel):
    """Append-only episodic record of what happened in one episode."""

    series_id: str
    episode_number: int = Field(ge=1)
    synopsis: str = Field(min_length=1)
    character_actions: dict[str, str] = Field(default_factory=dict)
    events: tuple[str, ...] = ()
    emotional_beat: str | None = None


class StoryBible(DomainModel):
    """Canonical aggregate: the current, authoritative state of a series."""

    series_id: str
    premise: str = ""
    world_rules: tuple[CanonFact, ...] = ()
    characters: tuple[CharacterState, ...] = ()
    open_threads: tuple[PlotThread, ...] = ()

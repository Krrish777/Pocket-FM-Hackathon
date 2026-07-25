"""Closed value sets for the story domain.

`StrEnum` so members render cleanly in JSON/LLM I/O while staying typed in the core. `CharacterStatus`
encodes SCORE-style *absorbing states* (a `DEAD` character cannot silently become `ACTIVE` again without
explicit justification) — the continuity checker enforces this. See research/memory-and-persistence.md.
"""

from enum import StrEnum


class Genre(StrEnum):
    """Starter genres — extend to the hackathon brief."""

    THRILLER = "thriller"
    ROMANCE = "romance"
    FANTASY = "fantasy"
    MYSTERY = "mystery"


class EpisodeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class CharacterStatus(StrEnum):
    """Discrete character state. DEAD/LOST are absorbing (see module docstring)."""

    ACTIVE = "active"
    LOST = "lost"
    DEAD = "dead"


class ThreadStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class CanonScope(StrEnum):
    WORLD = "world"
    CHARACTER = "character"
    PLOT = "plot"

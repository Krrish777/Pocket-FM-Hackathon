"""Character state (entity memory).

The canonical, authoritative record of a character — updated deterministically by the story-bible
repository, NOT by an LLM's automatic memory. `status` uses absorbing states (see enums).
STARTER model — refine to the brief.
"""

from pydantic import Field

from story_engine.domain.base import DomainModel
from story_engine.domain.enums import CharacterStatus


class CharacterState(DomainModel):
    """What is currently true about a character in a series."""

    character_id: str
    name: str = Field(min_length=1)
    traits: tuple[str, ...] = ()
    knowledge: tuple[str, ...] = Field(
        default=(),
        description="Facts this character currently knows (drives POV consistency).",
    )
    location: str | None = None
    status: CharacterStatus = CharacterStatus.ACTIVE
    arc_notes: str | None = None
    last_seen_episode: int | None = Field(default=None, ge=1)

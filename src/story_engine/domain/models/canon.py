"""The Canon Kernel schema — an external, typed, tri-temporal story state.

Three time axes, because two cannot express "true in the world, but the audience has not
learned it yet" — which is the entire basis of the spoiler guard:

- **Story time** (`valid_from`/`valid_to`): when the claim was true in the world.
- **Telling time** (`revealed_at`): when the *audience* learned it.
- **Record time** (`recorded_at`/`superseded_at`): when *this store* learned or changed it.

The domain takes no clock: callers supply `recorded_at`, so the core stays deterministic
and offline-testable. See PRD-KNOWLEDGE-BASE.md §8.1 and §9.
"""

from pydantic import Field, model_validator

from story_engine.domain.base import DomainModel
from story_engine.domain.enums import SourceType

type ChapterIndex = int
"""1-based position in the telling. Ordering only — it carries no duration."""

AUDIENCE = "audience"
"""Knower-scope sentinel: the reader/listener at the current point in the telling."""

NARRATOR = "narrator"
"""Knower-scope sentinel: the telling voice, which may know more than it reveals."""


class Provenance(DomainModel):
    """Where a fact came from, precisely enough to re-read it.

    A flag without provenance is an opinion; a flag with it is evidence. `quote` is stored
    verbatim so a citation can be rendered without re-fetching the source text.
    """

    source_id: str = Field(min_length=1)
    chapter: ChapterIndex = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def _span_moves_forward(self) -> "Provenance":
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be greater than char_start")
        return self


class Source(DomainModel):
    """A body of ingested text and the authority it carries.

    `tier` is the Holocron move: when two sources disagree, rank decides rather than
    argument. Lower is more authoritative (0 = base canon).
    """

    id: str = Field(min_length=1)
    type: SourceType
    tier: int = Field(ge=0)
    title: str = Field(min_length=1)
    url: str | None = None
    license_note: str | None = None


class Fork(DomainModel):
    """A branch of canon: the base novel, a fan story, or a user's takeover session.

    Contradicting canon is legal *inside* a fork and illegal outside it, which is what
    makes fan fiction representable instead of an error. Resolution walks
    fork -> parent -> ... -> root, with nearer facts shadowing ancestors.
    """

    id: str = Field(min_length=1)
    parent_fork_id: str | None = None
    divergence_at: ChapterIndex | None = Field(default=None, ge=1)
    source_id: str | None = None
    label: str = Field(min_length=1)

    @property
    def is_root(self) -> bool:
        """True when this fork is base canon rather than a branch."""
        return self.parent_fork_id is None

    @model_validator(mode="after")
    def _divergence_matches_parenthood(self) -> "Fork":
        if self.parent_fork_id is None and self.divergence_at is not None:
            raise ValueError("a root fork must not declare a divergence point")
        if self.parent_fork_id is not None and self.divergence_at is None:
            raise ValueError("a non-root fork must declare a divergence point")
        return self

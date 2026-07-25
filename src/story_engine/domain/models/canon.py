"""The Canon Kernel schema — an external, typed, tri-temporal story state.

Three time axes, because two cannot express "true in the world, but the audience has not
learned it yet" — which is the entire basis of the spoiler guard:

- **Story time** (`valid_from`/`valid_to`): when the claim was true in the world.
- **Telling time** (`revealed_at`): when the *audience* learned it.
- **Record time** (`recorded_at`/`superseded_at`): when *this store* learned or changed it.

The domain takes no clock: callers supply `recorded_at`, so the core stays deterministic
and offline-testable. See PRD-KNOWLEDGE-BASE.md §8.1 and §9.
"""

from datetime import datetime

from pydantic import Field, model_validator

from story_engine.domain.base import DomainModel
from story_engine.domain.enums import AssertionMode, FactStatus, SourceType

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


class Fact(DomainModel):
    """One atomic claim, scoped in three time axes and bound to who may know it.

    Facts are decomposed to atomic propositions on purpose: "the killer is left-handed"
    and "the killer is Moriarty" are separate records with separate `revealed_at`, so a
    partial reveal is representable instead of collapsing into the full answer.

    Facts are never overwritten. A superseding claim closes this one's `valid_to` and sets
    `superseded_at`; both rows stay queryable, because the superseded fact is still canon
    at its own timestamp.
    """

    id: str = Field(min_length=1)
    fork_id: str = Field(min_length=1)

    subject_id: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object_id: str | None = None
    object_literal: str | None = None

    valid_from: ChapterIndex = Field(ge=1, description="Story time: true from here.")
    valid_to: ChapterIndex | None = Field(
        default=None,
        ge=1,
        description="Story time: true until here. None = still true.",
    )
    revealed_at: ChapterIndex | None = Field(
        default=None,
        ge=1,
        description="Telling time: chapter whose text first asserts this on-page. "
        "None = the audience has not earned it yet.",
    )

    assertion_mode: AssertionMode
    attributed_to: str | None = Field(
        default=None, description="Required iff assertion_mode is ATTRIBUTED."
    )

    knower_scope: frozenset[str] | None = Field(
        default=None,
        min_length=1,
        description="Entity ids plus AUDIENCE/NARRATOR sentinels that know this. "
        "None = NOT TRACKED: visibility is governed by revealed_at alone. Populate only "
        "for typed secrets, lies and deliberately withheld information — universal "
        "per-character tracking is not evidence-supported and its false-extraction rate "
        "produces false blocks on legitimate dialogue.",
    )
    provenance: Provenance
    confidence: float = Field(ge=0.0, le=1.0)
    tier: int = Field(
        ge=0, description="Authority, inherited from the source. Lower wins."
    )
    status: FactStatus = FactStatus.ACTIVE

    recorded_at: datetime = Field(
        description="Record time: when this store learned it."
    )
    superseded_at: datetime | None = Field(
        default=None, description="Record time: when this store retired it."
    )

    @property
    def is_foreshadowed(self) -> bool:
        """True when the audience learned this before it became true in the world."""
        return self.revealed_at is not None and self.revealed_at < self.valid_from

    def is_valid_at(self, chapter: ChapterIndex) -> bool:
        """Whether the claim holds in the world at this story-time position."""
        if chapter < self.valid_from:
            return False
        return self.valid_to is None or chapter <= self.valid_to

    def is_revealed_by(self, chapter: ChapterIndex) -> bool:
        """Whether the audience has learned this by this point in the telling."""
        return self.revealed_at is not None and self.revealed_at <= chapter

    def is_known_by(self, knower: str) -> bool:
        """Whether this knower holds the fact.

        An untracked fact (`knower_scope is None`) is held by everyone: its visibility is
        governed by telling time alone. Only typed secrets and lies carry a scope.
        """
        if self.knower_scope is None:
            return True
        return knower in self.knower_scope

    def is_visible_to(self, knower: str, chapter: ChapterIndex) -> bool:
        """Whether this fact may be surfaced to `knower` at this point in the telling.

        The spoiler guard in one predicate. Deliberately does NOT consider story-time
        validity: a fact that stopped being true is still safely *knowable* (Kael's old
        loyalty is not a spoiler). Callers wanting current truth compose with
        `is_valid_at`.
        """
        if self.status is not FactStatus.ACTIVE:
            return False
        return self.is_revealed_by(chapter) and self.is_known_by(knower)

    @model_validator(mode="after")
    def _exactly_one_object(self) -> "Fact":
        if (self.object_id is None) == (self.object_literal is None):
            raise ValueError("set exactly one of object_id or object_literal")
        return self

    @model_validator(mode="after")
    def _attribution_matches_mode(self) -> "Fact":
        is_attributed = self.assertion_mode is AssertionMode.ATTRIBUTED
        if is_attributed and self.attributed_to is None:
            raise ValueError("an ATTRIBUTED fact must name attributed_to")
        if not is_attributed and self.attributed_to is not None:
            raise ValueError("attributed_to is only valid when mode is ATTRIBUTED")
        return self

    @model_validator(mode="after")
    def _validity_window_is_ordered(self) -> "Fact":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        return self

    @model_validator(mode="after")
    def _invalidated_facts_record_supersession(self) -> "Fact":
        if self.status is FactStatus.INVALIDATED and self.superseded_at is None:
            raise ValueError("an INVALIDATED fact must record superseded_at")
        return self

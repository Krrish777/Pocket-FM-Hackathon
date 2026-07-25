"""The Canon Kernel schema — an external, typed, tri-temporal story state.

Three time axes, because two cannot express "true in the world, but the audience has not
learned it yet" — which is the entire basis of the spoiler guard:

- **Story time** (`valid_from`/`valid_to`): when the claim was true in the world.
- **Telling time** (`revealed_at`): when the *audience* learned it.
- **Record time** (`recorded_at`/`superseded_at`): when *this store* learned or changed it.

The domain takes no clock: callers supply `recorded_at`, so the core stays deterministic
and offline-testable. See PRD-KNOWLEDGE-BASE.md §8.1 and §9.
"""

from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import AwareDatetime, Field, field_validator, model_validator

from story_engine.domain.base import DomainModel
from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    CommitmentType,
    EntityStatus,
    EntityType,
    FactStatus,
    FlagSeverity,
    InvariantKind,
    PresenceGrade,
    SourceType,
    VerificationLane,
)

type ChapterIndex = Annotated[int, Field(ge=1)]
"""1-based position in the telling. Ordering only — it carries no duration.

The `ge=1` travels with the type so every use — even one that forgets to repeat the
field-level constraint — still rejects nonsense like a negative chapter. Existing
field-level `ge=1` constraints are kept anyway (belt and braces); removing them would be
a larger diff than this fix warrants.
"""

AUDIENCE = "audience"
"""Knower-scope sentinel: the reader/listener at the current point in the telling."""

NARRATOR = "narrator"
"""Knower-scope sentinel: the telling voice, which may know more than it reveals."""


class Awareness(DomainModel):
    """One knower, and the chapter at which they learned a fact.

    Knowledge is not a set, it is a set of *arrivals*. Storing membership without an
    acquisition time forces every knower onto one clock — and the only clock available is
    the audience's `revealed_at`, which makes "Doakes suspects at chapter 6, the audience
    finds out at chapter 20" unrepresentable. That sentence is the product, so the time
    travels with the knower.

    Modelled as a frozen value object rather than a `dict` field because `DomainModel` sets
    `frozen=True` to guarantee hashable value objects, and a mapping field would silently
    break `hash(fact)`.
    """

    knower: str = Field(min_length=1)
    learned_at: "ChapterIndex"


def is_visible(
    *,
    status: FactStatus,
    revealed_at: "ChapterIndex | None",
    knower_scope: tuple[Awareness, ...] | None,
    knower: str,
    chapter: "ChapterIndex",
) -> bool:
    """The spoiler guard, as ONE function over the fields that decide it.

    Extracted from `Fact` so every retrieval lane can call the same predicate instead of
    mirroring it. The vector store previously kept its own copy that checked reveal time
    and knower scope but not `status`, so a QUARANTINED fact the canon store hid was
    returned by similarity search — a second implementation of a security predicate drifts
    from the first, and the drift is invisible until something like this asks both.

    Args:
        status: QUARANTINED never reached canon and stays invisible everywhere, always.
            INVALIDATED was canon and is still knowable at points where it held.
        revealed_at: Telling time — when the audience learned it. Governs untracked facts.
        knower_scope: Per-knower acquisition chapters, or None for untracked.
        knower: Whose view is being assembled.
        chapter: The position in the telling being played.
    """
    if status is FactStatus.QUARANTINED:
        return False
    if knower_scope is None:
        return revealed_at is not None and revealed_at <= chapter
    for awareness in knower_scope:
        if awareness.knower == knower:
            return awareness.learned_at <= chapter
    return False


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

    knower_scope: tuple[Awareness, ...] | None = Field(
        default=None,
        min_length=1,
        description="Who knows this, and from which chapter each of them knows it. "
        "AUDIENCE/NARRATOR are ordinary knowers here — the audience holds no privileged "
        "clock. None = NOT TRACKED: visibility is governed by revealed_at alone. Populate "
        "only for typed secrets, lies and deliberately withheld information — universal "
        "per-character tracking is not evidence-supported and its false-extraction rate "
        "produces false blocks on legitimate dialogue. Accepts a {knower: chapter} mapping "
        "for readability; a bare set of names is rejected, because a name without an "
        "acquisition chapter is exactly the ambiguity this field exists to remove.",
    )
    provenance: Provenance
    confidence: float = Field(ge=0.0, le=1.0)
    tier: int = Field(
        ge=0, description="Authority, inherited from the source. Lower wins."
    )
    status: FactStatus = FactStatus.ACTIVE

    recorded_at: AwareDatetime = Field(
        description="Record time: when this store learned it. Timezone-aware only — "
        "SQLite round-trips through text, and one naive row next to one aware row makes "
        "as-of comparisons raise TypeError."
    )
    superseded_at: AwareDatetime | None = Field(
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

    def learned_at(self, knower: str) -> ChapterIndex | None:
        """The chapter `knower` learned this, or None if they never do.

        An untracked fact (`knower_scope is None`) is learned by everyone exactly when the
        audience learns it, so it answers with `revealed_at`.
        """
        if self.knower_scope is None:
            return self.revealed_at
        for awareness in self.knower_scope:
            if awareness.knower == knower:
                return awareness.learned_at
        return None

    def is_known_by(self, knower: str, chapter: ChapterIndex) -> bool:
        """Whether this knower holds the fact by this point in the telling."""
        acquired = self.learned_at(knower)
        return acquired is not None and acquired <= chapter

    def is_visible_to(self, knower: str, chapter: ChapterIndex) -> bool:
        """Whether this fact may be surfaced to `knower` at this point in the telling.

        The spoiler guard in one predicate. Each knower is gated on THEIR OWN acquisition
        chapter, never on the audience's. Gating a character on `revealed_at` collapses
        five points of view into one: a character could not act on a secret they were
        shown on the page until the audience was also told, so every cast member ends up
        holding the identical fact set and the epistemic layer becomes decorative.

        Deliberately does NOT consider story-time validity: a fact that stopped being true
        is still safely *knowable* (Kael's old loyalty is not a spoiler). Callers wanting
        current truth compose with `is_valid_at`.

        Excludes only QUARANTINED, not every non-ACTIVE status: QUARANTINED and
        INVALIDATED mean different things. QUARANTINED never reached canon and must
        stay invisible everywhere, always. INVALIDATED means the fact WAS canon and
        was later superseded — it is still knowable at points where it held, which is
        exactly the "Kael's old loyalty" example above. Hiding INVALIDATED facts
        unconditionally would make the fact invisible even at chapters where it was
        both true and already public, contradicting this docstring's own promise.
        """
        return is_visible(
            status=self.status,
            revealed_at=self.revealed_at,
            knower_scope=self.knower_scope,
            knower=knower,
            chapter=chapter,
        )

    @field_validator("knower_scope", mode="before")
    @classmethod
    def _normalise_knower_scope(cls, value: Any) -> Any:
        """Accept a `{knower: chapter}` mapping, and order the result by knower.

        Call sites read far better as `{AUDIENCE: 20, "doakes": 6}` than as a sequence of
        constructed value objects, and the mapping form makes the acquisition chapter
        impossible to omit by accident.

        Held as an ORDER-NORMALISED tuple rather than a set. A set of `Awareness` would be
        the truer model — order is meaningless here — but `model_dump()` renders each
        member as a `dict`, and a set of dicts is unhashable, so dumping the model raised
        `TypeError` and the dump→validate round trip died. Sorting on the way in gives the
        same equality semantics a set would, while staying serialisable.
        """
        if isinstance(value, Mapping):
            value = [
                Awareness(knower=knower, learned_at=learned_at)
                for knower, learned_at in value.items()
            ]
        if isinstance(value, list | tuple | set | frozenset):
            entries = [
                item if isinstance(item, Awareness) else Awareness.model_validate(item)
                for item in value
            ]
            return tuple(sorted(entries, key=lambda a: a.knower))
        return value

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

    @model_validator(mode="after")
    def _record_window_is_ordered(self) -> "Fact":
        # Mirrors _validity_window_is_ordered, but for record time: a fact whose record
        # window closed while status stayed ACTIVE would stay visible and still count as
        # current, and one retired before it was recorded is nonsense.
        if self.status is FactStatus.ACTIVE and self.superseded_at is not None:
            raise ValueError("an ACTIVE fact must not carry a superseded_at")
        if self.superseded_at is not None and self.superseded_at < self.recorded_at:
            raise ValueError("superseded_at must not precede recorded_at")
        return self

    @model_validator(mode="after")
    def _scope_names_each_knower_once(self) -> "Fact":
        # Two arrival chapters for one knower is not a merge conflict the guard can
        # resolve — it would silently pick whichever the frozenset iterated first.
        if self.knower_scope is None:
            return self
        names = [awareness.knower for awareness in self.knower_scope]
        if len(names) != len(set(names)):
            raise ValueError("knower_scope must not name the same knower twice")
        return self

    @model_validator(mode="after")
    def _reveal_matches_scope(self) -> "Fact":
        # revealed_at and the AUDIENCE entry are two encodings of one thing: when the
        # audience learned it. Letting them disagree lets a fact the text put on the page
        # still be denied to the audience, or vice versa.
        if self.knower_scope is None:
            return self
        audience_learned_at = self.learned_at(AUDIENCE)
        if self.revealed_at is None and audience_learned_at is not None:
            raise ValueError(
                "a fact whose knower_scope includes AUDIENCE must set revealed_at to the "
                "same chapter"
            )
        if self.revealed_at is not None and audience_learned_at is None:
            raise ValueError(
                "a revealed_at fact with a tracked knower_scope must include AUDIENCE"
            )
        if audience_learned_at is not None and audience_learned_at != self.revealed_at:
            raise ValueError(
                "revealed_at and the AUDIENCE entry in knower_scope must agree"
            )
        return self


_FORWARD_TRANSITIONS: dict[CommitmentState, frozenset[CommitmentState]] = {
    CommitmentState.PLANTED: frozenset(
        {CommitmentState.TRIGGERED, CommitmentState.BROKEN}
    ),
    CommitmentState.TRIGGERED: frozenset(
        {CommitmentState.PAID_OFF, CommitmentState.BROKEN}
    ),
    CommitmentState.PAID_OFF: frozenset(),
    CommitmentState.BROKEN: frozenset(),
}


class CanonEntity(DomainModel):
    """A persistent thing the story is about, with every surface form it answers to.

    Named `CanonEntity` rather than `Entity` to stay unambiguous alongside the STARTER
    `CharacterState` in `memory.py` until that migration happens.
    """

    id: str = Field(min_length=1)
    fork_id: str = Field(min_length=1)
    type: EntityType
    canonical_name: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    status: EntityStatus = EntityStatus.ACTIVE

    def matches_name(self, name: str) -> bool:
        """Whether a surface form refers to this entity, ignoring case and padding."""
        needle = name.strip().casefold()
        if needle == self.canonical_name.casefold():
            return True
        return any(needle == alias.casefold() for alias in self.aliases)


class Presence(DomainModel):
    """How present one entity is in one scene."""

    entity_id: str = Field(min_length=1)
    grade: PresenceGrade


class Scene(DomainModel):
    """A unit of telling, and the roster that decides who could have witnessed it.

    The roster is the cheapest sound route to per-character knowledge: presence confers
    it, being merely referenced does not.
    """

    id: str = Field(min_length=1)
    fork_id: str = Field(min_length=1)
    chapter: ChapterIndex = Field(ge=1)
    order_in_chapter: int = Field(ge=0)
    summary: str = Field(min_length=1)
    roster: tuple[Presence, ...] = ()

    @property
    def witnesses(self) -> frozenset[str]:
        """Entities present enough to have learned what happened here."""
        return frozenset(
            p.entity_id for p in self.roster if p.grade is not PresenceGrade.REFERENCED
        )

    @model_validator(mode="after")
    def _roster_has_no_duplicate_entities(self) -> "Scene":
        seen_ids = [p.entity_id for p in self.roster]
        if len(seen_ids) != len(set(seen_ids)):
            raise ValueError("roster must not grade the same entity_id twice")
        return self


class Commitment(DomainModel):
    """A narrative debt, tracked from planting to discharge.

    Dropped setups are invisible to similarity search — nothing ever *asks* about an
    unfired gun — but trivial to a lifecycle filter.
    """

    id: str = Field(min_length=1)
    fork_id: str = Field(min_length=1)
    type: CommitmentType
    planted_at: ChapterIndex = Field(ge=1)
    state: CommitmentState = CommitmentState.PLANTED
    payoff_at: ChapterIndex | None = Field(default=None, ge=1)
    entity_ids: tuple[str, ...] = ()
    provenance: Provenance

    @property
    def is_open(self) -> bool:
        """True while the story still owes this debt."""
        return self.state in {CommitmentState.PLANTED, CommitmentState.TRIGGERED}

    def can_transition_to(self, state: CommitmentState) -> bool:
        """Whether moving to `state` is legal — "paid off before planted" is not."""
        return state in _FORWARD_TRANSITIONS[self.state]

    @model_validator(mode="after")
    def _payoff_is_consistent(self) -> "Commitment":
        if self.state is CommitmentState.PAID_OFF and self.payoff_at is None:
            raise ValueError("a PAID_OFF commitment must record payoff_at")
        if self.payoff_at is not None and self.state is not CommitmentState.PAID_OFF:
            raise ValueError("payoff_at is only valid on a PAID_OFF commitment")
        if self.payoff_at is not None and self.payoff_at < self.planted_at:
            raise ValueError("payoff_at must not precede planted_at")
        return self


class Flag(DomainModel):
    """A verifier finding, carrying the evidence that makes it actionable."""

    id: str = Field(min_length=1)
    invariant: InvariantKind
    severity: FlagSeverity
    lane: VerificationLane
    draft_span: str = Field(min_length=1)
    cited_fact_ids: tuple[str, ...] = ()
    citation_text: str = Field(min_length=1)
    suggested_action: str | None = None

    @model_validator(mode="after")
    def _hard_lane_flags_cite_evidence(self) -> "Flag":
        if self.lane is VerificationLane.HARD and not self.cited_fact_ids:
            raise ValueError("a HARD-lane flag must cite at least one fact")
        return self

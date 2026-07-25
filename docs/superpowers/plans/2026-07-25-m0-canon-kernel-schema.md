# M0 — Canon Kernel Schema & Invariants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the tri-temporal Canon Kernel domain schema and its pure invariant predicates to `story_engine.domain`, so later milestones (extraction, verifier, spoiler guard) have a typed, validated foundation.

**Architecture:** Pure Pydantic domain models on the existing frozen `DomainModel` base, plus one module of free functions over collections of those models. No IO, no vendor SDKs, no clock — every timestamp is supplied by the caller so the domain stays deterministic and offline-testable. New models live in a *new* module (`domain/models/canon.py`) **alongside** the existing STARTER models in `memory.py`; nothing existing is modified or deleted, so the 7 currently-passing tests stay green.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, ruff, mypy (strict).

## Global Constraints

- Spec: `PRD-KNOWLEDGE-BASE.md` (§9 Data Model, §10 Component Responsibilities, §11 KB-F-04/F-13, §18 Edge Cases).
- Type-hint every public signature. Modern syntax only: `list[str]`, `X | None`, PEP 695 aliases. Never `Optional`/`List`/`Union`.
- All domain models inherit `story_engine.domain.base.DomainModel` (frozen, `extra="forbid"`, strict).
- Closed value sets are `enum.StrEnum` in `domain/enums.py`. Compare members with `is`.
- `domain/` imports **nothing** outward — no vendor SDKs, no IO, no `datetime.now()`. Callers pass timestamps in.
- Google-style docstrings on every public module, class and function.
- Immutable collections on models are `tuple[...]` or `frozenset[...]`, never `list`/`set`.
- Tests mirror the package: `src/story_engine/domain/models/canon.py` → `tests/unit/domain/test_canon_models.py`.
- Tests assert schema and invariants, never generated text.
- **Never run `git commit`.** Tasks end at staging. The maintainer gates every commit.
- Gate for the whole plan: `make check` (ruff + ruff-format + mypy strict + pytest) green.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/story_engine/domain/enums.py` | Modify (append only) | Closed value sets for the Kernel. Existing enums untouched. |
| `src/story_engine/domain/models/canon.py` | Create | The Kernel schema: provenance, sources, forks, entities, facts, scenes, commitments, flags. |
| `src/story_engine/domain/invariants.py` | Create | Pure predicates over collections of Kernel models. No models defined here. |
| `tests/unit/domain/test_canon_models.py` | Create | Schema validation + per-model predicate behaviour. |
| `tests/unit/domain/test_invariants.py` | Create | Collection-level predicate behaviour. |

Why `invariants.py` is a module and not a package: M0 ships six predicates. A package with one file inside is ceremony. Split it when M2 adds timeline-folding and inventory checks.

Why `canon.py` is separate from `memory.py`: `memory.py`'s `CanonFact` carries a single `established_episode` — one time axis. It structurally cannot express "true, but the audience hasn't learned it yet". Migrating it is a breaking change to `episode_generator` and 7 passing tests, so it is a **separate later task**, not M0.

---

### Task 1: Kernel enums

**Files:**
- Modify: `src/story_engine/domain/enums.py` (append after the existing `CanonScope`)
- Test: `tests/unit/domain/test_canon_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SourceType`, `EntityType`, `EntityStatus`, `AssertionMode`, `FactStatus`, `CommitmentType`, `CommitmentState`, `PresenceGrade`, `InvariantKind`, `FlagSeverity`, `VerificationLane` — all `StrEnum`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/domain/test_canon_models.py`:

```python
"""Unit tests for the Canon Kernel schema (domain/models/canon.py)."""

from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    EntityStatus,
    FactStatus,
    PresenceGrade,
)


def test_kernel_enums_are_str_enums() -> None:
    """Kernel enums render as plain strings across the LLM/JSON boundary."""
    assert AssertionMode.ATTRIBUTED == "attributed"
    assert FactStatus.QUARANTINED == "quarantined"
    assert EntityStatus.DEAD == "dead"
    assert CommitmentState.PAID_OFF == "paid_off"
    assert PresenceGrade.SILENT == "silent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'AssertionMode'`

- [ ] **Step 3: Append the enums**

Append to `src/story_engine/domain/enums.py`:

```python
class SourceType(StrEnum):
    """Where a body of text came from. Drives the authority tier."""

    NOVEL = "novel"
    FANFIC = "fanfic"
    USER_SESSION = "user_session"


class EntityType(StrEnum):
    """The kinds of persistent thing a story is about."""

    CHARACTER = "character"
    LOCATION = "location"
    OBJECT = "object"
    ORGANIZATION = "organization"


class EntityStatus(StrEnum):
    """Discrete entity state. DEAD/DESTROYED are absorbing; IMPRISONED gates free action."""

    ACTIVE = "active"
    DEAD = "dead"
    DESTROYED = "destroyed"
    IMPRISONED = "imprisoned"
    LOST = "lost"
    UNKNOWN = "unknown"


class AssertionMode(StrEnum):
    """How a proposition entered the text.

    The single most important field for spoiler-safety: an extractor that flattens
    "Marcus said the vault was empty" into a bare world fact leaks a reveal AND stores
    a falsehood. NARRATED is world truth; ATTRIBUTED is a claim (and may be a lie);
    NON_ACTUAL is a dream, hypothetical or imagining.
    """

    NARRATED = "narrated"
    ATTRIBUTED = "attributed"
    NON_ACTUAL = "non_actual"


class FactStatus(StrEnum):
    """Lifecycle of a fact in the store. QUARANTINED never reaches retrieval."""

    ACTIVE = "active"
    INVALIDATED = "invalidated"
    QUARANTINED = "quarantined"


class CommitmentType(StrEnum):
    """A narrative debt the story has taken on and must discharge."""

    FORESHADOW = "foreshadow"
    PROMISE = "promise"
    SECRET = "secret"
    MYSTERY = "mystery"


class CommitmentState(StrEnum):
    """Commitment lifecycle. BROKEN is a deliberate abandonment, not an error."""

    PLANTED = "planted"
    TRIGGERED = "triggered"
    PAID_OFF = "paid_off"
    BROKEN = "broken"


class PresenceGrade(StrEnum):
    """How present an entity is in a scene, for deriving who witnessed what."""

    ACTIVE = "active"
    SILENT = "silent"
    REFERENCED = "referenced"


class InvariantKind(StrEnum):
    """The narrative property a verifier flag says was violated."""

    IDENTITY = "identity"
    MORTALITY = "mortality"
    TIMELINE = "timeline"
    INVENTORY = "inventory"
    EPISTEMIC = "epistemic"
    COMMITMENT = "commitment"


class FlagSeverity(StrEnum):
    """How hard a flag pushes back."""

    BLOCKING = "blocking"
    WARNING = "warning"
    ADVISORY = "advisory"


class VerificationLane(StrEnum):
    """Which lane produced a flag. HARD is deterministic; SOFT is probabilistic."""

    HARD = "hard"
    SOFT = "soft"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: PASS

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add src/story_engine/domain/enums.py tests/unit/domain/test_canon_models.py
```

---

### Task 2: Provenance, Source and Fork

**Files:**
- Create: `src/story_engine/domain/models/canon.py`
- Test: `tests/unit/domain/test_canon_models.py`

**Interfaces:**
- Consumes: `SourceType` (Task 1); `DomainModel` from `story_engine.domain.base`.
- Produces:
  - `type ChapterIndex = int`
  - `AUDIENCE: str`, `NARRATOR: str` module constants
  - `Provenance(source_id: str, chapter: ChapterIndex, char_start: int, char_end: int, quote: str)`
  - `Source(id: str, type: SourceType, tier: int, title: str, url: str | None, license_note: str | None)`
  - `Fork(id: str, parent_fork_id: str | None, divergence_at: ChapterIndex | None, source_id: str | None, label: str)`
  - `Fork.is_root -> bool`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/domain/test_canon_models.py`:

```python
import pytest
from pydantic import ValidationError

from story_engine.domain.enums import SourceType
from story_engine.domain.models.canon import Fork, Provenance, Source


def test_provenance_requires_a_forward_span() -> None:
    """char_end must come after char_start — a zero-width span cites nothing."""
    with pytest.raises(ValidationError):
        Provenance(
            source_id="src-1", chapter=3, char_start=100, char_end=100, quote="x"
        )


def test_provenance_accepts_a_valid_span() -> None:
    prov = Provenance(
        source_id="src-1",
        chapter=3,
        char_start=100,
        char_end=118,
        quote="the vault was empty",
    )
    assert prov.chapter == 3


def test_root_fork_has_no_parent_and_no_divergence() -> None:
    root = Fork(
        id="canon", parent_fork_id=None, divergence_at=None, source_id="src-1",
        label="base novel",
    )
    assert root.is_root is True


def test_non_root_fork_must_declare_a_divergence_point() -> None:
    """A branch without a divergence point cannot be resolved against its parent."""
    with pytest.raises(ValidationError):
        Fork(
            id="fork-a", parent_fork_id="canon", divergence_at=None,
            source_id="src-2", label="what if Kael never defects",
        )


def test_root_fork_may_not_declare_a_divergence_point() -> None:
    with pytest.raises(ValidationError):
        Fork(
            id="canon", parent_fork_id=None, divergence_at=12,
            source_id="src-1", label="base novel",
        )


def test_source_carries_an_authority_tier() -> None:
    source = Source(
        id="src-2", type=SourceType.FANFIC, tier=2, title="A Study in Anything",
        url=None, license_note=None,
    )
    assert source.tier == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'story_engine.domain.models.canon'`

- [ ] **Step 3: Create the module with the three models**

Create `src/story_engine/domain/models/canon.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add src/story_engine/domain/models/canon.py tests/unit/domain/test_canon_models.py
```

---

### Task 3: The Fact model and its four predicates

This is the load-bearing task. Everything downstream reads these fields.

**Files:**
- Modify: `src/story_engine/domain/models/canon.py` (append)
- Test: `tests/unit/domain/test_canon_models.py` (append)

**Interfaces:**
- Consumes: `Provenance`, `ChapterIndex`, `AUDIENCE` (Task 2); `AssertionMode`, `FactStatus` (Task 1).
- Produces:
  - `Fact` with fields: `id, fork_id, subject_id, predicate, object_id, object_literal, valid_from, valid_to, revealed_at, assertion_mode, attributed_to, knower_scope, provenance, confidence, tier, status, recorded_at, superseded_at`
  - `Fact.is_valid_at(chapter: ChapterIndex) -> bool`
  - `Fact.is_revealed_by(chapter: ChapterIndex) -> bool`
  - `Fact.is_known_by(knower: str) -> bool`
  - `Fact.is_visible_to(knower: str, chapter: ChapterIndex) -> bool`
  - `Fact.is_foreshadowed -> bool`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/domain/test_canon_models.py`:

```python
from datetime import UTC, datetime

from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models.canon import AUDIENCE, Fact

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(**overrides: object) -> Fact:
    """Build a valid Fact, overriding named fields."""
    defaults: dict[str, object] = {
        "id": "f-1",
        "fork_id": "canon",
        "subject_id": "kael",
        "predicate": "loyal_to",
        "object_id": "the_crown",
        "object_literal": None,
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": frozenset({AUDIENCE, "kael"}),
        "provenance": Provenance(
            source_id="src-1", chapter=1, char_start=0, char_end=12, quote="Kael knelt."
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def test_fact_requires_exactly_one_object() -> None:
    """A fact points at an entity or a literal, never both and never neither."""
    with pytest.raises(ValidationError):
        _fact(object_id="the_crown", object_literal="the Crown")
    with pytest.raises(ValidationError):
        _fact(object_id=None, object_literal=None)


def test_attributed_fact_must_name_its_speaker() -> None:
    """ATTRIBUTED without attributed_to is the bug that leaks reveals and stores lies."""
    with pytest.raises(ValidationError):
        _fact(assertion_mode=AssertionMode.ATTRIBUTED, attributed_to=None)


def test_narrated_fact_must_not_name_a_speaker() -> None:
    with pytest.raises(ValidationError):
        _fact(assertion_mode=AssertionMode.NARRATED, attributed_to="marcus")


def test_knower_scope_must_not_be_empty() -> None:
    """A fact nobody knows cannot be retrieved or reasoned about."""
    with pytest.raises(ValidationError):
        _fact(knower_scope=frozenset())


def test_validity_window_must_not_close_before_it_opens() -> None:
    with pytest.raises(ValidationError):
        _fact(valid_from=10, valid_to=4)


def test_invalidated_fact_must_record_when_it_was_superseded() -> None:
    with pytest.raises(ValidationError):
        _fact(status=FactStatus.INVALIDATED, superseded_at=None)


def test_is_valid_at_respects_the_story_time_window() -> None:
    fact = _fact(valid_from=5, valid_to=10)
    assert fact.is_valid_at(4) is False
    assert fact.is_valid_at(5) is True
    assert fact.is_valid_at(10) is True
    assert fact.is_valid_at(11) is False


def test_open_validity_window_never_closes() -> None:
    fact = _fact(valid_from=5, valid_to=None)
    assert fact.is_valid_at(9999) is True


def test_is_revealed_by_respects_telling_time() -> None:
    fact = _fact(revealed_at=7)
    assert fact.is_revealed_by(6) is False
    assert fact.is_revealed_by(7) is True


def test_unrevealed_fact_is_never_revealed() -> None:
    """revealed_at=None means the audience has not earned it at any point yet."""
    fact = _fact(revealed_at=None)
    assert fact.is_revealed_by(9999) is False


def test_is_visible_to_combines_status_reveal_and_scope() -> None:
    fact = _fact(revealed_at=3, knower_scope=frozenset({AUDIENCE, "holmes"}))
    assert fact.is_visible_to("holmes", 5) is True
    assert fact.is_visible_to("watson", 5) is False  # not in scope
    assert fact.is_visible_to("holmes", 2) is False  # not yet revealed


def test_quarantined_fact_is_visible_to_nobody() -> None:
    fact = _fact(status=FactStatus.QUARANTINED)
    assert fact.is_visible_to(AUDIENCE, 9999) is False


def test_foreshadowed_fact_is_revealed_before_it_is_true() -> None:
    """Legal, not an error — this is what foreshadowing IS."""
    assert _fact(revealed_at=2, valid_from=40).is_foreshadowed is True
    assert _fact(revealed_at=40, valid_from=40).is_foreshadowed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Fact'`

- [ ] **Step 3: Append the Fact model**

Append to `src/story_engine/domain/models/canon.py` (and extend the existing enum import line to include `AssertionMode, FactStatus`, and add `from datetime import datetime` at the top):

```python
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
        default=None, ge=1, description="Story time: true until here. None = still true."
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

    knower_scope: frozenset[str] = Field(
        min_length=1,
        description="Entity ids plus the AUDIENCE/NARRATOR sentinels that know this.",
    )
    provenance: Provenance
    confidence: float = Field(ge=0.0, le=1.0)
    tier: int = Field(ge=0, description="Authority, inherited from the source. Lower wins.")
    status: FactStatus = FactStatus.ACTIVE

    recorded_at: datetime = Field(description="Record time: when this store learned it.")
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
        """Whether this knower holds the fact at all."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: PASS (19 tests)

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add src/story_engine/domain/models/canon.py tests/unit/domain/test_canon_models.py
```

---

### Task 4: Entity, Scene roster, Commitment and Flag

**Files:**
- Modify: `src/story_engine/domain/models/canon.py` (append)
- Test: `tests/unit/domain/test_canon_models.py` (append)

**Interfaces:**
- Consumes: `Provenance`, `ChapterIndex` (Task 2); `EntityType`, `EntityStatus`, `CommitmentType`, `CommitmentState`, `PresenceGrade`, `InvariantKind`, `FlagSeverity`, `VerificationLane` (Task 1).
- Produces:
  - `CanonEntity(id, fork_id, type, canonical_name, aliases, status)` with `CanonEntity.matches_name(name: str) -> bool`
  - `Presence(entity_id: str, grade: PresenceGrade)`
  - `Scene(id, fork_id, chapter, order_in_chapter, summary, roster)` with `Scene.witnesses -> frozenset[str]`
  - `Commitment(id, fork_id, type, planted_at, state, payoff_at, entity_ids, provenance)` with `Commitment.can_transition_to(state: CommitmentState) -> bool` and `Commitment.is_open -> bool`
  - `Flag(id, invariant, severity, lane, draft_span, cited_fact_ids, citation_text, suggested_action)`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/domain/test_canon_models.py`:

```python
from story_engine.domain.enums import (
    CommitmentType,
    EntityType,
    FlagSeverity,
    InvariantKind,
    VerificationLane,
)
from story_engine.domain.models.canon import (
    CanonEntity,
    Commitment,
    Flag,
    Presence,
    Scene,
)


def test_entity_matches_any_of_its_aliases_case_insensitively() -> None:
    """One node per identity: "the Stranger" and "the King" must resolve together."""
    entity = CanonEntity(
        id="e-1", fork_id="canon", type=EntityType.CHARACTER,
        canonical_name="Aldric", aliases=("the Stranger", "the King"),
        status=EntityStatus.ACTIVE,
    )
    assert entity.matches_name("aldric") is True
    assert entity.matches_name("The Stranger") is True
    assert entity.matches_name("Moriarty") is False


def test_scene_witnesses_exclude_merely_referenced_entities() -> None:
    """Being talked about is not being present — it must not confer knowledge."""
    scene = Scene(
        id="s-1", fork_id="canon", chapter=3, order_in_chapter=1,
        summary="Holmes examines the ash while Watson watches.",
        roster=(
            Presence(entity_id="holmes", grade=PresenceGrade.ACTIVE),
            Presence(entity_id="watson", grade=PresenceGrade.SILENT),
            Presence(entity_id="moriarty", grade=PresenceGrade.REFERENCED),
        ),
    )
    assert scene.witnesses == frozenset({"holmes", "watson"})


def _commitment(**overrides: object) -> Commitment:
    defaults: dict[str, object] = {
        "id": "c-1",
        "fork_id": "canon",
        "type": CommitmentType.FORESHADOW,
        "planted_at": 3,
        "state": CommitmentState.PLANTED,
        "payoff_at": None,
        "entity_ids": ("holmes",),
        "provenance": Provenance(
            source_id="src-1", chapter=3, char_start=0, char_end=9, quote="a scratch"
        ),
    }
    return Commitment(**(defaults | overrides))  # type: ignore[arg-type]


def test_commitment_allows_only_forward_transitions() -> None:
    planted = _commitment(state=CommitmentState.PLANTED)
    assert planted.can_transition_to(CommitmentState.TRIGGERED) is True
    assert planted.can_transition_to(CommitmentState.BROKEN) is True
    assert planted.can_transition_to(CommitmentState.PAID_OFF) is False


def test_paid_off_commitment_is_terminal() -> None:
    paid = _commitment(state=CommitmentState.PAID_OFF, payoff_at=40)
    assert paid.can_transition_to(CommitmentState.TRIGGERED) is False
    assert paid.is_open is False


def test_paid_off_commitment_must_record_where_it_paid_off() -> None:
    with pytest.raises(ValidationError):
        _commitment(state=CommitmentState.PAID_OFF, payoff_at=None)


def test_payoff_must_not_precede_planting() -> None:
    with pytest.raises(ValidationError):
        _commitment(state=CommitmentState.PAID_OFF, planted_at=10, payoff_at=4)


def test_hard_lane_flag_must_cite_at_least_one_fact() -> None:
    """An uncited flag is an opinion; a cited flag is evidence."""
    with pytest.raises(ValidationError):
        Flag(
            id="fl-1", invariant=InvariantKind.MORTALITY,
            severity=FlagSeverity.BLOCKING, lane=VerificationLane.HARD,
            draft_span="Kael spoke again.", cited_fact_ids=(),
            citation_text="draft says Kael speaks; canon: died @ ep 181",
            suggested_action=None,
        )


def test_flag_renders_a_citation() -> None:
    flag = Flag(
        id="fl-2", invariant=InvariantKind.MORTALITY,
        severity=FlagSeverity.BLOCKING, lane=VerificationLane.HARD,
        draft_span="Kael spoke again.", cited_fact_ids=("f-9",),
        citation_text="draft says Kael speaks; canon: died @ ep 181 s3",
        suggested_action="invalidate or depict a resurrection",
    )
    assert "ep 181" in flag.citation_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'CanonEntity'`

- [ ] **Step 3: Append the four models**

Append to `src/story_engine/domain/models/canon.py` (extend the enum import line with `CommitmentState, CommitmentType, EntityStatus, EntityType, FlagSeverity, InvariantKind, PresenceGrade, VerificationLane`):

```python
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
            p.entity_id
            for p in self.roster
            if p.grade is not PresenceGrade.REFERENCED
        )


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/domain/test_canon_models.py -v`
Expected: PASS (27 tests)

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add src/story_engine/domain/models/canon.py tests/unit/domain/test_canon_models.py
```

---

### Task 5: Pure invariant predicates

**Files:**
- Create: `src/story_engine/domain/invariants.py`
- Test: `tests/unit/domain/test_invariants.py`

**Interfaces:**
- Consumes: `Fact`, `CanonEntity`, `Commitment`, `Scene`, `ChapterIndex` (Tasks 2-4); `EntityStatus`, `FactStatus` (Task 1).
- Produces (all free functions, no state):
  - `visible_facts(facts, knower, chapter) -> tuple[Fact, ...]`
  - `withheld_facts(facts, knower, chapter) -> tuple[Fact, ...]`
  - `epistemic_violations(used_fact_ids, facts, knower, chapter) -> tuple[Fact, ...]`
  - `conflicting_active_facts(facts, chapter) -> tuple[tuple[Fact, Fact], ...]`
  - `open_commitments(commitments) -> tuple[Commitment, ...]`
  - `entities_acting_while_incapacitated(acting_entity_ids, entities) -> tuple[CanonEntity, ...]`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/domain/test_invariants.py`:

```python
"""Unit tests for the pure invariant predicates (domain/invariants.py)."""

from datetime import UTC, datetime

from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    CommitmentType,
    EntityStatus,
    EntityType,
    FactStatus,
)
from story_engine.domain.invariants import (
    conflicting_active_facts,
    entities_acting_while_incapacitated,
    epistemic_violations,
    open_commitments,
    visible_facts,
    withheld_facts,
)
from story_engine.domain.models.canon import (
    AUDIENCE,
    CanonEntity,
    Commitment,
    Fact,
    Provenance,
)

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
PROV = Provenance(
    source_id="src-1", chapter=1, char_start=0, char_end=5, quote="Kael"
)


def _fact(fact_id: str, **overrides: object) -> Fact:
    defaults: dict[str, object] = {
        "id": fact_id,
        "fork_id": "canon",
        "subject_id": "kael",
        "predicate": "loyal_to",
        "object_id": "the_crown",
        "object_literal": None,
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": frozenset({AUDIENCE}),
        "provenance": PROV,
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


def test_visible_and_withheld_partition_the_fact_set() -> None:
    """Every fact is either servable or withheld — nothing may fall through."""
    facts = (
        _fact("f-1", revealed_at=1),
        _fact("f-2", revealed_at=9),
        _fact("f-3", revealed_at=None),
    )
    visible = visible_facts(facts, AUDIENCE, chapter=5)
    withheld = withheld_facts(facts, AUDIENCE, chapter=5)

    assert {f.id for f in visible} == {"f-1"}
    assert {f.id for f in withheld} == {"f-2", "f-3"}
    assert len(visible) + len(withheld) == len(facts)


def test_epistemic_violations_catch_acting_on_unknown_information() -> None:
    """Watson may not act on a fact only Holmes knows."""
    facts = (
        _fact("f-1", knower_scope=frozenset({AUDIENCE, "holmes"})),
        _fact("f-2", knower_scope=frozenset({AUDIENCE, "watson"})),
    )
    violations = epistemic_violations(
        used_fact_ids=("f-1", "f-2"), facts=facts, knower="watson", chapter=5
    )
    assert {f.id for f in violations} == {"f-1"}


def test_epistemic_violations_ignore_unknown_fact_ids() -> None:
    """An id with no matching fact is not this predicate's problem."""
    facts = (_fact("f-1"),)
    assert epistemic_violations(("f-404",), facts, AUDIENCE, chapter=5) == ()


def test_conflicting_active_facts_detect_two_current_values() -> None:
    """A single-valued predicate must not hold two values at one story time."""
    facts = (
        _fact("f-1", predicate="located_in", object_id="london", valid_from=1),
        _fact("f-2", predicate="located_in", object_id="paris", valid_from=1),
    )
    conflicts = conflicting_active_facts(facts, chapter=3)
    assert len(conflicts) == 1
    assert {conflicts[0][0].id, conflicts[0][1].id} == {"f-1", "f-2"}


def test_superseded_facts_do_not_conflict() -> None:
    """Invalidate-not-overwrite means both rows exist; only one is current."""
    facts = (
        _fact("f-1", predicate="located_in", object_id="london",
              valid_from=1, valid_to=2),
        _fact("f-2", predicate="located_in", object_id="paris", valid_from=3),
    )
    assert conflicting_active_facts(facts, chapter=5) == ()


def test_facts_in_different_forks_do_not_conflict() -> None:
    """Contradicting canon is legal inside a fork — that is what a fork is for."""
    facts = (
        _fact("f-1", predicate="located_in", object_id="london"),
        _fact("f-2", fork_id="fork-a", predicate="located_in", object_id="paris"),
    )
    assert conflicting_active_facts(facts, chapter=3) == ()


def test_open_commitments_exclude_discharged_ones() -> None:
    prov = PROV
    commitments = (
        Commitment(id="c-1", fork_id="canon", type=CommitmentType.FORESHADOW,
                   planted_at=3, state=CommitmentState.PLANTED, payoff_at=None,
                   entity_ids=(), provenance=prov),
        Commitment(id="c-2", fork_id="canon", type=CommitmentType.SECRET,
                   planted_at=3, state=CommitmentState.PAID_OFF, payoff_at=40,
                   entity_ids=(), provenance=prov),
    )
    assert {c.id for c in open_commitments(commitments)} == {"c-1"}


def test_dead_and_imprisoned_entities_cannot_act_freely() -> None:
    entities = (
        CanonEntity(id="kael", fork_id="canon", type=EntityType.CHARACTER,
                    canonical_name="Kael", aliases=(), status=EntityStatus.DEAD),
        CanonEntity(id="mara", fork_id="canon", type=EntityType.CHARACTER,
                    canonical_name="Mara", aliases=(),
                    status=EntityStatus.IMPRISONED),
        CanonEntity(id="finn", fork_id="canon", type=EntityType.CHARACTER,
                    canonical_name="Finn", aliases=(), status=EntityStatus.ACTIVE),
    )
    offenders = entities_acting_while_incapacitated(
        acting_entity_ids=("kael", "mara", "finn"), entities=entities
    )
    assert {e.id for e in offenders} == {"kael", "mara"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/domain/test_invariants.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'story_engine.domain.invariants'`

- [ ] **Step 3: Create the invariants module**

Create `src/story_engine/domain/invariants.py`:

```python
"""Pure narrative invariant predicates over Canon Kernel collections.

Free functions, no state, no IO — every one is a deterministic function of the models it
is handed, so the whole module is unit-testable offline and costs no model calls. This is
the HARD lane's vocabulary: the checks that are decidable by boolean logic over typed
state. Semantic checks (motivation, tone) belong to the soft lane and are not here.

See PRD-KNOWLEDGE-BASE.md §11 KB-F-12 and the invariant catalog in the research vault.
"""

from collections.abc import Iterable

from story_engine.domain.enums import EntityStatus, FactStatus
from story_engine.domain.models.canon import (
    CanonEntity,
    ChapterIndex,
    Commitment,
    Fact,
)

_INCAPACITATED = frozenset(
    {EntityStatus.DEAD, EntityStatus.DESTROYED, EntityStatus.IMPRISONED}
)


def visible_facts(
    facts: Iterable[Fact], knower: str, chapter: ChapterIndex
) -> tuple[Fact, ...]:
    """Facts that may be surfaced to `knower` at this point in the telling."""
    return tuple(f for f in facts if f.is_visible_to(knower, chapter))


def withheld_facts(
    facts: Iterable[Fact], knower: str, chapter: ChapterIndex
) -> tuple[Fact, ...]:
    """The spoiler-guard exclusion set — retrieval performed in order to EXCLUDE.

    Exposed rather than merely applied, because being able to *show* what was withheld is
    what makes the guarantee demonstrable instead of merely asserted.
    """
    return tuple(f for f in facts if not f.is_visible_to(knower, chapter))


def epistemic_violations(
    used_fact_ids: Iterable[str],
    facts: Iterable[Fact],
    knower: str,
    chapter: ChapterIndex,
) -> tuple[Fact, ...]:
    """Facts a draft used that `knower` could not have known.

    The most common AI-fiction tell: a character acting on information no scene gave them.
    Ids with no matching fact are ignored — resolving them is the caller's job.
    """
    by_id = {f.id: f for f in facts}
    offenders = []
    for fact_id in used_fact_ids:
        fact = by_id.get(fact_id)
        if fact is not None and not fact.is_visible_to(knower, chapter):
            offenders.append(fact)
    return tuple(offenders)


def conflicting_active_facts(
    facts: Iterable[Fact], chapter: ChapterIndex
) -> tuple[tuple[Fact, Fact], ...]:
    """Pairs asserting different values for one subject+predicate at one story time.

    Scoped to a single fork: contradicting an ancestor is legal inside a branch, so
    cross-fork pairs are not conflicts. Superseded facts fall out naturally because a
    closed validity window fails `is_valid_at`.
    """
    current = [
        f
        for f in facts
        if f.status is FactStatus.ACTIVE and f.is_valid_at(chapter)
    ]
    conflicts: list[tuple[Fact, Fact]] = []
    for index, left in enumerate(current):
        for right in current[index + 1 :]:
            if left.fork_id != right.fork_id:
                continue
            if left.subject_id != right.subject_id:
                continue
            if left.predicate != right.predicate:
                continue
            same_object = (
                left.object_id == right.object_id
                and left.object_literal == right.object_literal
            )
            if not same_object:
                conflicts.append((left, right))
    return tuple(conflicts)


def open_commitments(commitments: Iterable[Commitment]) -> tuple[Commitment, ...]:
    """Narrative debts the story still owes — the unfired Chekhov's guns."""
    return tuple(c for c in commitments if c.is_open)


def entities_acting_while_incapacitated(
    acting_entity_ids: Iterable[str], entities: Iterable[CanonEntity]
) -> tuple[CanonEntity, ...]:
    """Entities that acted despite being dead, destroyed or imprisoned.

    Resurrection is not hardcoded as impossible — a world rule may permit it — but it must
    be depicted, so an undepicted status change surfaces here for the caller to adjudicate.
    """
    acting = set(acting_entity_ids)
    return tuple(
        e for e in entities if e.id in acting and e.status in _INCAPACITATED
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/domain/test_invariants.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Run the full gate**

Run: `make check`
Expected: ruff clean, ruff-format clean, mypy `Success`, pytest **42 passed** (7 pre-existing + 27 canon + 8 invariants).

If mypy complains about `defaults | overrides` in the test helpers, the `# type: ignore[arg-type]` comments already present handle it; do not weaken the models to satisfy a test helper.

- [ ] **Step 6: Stage (do NOT commit)**

```bash
git add src/story_engine/domain/invariants.py tests/unit/domain/test_invariants.py
```

Then ask the maintainer to review and gate the commit. Per the project's global rules, **never** run `git commit` yourself.

---

## Self-Review

**Spec coverage.** PRD §9 Data Model: `Source`, `Fork`, `Entity`→`CanonEntity`, `Fact`, `Commitment`, `Flag` all present; `Event` is deferred to M2, where timeline folding actually needs it — noted below as a known gap. PRD §8.1 three time axes: all three on `Fact`. KB-F-04 invalidate-never-overwrite: enforced by `_invalidated_facts_record_supersession` plus `conflicting_active_facts` ignoring closed windows. KB-F-13 flags cite provenance: enforced by `_hard_lane_flags_cite_evidence`. KB-F-09 spoiler guard: `is_visible_to` + `withheld_facts`. Research finding on assertion mode: `AssertionMode` + `attributed_to` with paired validators. REVERIEMEM scene rosters: `Presence`/`Scene.witnesses`.

**Known gaps, deliberately deferred:** `Event` (M2, with timeline invariants); knowledge-transfer records that let `knower_scope` change over time (M3 — M0 treats scope as fixed at establishment); fork lineage *resolution* (M4, blocked on OD-1); the `memory.py` migration (separate task, would break passing tests).

**Placeholder scan:** none — every step carries runnable code.

**Type consistency:** `ChapterIndex` used uniformly; `CanonEntity` named consistently across Tasks 4 and 5; `is_visible_to(knower, chapter)` has one signature everywhere; `_fact` helpers in both test files use the same field set.

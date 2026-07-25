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

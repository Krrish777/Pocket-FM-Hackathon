"""SQLModel table rows — a PERSISTENCE detail, not domain models.

Rows exist only for storage; repositories map Row ⇄ domain explicitly so the pure core (`domain/`)
never imports SQLModel/SQLAlchemy (hexagon red line #7). One table class per aggregate. JSON columns
hold the domain's dict/collection fields; the repo converts `tuple ⇄ list` at the boundary.
"""

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EpisodeSummaryRow(SQLModel, table=True):
    """Storage row for `domain.models.EpisodeSummary` (append-only episodic log)."""

    __tablename__ = "episode_summary"

    id: int | None = Field(default=None, primary_key=True)
    series_id: str = Field(index=True)
    episode_number: int = Field(index=True)
    synopsis: str
    character_actions: dict[str, str] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    events: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    emotional_beat: str | None = Field(default=None)


class FactRow(SQLModel, table=True):
    """Storage row for `domain.models.Fact` — the tri-temporal canon record.

    Enums are stored as their string values (they are `StrEnum`, so this is lossless).
    `knower_scope` is a JSON list or SQL NULL: NULL means NOT TRACKED, which is a different
    state from "tracked but empty" — the domain rejects the latter, so conflating them would
    surface as a validation error on read.
    """

    __tablename__ = "canon_fact"

    id: str = Field(primary_key=True)
    fork_id: str = Field(index=True)
    subject_id: str = Field(index=True)
    predicate: str = Field(index=True)
    object_id: str | None = Field(default=None)
    object_literal: str | None = Field(default=None)

    valid_from: int = Field(index=True)
    valid_to: int | None = Field(default=None)
    revealed_at: int | None = Field(default=None, index=True)

    assertion_mode: str
    attributed_to: str | None = Field(default=None)

    knower_scope: list[str] | None = Field(default=None, sa_column=Column(JSON))
    provenance: dict[str, object] = Field(default_factory=dict, sa_column=Column(JSON))
    confidence: float
    tier: int
    status: str = Field(index=True)

    # Stored as ISO-8601 text, not a native DateTime column: SQLite has no timezone type, so
    # SQLAlchemy's DateTime silently returns a naive datetime on read and drops `tzinfo` —
    # a lossy round-trip the mapping-round-trip test exists to catch. `datetime.isoformat()`
    # / `datetime.fromisoformat()` preserve the offset exactly.
    recorded_at: str
    superseded_at: str | None = Field(default=None)


class VectorRow(SQLModel, table=True):
    """Storage row for a semantic-recall embedding — the vector store's only table.

    Denormalized copy of `revealed_at`/`knower_scope` from the owning fact so `search` can
    apply the spoiler guard without a join back to `FactRow`. Same NULL-vs-empty-list
    semantics as `FactRow.knower_scope`: NULL means NOT TRACKED (visible to everyone).
    """

    __tablename__ = "canon_vector"

    id: int | None = Field(default=None, primary_key=True)
    fact_id: str = Field(index=True)
    fork_id: str = Field(index=True)
    text: str
    vector: list[float] = Field(default_factory=list, sa_column=Column(JSON))
    revealed_at: int | None = Field(default=None, index=True)
    knower_scope: list[str] | None = Field(default=None, sa_column=Column(JSON))

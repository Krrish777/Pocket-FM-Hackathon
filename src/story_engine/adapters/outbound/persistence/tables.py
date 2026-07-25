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

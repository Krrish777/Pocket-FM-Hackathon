"""SQLite-backed episode-log repository — implements `EpisodeLogRepositoryPort`.

Append-only episodic memory persisted in SQLite. Maps Row ⇄ domain `EpisodeSummary` explicitly
(the domain model stays pure Pydantic; `tuple` fields round-trip through JSON `list` columns).
`col()` re-types class attributes so filters/ordering type-check under strict mypy.
"""

from sqlalchemy import Engine
from sqlmodel import col, select

from story_engine.adapters.outbound.persistence.db import session_scope
from story_engine.adapters.outbound.persistence.tables import EpisodeSummaryRow
from story_engine.domain.models import EpisodeSummary


def _to_domain(row: EpisodeSummaryRow) -> EpisodeSummary:
    """Map a storage row back to the pure domain model."""
    return EpisodeSummary(
        series_id=row.series_id,
        episode_number=row.episode_number,
        synopsis=row.synopsis,
        character_actions=dict(row.character_actions),
        events=tuple(row.events),
        emotional_beat=row.emotional_beat,
    )


def _to_row(summary: EpisodeSummary) -> EpisodeSummaryRow:
    """Map a domain model to a fresh storage row (id assigned by the DB)."""
    return EpisodeSummaryRow(
        series_id=summary.series_id,
        episode_number=summary.episode_number,
        synopsis=summary.synopsis,
        character_actions=dict(summary.character_actions),
        events=list(summary.events),
        emotional_beat=summary.emotional_beat,
    )


class SqliteEpisodeLogRepository:
    """SQLite implementation of `EpisodeLogRepositoryPort` (append-only, ordered by insertion)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append_summary(self, summary: EpisodeSummary) -> None:
        """Append one episode summary (never overwrite)."""
        with session_scope(self._engine) as session:
            session.add(_to_row(summary))

    def get_recent(self, series_id: str, n: int) -> tuple[EpisodeSummary, ...]:
        """Return the most recent `n` summaries for a series, newest last."""
        with session_scope(self._engine) as session:
            statement = (
                select(EpisodeSummaryRow)
                .where(col(EpisodeSummaryRow.series_id) == series_id)
                .order_by(col(EpisodeSummaryRow.id).desc())
                .limit(n)
            )
            rows = list(session.exec(statement).all())
            # Map to pure domain models WHILE the session is open (rows detach on close).
            return tuple(_to_domain(row) for row in reversed(rows))

    def get_by_episode(
        self, series_id: str, episode_number: int
    ) -> EpisodeSummary | None:
        """Return the first-appended summary for a given episode number, or None."""
        with session_scope(self._engine) as session:
            statement = (
                select(EpisodeSummaryRow)
                .where(col(EpisodeSummaryRow.series_id) == series_id)
                .where(col(EpisodeSummaryRow.episode_number) == episode_number)
                .order_by(col(EpisodeSummaryRow.id).asc())
            )
            row = session.exec(statement).first()
            # Map while the session is open (rows detach on close).
            return _to_domain(row) if row is not None else None

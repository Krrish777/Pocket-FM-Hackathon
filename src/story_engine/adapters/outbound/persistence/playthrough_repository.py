"""SQLite-backed playthrough repository — implements `PlaythroughRepositoryPort`.

Persists the run envelope so `POST /play` and `POST /play/{id}/act` — two separate HTTP requests,
possibly two separate processes — can share one run. **This is NOT a second source of truth.**
Canon facts already live in the canon store (`ports.canon_store`) behind
`story_engine.domain.models.canon.is_visible`; a `Playthrough` here is a replayable *view* of a run
over that store, serialized whole via `Playthrough.model_dump_json()` / `.model_validate_json()`.
Nothing about a fact is duplicated into this table — only the rendered turns the player has already
been shown.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine
from sqlmodel import col, select

from story_engine.adapters.outbound.persistence.db import session_scope
from story_engine.adapters.outbound.persistence.tables import PlaythroughRunRow
from story_engine.domain.models.play import Playthrough


def _to_domain(row: PlaythroughRunRow) -> Playthrough:
    """Map a storage row back to the pure domain model."""
    return Playthrough.model_validate_json(row.payload)


class SqlitePlaythroughRepository:
    """SQLite implementation of `PlaythroughRepositoryPort`."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(self, run: Playthrough) -> str:
        """Persist a new run under a freshly generated `run_id` and return it.

        `run_id` is generated here, never accepted from a caller — a caller-supplied id would be
        both an id-collision surface and an enumeration surface.
        """
        run_id = uuid4().hex
        row = PlaythroughRunRow(
            run_id=run_id,
            fork_id=run.fork_id,
            protagonist=run.protagonist,
            created_at=datetime.now(UTC),
            payload=run.model_dump_json(),
        )
        with session_scope(self._engine) as session:
            session.add(row)
        return run_id

    def get(self, run_id: str) -> Playthrough | None:
        """Return the run for `run_id`, or `None` if no such run exists."""
        with session_scope(self._engine) as session:
            row = session.get(PlaythroughRunRow, run_id)
            # Map while the session is open (rows detach on close).
            return _to_domain(row) if row is not None else None

    def save(self, run_id: str, run: Playthrough) -> None:
        """Overwrite the run stored at `run_id`.

        Raises:
            KeyError: `run_id` does not name an existing run — a save must never invent a row
                (that would hide a caller bug behind a silent insert).
        """
        with session_scope(self._engine) as session:
            statement = select(PlaythroughRunRow).where(
                col(PlaythroughRunRow.run_id) == run_id
            )
            row = session.exec(statement).first()
            if row is None:
                raise KeyError(f"no playthrough run with run_id={run_id!r}")
            row.fork_id = run.fork_id
            row.protagonist = run.protagonist
            row.payload = run.model_dump_json()
            session.add(row)

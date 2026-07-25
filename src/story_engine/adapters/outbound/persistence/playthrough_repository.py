"""SQLite-backed playthrough repository — implements `PlaythroughRepositoryPort`.

Persists the run envelope so `POST /play` and `POST /play/{id}/act` — two separate HTTP requests,
possibly two separate processes — can share one run.

**What this stores, precisely:** the rendered turns already shown to this protagonist (each
`Turn`'s scene, citations and `withheld_count`) plus the live choice set `PlaythroughService.advance`
needs to resolve the player's next action (`_find_choice` looks a `ChoiceOption` up by id and applies
its `Consequence`) — so `Consequence` and `Citation.quote` are deliberately part of the payload, not
stripped from it. Without them, no choice could be applied after a reload, which defeats the entire
reason this repository exists.

**What this is NOT:** a second source of truth for canon, and NOT a read path for it. Canon facts
live in the canon store (`ports.canon_store`) and every FRESH read of canon — anything not already
rendered into a stored turn — goes through `store.visible_to()` / the spoiler guard
(`story_engine.domain.models.canon.is_visible`), never through this repository. This repository has
no method that returns a bare `Fact`; the only object it hands back is a `Playthrough`, and a caller
must never re-serialize a stored `Consequence`/`Citation` outward to an API client — those exist here
only so the service can apply the next choice, not to be republished.

**Known, deliberate limitation:** a transcript records what was shown to the player *at the time*.
If a fact underlying an already-rendered turn is later superseded or quarantined in the canon store,
the stored turn does not change retroactively — it is a historical record of a past render, not a
live view. Re-deriving already-shown turns from current canon on every read would also silently
rewrite a transcript the player already saw, which is worse. This is accepted as correct, not as a
bug to fix later.
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
            # ISO-8601 text preserves tzinfo; a native SQLite DateTime column would not
            # (see the comment on `PlaythroughRunRow.created_at`).
            created_at=datetime.now(UTC).isoformat(),
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

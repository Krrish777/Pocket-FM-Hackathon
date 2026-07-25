"""Playthrough-repository port — durability for a run BETWEEN requests.

`POST /play` and `POST /play/{id}/act` are separate HTTP requests, possibly separate processes.
This port is how the run survives the gap. It is emphatically NOT a second source of truth: canon
facts already live in the canon store (`ports.canon_store`), and everything this port persists is a
replayable *view* of a run over that store — never a duplicate of fact data.
"""

from typing import Protocol

from story_engine.domain.models.play import Playthrough


class PlaythroughRepositoryPort(Protocol):
    """Create, load, and overwrite a run envelope, keyed by an opaque `run_id`."""

    def create(self, run: Playthrough) -> str:
        """Persist a new run and return its freshly generated `run_id`."""
        ...

    def get(self, run_id: str) -> Playthrough | None:
        """Return the run for `run_id`, or `None` if no such run exists."""
        ...

    def save(self, run_id: str, run: Playthrough) -> None:
        """Overwrite the run stored at `run_id`.

        Raises:
            KeyError: `run_id` does not name an existing run — a save must never invent a row.
        """
        ...

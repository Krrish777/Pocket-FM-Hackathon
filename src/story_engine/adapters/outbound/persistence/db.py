"""SQLite engine + session lifecycle for the persistence adapters.

Outbound-adapter infrastructure: SQLModel/SQLAlchemy imports live here (never in `domain/`/`services/`).
`init_db` uses `create_all` (no Alembic for the hackathon); tables must be imported/registered first —
importing the `persistence` package does that. Adapted from the tiangolo template, restructured to our
conventions. See .claude/rules/structure.md.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine


def create_db_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine. SQLite needs `check_same_thread=False` for the ASGI server."""
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    """Create all registered tables. Call after the `persistence` package is imported."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Transactional session: commit on success, roll back on error, always close (fail loud)."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

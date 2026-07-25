"""SQLite persistence adapter (SQLModel).

Outbound adapter: SQLModel/SQLAlchemy live ONLY here. Importing this package registers the table
metadata (via the repository → tables import chain) so `init_db` can create everything.
"""

from story_engine.adapters.outbound.persistence.db import (
    create_db_engine,
    init_db,
    session_scope,
)
from story_engine.adapters.outbound.persistence.episode_log_repository import (
    SqliteEpisodeLogRepository,
)
from story_engine.adapters.outbound.persistence.playthrough_repository import (
    SqlitePlaythroughRepository,
)

__all__ = [
    "SqliteEpisodeLogRepository",
    "SqlitePlaythroughRepository",
    "create_db_engine",
    "init_db",
    "session_scope",
]

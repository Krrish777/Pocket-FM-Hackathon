"""Composition root — the ONLY module that imports concrete outbound adapters.

`build_container()` instantiates adapters and injects them into services. Both the API app factory
and the CLI call it, so `domain/` and `services/` stay free of vendor SDKs (Hard Constraint #7).
Swap adapters (SQLite, anthropic/openai, mem0) here — nowhere else. The SQLite engine is created and
its schema initialized here at startup (no Alembic for the hackathon).
"""

from dataclasses import dataclass

from sqlalchemy import Engine

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.in_memory import InMemoryStoryBibleRepository
from story_engine.adapters.outbound.persistence import (
    SqliteEpisodeLogRepository,
    create_db_engine,
    init_db,
)
from story_engine.adapters.outbound.stub_llm import StubLLM
from story_engine.config.settings import Settings, get_settings
from story_engine.observability.logging import configure_logging
from story_engine.services.episode_generator import EpisodeGenerator


@dataclass(frozen=True)
class Container:
    """Wired application services + shared resources, ready for an inbound adapter."""

    settings: Settings
    engine: Engine
    episode_generator: EpisodeGenerator


def build_container(settings: Settings | None = None) -> Container:
    """Build the application container (logging once, DB engine + schema, wired adapters)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.database_url)
    init_db(engine)  # create_all — tables registered via the persistence package import
    generator = EpisodeGenerator(
        llm=StubLLM(),  # swap for a real, cost-logging LLM adapter (deferred to the event brief)
        prompts=FilePromptStore("prompts"),
        bible=InMemoryStoryBibleRepository(),  # canonical store still in-memory for now
        episodes=SqliteEpisodeLogRepository(engine),  # episodic log persisted in SQLite
    )
    return Container(settings=settings, engine=engine, episode_generator=generator)

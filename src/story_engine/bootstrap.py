"""Composition root — the ONLY module that imports concrete outbound adapters.

`build_container()` instantiates adapters and injects them into services. Both the API app factory
and the CLI call it, so `domain/` and `services/` stay free of vendor SDKs (Hard Constraint #7).
Swap adapters (SQLite, anthropic/openai, mem0) here — nowhere else. The SQLite engine is created and
its schema initialized here at startup (no Alembic for the hackathon).

Wires the Knowledge Base (canon store, working memory, the turn loop) alongside the
pre-existing `EpisodeGenerator`, and seeds the demo fork from the source novel the first time the
store is empty — never a second time, and never when the novel PDF is absent (seeding then logs
and continues rather than crashing boot; the container must still come up for anything that does
not need the demo fork seeded).
"""

import logging
from dataclasses import dataclass

from sqlalchemy import Engine

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder
from story_engine.adapters.outbound.fanfic.branch_oracle_factory import (
    build_branch_oracle,
)
from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.in_memory import InMemoryStoryBibleRepository
from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.adapters.outbound.llm_factory import build_llm
from story_engine.adapters.outbound.persistence import (
    SqliteEpisodeLogRepository,
    SqlitePlaythroughRepository,
    create_db_engine,
    init_db,
)
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore
from story_engine.adapters.outbound.scripted_oracle import ScriptedBranchOracle
from story_engine.config.settings import Settings, get_settings
from story_engine.observability.logging import configure_logging
from story_engine.ports.llm import LLMPort
from story_engine.ports.playthrough_repository import PlaythroughRepositoryPort
from story_engine.resources.dexter_demo import CAST, FORK_ID
from story_engine.services.canon_ingest import CanonIngestService
from story_engine.services.demo_seed import (
    DEFAULT_NOVEL,
    DemoSeedError,
    demo_branches,
    seed_canon,
)
from story_engine.services.episode_generator import EpisodeGenerator
from story_engine.services.intent_router import IntentRouter
from story_engine.services.playthrough import PlaythroughService
from story_engine.services.working_memory import WorkingMemory
from story_engine.shared.errors import DocumentIngestionError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Container:
    """Wired application services + shared resources, ready for an inbound adapter."""

    settings: Settings
    engine: Engine
    episode_generator: EpisodeGenerator
    canon_store: SqliteCanonStore
    memory: WorkingMemory
    playthrough: PlaythroughService
    intent_router: IntentRouter
    llm: LLMPort
    playthrough_repository: PlaythroughRepositoryPort


def build_container(settings: Settings | None = None) -> Container:
    """Build the application container (logging once, DB engine + schema, wired adapters).

    Must stay callable with **no API key** whenever `settings.llm_provider == "scripted"` — the
    offline demo and the test suite both depend on booting without `OPENAI_API_KEY` set.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.database_url)
    init_db(engine)  # create_all — tables registered via the persistence package import

    llm = build_llm(settings)
    prompts = FilePromptStore("prompts")
    canon_store = SqliteCanonStore(engine)
    memory = WorkingMemory(canon_store)

    _seed_demo_fork_if_empty(canon_store, engine)

    oracle = build_branch_oracle(
        settings, fallback=ScriptedBranchOracle(demo_branches())
    )
    playthrough = PlaythroughService(
        store=canon_store,
        memory=memory,
        oracle=oracle,
        llm=llm,
        prompts=prompts,
        cast=CAST,
        model=settings.default_model,
    )
    intent_router = IntentRouter(llm=llm, prompts=prompts, model=settings.intent_model)
    playthrough_repository = SqlitePlaythroughRepository(engine)

    generator = EpisodeGenerator(
        llm=llm,
        prompts=prompts,
        bible=InMemoryStoryBibleRepository(),  # canonical store still in-memory for now
        episodes=SqliteEpisodeLogRepository(engine),  # episodic log persisted in SQLite
    )
    return Container(
        settings=settings,
        engine=engine,
        episode_generator=generator,
        canon_store=canon_store,
        memory=memory,
        playthrough=playthrough,
        intent_router=intent_router,
        llm=llm,
        playthrough_repository=playthrough_repository,
    )


def build_canon_ingest_service(container: Container) -> CanonIngestService:
    """Build a `CanonIngestService` over the same store/engine the container already wired.

    Kept out of `Container` itself: ingestion is an occasional, explicit operation (seeding,
    `story-engine reconcile`), not something every request path needs a handle to.
    """
    return CanonIngestService(
        store=container.canon_store,
        vectors=SqliteVectorStore(container.engine),
        embedder=HashingEmbedder(),
    )


def _seed_demo_fork_if_empty(store: SqliteCanonStore, engine: Engine) -> None:
    """Seed the demo fork's canon (and its vector index) the first time the store is empty.

    Checked by presence of any fact in `FORK_ID`, never attempted a second time. Missing the
    source novel is not a boot failure: it is logged and skipped, because most of the container
    (the API, harvesting, episode generation) needs none of the demo fork's seeded canon.

    Raises:
        Nothing — every failure mode here is caught and logged; a broken demo seed must not
        prevent the rest of the application from booting.
    """
    if store.all_facts(FORK_ID):
        return

    if not DEFAULT_NOVEL.exists():
        logger.info(
            "demo fork %r has no facts and the source novel is absent at %s; "
            "skipping seed — the demo fork will stay empty until it is seeded manually",
            FORK_ID,
            DEFAULT_NOVEL,
        )
        return

    try:
        seed_canon(store, PdfDocumentSource(), DEFAULT_NOVEL)
    except (DemoSeedError, DocumentIngestionError):
        # `seed_canon` itself raises `DemoSeedError` (a missing chapter, an anchor whose offsets
        # have drifted, or a slice that no longer contains its `must_contain` sentinel — see
        # services/demo_seed.py); `DocumentIngestionError` is what `PdfDocumentSource.read_chapters`
        # raises before `seed_canon` gets a chance to. Both are reachable from this call and
        # neither is a subclass of the other (both are siblings under `StoryEngineError`), so both
        # are named here explicitly rather than caught via a shared, broader ancestor.
        logger.exception(
            "demo fork %r could not be seeded: the novel at %s failed to ingest",
            FORK_ID,
            DEFAULT_NOVEL,
        )
        return

    # `seed_canon` already wrote the facts to canon (canon-first is satisfied by construction);
    # `reconcile` is the vector-second half of the same unit of work. Using it rather than
    # `CanonIngestService.ingest` avoids re-appending facts `seed_canon` already wrote — a
    # second `append` of the same fact id would collide on the canon store's primary key.
    ingest = CanonIngestService(
        store=store,
        vectors=SqliteVectorStore(engine),
        embedder=HashingEmbedder(),
    )
    repaired, still_missing = ingest.reconcile(FORK_ID)
    if still_missing:
        logger.error(
            "demo fork %r seeded, but %d fact(s) failed to index in the vector lane; "
            "run `story-engine reconcile --fork %s` to repair",
            FORK_ID,
            still_missing,
            FORK_ID,
        )
    else:
        logger.info(
            "demo fork %r seeded and indexed (%d fact(s) newly indexed)",
            FORK_ID,
            repaired,
        )

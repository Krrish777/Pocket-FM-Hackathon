"""The retrieval lane, packaged as one callable so an eval can exercise the real thing.

This is deliberately *not* a reimplementation of retrieval for eval purposes. It wires the same
adapters the product uses — `PdfDocumentSource` → `chunk_text` → `SqliteVectorStore` — so a score
here is a statement about the shipped path, not about a test double.

The index is built once per process and cached: ingesting the novel is ~400k characters and 523
embeddings, which is fine once and intolerable per golden.

**No generator.** There is no LLM adapter in this repo yet (`StubLLM` is all there is), so this
exposes the retriever alone. That constrains which metrics can run — see `metrics.py`.
"""

import logging
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder
from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore
from story_engine.domain.chunking import chunk_text
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.domain.models.canon import Awareness

logger = logging.getLogger(__name__)

NOVEL = Path("data/external/Darkly-Dreaming-Dexter-1.pdf")
SOURCE_ID = "darkly-dreaming-dexter"
FORK = "canon"
INGESTED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)

LAST_CHAPTER = 27
"""Story-time cutoff used by evals that mean "the whole book is on the table"."""


class CanonRetriever:
    """Ingests the novel once, then answers queries through the real vector lane."""

    def __init__(self, novel: Path = NOVEL, index_path: Path | None = None) -> None:
        self._embedder = HashingEmbedder()
        db = index_path or Path("evals/.canon_index.db")
        db.parent.mkdir(parents=True, exist_ok=True)
        fresh = not db.exists()
        engine = create_engine(f"sqlite:///{db}")
        SQLModel.metadata.create_all(engine)
        self._store = SqliteVectorStore(engine)
        if fresh:
            self._ingest(novel)

    def _ingest(self, novel: Path) -> None:
        chapters = PdfDocumentSource().read_chapters(novel)
        indexed = 0
        for chapter in chapters:
            for position, span in enumerate(chunk_text(chapter.text)):
                self._store.add(
                    Fact(
                        id=f"{SOURCE_ID}-{chapter.index}-{position}",
                        fork_id=FORK,
                        subject_id="dexter",
                        predicate="narrated_in",
                        object_literal=f"chapter-{chapter.index}",
                        valid_from=chapter.index,
                        revealed_at=chapter.index,
                        assertion_mode=AssertionMode.NARRATED,
                        knower_scope=(
                            Awareness(knower=AUDIENCE, learned_at=chapter.index),
                        ),
                        provenance=Provenance(
                            source_id=SOURCE_ID,
                            chapter=chapter.index,
                            char_start=span.char_start,
                            char_end=span.char_end,
                            quote=span.quote,
                        ),
                        confidence=1.0,
                        tier=0,
                        status=FactStatus.ACTIVE,
                        recorded_at=INGESTED_AT,
                    ),
                    span.quote,
                    self._embedder.embed(span.quote),
                )
                indexed += 1
        logger.info("indexed %d spans from %d chapters", indexed, len(chapters))

    def retrieve(
        self,
        query: str,
        *,
        k: int = 5,
        knower: str = AUDIENCE,
        chapter: int = LAST_CHAPTER,
    ) -> list[str]:
        """Return the passages the retriever surfaces for `query`, most similar first.

        `knower` and `chapter` are not decoration: retrieval is spoiler-guarded, so the same query
        legitimately returns different passages for a different character at a different point in
        the telling. An eval that ignored them would be scoring a system we do not ship.
        """
        hits = self._store.search(FORK, self._embedder.embed(query), knower, chapter, k)
        return [hit.text for hit in hits]


@lru_cache(maxsize=1)
def get_retriever() -> CanonRetriever:
    """The process-wide retriever, built on first use."""
    return CanonRetriever()

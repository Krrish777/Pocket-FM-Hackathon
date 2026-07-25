"""`story-engine ingest` — a novel PDF, at real depth, through the one write path.

Reads a novel, chunks every chapter into citable spans (`domain/chunking.py`), turns each span
into a `Fact`, and hands the whole batch to `CanonIngestService.ingest` — the SAME write path
`services/demo_seed.py` uses for the hand-anchored demo facts, and the same one `reconcile`
repairs. This command exists to bootstrap the knowledge base at novel-length depth instead of a
handful of hand-placed anchors, so the three lanes (canon store, vector index, graph projection)
can be proven to agree over something resembling the real book.

Two families of fact are produced, deliberately narrow so this stays honest about what it does:

1. **Narration spans** — one fact per chunk, citable back to its exact chapter offsets. These are
   what make the ingested canon a real receipt rather than a summary.
2. **Character appearances** — one fact per (character, chapter) the first time a cast member's
   name surfaces in that chapter's text, `subject_id -> appears_in -> chapter-N`. These carry an
   `object_id` (narration spans deliberately do not — a span is an attribute of a chapter, not a
   relation between two entities), which is what gives the graph projection real edges to build
   and the guard-parity check something to traverse.

Both families are UNTRACKED (`knower_scope=None`): visibility is governed by `revealed_at` alone,
gating every knower identically once the telling reaches that chapter — the same shape
`tests/e2e/test_ingestion_citation_e2e.py` already exercises. This command does not attempt to
infer WHO privately knows what; that is what `resources/dexter_demo.py`'s hand-authored `ANCHORS`
are for. Two write paths producing two kinds of fact side by side is intentional: hand-anchored
secrets stay reviewable, bulk narration depth comes from here.
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import typer
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder
from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore
from story_engine.domain.chunking import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, chunk_text
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import Fact, Provenance
from story_engine.domain.models.document import SourceChapter
from story_engine.resources.dexter_demo import CAST
from story_engine.services.canon_ingest import CanonIngestService
from story_engine.shared.errors import IngestDriftError

logger = logging.getLogger(__name__)

DEFAULT_DB = Path("data/interim/canon_ingest.db")
NARRATION_SUBJECT = "narration"
NARRATION_PREDICATE = "narrated_in"
APPEARANCE_PREDICATE = "appears_in"


def _narration_facts(
    chapter: SourceChapter,
    *,
    source_id: str,
    fork_id: str,
    chunk_size: int,
    overlap: int,
    recorded_at: datetime,
) -> list[Fact]:
    """One citable fact per chunk of a chapter's text, gated by `revealed_at` alone."""
    facts: list[Fact] = []
    for position, span in enumerate(
        chunk_text(chapter.text, chunk_size=chunk_size, overlap=overlap)
    ):
        facts.append(
            Fact(
                id=f"{source_id}-ch{chapter.index}-span{position}",
                fork_id=fork_id,
                subject_id=NARRATION_SUBJECT,
                predicate=NARRATION_PREDICATE,
                object_literal=f"chapter-{chapter.index}",
                valid_from=chapter.index,
                revealed_at=chapter.index,
                assertion_mode=AssertionMode.NARRATED,
                knower_scope=None,
                provenance=Provenance(
                    source_id=source_id,
                    chapter=chapter.index,
                    char_start=span.char_start,
                    char_end=span.char_end,
                    quote=span.quote,
                ),
                confidence=1.0,
                tier=0,
                status=FactStatus.ACTIVE,
                recorded_at=recorded_at,
            )
        )
    return facts


def _appearance_facts(
    chapter: SourceChapter,
    *,
    source_id: str,
    fork_id: str,
    chunk_size: int,
    overlap: int,
    recorded_at: datetime,
) -> list[Fact]:
    """One fact per cast member whose name first surfaces in this chapter.

    Gives the graph projection real `subject -> object` edges to traverse (narration facts
    carry only an `object_literal`, which `LoreGraph.from_facts` deliberately excludes — a
    literal-valued fact is an attribute, not a relation). Detection is a plain word-boundary
    name match, not NLP: good enough to prove the three lanes agree, not a claim about
    entity-extraction quality.
    """
    facts: list[Fact] = []
    seen: set[str] = set()
    for span in chunk_text(chapter.text, chunk_size=chunk_size, overlap=overlap):
        lowered = span.quote.lower()
        for key, full_name in CAST.items():
            if key in seen:
                continue
            first_name = full_name.split()[0]
            if not (
                re.search(rf"\b{re.escape(key)}\b", lowered)
                or re.search(rf"\b{re.escape(first_name.lower())}\b", lowered)
            ):
                continue
            seen.add(key)
            facts.append(
                Fact(
                    id=f"{source_id}-ch{chapter.index}-appears-{key}",
                    fork_id=fork_id,
                    subject_id=key,
                    predicate=APPEARANCE_PREDICATE,
                    object_id=f"chapter-{chapter.index}",
                    valid_from=chapter.index,
                    revealed_at=chapter.index,
                    assertion_mode=AssertionMode.NARRATED,
                    knower_scope=None,
                    provenance=Provenance(
                        source_id=source_id,
                        chapter=chapter.index,
                        char_start=span.char_start,
                        char_end=span.char_end,
                        quote=span.quote,
                    ),
                    confidence=0.6,
                    tier=0,
                    status=FactStatus.ACTIVE,
                    recorded_at=recorded_at,
                )
            )
    return facts


def build_facts_from_novel(
    novel: Path,
    *,
    source_id: str,
    fork_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    recorded_at: datetime | None = None,
    max_chapters: int | None = None,
) -> list[Fact]:
    """Read a novel PDF and turn it into `Fact`s, ready for `CanonIngestService.ingest`.

    Args:
        novel: Path to the novel PDF.
        source_id: `Provenance.source_id` stamped on every produced fact.
        fork_id: Which fork the facts belong to.
        chunk_size: Passed through to `chunk_text`.
        overlap: Passed through to `chunk_text`.
        recorded_at: Record time stamped on every fact. Defaults to now (UTC).
        max_chapters: Ingest only the first N chapters. `None` (the CLI default) ingests the
            whole book — this exists so tests can bound the scope of what they exercise
            without capping the CLI itself.

    Raises:
        DocumentIngestionError: `PdfDocumentSource.read_chapters` found no chapter headings, the
            file is missing, or it holds no extractable text. Never caught here — a document
            that cannot be chaptered must not be silently ingested as one fake chapter (see
            `PdfDocumentSource`'s docstring).
    """
    chapters = PdfDocumentSource().read_chapters(novel)
    if max_chapters is not None:
        chapters = chapters[:max_chapters]
    stamp = recorded_at or datetime.now(UTC)

    facts: list[Fact] = []
    for chapter in chapters:
        facts.extend(
            _narration_facts(
                chapter,
                source_id=source_id,
                fork_id=fork_id,
                chunk_size=chunk_size,
                overlap=overlap,
                recorded_at=stamp,
            )
        )
        facts.extend(
            _appearance_facts(
                chapter,
                source_id=source_id,
                fork_id=fork_id,
                chunk_size=chunk_size,
                overlap=overlap,
                recorded_at=stamp,
            )
        )
    return facts


def build_ingest_service(
    db: Path,
) -> tuple[CanonIngestService, SqliteCanonStore, SqliteVectorStore]:
    """Wire a `CanonIngestService` over its own SQLite file — a local factory, not the shared
    container.

    Deliberately does not go through `bootstrap.build_container()`: that composition root also
    seeds the demo fork the first time its store is empty, which is behaviour this command has
    no business triggering as a side effect of an explicit full-novel ingest. Mirrors
    `cli/play.py`'s existing pattern of building its own engine from a `--db` option.
    """
    db.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)
    vectors = SqliteVectorStore(engine)
    service = CanonIngestService(
        store=store, vectors=vectors, embedder=HashingEmbedder()
    )
    return service, store, vectors


def register(app: typer.Typer) -> None:
    """Attach the `ingest` command to the CLI app."""

    @app.command()
    def ingest(
        novel: Path = typer.Option(
            ..., "--novel", help="Path to the novel PDF to ingest."
        ),
        db: Path = typer.Option(
            DEFAULT_DB,
            "--db",
            help="SQLite file to ingest into. To serve these facts from the running API/CLI "
            "container (not just this command), set DATABASE_URL=sqlite:///<this path> — "
            "`bootstrap.build_container` reads `settings.database_url` and will NOT re-seed or "
            "duplicate facts if this fork already has any.",
        ),
        fork: str = typer.Option("canon", "--fork", help="Fork to write facts into."),
        source_id: str = typer.Option(
            "darkly-dreaming-dexter", "--source-id", help="Provenance source id."
        ),
        chunk_size: int = typer.Option(DEFAULT_CHUNK_SIZE, "--chunk-size"),
        overlap: int = typer.Option(DEFAULT_OVERLAP, "--overlap"),
        max_chapters: int | None = typer.Option(
            None,
            "--max-chapters",
            help="Ingest only the first N chapters. Unset ingests the whole book — a full run "
            "may be slow, which is expected; this flag exists for quick smoke runs, not as a "
            "silent cap.",
        ),
    ) -> None:
        """Ingest a novel PDF into canon at real depth, through `CanonIngestService`.

        Reports facts written and whether the canon and vector lanes ended up in sync.
        """
        logging.basicConfig(
            level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
        )

        facts = build_facts_from_novel(
            novel,
            source_id=source_id,
            fork_id=fork,
            chunk_size=chunk_size,
            overlap=overlap,
            max_chapters=max_chapters,
        )
        chapters_seen = len({fact.provenance.chapter for fact in facts})
        typer.echo(f"Chunked {len(facts)} fact(s) across {chapters_seen} chapter(s).")

        service, store, vectors = build_ingest_service(db)

        written = len(facts)
        try:
            written = service.ingest(facts)
        except IngestDriftError as exc:
            typer.echo(
                f"WARNING: {len(exc.orphan_fact_ids)} fact(s) written to canon but not "
                f"indexed in the vector lane. Run `story-engine reconcile --fork {fork}` "
                "to repair."
            )

        canon_count = len(store.all_facts(fork))
        vector_count = len(vectors.ids(fork))
        typer.echo(f"Facts written to canon : {written}")
        typer.echo(f"Canon lane total       : {canon_count}")
        typer.echo(f"Vector lane total      : {vector_count}")
        if canon_count == vector_count:
            typer.echo("Lanes synced: canon and vector fact counts match.")
        else:
            typer.echo(
                f"Lanes DIVERGED: canon={canon_count} vector={vector_count}. "
                f"Run `story-engine reconcile --fork {fork}`."
            )
            raise typer.Exit(code=1)

        typer.echo(
            "\nThis novel is now on disk, but NOT yet served by the running API/CLI unless you "
            "point it at this file. To serve the full novel:\n"
            f"  DATABASE_URL=sqlite:///{db}\n"
            "`bootstrap.build_container` reads `settings.database_url` (env `DATABASE_URL`) to "
            "open the canon store, so setting it before starting the API or `story-engine play` "
            "serves exactly what was just ingested. It will NOT re-seed the demo fork or "
            f"duplicate facts, because fork {fork!r} already has some."
        )

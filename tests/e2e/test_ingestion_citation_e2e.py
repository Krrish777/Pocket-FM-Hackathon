"""L3 — the receipt, proven end to end: a PDF on disk becomes a fact you can cite back to it.

`project_context.md` §5.4 makes one hard promise — *"every fact is checked, and we show you the
receipt"* — and that promise is a chain, not a component. It only holds if a character offset
recorded during ingestion still lands on the right words after the fact has been through Pydantic,
SQLite's text encoding, an engine restart, and a fresh re-read of the source document.

Every link is exercised for real: a real PDF (not a fixture string), real PyMuPDF extraction, the
real chunker, a real on-disk store, a genuine restart, and finally the *source document re-opened
from scratch* to confirm the quote still resolves. Deliberately one long test — each link passing
in isolation would not prove the chain, which is the only thing anyone cares about here.
"""

from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.chunking import chunk_text
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.domain.models.canon import Awareness

pytestmark = pytest.mark.e2e

INGESTED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
SOURCE_ID = "dexter-novel-1"

CHAPTERS = [
    "Chapter 1: Night Work\n"
    "Dexter kept the slides in a rosewood box beneath the air conditioner. "
    "He counted them twice before the sun came up, and the Passenger counted with him. "
    "Nobody in the department had ever asked what was in the box.",
    "Chapter 2: Deborah\n"
    "Deborah asked about the harbour again over breakfast. "
    "She did not know about the box, and Dexter intended to keep it that way. "
    "She talked instead about the case files that would not close.",
    "Chapter 3: Doakes\n"
    "Doakes watched from the far side of the parking lot and said nothing at all. "
    "He had begun to suspect what Deborah still could not see.",
]


def _write_novel(path: Path) -> Path:
    """Render the chapters into a genuine multi-page PDF."""
    document = pymupdf.open()
    for body in CHAPTERS:
        page = document.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    document.save(path)
    document.close()
    return path


def test_a_fact_ingested_from_a_pdf_can_be_cited_back_to_it(tmp_path: Path) -> None:
    """PDF -> chapter -> chunk -> Provenance -> SQLite -> restart -> resolve against the source."""
    novel = _write_novel(tmp_path / "dexter.pdf")
    db = tmp_path / "canon.db"

    # --- 1. INGEST: read the novel and turn its chapters into citable facts ------------------
    reader = PdfDocumentSource()
    chapters = reader.read_chapters(novel)
    assert len(chapters) == 3, (
        "the reader must find every chapter before anything else matters"
    )

    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)

    expected_quotes: dict[str, str] = {}
    for chapter in chapters:
        for position, span in enumerate(
            chunk_text(chapter.text, chunk_size=120, overlap=30)
        ):
            fact_id = f"f-ch{chapter.index}-{position}"
            expected_quotes[fact_id] = span.quote
            store.append(
                Fact(
                    id=fact_id,
                    fork_id="canon",
                    subject_id="dexter",
                    predicate="narrated_in",
                    object_literal=f"chapter-{chapter.index}",
                    valid_from=chapter.index,
                    # The audience learns each passage exactly when its chapter is told, which is
                    # what lets the guard assertion below mean something.
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
                )
            )

    assert expected_quotes, "ingestion produced no facts at all"

    # --- 2. RESTART: dispose every pooled connection and reopen a fresh engine ---------------
    engine.dispose()
    reopened = SqliteCanonStore(create_engine(f"sqlite:///{db}"))

    # --- 3. THE RECEIPT: the stored offsets still land on the right words in the real novel --
    # Re-read the PDF from scratch rather than reusing `chapters`: a citation that only resolves
    # against an in-memory copy of the source is not a citation, it is a cache.
    rereads = {chapter.index: chapter.text for chapter in reader.read_chapters(novel)}

    for fact_id, quote in expected_quotes.items():
        fact = reopened.get(fact_id)
        assert fact is not None, f"{fact_id} did not survive the restart"

        source_text = rereads[fact.provenance.chapter]
        resolved = source_text[fact.provenance.char_start : fact.provenance.char_end]

        assert resolved == fact.provenance.quote == quote, (
            f"{fact_id} cites chapter {fact.provenance.chapter} "
            f"[{fact.provenance.char_start}:{fact.provenance.char_end}] but those characters "
            f"read {resolved!r}, not {fact.provenance.quote!r} — the receipt does not resolve"
        )

    # --- 4. THE GUARD: ingested facts obey the spoiler guard like any other ------------------
    # Ingestion is not a side door into the store. A reader at chapter 1 must not be handed
    # chapter 3's passages, or the whole epistemic claim collapses at the point of ingest.
    visible_at_one = reopened.visible_to("canon", AUDIENCE, 1)
    assert visible_at_one, "chapter 1 passages should be visible at chapter 1"
    assert {f.provenance.chapter for f in visible_at_one} == {1}

    visible_at_three = reopened.visible_to("canon", AUDIENCE, 3)
    assert {f.provenance.chapter for f in visible_at_three} == {1, 2, 3}


def test_every_ingested_passage_is_citable(tmp_path: Path) -> None:
    """No chapter may ingest to zero facts — a silently empty chapter is unrecoverable later.

    The session-6 audit's finding was exactly this shape: works shipped truncated with nothing
    marking the gap. A chapter that produces no facts looks identical to a chapter with nothing
    worth saying, so it is asserted here rather than discovered during the demo.
    """
    novel = _write_novel(tmp_path / "dexter.pdf")

    chapters = PdfDocumentSource().read_chapters(novel)

    for chapter in chapters:
        spans = chunk_text(chapter.text, chunk_size=120, overlap=30)
        assert spans, f"chapter {chapter.index} produced no citable spans"
        for span in spans:
            Provenance(
                source_id=SOURCE_ID,
                chapter=chapter.index,
                char_start=span.char_start,
                char_end=span.char_end,
                quote=span.quote,
            )

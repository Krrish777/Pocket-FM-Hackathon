"""The PDF reader is tested against real PDFs it builds itself, never against a mocked PyMuPDF.

Mocking the parser would test our regexes against a string we typed, which is the one thing that
cannot fail. Every test here writes a genuine PDF to `tmp_path`, reads it back through PyMuPDF, and
asserts on what actually survived the round trip — the same discipline the canon-store tests use.
"""

from pathlib import Path

import pymupdf
import pytest

from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.domain.chunking import chunk_text
from story_engine.shared.errors import DocumentIngestionError


def _write_pdf(path: Path, pages: list[str]) -> Path:
    """Render one text block per page into a real PDF."""
    document = pymupdf.open()
    for body in pages:
        page = document.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    document.save(path)
    document.close()
    return path


def _novel(path: Path) -> Path:
    return _write_pdf(
        path,
        [
            "Chapter 1: The Ice Truck\nDexter kept the slides in a rosewood box.\n"
            "He counted them twice before the sun came up.",
            "Chapter 2: Deborah\nDeborah did not know about the box.\n"
            "She asked about the harbour instead.",
            "Chapter 3\nDoakes watched from the far side of the lot.",
        ],
    )


def test_reads_every_chapter_in_order(tmp_path: Path) -> None:
    chapters = PdfDocumentSource().read_chapters(_novel(tmp_path / "novel.pdf"))

    assert [c.index for c in chapters] == [1, 2, 3]
    assert "rosewood box" in chapters[0].text
    assert "harbour" in chapters[1].text
    assert "far side of the lot" in chapters[2].text


def test_captures_the_chapter_title_when_the_heading_carries_one(
    tmp_path: Path,
) -> None:
    chapters = PdfDocumentSource().read_chapters(_novel(tmp_path / "novel.pdf"))

    assert chapters[0].title == "The Ice Truck"
    assert chapters[1].title == "Deborah"
    assert chapters[2].title is None  # "Chapter 3" carries no title


def test_the_heading_line_is_not_part_of_the_chapter_body(tmp_path: Path) -> None:
    """A citation quoting "Chapter 2: Deborah" as narration would be nonsense."""
    chapters = PdfDocumentSource().read_chapters(_novel(tmp_path / "novel.pdf"))

    for chapter in chapters:
        assert not chapter.text.lower().startswith("chapter")


def test_chapters_are_renumbered_densely_from_one(tmp_path: Path) -> None:
    """A prologue must not leave a hole in the sequence — ChapterIndex must be dense and rising.

    The printed numbering is untrustworthy: novels restart at "Book Two", skip numbers, or open
    with an unnumbered prologue. Downstream, `visible_to(..., chapter)` compares these as ordinals.
    """
    path = _write_pdf(
        tmp_path / "prologue.pdf",
        [
            "Part One\nBefore any of it began, there was the boat.",
            "Chapter 7\nThe numbering in this book is a lie.",
            "Chapter 9\nAnd it stays a lie.",
        ],
    )

    chapters = PdfDocumentSource().read_chapters(path)

    assert [c.index for c in chapters] == [1, 2, 3]


def test_offsets_from_chunking_resolve_against_the_chapter_text(tmp_path: Path) -> None:
    """The end-to-end citation guarantee: chapter text in, resolvable quote out.

    This is the property the whole receipt rests on — if it holds, every fact extracted from this
    chapter can be traced back to the exact characters it came from.
    """
    chapters = PdfDocumentSource().read_chapters(_novel(tmp_path / "novel.pdf"))

    for chapter in chapters:
        for span in chunk_text(chapter.text, chunk_size=60, overlap=15):
            assert chapter.text[span.char_start : span.char_end] == span.quote


def test_a_missing_file_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(DocumentIngestionError, match="not found"):
        PdfDocumentSource().read_chapters(tmp_path / "absent.pdf")


def test_a_pdf_with_no_extractable_text_fails_loudly(tmp_path: Path) -> None:
    """A scanned novel needs OCR. Returning zero chapters would look like an empty book."""
    path = tmp_path / "scanned.pdf"
    document = pymupdf.open()
    document.new_page()  # a page with no text at all
    document.save(path)
    document.close()

    with pytest.raises(DocumentIngestionError, match="no extractable text"):
        PdfDocumentSource().read_chapters(path)


def test_a_document_without_chapters_is_refused_by_default(tmp_path: Path) -> None:
    """Collapsing to one chapter would silently reveal the whole book to every character.

    The spoiler guard gates on chapter. Stamping every fact `chapter=1` leaves the guard running,
    its tests green, and the entire novel visible from turn one — so this must not degrade quietly.
    """
    path = _write_pdf(
        tmp_path / "flat.pdf", ["There are no headings anywhere in this document."]
    )

    with pytest.raises(DocumentIngestionError, match="No chapter headings"):
        PdfDocumentSource().read_chapters(path)


def test_a_single_chapter_document_is_allowed_when_asked_for_explicitly(
    tmp_path: Path,
) -> None:
    path = _write_pdf(
        tmp_path / "flat.pdf", ["There are no headings anywhere in this document."]
    )

    chapters = PdfDocumentSource(allow_single_chapter=True).read_chapters(path)

    assert len(chapters) == 1
    assert chapters[0].index == 1
    assert "no headings" in chapters[0].text


def test_a_table_of_contents_line_does_not_become_a_chapter(tmp_path: Path) -> None:
    """Found by running the real novel, not by imagining a case.

    `Darkly-Dreaming-Dexter-1.pdf` opens with a contents line reading `Chapter 1 thru Chapter 27`,
    which matched the heading pattern and produced a 28th chapter holding the copyright page — so
    every real chapter was shifted by one. That is not cosmetic: the spoiler guard gates on
    `chapter`, so an off-by-one moves every reveal boundary in the book. All the synthetic fixtures
    stayed green throughout, because none of them had a table of contents.
    """
    path = _write_pdf(
        tmp_path / "with_toc.pdf",
        [
            "Chapter 1 thru Chapter 27\nThis book is a work of fiction. Any resemblance is "
            "coincidental.",
            "Chapter 1\nMoon. Glorious moon. The night was as light as day.",
            "Chapter 2\nDeborah asked about the harbour again.",
        ],
    )

    chapters = PdfDocumentSource().read_chapters(path)

    assert len(chapters) == 2, "the contents line must not open a chapter of its own"
    assert chapters[0].text.startswith("Moon."), (
        "chapter 1 must be the real first chapter"
    )


def test_the_word_chapter_mid_sentence_does_not_open_a_chapter(tmp_path: Path) -> None:
    """The unanchored-pattern trap: session 6 found exactly this bug in the scraper's stripper."""
    path = _write_pdf(
        tmp_path / "inline.pdf",
        [
            "Chapter 1\nHe closed that chapter 2 of his life and never spoke of it again.\n"
            "The next part chapter three would have to wait.",
        ],
    )

    chapters = PdfDocumentSource().read_chapters(path)

    assert len(chapters) == 1

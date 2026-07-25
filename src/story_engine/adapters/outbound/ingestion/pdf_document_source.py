"""PyMuPDF-backed document reader — a novel PDF in, citable chapters out.

Adapted from `patchy631/ai-engineering-hub/notebook-lm-clone` (MIT, © 2024 patchy631), which
supplied the extraction shape: open with PyMuPDF, pull text page by page, skip pages that carry
no text, and keep positional metadata so a retrieved passage can name where it came from.

What changed, and why:

* **Chapters, not pages.** Upstream tagged each chunk with a page number. `Provenance` addresses by
  `chapter`, and — decisively — the spoiler guard gates visibility on chapter
  (`store.visible_to(fork, knower, chapter)`). A page number cannot answer "had this been revealed
  yet?"; a chapter can. Pages are a printing artifact, so we detect chapter headings and discard
  pagination entirely.
* **Offsets are continuous within a chapter.** Upstream restarted character offsets on every page,
  which makes an offset meaningless unless the page travels with it. Here a chapter is one string
  and offsets run through it, so `(source_id, chapter, char_start, char_end)` resolves on its own.
* **Failure is loud.** Upstream logged and continued past unreadable files. See
  `DocumentIngestionError` below for why silently degrading is worse than not ingesting at all.

The vendor import is confined to this module; services depend on `DocumentSourcePort`.
"""

import logging
import re
from pathlib import Path

import pymupdf

from story_engine.domain.models.document import SourceChapter
from story_engine.shared.errors import DocumentIngestionError

logger = logging.getLogger(__name__)

_WORD_NUMBERS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    "fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty"
)

_CHAPTER_HEADING = re.compile(
    rf"^[ \t]*(?:chapter|part|book)[ \t]+(?:\d{{1,3}}|[ivxlcdm]{{1,7}}|{_WORD_NUMBERS})"
    rf"[ \t]*[.:—-]?[ \t]*(?P<title>.*)$",
    re.IGNORECASE | re.MULTILINE,
)
"""Matches a chapter heading line and captures any title that trails it on the same line.

Anchored to a whole line (MULTILINE) so the word "chapter" inside a sentence cannot open a new
chapter — the same anchoring mistake the session-6 audit found in the scraper's boilerplate
stripper, where an unanchored pattern deleted real narration.
"""

_NUMERIC_HEADING = re.compile(r"^[ \t]*(?:\d{1,3}|[IVXLCDM]{1,7})[ \t]*$", re.MULTILINE)
"""A bare number alone on a line — how many novels mark chapters. Case-sensitive for roman
numerals so a line containing only the word "I" is not mistaken for chapter 1."""

_CHAPTER_REFERENCE = re.compile(
    r"(?:chapter|part|book)[ \t]+(?:\d|[ivxlcdm])", re.IGNORECASE
)
"""A second chapter reference *inside* a heading's trailing title — the signature of a
table-of-contents line rather than a chapter opening.

Found by running the real novel: `Darkly-Dreaming-Dexter-1.pdf` opens with a contents line reading
`Chapter 1 thru ... Chapter 27`, which matched `_CHAPTER_HEADING` and became a 28th chapter holding
the copyright page. A real chapter opening never names another chapter on its own line, and the
consequence of letting one through is not cosmetic: it shifts every subsequent `ChapterIndex` by
one, and the spoiler guard gates on exactly that number, so every reveal boundary in the book moves.
"""


class PdfDocumentSource:
    """Reads a PDF into chapters using PyMuPDF. Implements `DocumentSourcePort`.

    Args:
        allow_single_chapter: Permit a document with no detectable chapter headings to be returned
            as one chapter. Off by default — see `read_chapters` for the reasoning.
    """

    def __init__(self, *, allow_single_chapter: bool = False) -> None:
        self._allow_single_chapter = allow_single_chapter

    def read_chapters(self, path: Path) -> list[SourceChapter]:
        """Extract chapters from a PDF.

        Args:
            path: The PDF to read.

        Returns:
            Chapters in reading order, renumbered densely from 1. Renumbered rather than trusting
            the printed number so a prologue, an unnumbered interlude, or a restart at "Book Two"
            still yields a strictly increasing `ChapterIndex`. The printed heading survives in
            `title`.

        Raises:
            DocumentIngestionError: If the file is missing, unreadable, holds no extractable text
                (a scanned/image-only PDF is the usual cause — it needs OCR, not this reader), or
                exposes no chapter structure while `allow_single_chapter` is False.
        """
        text = self._extract_text(path)
        chapters = self._split_into_chapters(text)

        if not chapters:
            if not self._allow_single_chapter:
                raise DocumentIngestionError(
                    f"No chapter headings found in {path.name}. Every fact ingested from it would "
                    f"be stamped chapter 1, and the spoiler guard gates on chapter — so the whole "
                    f"document would become visible to every character at once. Pass "
                    f"allow_single_chapter=True only if this document genuinely has one chapter."
                )
            logger.warning(
                "No chapter headings in %s; ingesting as a single chapter", path.name
            )
            return [SourceChapter(index=1, title=None, text=text)]

        return chapters

    def _extract_text(self, path: Path) -> str:
        """Pull every page's text into one string, joined by form feeds."""
        if not path.exists():
            raise DocumentIngestionError(f"Document not found: {path}")

        try:
            with pymupdf.open(path) as document:
                pages = [page.get_text() for page in document]
        except DocumentIngestionError:
            raise
        except (
            Exception
        ) as err:  # PyMuPDF raises bare exception types for corrupt files
            raise DocumentIngestionError(f"Could not read {path.name}: {err}") from err

        text = "\n".join(pages)
        if not text.strip():
            raise DocumentIngestionError(
                f"{path.name} yielded no extractable text across {len(pages)} pages. "
                f"It is most likely a scanned or image-only PDF, which needs OCR first."
            )

        logger.info(
            "Extracted %d characters from %d pages of %s",
            len(text),
            len(pages),
            path.name,
        )
        return text

    def _split_into_chapters(self, text: str) -> list[SourceChapter]:
        """Cut the document at chapter headings, dropping front matter before the first one."""
        headings = sorted(
            [
                (m.start(), m.end(), (m.group("title") or "").strip())
                for m in _CHAPTER_HEADING.finditer(text)
                # A heading naming another chapter is a contents line, not a chapter opening.
                if not _CHAPTER_REFERENCE.search(m.group("title") or "")
            ]
            + [(m.start(), m.end(), "") for m in _NUMERIC_HEADING.finditer(text)]
        )
        if not headings:
            return []

        # Text before the first heading is a title page, copyright notice, or table of contents.
        # Reported rather than dropped in silence — an unexplained gap in a corpus is how the
        # session-6 audit's truncated works went unnoticed.
        front_matter = len(text[: headings[0][0]].strip())
        if front_matter:
            logger.info(
                "Skipped %d characters of front matter before chapter 1", front_matter
            )

        chapters: list[SourceChapter] = []
        for position, (_, body_start, title) in enumerate(headings):
            body_end = (
                headings[position + 1][0] if position + 1 < len(headings) else len(text)
            )
            body = text[body_start:body_end].strip()
            if not body:
                continue  # a heading in a table of contents, with no chapter body behind it
            chapters.append(
                SourceChapter(
                    index=len(chapters) + 1,
                    title=title or None,
                    text=body,
                )
            )

        logger.info("Split document into %d chapters", len(chapters))
        return chapters

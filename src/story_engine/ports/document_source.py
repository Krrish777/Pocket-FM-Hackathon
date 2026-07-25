"""The port for reading a source document into chapters.

Keeps PDF parsing (and any future EPUB/plain-text reader) out of the core: ingestion services
depend on this Protocol, never on PyMuPDF. See .claude/rules/structure.md.
"""

from pathlib import Path
from typing import Protocol

from story_engine.domain.models.document import SourceChapter


class DocumentSourcePort(Protocol):
    """Reads a document from disk and returns its chapters in reading order."""

    def read_chapters(self, path: Path) -> list[SourceChapter]:
        """Extract chapters from the document at `path`.

        Returns:
            Chapters in reading order, numbered from 1, each carrying the full text a citation
            offset resolves against.

        Raises:
            DocumentIngestionError: If the document cannot be read, holds no extractable text,
                or its chapter structure cannot be determined.
        """
        ...

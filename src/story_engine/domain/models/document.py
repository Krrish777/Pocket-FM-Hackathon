"""Source documents as the ingestion pipeline sees them — chapters of addressable text.

A `Provenance` addresses a fact by `(source_id, chapter, char_start, char_end)`, so the chapter is
the unit ingestion must produce. Pages are a printing artifact and deliberately do not appear here:
a novel's chapter boundary is what the story, the reader, and the spoiler guard all agree on.
"""

from pydantic import Field

from story_engine.domain.base import DomainModel
from story_engine.domain.models.canon import ChapterIndex


class SourceChapter(DomainModel):
    """One chapter of an ingested document, with the text a citation resolves against.

    `text` is the whole chapter as a single string. Offsets produced by
    `story_engine.domain.chunking.chunk_text` are relative to it, which is what makes
    `(source_id, chapter, char_start, char_end)` resolve without any further context.
    """

    index: ChapterIndex = Field(ge=1)
    title: str | None = None
    text: str = Field(min_length=1)

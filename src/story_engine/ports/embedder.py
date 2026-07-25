"""Embedder port — the seam a real embedding model plugs into without touching storage.

Swapping `HashingEmbedder` for an OpenAI/sentence-transformers embedder later means writing
one new adapter behind this Protocol; the vector store and every caller stay unchanged.
"""

from typing import Protocol


class EmbedderPort(Protocol):
    """Turns text into a fixed-width vector for semantic search."""

    dimensions: int

    def embed(self, text: str) -> tuple[float, ...]:
        """Return the embedding vector for `text`, of length `dimensions`."""
        ...

"""Lore retriever port — the FUZZY associative-recall lane (RAG).

Embedding/similarity search for "surface lore relevant to this scene." Returns candidate refs, NOT
authority — resolve/validate hits against the canonical bible before use. `lane` implements the
FictionRAG factual/persona/worldview separation. mem0/vector SDKs live only in the adapter.
See research/memory-and-persistence.md.
"""

from enum import StrEnum
from typing import Protocol

from story_engine.domain.base import DomainModel


class RetrievalLane(StrEnum):
    FACTUAL = "factual"
    PERSONA = "persona"
    WORLDVIEW = "worldview"


class RetrievedItem(DomainModel):
    """A candidate recall hit — a reference + score, not canonical truth."""

    ref_id: str
    text: str
    score: float
    lane: RetrievalLane


class LoreRetrieverPort(Protocol):
    """Index and associatively retrieve lore/color for a query."""

    def index(self, items: list[RetrievedItem]) -> None: ...

    def retrieve(
        self, query: str, *, k: int, lane: RetrievalLane
    ) -> tuple[RetrievedItem, ...]:
        """Return up to `k` associative hits in `lane` (candidates, not authority)."""
        ...

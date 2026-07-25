"""SQLite-backed vector store — implements `VectorStorePort`.

The semantic-recall lane: "what in this story is *about* grief?" Cosine similarity over
JSON-stored float vectors in plain Python (fine at demo scale; no pre-optimisation).

Maps Row ⇄ port args explicitly, mirroring `canon_store.py`'s structure. Two rules this
module exists to hold:

1. **The guard is not re-implemented here.** `search` calls the domain's `is_visible`, the
   same predicate `Fact.is_visible_to` calls. This file used to keep its own copy that
   checked reveal time and knower scope but not `status`; the copy drifted, and a
   QUARANTINED fact was retrievable by similarity while the canon store correctly hid it.
2. **Filter BEFORE ranking**, never after — a post-filter on a top-k result silently
   returns fewer than k and hides the leak in the gap.
"""

import math

from sqlalchemy import Engine
from sqlmodel import col, select

from story_engine.adapters.outbound.persistence.db import session_scope
from story_engine.adapters.outbound.persistence.tables import VectorRow
from story_engine.domain.enums import FactStatus
from story_engine.domain.models import Awareness, ChapterIndex, Fact, is_visible
from story_engine.ports.vector_store import VectorHit


def _to_row(fact: Fact, text: str, vector: tuple[float, ...]) -> VectorRow:
    """Map a fact plus its embedding to a fresh storage row."""
    return VectorRow(
        fact_id=fact.id,
        fork_id=fact.fork_id,
        text=text,
        vector=list(vector),
        status=str(fact.status),
        revealed_at=fact.revealed_at,
        # None (untracked) must stay NULL — an empty list would be a different, invalid state.
        knower_scope=(
            None
            if fact.knower_scope is None
            else [
                {"knower": a.knower, "learned_at": a.learned_at}
                for a in fact.knower_scope
            ]
        ),
    )


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 when either is a zero vector."""
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (norm_a * norm_b)


def _row_is_visible(row: VectorRow, knower: str, chapter: ChapterIndex) -> bool:
    """Rehydrate the row's guard fields and ask the ONE domain predicate."""
    return is_visible(
        status=FactStatus(row.status),
        revealed_at=row.revealed_at,
        knower_scope=(
            None
            if row.knower_scope is None
            else tuple(Awareness.model_validate(entry) for entry in row.knower_scope)
        ),
        knower=knower,
        chapter=chapter,
    )


class SqliteVectorStore:
    """SQLite implementation of `VectorStorePort`.

    Every read maps Row → port types INSIDE the session scope, then returns pure values, so
    no caller can trip `DetachedInstanceError` on a lazily-loaded attribute.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, fact: Fact, text: str, vector: tuple[float, ...]) -> None:
        """Index one fact's text under its embedding, replacing any earlier row for it.

        Takes the whole fact rather than loose guard fields so a caller cannot pair one
        fact's text with another's `revealed_at`/`knower_scope`/`status` — the guard fields
        and the text they describe now travel together by construction.

        Idempotent: re-indexing the same `fact_id` overwrites, so a re-run of ingestion
        cannot fill the index with duplicates that eat the caller's top-k budget.
        """
        with session_scope(self._engine) as session:
            existing = session.exec(
                select(VectorRow).where(col(VectorRow.fact_id) == fact.id)
            ).first()
            if existing is not None:
                session.delete(existing)
                session.flush()
            session.add(_to_row(fact, text, vector))

    def remove(self, fact_id: str) -> None:
        """Drop a fact's row from the index. Silent when absent — removal is idempotent.

        Exists so a supersession can retire the old fact's vector in the same unit of work
        that closes its window. Without it the index keeps ranking a fact the canon store
        has already retired, and the two stores disagree about what the story says.
        """
        with session_scope(self._engine) as session:
            row = session.exec(
                select(VectorRow).where(col(VectorRow.fact_id) == fact_id)
            ).first()
            if row is not None:
                session.delete(row)

    def search(
        self,
        fork_id: str,
        query_vector: tuple[float, ...],
        knower: str,
        chapter: ChapterIndex,
        k: int,
    ) -> tuple[VectorHit, ...]:
        """Return up to `k` semantically nearest, spoiler-safe hits, most similar first.

        Filters candidates on the spoiler guard first, THEN scores and ranks only the
        survivors — see the module docstring for why the order is not negotiable.

        Raises:
            ValueError: `k` is less than 1 — an empty result that looks identical to
                "nothing is relevant" is exactly the silent failure this store must not
                have.
        """
        if k < 1:
            raise ValueError("k must be at least 1")
        with session_scope(self._engine) as session:
            statement = select(VectorRow).where(col(VectorRow.fork_id) == fork_id)
            visible_rows = [
                row
                for row in session.exec(statement).all()
                if _row_is_visible(row, knower, chapter)
            ]
            scored = [
                (row, _cosine_similarity(query_vector, tuple(row.vector)))
                for row in visible_rows
            ]
            # Tie-break on fact_id so equal scores rank in a stable, reproducible order
            # rather than whatever order SQLite happened to return the rows in.
            scored.sort(key=lambda pair: (-pair[1], pair[0].fact_id))
            return tuple(
                VectorHit(fact_id=row.fact_id, text=row.text, score=score)
                for row, score in scored[:k]
            )

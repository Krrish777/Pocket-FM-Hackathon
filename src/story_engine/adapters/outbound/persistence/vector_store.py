"""SQLite-backed vector store — implements `VectorStorePort`.

The semantic-recall lane: "what in this story is *about* grief?" Cosine similarity over
JSON-stored float vectors in plain Python (fine at demo scale; no pre-optimisation).

Maps Row ⇄ port args explicitly, mirroring `canon_store.py`'s structure. The spoiler guard
is enforced in `search` by filtering candidate rows BEFORE computing/ranking similarity —
never after, because a post-filter on a top-k result silently returns fewer than k and hides
the leak in the gap.
"""

import math

from sqlalchemy import Engine
from sqlmodel import col, select

from story_engine.adapters.outbound.persistence.db import session_scope
from story_engine.adapters.outbound.persistence.tables import VectorRow
from story_engine.domain.models import ChapterIndex
from story_engine.ports.vector_store import VectorHit


def _to_row(
    fact_id: str,
    fork_id: str,
    text: str,
    vector: tuple[float, ...],
    revealed_at: ChapterIndex | None,
    knower_scope: frozenset[str] | None,
) -> VectorRow:
    """Map `add()` arguments to a fresh storage row."""
    return VectorRow(
        fact_id=fact_id,
        fork_id=fork_id,
        text=text,
        vector=list(vector),
        revealed_at=revealed_at,
        # None (untracked) must stay NULL — an empty list would be a different, invalid state.
        knower_scope=(None if knower_scope is None else sorted(knower_scope)),
    )


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 when either is a zero vector."""
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (norm_a * norm_b)


def _is_visible(row: VectorRow, knower: str, chapter: ChapterIndex) -> bool:
    """The spoiler guard, mirroring `Fact.is_visible_to` — evaluated before any ranking.

    Excludes a row whose `revealed_at` is null (never revealed) or in the future relative to
    `chapter`, and a row whose `knower_scope` is non-null and does not contain `knower`.
    """
    if row.revealed_at is None or row.revealed_at > chapter:
        return False
    return row.knower_scope is None or knower in row.knower_scope


class SqliteVectorStore:
    """SQLite implementation of `VectorStorePort`.

    Every read maps Row → port types INSIDE the session scope, then returns pure values, so
    no caller can trip `DetachedInstanceError` on a lazily-loaded attribute.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(
        self,
        fact_id: str,
        fork_id: str,
        text: str,
        vector: tuple[float, ...],
        revealed_at: ChapterIndex | None,
        knower_scope: frozenset[str] | None,
    ) -> None:
        """Index one fact's text under its embedding."""
        with session_scope(self._engine) as session:
            session.add(
                _to_row(fact_id, fork_id, text, vector, revealed_at, knower_scope)
            )

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
        """
        with session_scope(self._engine) as session:
            statement = select(VectorRow).where(col(VectorRow.fork_id) == fork_id)
            visible_rows = [
                row
                for row in session.exec(statement).all()
                if _is_visible(row, knower, chapter)
            ]
            scored = [
                (row, _cosine_similarity(query_vector, tuple(row.vector)))
                for row in visible_rows
            ]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            return tuple(
                VectorHit(fact_id=row.fact_id, text=row.text, score=score)
                for row, score in scored[:k]
            )

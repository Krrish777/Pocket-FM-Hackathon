"""Integration tests for the SQLite vector store — REAL database file, never `:memory:`.

Mirrors `test_canon_store_sqlite.py`'s discipline: real file via `tmp_path`, close-then-reopen
for durability. The leak test below is the reason this store exists as a guarded adapter and
not a bare cosine-similarity function — see `search`'s docstring for why filtering must
happen before ranking.
"""

from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore

pytestmark = pytest.mark.integration

EMBEDDER = HashingEmbedder(dimensions=64)


@pytest.fixture
def store(tmp_path: Path) -> SqliteVectorStore:
    """A store backed by a REAL file on disk — never `:memory:`."""
    engine = create_engine(f"sqlite:///{tmp_path / 'vectors.db'}")
    SQLModel.metadata.create_all(engine)
    return SqliteVectorStore(engine)


def test_add_then_search_returns_the_row_with_id_and_text_intact(
    store: SqliteVectorStore,
) -> None:
    text = "Kael knelt before the crown, grieving."
    store.add(
        fact_id="f-1",
        fork_id="canon",
        text=text,
        vector=EMBEDDER.embed(text),
        revealed_at=1,
        knower_scope=None,
    )
    hits = store.search(
        fork_id="canon",
        query_vector=EMBEDDER.embed(text),
        knower="audience",
        chapter=5,
        k=5,
    )
    assert len(hits) == 1
    assert hits[0].fact_id == "f-1"
    assert hits[0].text == text


def test_the_leak_test_a_future_revealed_row_is_excluded_even_when_most_similar(
    store: SqliteVectorStore,
) -> None:
    """The most important test in this file.

    Seed rows revealed at chapters 1, 5 and 30; query with a vector MOST similar to the
    chapter-30 row (its own embedding, which scores a perfect 1.0 against itself). Searching
    at chapter 10 must still exclude it — a naive rank-then-filter implementation would
    return it first and fail here.
    """
    early_text = "The village celebrated the harvest."
    mid_text = "A stranger arrived at the gate."
    spoiler_text = "The killer was Kael's own brother, hidden until now."

    store.add(
        fact_id="f-early",
        fork_id="canon",
        text=early_text,
        vector=EMBEDDER.embed(early_text),
        revealed_at=1,
        knower_scope=None,
    )
    store.add(
        fact_id="f-mid",
        fork_id="canon",
        text=mid_text,
        vector=EMBEDDER.embed(mid_text),
        revealed_at=5,
        knower_scope=None,
    )
    store.add(
        fact_id="f-spoiler",
        fork_id="canon",
        text=spoiler_text,
        vector=EMBEDDER.embed(spoiler_text),
        revealed_at=30,
        knower_scope=None,
    )

    hits = store.search(
        fork_id="canon",
        query_vector=EMBEDDER.embed(spoiler_text),  # most similar to f-spoiler itself
        knower="audience",
        chapter=10,
        k=5,
    )

    assert "f-spoiler" not in {hit.fact_id for hit in hits}


def test_scope_leak_a_row_scoped_to_another_knower_is_excluded(
    store: SqliteVectorStore,
) -> None:
    text = "Holmes alone knew the truth of the letter."
    store.add(
        fact_id="f-scoped",
        fork_id="canon",
        text=text,
        vector=EMBEDDER.embed(text),
        revealed_at=1,
        knower_scope=frozenset({"holmes"}),
    )
    hits = store.search(
        fork_id="canon",
        query_vector=EMBEDDER.embed(text),
        knower="watson",
        chapter=10,
        k=5,
    )
    assert hits == ()

    hits_for_holmes = store.search(
        fork_id="canon",
        query_vector=EMBEDDER.embed(text),
        knower="holmes",
        chapter=10,
        k=5,
    )
    assert {hit.fact_id for hit in hits_for_holmes} == {"f-scoped"}


def test_k_bounds_the_result_count(store: SqliteVectorStore) -> None:
    for i in range(5):
        text = f"Fact number {i} about the story."
        store.add(
            fact_id=f"f-{i}",
            fork_id="canon",
            text=text,
            vector=EMBEDDER.embed(text),
            revealed_at=1,
            knower_scope=None,
        )
    hits = store.search(
        fork_id="canon",
        query_vector=EMBEDDER.embed("Fact number 2 about the story."),
        knower="audience",
        chapter=10,
        k=2,
    )
    assert len(hits) == 2


def test_results_are_ordered_by_descending_similarity(store: SqliteVectorStore) -> None:
    query_text = "The crown belongs to Kael."
    close_text = "The crown belongs to Kael now."
    far_text = "A recipe for bread involves flour and water."

    store.add(
        fact_id="f-close",
        fork_id="canon",
        text=close_text,
        vector=EMBEDDER.embed(close_text),
        revealed_at=1,
        knower_scope=None,
    )
    store.add(
        fact_id="f-far",
        fork_id="canon",
        text=far_text,
        vector=EMBEDDER.embed(far_text),
        revealed_at=1,
        knower_scope=None,
    )

    hits = store.search(
        fork_id="canon",
        query_vector=EMBEDDER.embed(query_text),
        knower="audience",
        chapter=10,
        k=5,
    )

    assert [hit.fact_id for hit in hits] == ["f-close", "f-far"]
    assert hits[0].score >= hits[1].score


def test_the_store_survives_a_restart(tmp_path: Path) -> None:
    """Write, CLOSE, reopen against the same file, and assert the data is intact."""
    db = tmp_path / "vectors.db"
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    text = "The final chapter closes the loop."
    SqliteVectorStore(engine).add(
        fact_id="f-1",
        fork_id="canon",
        text=text,
        vector=EMBEDDER.embed(text),
        revealed_at=1,
        knower_scope=None,
    )
    engine.dispose()  # close every pooled connection — simulate process exit

    reopened = create_engine(f"sqlite:///{db}")
    hits = SqliteVectorStore(reopened).search(
        fork_id="canon",
        query_vector=EMBEDDER.embed(text),
        knower="audience",
        chapter=1,
        k=5,
    )
    assert len(hits) == 1
    assert hits[0].fact_id == "f-1"

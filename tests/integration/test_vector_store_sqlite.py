"""Integration tests for the SQLite vector store — REAL database file, never `:memory:`.

Mirrors `test_canon_store_sqlite.py`'s discipline: real file via `tmp_path`, close-then-reopen
for durability. The leak tests below are the reason this store exists as a guarded adapter and
not a bare cosine-similarity function — see `search`'s docstring for why filtering must
happen before ranking.

`add()` takes a whole `Fact` rather than loose guard fields, so these tests build facts. That
is deliberate: the previous signature let a caller pass one fact's text beside another fact's
visibility, and it let the row omit `status` entirely — which is exactly how a QUARANTINED
fact stayed searchable while the canon store correctly hid it.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.embedding.hashing_embedder import HashingEmbedder
from story_engine.adapters.outbound.persistence.vector_store import SqliteVectorStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Provenance

pytestmark = pytest.mark.integration

EMBEDDER = HashingEmbedder(dimensions=64)
RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(fact_id: str, **overrides: object) -> Fact:
    """Build a valid Fact whose guard fields can be overridden per test."""
    defaults: dict[str, object] = {
        "id": fact_id,
        "fork_id": "canon",
        "subject_id": "kael",
        "predicate": "loyal_to",
        "object_id": "the_crown",
        "object_literal": None,
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="src-1", chapter=1, char_start=0, char_end=4, quote="Kael"
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> SqliteVectorStore:
    """A store backed by a REAL file on disk — never `:memory:`."""
    engine = create_engine(f"sqlite:///{tmp_path / 'vectors.db'}")
    SQLModel.metadata.create_all(engine)
    return SqliteVectorStore(engine)


def _index(store: SqliteVectorStore, fact: Fact, text: str) -> None:
    """Embed and index one fact's text."""
    store.add(fact, text, EMBEDDER.embed(text))


def test_add_then_search_returns_the_row_with_id_and_text_intact(
    store: SqliteVectorStore,
) -> None:
    text = "Kael knelt before the crown, grieving."
    _index(store, _fact("f-1"), text)

    hits = store.search("canon", EMBEDDER.embed(text), AUDIENCE, chapter=5, k=5)

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
    early = "The village celebrated the harvest."
    mid = "A stranger arrived at the gate."
    spoiler = "The killer was Kael's own brother, hidden until now."

    _index(store, _fact("f-early", revealed_at=1), early)
    _index(store, _fact("f-mid", revealed_at=5), mid)
    _index(store, _fact("f-spoiler", revealed_at=30), spoiler)

    hits = store.search("canon", EMBEDDER.embed(spoiler), AUDIENCE, chapter=10, k=5)

    assert {hit.fact_id for hit in hits} == {"f-early", "f-mid"}


def test_a_quarantined_fact_is_never_returned_however_similar(
    store: SqliteVectorStore,
) -> None:
    """Status must dominate similarity, or the curation gate is decorative here.

    REGRESSION: this store used to keep its own copy of the spoiler guard that checked
    reveal time and knower scope but not `status`. A QUARANTINED fact — one that never
    reached canon and must stay invisible everywhere, always — was fully retrievable by
    similarity while the canon store correctly hid it. `search` now calls the same
    `is_visible` predicate the canon store calls.
    """
    text = "An unverified rumour that never reached canon."
    _index(store, _fact("f-q", revealed_at=1, status=FactStatus.QUARANTINED), text)

    hits = store.search("canon", EMBEDDER.embed(text), AUDIENCE, chapter=9999, k=5)

    assert hits == (), "LEAK: a quarantined fact was reachable by similarity search"


def test_search_is_fork_scoped(store: SqliteVectorStore) -> None:
    """A branch's semantic recall must not reach into a sibling branch.

    There was no test for this at all: `search` filtered on `fork_id`, but nothing proved
    it, so removing the clause would have kept the whole suite green while every branch
    leaked into every other.
    """
    text = "The crown changed hands in the night."
    _index(store, _fact("f-canon", fork_id="canon"), text)
    _index(store, _fact("f-branch", fork_id="branch-a"), text)

    canon_hits = store.search("canon", EMBEDDER.embed(text), AUDIENCE, chapter=10, k=5)
    branch_hits = store.search(
        "branch-a", EMBEDDER.embed(text), AUDIENCE, chapter=10, k=5
    )

    assert {h.fact_id for h in canon_hits} == {"f-canon"}
    assert {h.fact_id for h in branch_hits} == {"f-branch"}


def test_scope_leak_a_row_scoped_to_another_knower_is_excluded(
    store: SqliteVectorStore,
) -> None:
    text = "Holmes alone knew the truth of the letter."
    _index(
        store,
        _fact("f-scoped", revealed_at=1, knower_scope={AUDIENCE: 1, "holmes": 1}),
        text,
    )

    assert store.search("canon", EMBEDDER.embed(text), "watson", 10, k=5) == ()
    assert {
        h.fact_id
        for h in store.search("canon", EMBEDDER.embed(text), "holmes", 10, k=5)
    } == {"f-scoped"}


def test_a_knower_cannot_reach_a_fact_before_they_learned_it(
    store: SqliteVectorStore,
) -> None:
    """Per-knower acquisition time is enforced in the semantic lane too.

    Doakes learns at chapter 6; the audience not until 20. Searching as Doakes at chapter 3
    must miss it, at chapter 6 must find it, and the audience must miss it at both.
    """
    text = "Doakes watched him leave, and did not look away."
    _index(
        store,
        _fact("f-suspicion", revealed_at=20, knower_scope={AUDIENCE: 20, "doakes": 6}),
        text,
    )
    query = EMBEDDER.embed(text)

    assert store.search("canon", query, "doakes", 3, k=5) == ()
    assert {h.fact_id for h in store.search("canon", query, "doakes", 6, k=5)} == {
        "f-suspicion"
    }
    assert store.search("canon", query, AUDIENCE, 6, k=5) == ()
    assert {h.fact_id for h in store.search("canon", query, AUDIENCE, 20, k=5)} == {
        "f-suspicion"
    }


def test_reindexing_a_fact_replaces_its_row_rather_than_duplicating_it(
    store: SqliteVectorStore,
) -> None:
    """Ingestion is re-runnable. Duplicates silently eat the caller's top-k budget.

    Three indexes of one fact used to produce three identical hits, so a k=5 search could
    return one distinct fact where the caller asked for five.
    """
    fact = _fact("f-1")
    for text in ("first pass", "second pass", "third and final pass"):
        _index(store, fact, text)

    hits = store.search(
        "canon", EMBEDDER.embed("third and final pass"), AUDIENCE, 10, 5
    )

    assert [h.fact_id for h in hits] == ["f-1"]
    assert hits[0].text == "third and final pass", "the newest text must win"


def test_remove_drops_a_fact_from_the_index(store: SqliteVectorStore) -> None:
    """Supersession needs a way to retire the old fact's vector."""
    text = "Kael is loyal to the crown."
    _index(store, _fact("f-1"), text)
    store.remove("f-1")

    assert store.search("canon", EMBEDDER.embed(text), AUDIENCE, 10, k=5) == ()
    store.remove("f-1")  # idempotent — removing what is absent must not raise


def test_k_bounds_the_result_count(store: SqliteVectorStore) -> None:
    for i in range(5):
        _index(store, _fact(f"f-{i}", subject_id=f"s{i}"), f"Fact number {i}.")

    hits = store.search("canon", EMBEDDER.embed("Fact number 2."), AUDIENCE, 10, k=2)

    assert len(hits) == 2


def test_a_non_positive_k_is_rejected(store: SqliteVectorStore) -> None:
    """An empty result must never be indistinguishable from 'nothing is relevant'."""
    with pytest.raises(ValueError):
        store.search("canon", EMBEDDER.embed("anything"), AUDIENCE, 10, k=0)


def test_an_empty_index_returns_no_hits(store: SqliteVectorStore) -> None:
    assert store.search("canon", EMBEDDER.embed("anything"), AUDIENCE, 10, k=5) == ()


def test_results_are_ordered_by_descending_similarity(
    store: SqliteVectorStore,
) -> None:
    """Assert the ORDERING PROPERTY, not which ids land where.

    The previous version asserted exact ids, which only held because of character-n-gram
    overlap in the placeholder embedder — swapping in a real model would have broken the
    test without anything being wrong. Monotonically non-increasing score is the contract
    that survives the swap.
    """
    _index(store, _fact("f-close"), "The crown belongs to Kael now.")
    _index(store, _fact("f-far", subject_id="baker"), "A recipe for bread.")

    hits = store.search(
        "canon", EMBEDDER.embed("The crown belongs to Kael."), AUDIENCE, 10, k=5
    )

    assert len(hits) == 2
    scores = [hit.score for hit in hits]
    assert scores == sorted(scores, reverse=True)


def test_the_store_survives_a_restart(tmp_path: Path) -> None:
    """Write, CLOSE, reopen against the same file, and assert the data is intact."""
    db = tmp_path / "vectors.db"
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    text = "The final chapter closes the loop."
    SqliteVectorStore(engine).add(_fact("f-1"), text, EMBEDDER.embed(text))
    engine.dispose()  # close every pooled connection — simulate process exit

    reopened = create_engine(f"sqlite:///{db}")
    hits = SqliteVectorStore(reopened).search(
        "canon", EMBEDDER.embed(text), AUDIENCE, chapter=1, k=5
    )

    assert len(hits) == 1
    assert hits[0].fact_id == "f-1"

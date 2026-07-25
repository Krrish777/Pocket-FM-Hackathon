"""Unit tests for `CanonIngestService` — the canon <-> vector atomicity policy.

Mocked store, vector lane and embedder (this is the unit tier); the vector fake is configured to
fail on a chosen fact id to exercise the mandated failure policy: canon-first, vector-second,
one bad embedding does not abort the batch, and the repair path (`reconcile`) is idempotent.

No test here asserts a vector-first write order — locking in the unsafe order would itself be a
defect (see `services/canon_ingest.py`'s module docstring for why).
"""

from datetime import UTC, datetime

import pytest

from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import Fact, Provenance
from story_engine.services.canon_ingest import CanonIngestService
from story_engine.shared.errors import IngestDriftError

FORK_ID = "canon"
RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(fact_id: str, **overrides: object) -> Fact:
    """Build a valid Fact whose fields can be overridden per test."""
    defaults: dict[str, object] = {
        "id": fact_id,
        "fork_id": FORK_ID,
        "subject_id": "dexter",
        "predicate": "hunts_with",
        "object_id": None,
        "object_literal": "the Dark Passenger",
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="src-1",
            chapter=1,
            char_start=0,
            char_end=4,
            quote=f"quote-{fact_id}",
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


class FakeCanonStore:
    """Minimal in-memory `CanonStorePort` — only what `CanonIngestService` calls."""

    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}

    def append(self, fact: Fact) -> None:
        self._facts[fact.id] = fact

    def all_facts(self, fork_id: str) -> tuple[Fact, ...]:
        return tuple(f for f in self._facts.values() if f.fork_id == fork_id)


class FakeVectorStore:
    """Minimal in-memory `VectorStorePort`, with a chosen fact id configured to fail on add."""

    def __init__(self, fail_on: frozenset[str] = frozenset()) -> None:
        self._fail_on = fail_on
        self._entries: dict[str, tuple[str, tuple[float, ...]]] = {}
        self._fork_of: dict[str, str] = {}

    def recover(self) -> None:
        """Test-only fault-injection reset: the backend stops refusing writes."""
        self._fail_on = frozenset()

    def add(self, fact: Fact, text: str, vector: tuple[float, ...]) -> None:
        if fact.id in self._fail_on:
            raise RuntimeError(f"embedding backend refused fact {fact.id}")
        self._entries[fact.id] = (text, vector)
        self._fork_of[fact.id] = fact.fork_id

    def remove(self, fact_id: str) -> None:
        self._entries.pop(fact_id, None)
        self._fork_of.pop(fact_id, None)

    def ids(self, fork_id: str) -> frozenset[str]:
        return frozenset(
            fact_id for fact_id, fork in self._fork_of.items() if fork == fork_id
        )


class FakeEmbedder:
    """Deterministic stand-in embedder — never raises, so only vector `add` can fail."""

    dimensions = 1

    def embed(self, text: str) -> tuple[float, ...]:
        return (float(len(text)),)


def test_ingest_writes_canon_and_vector_for_every_fact() -> None:
    canon, vectors = FakeCanonStore(), FakeVectorStore()
    service = CanonIngestService(store=canon, vectors=vectors, embedder=FakeEmbedder())
    facts = [_fact("f-1"), _fact("f-2"), _fact("f-3")]

    written = service.ingest(facts)

    assert written == 3
    assert {f.id for f in canon.all_facts(FORK_ID)} == {"f-1", "f-2", "f-3"}
    assert vectors.ids(FORK_ID) == {"f-1", "f-2", "f-3"}


def test_vector_failure_leaves_canon_fact_present_and_vector_entry_absent() -> None:
    canon = FakeCanonStore()
    vectors = FakeVectorStore(fail_on=frozenset({"f-bad"}))
    service = CanonIngestService(store=canon, vectors=vectors, embedder=FakeEmbedder())

    with pytest.raises(IngestDriftError) as excinfo:
        service.ingest([_fact("f-bad")])

    assert excinfo.value.orphan_fact_ids == ("f-bad",)
    assert "f-bad" in str(excinfo.value)
    assert canon.all_facts(FORK_ID)[0].id == "f-bad"  # canon write survived
    assert "f-bad" not in vectors.ids(FORK_ID)  # vector write did not


def test_one_failure_does_not_abort_the_rest_of_the_batch() -> None:
    canon = FakeCanonStore()
    vectors = FakeVectorStore(fail_on=frozenset({"f-bad"}))
    service = CanonIngestService(store=canon, vectors=vectors, embedder=FakeEmbedder())

    with pytest.raises(IngestDriftError):
        service.ingest([_fact("f-good-1"), _fact("f-bad"), _fact("f-good-2")])

    assert {f.id for f in canon.all_facts(FORK_ID)} == {
        "f-good-1",
        "f-bad",
        "f-good-2",
    }
    assert vectors.ids(FORK_ID) == {"f-good-1", "f-good-2"}


def test_reconcile_repairs_a_missing_fact_and_leaves_counts_equal() -> None:
    canon = FakeCanonStore()
    vectors = FakeVectorStore(fail_on=frozenset({"f-bad"}))
    service = CanonIngestService(store=canon, vectors=vectors, embedder=FakeEmbedder())
    with pytest.raises(IngestDriftError):
        service.ingest([_fact("f-bad")])

    vectors.recover()  # the underlying backend recovers before reconciliation runs

    repaired, still_missing = service.reconcile(FORK_ID)

    assert (repaired, still_missing) == (1, 0)
    assert vectors.ids(FORK_ID) == {f.id for f in canon.all_facts(FORK_ID)}


def test_reconcile_on_a_healthy_store_is_a_noop() -> None:
    canon, vectors = FakeCanonStore(), FakeVectorStore()
    service = CanonIngestService(store=canon, vectors=vectors, embedder=FakeEmbedder())
    service.ingest([_fact("f-1"), _fact("f-2")])

    assert service.reconcile(FORK_ID) == (0, 0)

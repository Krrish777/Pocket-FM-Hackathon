"""Keeps the canon store and the vector index from drifting apart.

The canon store is the single source of truth; the vector lane is a projection over it, built
for semantic recall. Writing a fact to both is not one write, it is two — and two independent
writes drift unless something makes them one unit of work.

**The write order is canon FIRST, vector SECOND, and it is not a style choice.**

- *Vector-first, canon fails* would leave a vector entry for a fact canon never heard of: an
  entry retrievable by similarity with no canon row to gate against — an unguarded fourth read
  path, exactly the spoiler side-channel this whole system exists to prevent. Unacceptable at
  any probability.
- *Canon-first, vector fails* leaves the fact correctly recorded in the source of truth and
  merely absent from a derived index. Semantic recall under-returns; the guard, the graph, and
  every correctness property still hold. This is a degradation, not a correctness violation —
  and it is repairable via `reconcile`.

An asymmetric failure mode with one safe direction is not a coin flip, so `ingest` always writes
canon before it ever calls the embedder or the vector store.

On a vector-write failure, this service does **not** compensate by deleting the canon row: the
canon store is append-only by design (`supersede` closes a validity window, it does not delete),
so a "rollback" here would mean writing a phantom correction claiming a true fact was never true.
Instead it logs the failure, keeps ingesting the rest of the batch, and raises `IngestDriftError`
naming every orphan once the whole batch has been attempted — fail loud, after doing all the work
that could succeed.
"""

import logging
from collections.abc import Sequence

from story_engine.domain.models import Fact
from story_engine.ports.canon_store import CanonStorePort
from story_engine.ports.embedder import EmbedderPort
from story_engine.ports.vector_store import VectorStorePort
from story_engine.shared.errors import IngestDriftError

logger = logging.getLogger(__name__)


class CanonIngestService:
    """Writes facts to canon and indexes them for semantic recall, as one unit of work."""

    def __init__(
        self,
        *,
        store: CanonStorePort,
        vectors: VectorStorePort,
        embedder: EmbedderPort,
    ) -> None:
        self._store = store
        self._vectors = vectors
        self._embedder = embedder

    def ingest(self, facts: Sequence[Fact]) -> int:
        """Write each fact to canon, then index it in the vector lane.

        Every fact in `facts` is attempted, in order, canon-write first: a vector-write
        failure on one fact never prevents the rest of the batch from being ingested (one
        bad embedding must not abort a novel-length ingest), and it never triggers a
        compensating delete of the canon row already written — see the module docstring.

        Returns:
            The number of facts written to canon (always `len(facts)` — a canon-write
            failure propagates immediately rather than being counted as an orphan).

        Raises:
            IngestDriftError: One or more facts were written to canon but could not be
                indexed. Raised once, after every fact in `facts` has been attempted, never
                mid-batch. Carries the orphaned fact ids as `orphan_fact_ids`.
        """
        written = 0
        orphans: list[str] = []
        for fact in facts:
            self._store.append(fact)
            written += 1
            try:
                self._index(fact)
            except Exception as exc:
                logger.error(
                    "canon ingest: fact %s was written to canon but failed to index in "
                    "the vector lane: %s",
                    fact.id,
                    exc,
                )
                orphans.append(fact.id)

        if orphans:
            raise IngestDriftError(
                f"{len(orphans)} fact(s) written to canon but not indexed: {orphans}",
                orphan_fact_ids=tuple(orphans),
            )
        return written

    def reconcile(self, fork_id: str) -> tuple[int, int]:
        """Re-index canon facts missing from the vector lane for `fork_id`.

        The repair path for `ingest`'s non-fatal-per-fact failures: diffs canon fact ids
        against what the vector lane actually holds and re-adds whatever is missing. Safe
        to run repeatedly — `VectorStorePort.add` is idempotent per fact id, so reconciling
        an already-healthy store is a no-op.

        Returns:
            `(repaired, still_missing)` — facts successfully re-indexed, and facts that
            failed again and remain missing.
        """
        canon_facts = {fact.id: fact for fact in self._store.all_facts(fork_id)}
        indexed_ids = self._vectors.ids(fork_id)
        missing = [
            fact for fact_id, fact in canon_facts.items() if fact_id not in indexed_ids
        ]

        repaired = 0
        still_missing: list[str] = []
        for fact in missing:
            try:
                self._index(fact)
                repaired += 1
            except Exception as exc:
                logger.error(
                    "canon ingest: reconcile could not index fact %s: %s", fact.id, exc
                )
                still_missing.append(fact.id)

        return repaired, len(still_missing)

    def _index(self, fact: Fact) -> None:
        """Embed and add one fact's provenance quote to the vector lane."""
        text = fact.provenance.quote
        vector = self._embedder.embed(text)
        self._vectors.add(fact, text, vector)

"""Vector-store port — the semantic-recall lane, a third store beside canon + graph.

The canon store answers "what is true, when, to whom"; the graph answers "what connects to
what"; this port answers the soft question neither can: "what in this story is *about*
grief?" Returns candidate hits, not authority — same discipline as `LoreRetrieverPort`.

The spoiler guard applies here exactly as it does to the canon store, and is in fact the
easiest place in the whole system to leak: a query about the victim will happily return the
killer's identity by similarity if nothing stops it. `search` MUST filter on `revealed_at`
and `knower_scope` BEFORE ranking by similarity — a post-filter on a top-k result silently
returns fewer than k and hides the leak in the gap.
"""

from typing import Protocol

from story_engine.domain.base import DomainModel
from story_engine.domain.models import ChapterIndex, Fact


class VectorHit(DomainModel):
    """A semantic-recall candidate — a reference + similarity score, not canonical truth."""

    fact_id: str
    text: str
    score: float


class VectorStorePort(Protocol):
    """Index and semantically search fact text, spoiler-guard enforced at the seam."""

    def add(self, fact: Fact, text: str, vector: tuple[float, ...]) -> None:
        """Index one fact's text under its embedding, replacing any earlier row for it.

        Takes the whole fact, not loose guard fields: every field the guard reads
        (`status`, `revealed_at`, `knower_scope`) is copied alongside the vector so
        `search` needs no join back to the canon store — and copying them from one object
        makes it impossible to pair one fact's text with another's visibility.

        Must be idempotent on `fact.id`: re-indexing replaces, never duplicates.
        """
        ...

    def remove(self, fact_id: str) -> None:
        """Drop a fact's row from the index; a no-op when it is absent.

        Supersession must be able to retire the old fact's vector in the same unit of work
        that closes its window, or the index keeps ranking a fact canon has retired.
        """
        ...

    def search(
        self,
        fork_id: str,
        query_vector: tuple[float, ...],
        knower: str,
        chapter: ChapterIndex,
        k: int,
    ) -> tuple[VectorHit, ...]:
        """Return up to `k` semantically nearest, spoiler-safe hits, most similar first.

        Must apply the domain's `is_visible` predicate — not a local re-implementation of
        it — and must apply it BEFORE ranking, never after.

        Raises:
            ValueError: `k` is less than 1.
        """
        ...

    def ids(self, fork_id: str) -> frozenset[str]:
        """Return every fact id currently indexed for `fork_id`, guard NOT applied.

        This is the repair-path seam, not a retrieval one: `CanonIngestService.reconcile`
        needs to know what is indexed regardless of who may currently see it, so a fact
        withheld from every knower must still be reported as present. Callers other than
        reconciliation should route through `search`, which enforces the spoiler guard.
        """
        ...

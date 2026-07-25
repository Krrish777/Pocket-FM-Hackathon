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
from story_engine.domain.models import ChapterIndex


class VectorHit(DomainModel):
    """A semantic-recall candidate — a reference + similarity score, not canonical truth."""

    fact_id: str
    text: str
    score: float


class VectorStorePort(Protocol):
    """Index and semantically search fact text, spoiler-guard enforced at the seam."""

    def add(
        self,
        fact_id: str,
        fork_id: str,
        text: str,
        vector: tuple[float, ...],
        revealed_at: ChapterIndex | None,
        knower_scope: frozenset[str] | None,
    ) -> None:
        """Index one fact's text under its embedding.

        `revealed_at`/`knower_scope` are stored alongside the vector so `search` can apply
        the spoiler guard without a join back to the canon store.
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

        Must exclude any row whose `revealed_at` is null or greater than `chapter`, and any
        row whose `knower_scope` is non-null and does not contain `knower`. Filter BEFORE
        ranking — never after.
        """
        ...

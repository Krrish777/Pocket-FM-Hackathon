"""Graph projection over canon facts — layer 2 of the hybrid knowledge base.

DERIVED, never a store. The graph is rebuilt from facts on demand and holds nothing the
store does not, so there is exactly one source of truth. It exists for the questions a flat
query answers badly: multi-hop connection, and what changed between two points in time.

No graph database. A dedicated engine would need a running service, and the default path
must work embedded and offline. (Airbnb ran a typed, provenance-tagged node/edge graph on a
relational store; the engine is not where the value is.)
"""

from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Self

from story_engine.domain.base import DomainModel
from story_engine.domain.models import ChapterIndex, Fact


class GraphEdge(DomainModel):
    """One relation between two entities, traceable to the fact that asserted it."""

    subject_id: str
    predicate: str
    object_id: str
    fact_id: str
    valid_from: ChapterIndex
    valid_to: ChapterIndex | None = None


class LoreGraph(DomainModel):
    """An adjacency projection of canon, already bounded by the spoiler guard."""

    edges: tuple[GraphEdge, ...] = ()

    @classmethod
    def from_facts(
        cls, facts: Iterable[Fact], knower: str, chapter: ChapterIndex
    ) -> Self:
        """Project the facts this knower may see at this point in the telling.

        The guard is applied HERE, at construction, so no caller can traverse into a fact
        the store would have withheld. A graph built from unguarded facts turns the whole
        layer into a spoiler side-channel.
        """
        visible = [
            f
            for f in facts
            if f.is_visible_to(knower, chapter) and f.is_valid_at(chapter)
        ]
        return cls(
            edges=tuple(
                GraphEdge(
                    subject_id=f.subject_id,
                    predicate=f.predicate,
                    object_id=f.object_id,
                    fact_id=f.id,
                    valid_from=f.valid_from,
                    valid_to=f.valid_to,
                )
                for f in visible
                # A literal-valued fact is an attribute, not a relation: no second endpoint.
                if f.object_id is not None
            )
        )

    def _adjacency(self) -> dict[str, list[GraphEdge]]:
        out: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in self.edges:
            out[edge.subject_id].append(edge)
        return out

    def neighbours(self, entity_id: str) -> tuple[GraphEdge, ...]:
        """Outgoing edges from one entity."""
        return tuple(e for e in self.edges if e.subject_id == entity_id)

    def related_within(self, entity_id: str, hops: int) -> frozenset[str]:
        """Entities reachable within `hops` steps, excluding the start.

        Breadth-first with a seen-set, because mutual relationships are ubiquitous in
        fiction and an unguarded walk would not terminate.
        """
        adjacency = self._adjacency()
        seen: set[str] = {entity_id}
        reached: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= hops:
                continue
            for edge in adjacency.get(current, []):
                reached.add(edge.object_id)
                if edge.object_id not in seen:
                    seen.add(edge.object_id)
                    queue.append((edge.object_id, depth + 1))
        return frozenset(reached)

    def relationship_diff(self, other: "LoreGraph") -> tuple[GraphEdge, ...]:
        """Edges present in exactly one of the two graphs.

        Comparing two projections at different chapters is how relationship drift becomes
        visible — the fastest-moving and least self-announcing layer of a serial.
        """
        mine = {e.fact_id: e for e in self.edges}
        theirs = {e.fact_id: e for e in other.edges}
        only_mine = tuple(e for k, e in mine.items() if k not in theirs)
        only_theirs = tuple(e for k, e in theirs.items() if k not in mine)
        return only_mine + only_theirs

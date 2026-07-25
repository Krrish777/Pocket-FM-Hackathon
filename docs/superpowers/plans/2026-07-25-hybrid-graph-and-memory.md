# Hybrid Knowledge Base — Graph Layer & Agent Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Complete the three-layer hybrid knowledge base and prove it end to end — canon store (layer 1, built separately) + **graph projection** (layer 2) + **agent working memory** (layer 3).

**Architecture:** All three layers read the SAME `Fact` rows. The store is the system of record; the graph is a *derived projection* rebuilt from facts on demand (no second source of truth); working memory is a bounded, spoiler-guarded slice assembled for one session. Nothing here introduces a service dependency — the whole hybrid runs embedded and offline.

**Tech Stack:** Python 3.12, Pydantic v2, SQLModel/SQLite, pytest 9. No graph database.

## Global Constraints

- **No new runtime dependencies.** Graphiti/Neo4j require a service; PRD NF-04 requires the default path run embedded and offline. Graphiti remains the documented upgrade path — see `DECISIONS.md`.
- The graph is a **projection**, never a store. It is rebuilt from facts; it never holds a fact the store does not.
- Layer 2 implements the existing `LoreRetrieverPort` where the shape fits; do not invent a parallel port.
- Every layer respects the **spoiler guard**: nothing surfaces a fact with `revealed_at > telling_time`, and nothing surfaces a scope-tracked fact to a knower outside its scope.
- Python 3.12, modern typing (`X | None`), `tuple`/`frozenset` on domain models, Google docstrings, comments explain WHY.
- `domain/` takes no clock and imports nothing outward.
- The gate is `make check`. Red at the end of a task = that task is not done.
- Commit with a **pathspec** and a conventional-commit subject. No `Co-Authored-By`, no AI attribution.
- Testing standard: `tests/README.md` § "Testing the Canon Kernel". **Assert every load-bearing field after a real save-and-reload; identity-only assertions are smoke tests.**

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/story_engine/domain/graph.py` | Create | Pure graph projection + traversal over facts. No IO. |
| `src/story_engine/services/working_memory.py` | Create | Assembles a bounded, guarded packet for one session |
| `tests/unit/domain/test_graph.py` | Create | Projection and traversal correctness |
| `tests/unit/services/test_working_memory.py` | Create | Assembly, bounding, guard enforcement |
| `tests/e2e/test_hybrid_kb_e2e.py` | Create | **All three layers, one real database, across a restart** |

Why `graph.py` is in `domain/` and not an adapter: it computes over facts with no IO and no vendor SDK. Putting it behind an adapter would imply an external engine we deliberately do not have.

---

### Task 1: The graph projection layer

**Files:** Create `src/story_engine/domain/graph.py`, `tests/unit/domain/test_graph.py`.

**Interfaces produced:**
- `EntityNode(id: str, edges_out: tuple[GraphEdge, ...])`
- `GraphEdge(subject_id: str, predicate: str, object_id: str, fact_id: str, valid_from: ChapterIndex, valid_to: ChapterIndex | None)`
- `LoreGraph.from_facts(facts: Iterable[Fact], knower: str, chapter: ChapterIndex) -> LoreGraph`
- `LoreGraph.neighbours(entity_id: str) -> tuple[GraphEdge, ...]`
- `LoreGraph.related_within(entity_id: str, hops: int) -> frozenset[str]`
- `LoreGraph.relationship_diff(other: LoreGraph) -> tuple[GraphEdge, ...]`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/domain/test_graph.py`:

```python
"""Unit tests for the graph projection.

The graph is DERIVED. Its only job is traversal over facts the store already holds, so the
tests that matter are: (a) it never contains a fact the guard would have withheld, and
(b) traversal answers multi-hop questions a flat query cannot.
"""

from datetime import UTC, datetime

from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.graph import LoreGraph
from story_engine.domain.models import AUDIENCE, Fact, Provenance

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(fact_id: str, subject: str, predicate: str, obj: str, **kw: object) -> Fact:
    defaults: dict[str, object] = {
        "id": fact_id, "fork_id": "canon", "subject_id": subject,
        "predicate": predicate, "object_id": obj, "object_literal": None,
        "valid_from": 1, "valid_to": None, "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED, "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="s", chapter=1, char_start=0, char_end=3, quote="abc"
        ),
        "confidence": 0.9, "tier": 0, "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED, "superseded_at": None,
    }
    return Fact(**(defaults | kw))  # type: ignore[arg-type]


def test_projection_excludes_facts_the_guard_would_withhold() -> None:
    """THE load-bearing property: the graph must not become a spoiler side-channel.

    A guard applied only at the store, with an unguarded graph beside it, leaks everything
    the guard was built to withhold.
    """
    facts = [
        _fact("f-1", "holmes", "knows", "watson", revealed_at=1),
        _fact("f-2", "moriarty", "killed", "victim", revealed_at=30),
    ]
    graph = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=10)
    assert graph.neighbours("moriarty") == ()
    assert "victim" not in graph.related_within("moriarty", hops=3)


def test_neighbours_returns_outgoing_edges() -> None:
    graph = LoreGraph.from_facts(
        [_fact("f-1", "holmes", "knows", "watson")], knower=AUDIENCE, chapter=5
    )
    edges = graph.neighbours("holmes")
    assert len(edges) == 1
    assert edges[0].object_id == "watson"
    assert edges[0].fact_id == "f-1"


def test_related_within_traverses_multiple_hops() -> None:
    """The question a flat store cannot answer: who is connected to whom, transitively."""
    facts = [
        _fact("f-1", "holmes", "knows", "watson"),
        _fact("f-2", "watson", "knows", "mary"),
        _fact("f-3", "mary", "knows", "stranger"),
    ]
    graph = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=5)
    assert graph.related_within("holmes", hops=1) == frozenset({"watson"})
    assert graph.related_within("holmes", hops=2) == frozenset({"watson", "mary"})


def test_related_within_terminates_on_a_cycle() -> None:
    """Stories are full of mutual relationships; an unguarded walk would hang."""
    facts = [
        _fact("f-1", "a", "knows", "b"),
        _fact("f-2", "b", "knows", "a"),
    ]
    graph = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=5)
    assert graph.related_within("a", hops=10) == frozenset({"a", "b"})


def test_relationship_diff_reports_edges_that_changed_between_chapters() -> None:
    """Relationships are the fastest-moving layer; the diff is what makes drift visible."""
    facts = [
        _fact("f-1", "kael", "loyal_to", "crown", valid_from=1, valid_to=180),
        _fact("f-2", "kael", "loyal_to", "rebels", valid_from=181),
    ]
    early = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=100)
    late = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=200)
    changed = early.relationship_diff(late)
    assert {e.object_id for e in changed} == {"crown", "rebels"}


def test_literal_valued_facts_do_not_become_edges() -> None:
    """An edge needs two endpoints. `eye_colour = "blue"` is an attribute, not a relation."""
    facts = [_fact("f-1", "holmes", "eye_colour", "x", object_id=None,
                   object_literal="grey")]
    graph = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=5)
    assert graph.neighbours("holmes") == ()
```

- [ ] **Step 2: Run; confirm failure** (`ModuleNotFoundError: ...domain.graph`).

- [ ] **Step 3: Implement `src/story_engine/domain/graph.py`**

```python
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
```

- [ ] **Step 4: Run tests → PASS (6). Then `make check` → green.**

- [ ] **Step 5: Commit**

```bash
git commit -- src/story_engine/domain/graph.py tests/unit/domain/test_graph.py \
  -m "feat(domain): graph projection layer with guard applied at construction"
```

---

### Task 2: Agent working memory

**Files:** Create `src/story_engine/services/working_memory.py`, `tests/unit/services/test_working_memory.py`.

**Interfaces produced:**
- `MemoryPacket(facts, graph, withheld_count, knower, chapter)`
- `WorkingMemory(store: CanonStorePort)` with `assemble(fork_id, knower, chapter, focus_entities, budget) -> MemoryPacket`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/services/test_working_memory.py`:

```python
"""Unit tests for agent working memory — layer 3.

Mocked store (this is the unit tier). The properties under test are assembly, bounding, and
that the guard survives every path through the service.
"""

from datetime import UTC, datetime

import pytest

from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.services.working_memory import WorkingMemory

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(fact_id: str, subject: str, **kw: object) -> Fact:
    defaults: dict[str, object] = {
        "id": fact_id, "fork_id": "canon", "subject_id": subject,
        "predicate": "knows", "object_id": "watson", "object_literal": None,
        "valid_from": 1, "valid_to": None, "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED, "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="s", chapter=1, char_start=0, char_end=3, quote="abc"
        ),
        "confidence": 0.9, "tier": 0, "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED, "superseded_at": None,
    }
    return Fact(**(defaults | kw))  # type: ignore[arg-type]


class _FakeStore:
    """A stand-in store. Records its calls so the service's guard usage is observable."""

    def __init__(self, facts: list[Fact]) -> None:
        self._facts = facts

    def visible_to(self, fork_id: str, knower: str, chapter: int) -> tuple[Fact, ...]:
        return tuple(f for f in self._facts if f.is_visible_to(knower, chapter))

    def withheld_from(self, fork_id: str, knower: str, chapter: int) -> tuple[Fact, ...]:
        return tuple(
            f for f in self._facts if not f.is_visible_to(knower, chapter)
        )


def test_assemble_returns_only_visible_facts() -> None:
    store = _FakeStore([
        _fact("f-1", "holmes", revealed_at=1),
        _fact("f-2", "moriarty", revealed_at=30),
    ])
    packet = WorkingMemory(store).assemble("canon", AUDIENCE, chapter=10)
    assert {f.id for f in packet.facts} == {"f-1"}


def test_assemble_reports_how_many_facts_were_withheld() -> None:
    """Being able to SHOW what was withheld is what makes the guarantee demonstrable."""
    store = _FakeStore([
        _fact("f-1", "holmes", revealed_at=1),
        _fact("f-2", "moriarty", revealed_at=30),
        _fact("f-3", "mary", revealed_at=None),
    ])
    packet = WorkingMemory(store).assemble("canon", AUDIENCE, chapter=10)
    assert packet.withheld_count == 2


def test_assemble_is_deterministic() -> None:
    """Identical inputs must produce an identical packet.

    A generator that receives a different packet each call cannot be debugged, and a
    continuity guarantee that varies run to run is not a guarantee.
    """
    store = _FakeStore([_fact(f"f-{i}", f"e{i}") for i in range(10)])
    memory = WorkingMemory(store)
    first = memory.assemble("canon", AUDIENCE, chapter=5)
    second = memory.assemble("canon", AUDIENCE, chapter=5)
    assert [f.id for f in first.facts] == [f.id for f in second.facts]


def test_budget_bounds_the_packet() -> None:
    """Context is finite. An unbounded packet silently truncates inside the model instead."""
    store = _FakeStore([_fact(f"f-{i}", f"e{i}") for i in range(50)])
    packet = WorkingMemory(store).assemble("canon", AUDIENCE, chapter=5, budget=5)
    assert len(packet.facts) == 5


def test_focus_entities_are_prioritised_within_the_budget() -> None:
    """Under a budget, the scene's own characters must not be evicted by unrelated canon."""
    store = _FakeStore(
        [_fact(f"f-{i}", f"other{i}") for i in range(20)]
        + [_fact("f-focus", "holmes")]
    )
    packet = WorkingMemory(store).assemble(
        "canon", AUDIENCE, chapter=5, focus_entities=("holmes",), budget=3
    )
    assert "f-focus" in {f.id for f in packet.facts}


def test_budget_must_be_positive() -> None:
    store = _FakeStore([])
    with pytest.raises(ValueError):
        WorkingMemory(store).assemble("canon", AUDIENCE, chapter=5, budget=0)
```

- [ ] **Step 2: Run; confirm failure.**

- [ ] **Step 3: Implement `src/story_engine/services/working_memory.py`**

```python
"""Agent working memory — layer 3 of the hybrid knowledge base.

The bounded slice of canon one session actually holds, as distinct from everything that is
true. Assembly is DETERMINISTIC and the store's guard is the only path in, so no caller can
construct a packet containing a fact the audience has not earned.
"""

from collections.abc import Sequence

from story_engine.domain.base import DomainModel
from story_engine.domain.graph import LoreGraph
from story_engine.domain.models import ChapterIndex, Fact
from story_engine.ports.canon_store import CanonStorePort

DEFAULT_BUDGET = 40


class MemoryPacket(DomainModel):
    """What one session may see, plus the count of what it may not."""

    knower: str
    chapter: ChapterIndex
    facts: tuple[Fact, ...]
    graph: LoreGraph
    withheld_count: int


class WorkingMemory:
    """Assembles a bounded, guarded memory packet for a single session."""

    def __init__(self, store: CanonStorePort) -> None:
        self._store = store

    def assemble(
        self,
        fork_id: str,
        knower: str,
        chapter: ChapterIndex,
        focus_entities: Sequence[str] = (),
        budget: int = DEFAULT_BUDGET,
    ) -> MemoryPacket:
        """Build the packet for `knower` at `chapter`.

        Facts about the scene's own characters are kept first: under a budget, evicting the
        entities the scene is ABOUT in favour of unrelated canon is the one failure that
        makes the packet useless.
        """
        if budget < 1:
            raise ValueError("budget must be at least 1")

        visible = self._store.visible_to(fork_id, knower, chapter)
        withheld = self._store.withheld_from(fork_id, knower, chapter)

        focus = set(focus_entities)
        # Stable sort on a boolean key: focus facts first, original order preserved within
        # each group, so the packet is reproducible across runs.
        ordered = sorted(visible, key=lambda f: f.subject_id not in focus)
        kept = tuple(ordered[:budget])

        return MemoryPacket(
            knower=knower,
            chapter=chapter,
            facts=kept,
            graph=LoreGraph.from_facts(kept, knower=knower, chapter=chapter),
            withheld_count=len(withheld),
        )
```

- [ ] **Step 4: Run tests → PASS (6). `make check` → green.**

- [ ] **Step 5: Commit**

```bash
git commit -- src/story_engine/services/working_memory.py \
  tests/unit/services/test_working_memory.py \
  -m "feat(services): agent working memory with deterministic bounded assembly"
```

---

### Task 3: Full hybrid end-to-end test

**Files:** Create `tests/e2e/test_hybrid_kb_e2e.py`.

- [ ] **Step 1: Write the E2E test**

```python
"""L3 — ALL THREE LAYERS against one real database, across a restart.

Layer 1 store · layer 2 graph projection · layer 3 working memory. Deliberately one long
test: the property proven is that a realistic SEQUENCE survives persistence with the guard
intact at every layer. Split into isolated cases, each step could pass while the hybrid as a
whole leaked.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.graph import LoreGraph
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.services.working_memory import WorkingMemory

pytestmark = pytest.mark.e2e

INGESTED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
CORRECTED = datetime(2026, 7, 25, 18, 0, tzinfo=UTC)


def _fact(fact_id: str, subject: str, predicate: str, obj: str, **kw: object) -> Fact:
    defaults: dict[str, object] = {
        "id": fact_id, "fork_id": "canon", "subject_id": subject,
        "predicate": predicate, "object_id": obj, "object_literal": None,
        "valid_from": 1, "valid_to": None, "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED, "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="novel", chapter=1, char_start=0, char_end=6, quote="Holmes"
        ),
        "confidence": 0.9, "tier": 0, "status": FactStatus.ACTIVE,
        "recorded_at": INGESTED, "superseded_at": None,
    }
    return Fact(**(defaults | kw))  # type: ignore[arg-type]


def test_hybrid_knowledge_base_end_to_end(tmp_path: Path) -> None:
    db = tmp_path / "hybrid.db"

    # --- LAYER 1: ingest into a real database ------------------------------------------
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)

    store.append(_fact("f-hw", "holmes", "knows", "watson", revealed_at=1))
    store.append(_fact("f-wm", "watson", "knows", "mary", revealed_at=1))
    store.append(_fact("f-kill", "moriarty", "killed", "victim", revealed_at=30))
    store.append(
        _fact("f-loyal", "kael", "loyal_to", "crown", valid_from=1, revealed_at=1)
    )

    # --- RESTART: prove persistence, not process memory ---------------------------------
    engine.dispose()
    reopened = SqliteCanonStore(create_engine(f"sqlite:///{db}"))
    assert len(reopened.all_facts("canon")) == 4, "data did not survive the restart"

    # --- LAYER 2: the graph must NOT be a spoiler side-channel --------------------------
    graph_at_10 = LoreGraph.from_facts(
        reopened.all_facts("canon"), knower=AUDIENCE, chapter=10
    )
    assert graph_at_10.neighbours("moriarty") == (), "LEAK: graph exposed the killer"
    assert "victim" not in graph_at_10.related_within("moriarty", hops=5)

    # ...and multi-hop traversal works for what IS revealed
    assert graph_at_10.related_within("holmes", hops=2) == frozenset({"watson", "mary"})

    # ...and the same fact becomes reachable once the telling reaches it
    graph_at_30 = LoreGraph.from_facts(
        reopened.all_facts("canon"), knower=AUDIENCE, chapter=30
    )
    assert graph_at_30.neighbours("moriarty") != ()

    # --- LAYER 3: working memory, bounded and guarded ------------------------------------
    packet = WorkingMemory(reopened).assemble(
        "canon", AUDIENCE, chapter=10, focus_entities=("holmes",), budget=3
    )
    assert "f-kill" not in {f.id for f in packet.facts}, "LEAK: packet exposed the killer"
    assert packet.withheld_count == 1
    assert len(packet.facts) <= 3
    assert "f-hw" in {f.id for f in packet.facts}, "focus entity was evicted"

    # the packet's own graph inherits the guard
    assert packet.graph.neighbours("moriarty") == ()

    # --- SUPERSESSION across all three layers -------------------------------------------
    reopened.supersede(
        "f-loyal",
        replacement=_fact(
            "f-defect", "kael", "loyal_to", "rebels", valid_from=181, revealed_at=181
        ),
        closes_at=180,
        superseded_at=CORRECTED,
    )

    assert reopened.as_of("canon", "kael", "loyal_to", 100).object_id == "crown"
    assert reopened.as_of("canon", "kael", "loyal_to", 200).object_id == "rebels"

    early = LoreGraph.from_facts(reopened.all_facts("canon"), AUDIENCE, chapter=100)
    late = LoreGraph.from_facts(reopened.all_facts("canon"), AUDIENCE, chapter=200)
    assert {e.object_id for e in early.relationship_diff(late)} == {"crown", "rebels"}

    # --- SECOND RESTART: the correction is durable too ------------------------------------
    final = SqliteCanonStore(create_engine(f"sqlite:///{db}"))
    assert final.get("f-loyal").status is FactStatus.INVALIDATED
    assert final.get("f-loyal").valid_from == 1, "supersession mutated an immutable field"
    final_packet = WorkingMemory(final).assemble("canon", AUDIENCE, chapter=200)
    assert "f-defect" in {f.id for f in final_packet.facts}
```

- [ ] **Step 2: Run.** `uv run pytest tests/e2e/test_hybrid_kb_e2e.py -v` → PASS. **If it fails, fix the code, never the assertion.**

- [ ] **Step 3: `make check`** → green, all layers.

- [ ] **Step 4: Commit**

```bash
git commit -- tests/e2e/test_hybrid_kb_e2e.py \
  -m "test(e2e): full hybrid knowledge base across a restart

Store, graph projection and working memory over one real database, proving
the spoiler guard holds at every layer and supersession is durable."
```

---

## Self-Review

**Spec coverage.** Layer 1 = the separate storage plan. Layer 2 = Task 1 (projection, traversal, diff). Layer 3 = Task 2 (bounded deterministic assembly). The hybrid proof = Task 3, which exercises all three over one real file across two restarts.

**The guard is tested at every layer, on purpose.** A guard enforced only at the store, with an unguarded graph or packet beside it, is not a guard — it is a side-channel. Hence `LoreGraph.from_facts` takes `knower`/`chapter` and applies the filter at construction rather than trusting callers.

**Deliberately deferred:** vector/semantic recall (nothing in the demo needs it, and it is the one layer the research says is *supporting*, never the core); Graphiti as a real backend (needs a service, breaks the offline constraint — documented as the upgrade path); per-character knowledge propagation across scenes (needs the extraction pipeline, which is M1).

**Placeholder scan:** none. **Type consistency:** `ChapterIndex` throughout; `LoreGraph.from_facts(facts, knower, chapter)` has one signature in all three files; `MemoryPacket.facts` is a `tuple` everywhere.

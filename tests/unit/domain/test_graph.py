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
        "id": fact_id,
        "fork_id": "canon",
        "subject_id": subject,
        "predicate": predicate,
        "object_id": obj,
        "object_literal": None,
        "valid_from": 1,
        "valid_to": None,
        "revealed_at": 1,
        "assertion_mode": AssertionMode.NARRATED,
        "attributed_to": None,
        "knower_scope": None,
        "provenance": Provenance(
            source_id="s", chapter=1, char_start=0, char_end=3, quote="abc"
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
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
    facts = [
        _fact("f-1", "holmes", "eye_colour", "x", object_id=None, object_literal="grey")
    ]
    graph = LoreGraph.from_facts(facts, knower=AUDIENCE, chapter=5)
    assert graph.neighbours("holmes") == ()

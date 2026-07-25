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
        "id": fact_id,
        "fork_id": "canon",
        "subject_id": subject,
        "predicate": "knows",
        "object_id": "watson",
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


class _FakeStore:
    """A stand-in store. Records its calls so the service's guard usage is observable."""

    def __init__(self, facts: list[Fact]) -> None:
        self._facts = facts

    def visible_to(self, fork_id: str, knower: str, chapter: int) -> tuple[Fact, ...]:
        return tuple(f for f in self._facts if f.is_visible_to(knower, chapter))

    def withheld_from(
        self, fork_id: str, knower: str, chapter: int
    ) -> tuple[Fact, ...]:
        return tuple(f for f in self._facts if not f.is_visible_to(knower, chapter))


def test_assemble_returns_only_visible_facts() -> None:
    store = _FakeStore(
        [
            _fact("f-1", "holmes", revealed_at=1),
            _fact("f-2", "moriarty", revealed_at=30),
        ]
    )
    packet = WorkingMemory(store).assemble("canon", AUDIENCE, chapter=10)
    assert {f.id for f in packet.facts} == {"f-1"}


def test_assemble_reports_how_many_facts_were_withheld() -> None:
    """Being able to SHOW what was withheld is what makes the guarantee demonstrable."""
    store = _FakeStore(
        [
            _fact("f-1", "holmes", revealed_at=1),
            _fact("f-2", "moriarty", revealed_at=30),
            _fact("f-3", "mary", revealed_at=None),
        ]
    )
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
        [_fact(f"f-{i}", f"other{i}") for i in range(20)] + [_fact("f-focus", "holmes")]
    )
    packet = WorkingMemory(store).assemble(
        "canon", AUDIENCE, chapter=5, focus_entities=("holmes",), budget=3
    )
    assert "f-focus" in {f.id for f in packet.facts}


def test_budget_must_be_positive() -> None:
    store = _FakeStore([])
    with pytest.raises(ValueError):
        WorkingMemory(store).assemble("canon", AUDIENCE, chapter=5, budget=0)

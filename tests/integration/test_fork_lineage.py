"""Fork lineage — a branch of a story must still contain the story.

`fork_id` used to be an opaque partition key: a player's branch held their one choice and
nothing else, so choosing "Debra opens the case files" dropped her into an empty world with
no Dexter, no Miami Metro and no novels. These tests pin the resolution rules that make a
branch a *branch*:

- own facts first, then inherited ancestor canon;
- inheritance stops at the divergence point;
- a nearer fork SHADOWS an ancestor on the same (subject_id, predicate);
- an unregistered fork behaves exactly like a root, so callers that never branch are
  unaffected.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.enums import AssertionMode, FactStatus
from story_engine.domain.models import AUDIENCE, Fact, Fork, Provenance

pytestmark = pytest.mark.integration

RECORDED = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _fact(fact_id: str, fork_id: str, **overrides: object) -> Fact:
    """Build a valid Fact in a named fork."""
    defaults: dict[str, object] = {
        "id": fact_id,
        "fork_id": fork_id,
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
            source_id="s", chapter=1, char_start=0, char_end=4, quote="Kael"
        ),
        "confidence": 0.9,
        "tier": 0,
        "status": FactStatus.ACTIVE,
        "recorded_at": RECORDED,
        "superseded_at": None,
    }
    return Fact(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> SqliteCanonStore:
    """A store backed by a REAL file on disk — never :memory:."""
    engine = create_engine(f"sqlite:///{tmp_path / 'forks.db'}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


def test_an_unregistered_fork_resolves_as_a_root(store: SqliteCanonStore) -> None:
    """Callers that never branch must see no behaviour change at all."""
    store.append(_fact("f-1", "canon"))

    assert store.lineage("canon") == (("canon", None),)
    assert {f.id for f in store.all_facts("canon")} == {"f-1"}


def test_a_branch_inherits_its_parents_canon(store: SqliteCanonStore) -> None:
    """THE fix. A branch that inherits nothing is not a branch of a story."""
    store.append(_fact("c-1", "canon", subject_id="dexter", predicate="sibling_of"))
    store.append(_fact("c-2", "canon", subject_id="dexter", predicate="works_at"))
    store.register_fork(
        Fork(
            id="branch",
            parent_fork_id="canon",
            divergence_at=12,
            source_id=None,
            label="a player choice",
        )
    )
    store.append(
        _fact(
            "b-1", "branch", subject_id="debra", predicate="investigates", valid_from=12
        )
    )

    assert {f.id for f in store.all_facts("branch")} == {"b-1", "c-1", "c-2"}
    # ...and inheritance is one-directional: the parent never sees the child's choice.
    assert {f.id for f in store.all_facts("canon")} == {"c-1", "c-2"}


def test_inheritance_stops_at_the_divergence_point(store: SqliteCanonStore) -> None:
    """Everything the parent does AFTER the branch point belongs to the parent alone.

    The branch replaced that future; importing it would hand the player both their own
    version of events and the one they diverged from.
    """
    store.append(_fact("c-before", "canon", predicate="p1", valid_from=5))
    store.append(_fact("c-after", "canon", predicate="p2", valid_from=40))
    store.register_fork(
        Fork(
            id="branch",
            parent_fork_id="canon",
            divergence_at=12,
            source_id=None,
            label="branch",
        )
    )

    assert {f.id for f in store.all_facts("branch")} == {"c-before"}


def test_a_nearer_fork_shadows_an_ancestor_on_the_same_key(
    store: SqliteCanonStore,
) -> None:
    """Shadowing is what makes a branch a rewrite rather than a contradiction.

    Without it the branch would hold "Kael is loyal to the crown" AND "Kael is loyal to the
    rebels" as simultaneously current, and the conflict detector would correctly report the
    branch as corrupt canon.
    """
    store.append(_fact("c-loyal", "canon", object_id="the_crown"))
    store.append(
        _fact("c-other", "canon", predicate="lives_in", object_id="the_capital")
    )
    store.register_fork(
        Fork(
            id="branch",
            parent_fork_id="canon",
            divergence_at=12,
            source_id=None,
            label="branch",
        )
    )
    store.append(_fact("b-loyal", "branch", object_id="the_rebels"))

    resolved = {f.id for f in store.all_facts("branch")}

    assert "b-loyal" in resolved
    assert "c-loyal" not in resolved, (
        "the branch's own version must shadow the ancestor"
    )
    assert "c-other" in resolved, "an unrelated key must still be inherited"


def test_a_grandchild_inherits_through_the_tightest_divergence(
    store: SqliteCanonStore,
) -> None:
    """A cap is the tightest point on the walk, not the local one.

    A grandchild that branched at 40 from a child that branched at 12 must not reach
    grandparent facts from chapter 30 — the child had already replaced that stretch.
    """
    store.append(_fact("g-early", "canon", predicate="p1", valid_from=5))
    store.append(_fact("g-late", "canon", predicate="p2", valid_from=30))
    store.register_fork(
        Fork(
            id="child",
            parent_fork_id="canon",
            divergence_at=12,
            source_id=None,
            label="child",
        )
    )
    store.register_fork(
        Fork(
            id="grandchild",
            parent_fork_id="child",
            divergence_at=40,
            source_id=None,
            label="grandchild",
        )
    )

    assert {f.id for f in store.all_facts("grandchild")} == {"g-early"}


def test_a_cyclic_lineage_is_rejected_rather_than_hanging(
    store: SqliteCanonStore,
) -> None:
    """An unguarded parent walk would loop forever instead of failing."""
    store.register_fork(
        Fork(id="a", parent_fork_id="b", divergence_at=5, source_id=None, label="a")
    )
    store.register_fork(
        Fork(id="b", parent_fork_id="a", divergence_at=5, source_id=None, label="b")
    )

    with pytest.raises(ValueError, match="cycle"):
        store.lineage("a")


def test_the_spoiler_guard_still_applies_across_inherited_facts(
    store: SqliteCanonStore,
) -> None:
    """Inheritance must not become a way around the guard.

    A branch resolves through `all_facts`, so a guard applied only to a fork's own rows
    would let every branch read its parent's withheld canon.
    """
    store.append(_fact("c-open", "canon", predicate="p1", revealed_at=1))
    store.append(_fact("c-secret", "canon", predicate="p2", revealed_at=30))
    store.register_fork(
        Fork(
            id="branch",
            parent_fork_id="canon",
            divergence_at=12,
            source_id=None,
            label="branch",
        )
    )

    visible = {f.id for f in store.visible_to("branch", AUDIENCE, 10)}

    assert visible == {"c-open"}, "LEAK: a branch read its parent's withheld canon"


def test_a_registered_fork_survives_a_restart(tmp_path: Path) -> None:
    """The branch registry is state, not process memory."""
    db = tmp_path / "forks.db"
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)
    store.append(_fact("c-1", "canon"))
    store.register_fork(
        Fork(
            id="branch",
            parent_fork_id="canon",
            divergence_at=12,
            source_id=None,
            label="branch",
        )
    )
    engine.dispose()

    reopened = SqliteCanonStore(create_engine(f"sqlite:///{db}"))

    assert reopened.get_fork("branch") is not None
    assert {f.id for f in reopened.all_facts("branch")} == {"c-1"}

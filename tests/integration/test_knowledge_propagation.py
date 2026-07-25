"""Knowledge that a player's choices create must survive a restart, and must never go backwards.

L2 against a real SQLite file, closed and reopened, because a scope that only holds while the
process is warm proves nothing about a demo that runs across turns.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.domain.enums import AssertionMode, FactStatus, PresenceGrade
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.domain.models.canon import Awareness, Presence, Scene
from story_engine.domain.propagation import witnesses_learn

pytestmark = pytest.mark.integration

RECORDED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _secret() -> Fact:
    """A typed secret: Dexter knows from chapter 1, the audience has not been told."""
    return Fact(
        id="f-the-passenger",
        fork_id="canon",
        subject_id="dexter",
        predicate="is_killer_of",
        object_id="the-priest",
        valid_from=1,
        revealed_at=None,
        assertion_mode=AssertionMode.NARRATED,
        knower_scope=(Awareness(knower="dexter", learned_at=1),),
        provenance=Provenance(
            source_id="ddd", chapter=1, char_start=0, char_end=6, quote="Dexter"
        ),
        confidence=1.0,
        tier=0,
        status=FactStatus.ACTIVE,
        recorded_at=RECORDED_AT,
    )


def _scene(chapter: int, roster: dict[str, PresenceGrade]) -> Scene:
    return Scene(
        id=f"sc-{chapter}",
        fork_id="canon",
        chapter=chapter,
        order_in_chapter=0,
        summary="a scene",
        roster=tuple(
            Presence(entity_id=entity, grade=grade) for entity, grade in roster.items()
        ),
    )


def _store(db: Path) -> SqliteCanonStore:
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


def test_learning_survives_a_restart_and_the_guard_honours_it(tmp_path: Path) -> None:
    """The full T3 loop: a scene teaches Doakes, the store keeps it, the guard enforces it."""
    db = tmp_path / "canon.db"
    store = _store(db)
    store.append(_secret())

    # Doakes walks in at chapter 6 and learns what Dexter has known since chapter 1.
    learned = witnesses_learn(
        _secret(),
        _scene(6, {"dexter": PresenceGrade.ACTIVE, "doakes": PresenceGrade.SILENT}),
    )
    assert learned.knower_scope is not None
    store.record_learning("f-the-passenger", learned.knower_scope)

    reopened = _store(db)
    stored = reopened.get("f-the-passenger")
    assert stored is not None
    assert {a.knower: a.learned_at for a in stored.knower_scope or ()} == {
        "dexter": 1,
        "doakes": 6,
    }

    # The guard now answers differently per character AND per chapter — the product claim.
    assert reopened.visible_to("canon", "dexter", 1), "Dexter knew from the start"
    assert not reopened.visible_to("canon", "doakes", 5), (
        "Doakes must not know before ch6"
    )
    assert reopened.visible_to("canon", "doakes", 6), "Doakes learned it at ch6"
    assert not reopened.visible_to("canon", "deb", 27), "Deborah was never in the room"


def test_a_scope_that_would_make_someone_forget_is_refused(tmp_path: Path) -> None:
    """Losing a knower is silent at read time, so it must be loud at write time."""
    store = _store(tmp_path / "canon.db")
    store.append(_secret())
    store.record_learning(
        "f-the-passenger",
        (
            Awareness(knower="dexter", learned_at=1),
            Awareness(knower="doakes", learned_at=6),
        ),
    )

    with pytest.raises(ValueError, match="would remove knower"):
        store.record_learning(
            "f-the-passenger", (Awareness(knower="dexter", learned_at=1),)
        )


def test_a_scope_that_would_delay_an_acquisition_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path / "canon.db")
    store.append(_secret())

    with pytest.raises(ValueError, match="would delay"):
        store.record_learning(
            "f-the-passenger", (Awareness(knower="dexter", learned_at=9),)
        )


def test_recording_learning_on_an_untracked_fact_is_refused(tmp_path: Path) -> None:
    """Attaching a scope to a public fact hides it from everyone not listed."""
    store = _store(tmp_path / "canon.db")
    store.append(_secret().model_copy(update={"knower_scope": None, "revealed_at": 1}))

    with pytest.raises(ValueError, match="untracked"):
        store.record_learning(
            "f-the-passenger", (Awareness(knower="deb", learned_at=2),)
        )


def test_recording_learning_on_a_missing_fact_fails_loudly(tmp_path: Path) -> None:
    """A silent no-op would drop a turn's knowledge update with nothing to show for it."""
    store = _store(tmp_path / "canon.db")

    with pytest.raises(KeyError):
        store.record_learning("f-absent", (Awareness(knower="deb", learned_at=2),))


def test_knowledge_compounds_across_turns_and_persists(tmp_path: Path) -> None:
    """project_context.md 4.2: at step N the world reflects every choice 1..N-1.

    Three turns, three scenes, a restart between each — the shape of an actual playthrough.
    """
    db = tmp_path / "canon.db"
    _store(db).append(_secret())

    for chapter, witness in ((3, "deb"), (5, "doakes"), (8, "rita")):
        store = _store(db)
        current = store.get("f-the-passenger")
        assert current is not None
        updated = witnesses_learn(
            current, _scene(chapter, {witness: PresenceGrade.ACTIVE})
        )
        assert updated.knower_scope is not None
        store.record_learning("f-the-passenger", updated.knower_scope)

    final = _store(db)
    stored = final.get("f-the-passenger")
    assert stored is not None
    assert {a.knower: a.learned_at for a in stored.knower_scope or ()} == {
        "dexter": 1,
        "deb": 3,
        "doakes": 5,
        "rita": 8,
    }

    # And the compounding is visible through the guard, per character, at every step.
    assert not final.visible_to("canon", "rita", 7)
    assert final.visible_to("canon", "rita", 8)
    assert not final.visible_to("canon", AUDIENCE, 27), "the audience was never told"

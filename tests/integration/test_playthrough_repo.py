"""L2 integration — the SQLite playthrough-repository adapter against a REAL database (tmp file).

Proves the run envelope survives across the exact gap it exists for: `POST /play` writes it,
`POST /play/{id}/act` (a separate request, maybe a separate process) reads it back. The durability
proof closes the engine and reopens a fresh one against the same file — a store that only works
while the process is warm would pass every test that skips that step.
"""

from pathlib import Path

import pytest

from story_engine.adapters.outbound.persistence import (
    SqlitePlaythroughRepository,
    create_db_engine,
    init_db,
)
from story_engine.domain.models.canon import Presence, PresenceGrade
from story_engine.domain.models.play import (
    ChoiceOption,
    Citation,
    Consequence,
    Playthrough,
    Turn,
)

pytestmark = pytest.mark.integration


def _choice(choice_id: str, present: tuple[str, ...]) -> ChoiceOption:
    return ChoiceOption(
        id=choice_id,
        label=f"option {choice_id}",
        source_work_id="wattpad:864850",
        consequence=Consequence(
            subject_id="dexter",
            predicate="chose",
            object_literal=f"the {choice_id} path",
            roster=tuple(
                Presence(entity_id=entity_id, grade=PresenceGrade.ACTIVE)
                for entity_id in present
            ),
            secret=False,
        ),
    )


def _turn(index: int, choices: tuple[ChoiceOption, ...]) -> Turn:
    return Turn(
        index=index,
        chapter=index + 1,
        protagonist="dexter",
        scene=f"scene text for turn {index}",
        choices=choices,
        citations=(
            Citation(
                fact_id="f-harry-code",
                source_id="darkly-dreaming-dexter",
                chapter=1,
                quote="Harry, who made the rules careful and exact",
            ),
        ),
        withheld_count=2,
    )


def _three_turn_run() -> Playthrough:
    """A run with realistic 2-4-choice turns — an empty stub would prove nothing here."""
    return Playthrough(
        fork_id="canon",
        protagonist="dexter",
        chapter=3,
        turns=(
            _turn(
                0,
                (
                    _choice("t1:hunt", ("dexter",)),
                    _choice("t1:answer-deb", ("dexter", "deborah")),
                ),
            ),
            _turn(
                1,
                (
                    _choice("t2:take-deb", ("dexter", "deborah")),
                    _choice("t2:shut-out", ("dexter",)),
                ),
            ),
            _turn(2, ()),  # run has ended: zero choices is the valid terminal shape
        ),
    )


@pytest.fixture
def repo(tmp_path: Path) -> SqlitePlaythroughRepository:
    """A repository backed by a fresh, real SQLite file per test."""
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    return SqlitePlaythroughRepository(engine)


def test_create_then_get_round_trips_the_run(
    repo: SqlitePlaythroughRepository,
) -> None:
    run = _three_turn_run()

    run_id = repo.create(run)
    loaded = repo.get(run_id)

    assert loaded == run


def test_create_generates_the_run_id_never_accepts_one(
    repo: SqlitePlaythroughRepository,
) -> None:
    run_id = repo.create(_three_turn_run())

    assert isinstance(run_id, str)
    assert run_id  # non-empty
    # A second create() gets a DIFFERENT id, even for an identical run — no collision.
    other_id = repo.create(_three_turn_run())
    assert other_id != run_id


def test_get_returns_none_for_an_unknown_run_id(
    repo: SqlitePlaythroughRepository,
) -> None:
    assert repo.get("does-not-exist") is None


def test_save_updates_an_existing_run(repo: SqlitePlaythroughRepository) -> None:
    run = _three_turn_run()
    run_id = repo.create(run)

    advanced = run.model_copy(update={"chapter": 4})
    repo.save(run_id, advanced)

    assert repo.get(run_id) == advanced


def test_save_on_an_unknown_run_id_raises_rather_than_inserting(
    repo: SqlitePlaythroughRepository,
) -> None:
    with pytest.raises(KeyError):
        repo.save("does-not-exist", _three_turn_run())

    assert repo.get("does-not-exist") is None  # confirms nothing was inserted


def test_round_trip_survives_a_close_and_reopen_of_the_engine(tmp_path: Path) -> None:
    """Write, CLOSE, reopen against the same file, and assert the data is intact.

    Skipping the close-and-reopen is how a store that only works while the process is warm
    passes every test that skips it (`.claude/rules/testing.md`).
    """
    db = tmp_path / "durable.db"
    engine = create_db_engine(f"sqlite:///{db}")
    init_db(engine)
    run = _three_turn_run()
    run_id = SqlitePlaythroughRepository(engine).create(run)
    engine.dispose()  # close every pooled connection — simulate process exit

    reopened = create_db_engine(f"sqlite:///{db}")
    reloaded = SqlitePlaythroughRepository(reopened).get(run_id)

    assert reloaded == run
    assert reloaded is not None
    assert reloaded.turns[0].choices[0].consequence.roster == (
        Presence(entity_id="dexter", grade=PresenceGrade.ACTIVE),
    )

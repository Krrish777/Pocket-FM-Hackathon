"""L2 integration — the SQLite episode-log adapter against a REAL database (tmp file).

Proves the adapter's side effects are correct (writes persist, ordering holds, JSON fields round-trip)
— the cross-layer behavior unit tests with mocks cannot catch. Asserts schema/invariants, never text.
"""

from pathlib import Path

import pytest

from story_engine.adapters.outbound.persistence import (
    SqliteEpisodeLogRepository,
    create_db_engine,
    init_db,
)
from story_engine.domain.models import EpisodeSummary


@pytest.fixture
def repo(tmp_path: Path) -> SqliteEpisodeLogRepository:
    """A repository backed by a fresh, real SQLite file per test."""
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    return SqliteEpisodeLogRepository(engine)


def _summary(series_id: str, number: int) -> EpisodeSummary:
    return EpisodeSummary(
        series_id=series_id,
        episode_number=number,
        synopsis=f"synopsis {number}",
        character_actions={"hero": "acts"},
        events=("event-a", "event-b"),
        emotional_beat="tense",
    )


@pytest.mark.integration
def test_append_then_get_recent_returns_newest_last(
    repo: SqliteEpisodeLogRepository,
) -> None:
    for n in (1, 2, 3):
        repo.append_summary(_summary("s1", n))

    recent = repo.get_recent("s1", n=2)

    assert [e.episode_number for e in recent] == [2, 3]  # newest last
    assert all(isinstance(e, EpisodeSummary) for e in recent)


@pytest.mark.integration
def test_json_collection_fields_round_trip(
    repo: SqliteEpisodeLogRepository,
) -> None:
    repo.append_summary(_summary("s1", 1))

    (loaded,) = repo.get_recent("s1", n=1)

    assert loaded.events == (
        "event-a",
        "event-b",
    )  # tuple preserved through JSON list column
    assert loaded.character_actions == {"hero": "acts"}


@pytest.mark.integration
def test_get_by_episode_hit_and_miss(repo: SqliteEpisodeLogRepository) -> None:
    repo.append_summary(_summary("s1", 7))

    assert repo.get_by_episode("s1", 7) is not None
    assert repo.get_by_episode("s1", 99) is None
    assert repo.get_by_episode("other", 7) is None  # series isolation


@pytest.mark.integration
def test_series_are_isolated(repo: SqliteEpisodeLogRepository) -> None:
    repo.append_summary(_summary("s1", 1))
    repo.append_summary(_summary("s2", 1))

    assert len(repo.get_recent("s1", n=10)) == 1
    assert len(repo.get_recent("s2", n=10)) == 1

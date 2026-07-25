"""Integration test for the composition root — REAL SQLite file, never `:memory:`.

Proves `bootstrap.build_container` actually wires the Knowledge Base (canon store, working
memory, the turn loop) end to end: a fresh container, against a real temp SQLite file, can begin
a playthrough and get back a rendered `Turn`.

`llm_provider="scripted"` throughout — this is the offline demo path and the whole test suite's
guarantee that `build_container` needs no `OPENAI_API_KEY` and touches no network.
"""

from pathlib import Path

import pytest

from story_engine.bootstrap import build_container
from story_engine.config.settings import Settings
from story_engine.domain.models.play import Playthrough, Turn
from story_engine.resources.dexter_demo import CAST, FORK_ID

pytestmark = pytest.mark.integration


def test_build_container_needs_no_api_key_when_llm_provider_is_scripted(
    tmp_path: Path,
) -> None:
    """The offline demo and the test suite both depend on this: no key, still boots."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'no_key.db'}",
        llm_provider="scripted",
        openai_api_key=None,
    )

    container = build_container(settings)

    assert container.llm is not None
    assert container.playthrough is not None


def test_container_playthrough_begins_a_run_and_renders_a_turn(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'demo.db'}",
        llm_provider="scripted",
    )

    container = build_container(settings)
    protagonist = next(iter(CAST))
    run = container.playthrough.begin(
        fork_id=FORK_ID, protagonist=protagonist, chapter=1
    )

    assert isinstance(run, Playthrough)
    assert len(run.turns) == 1
    assert isinstance(run.turns[0], Turn)
    assert run.turns[0].protagonist == protagonist

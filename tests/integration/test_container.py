"""Integration test for the composition root — REAL SQLite file, never `:memory:`.

Proves `bootstrap.build_container` actually wires the Knowledge Base (canon store, working
memory, the turn loop) end to end: a fresh container, against a real temp SQLite file, can begin
a playthrough and get back a rendered `Turn`.

`llm_provider="scripted"` throughout — this is the offline demo path and the whole test suite's
guarantee that `build_container` needs no `OPENAI_API_KEY` and touches no network.
"""

from pathlib import Path

import pytest

from story_engine import bootstrap as bootstrap_module
from story_engine.bootstrap import build_container
from story_engine.config.settings import Settings
from story_engine.domain.models.play import Playthrough, Turn
from story_engine.resources.dexter_demo import CAST, FORK_ID
from story_engine.services.demo_seed import DemoSeedError

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


def test_build_container_degrades_rather_than_crashing_when_the_demo_seed_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for the bug fixed in the Task 3 review round.

    `bootstrap._seed_demo_fork_if_empty` originally caught `DocumentIngestionError` around the
    call to `seed_canon`, but `seed_canon` actually raises `DemoSeedError` — a SIBLING of
    `DocumentIngestionError` under `StoryEngineError`, not a subclass of it — so that `except`
    never fired for the failure it was written to catch. A drifted anchor offset (a realistic,
    anticipated failure — the novel text or its chunking changes between sessions) therefore
    propagated uncaught straight out of `build_container()`, crashing app boot, and made
    `story-engine reconcile` (which itself calls `build_container()`) unreachable in exactly the
    situation it exists to repair.

    This forces that exact failure via monkeypatch and asserts `build_container` still returns a
    usable container instead of raising. Without the fix (reverting the `except` clause to name
    only `DocumentIngestionError`), this test fails with an uncaught `DemoSeedError`.
    """

    def _raise_demo_seed_error(*_args: object, **_kwargs: object) -> tuple[object, ...]:
        raise DemoSeedError("simulated anchor drift: offsets no longer resolve")

    monkeypatch.setattr(bootstrap_module, "seed_canon", _raise_demo_seed_error)
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'seed_failure.db'}",
        llm_provider="scripted",
    )

    container = build_container(settings)  # must not raise

    assert container.llm is not None
    assert container.playthrough is not None
    # The failed seed left the fork's canon empty — that is the honest, reported degradation.
    assert container.canon_store.all_facts(FORK_ID) == ()

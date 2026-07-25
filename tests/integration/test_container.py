"""Integration test for the composition root — REAL SQLite file, never `:memory:`.

Proves `bootstrap.build_container` actually wires the Knowledge Base (canon store, working
memory, the turn loop) end to end: a fresh container, against a real temp SQLite file, can begin
a playthrough and get back a rendered `Turn`.

`llm_provider="scripted"` throughout — this is the offline demo path and the whole test suite's
guarantee that `build_container` needs no `OPENAI_API_KEY` and touches no network.
"""

from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import pytest

from story_engine import bootstrap as bootstrap_module
from story_engine.bootstrap import build_container
from story_engine.cli.ingest import build_facts_from_novel, build_ingest_service
from story_engine.config.settings import Settings
from story_engine.domain.models.play import Playthrough, Turn
from story_engine.resources.dexter_demo import CAST, FORK_ID
from story_engine.services.demo_seed import DemoSeedError

pytestmark = pytest.mark.integration

_INGEST_CHAPTERS = [
    "Chapter 1: Night Work\n"
    "Dexter kept the slides in a rosewood box beneath the air conditioner. He counted them "
    "twice before the sun came up, and the Passenger counted with him.",
    "Chapter 2: Deborah\n"
    "Deborah asked about the harbour again over breakfast. She did not know about the box, "
    "and Dexter intended to keep it that way.",
]


def _write_novel(path: Path) -> Path:
    """Render `_INGEST_CHAPTERS` into a genuine multi-page PDF, one chapter per page."""
    document = pymupdf.open()
    for body in _INGEST_CHAPTERS:
        page = document.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    document.save(path)
    document.close()
    return path


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


def test_container_serves_a_novel_ingested_via_the_ingest_cli_path(
    tmp_path: Path,
) -> None:
    """GAP 1 regression test: an ingested novel must be reachable through `build_container`.

    `story-engine ingest` and `bootstrap.build_container` used to point at different DBs by
    default (`data/interim/canon_ingest.db` vs `data/interim/demo.db`), so a fully-ingested novel
    was inert — unreachable from the API or `PlaythroughService`. This proves the fix:
    `settings.database_url` pointed at the SAME file the ingest CLI wrote to makes the container's
    canon store serve exactly those facts, unmodified, through the existing `visible_to` guard —
    no new read path, no re-seed, no duplication.
    """
    novel = _write_novel(tmp_path / "novel.pdf")
    db = tmp_path / "canon_ingest.db"

    facts = build_facts_from_novel(
        novel,
        source_id="test-novel",
        fork_id=FORK_ID,  # matches both the ingest CLI's default `--fork` and the demo's FORK_ID
        chunk_size=200,
        overlap=50,
        recorded_at=datetime(2026, 7, 26, 9, 0, tzinfo=UTC),
    )
    assert facts, "ingestion produced no facts at all"

    service, _store, _vectors = build_ingest_service(db)
    written = service.ingest(facts)
    assert written == len(facts)

    settings = Settings(
        database_url=f"sqlite:///{db}",
        llm_provider="scripted",
    )

    container = build_container(settings)

    # The 612-fact trap: pointing the container at an already-populated DB must NOT trigger the
    # demo-fork seed-on-empty path, and must not duplicate the ingested facts.
    served_facts = container.canon_store.all_facts(FORK_ID)
    assert {f.id for f in served_facts} == {f.id for f in facts}
    assert len(served_facts) == len(facts)

    # The API/services read path — `visible_to` — still gates by chapter over the ingested data.
    max_chapter = max(f.provenance.chapter for f in facts)
    visible_at_one = container.canon_store.visible_to(FORK_ID, "dexter", 1)
    assert {f.provenance.chapter for f in visible_at_one} == {1}

    visible_at_end = container.canon_store.visible_to(FORK_ID, "dexter", max_chapter)
    assert {f.provenance.chapter for f in visible_at_end} == set(
        range(1, max_chapter + 1)
    )

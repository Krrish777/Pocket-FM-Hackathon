"""The rehearsed demo path must be fully authored — no beat may fall through to the composer.

A gap in the script does not raise. It silently degrades one beat to mechanical prose in the middle
of the pitch, and it degrades the beat *nobody rehearsed*, which is by definition the one nobody
checked. So coverage is asserted mechanically rather than eyeballed.

The second test is the one that matters: it re-derives Deborah's visible-fact counts from the guard
and pins the flat spot at chapters 3-4. That flat spot is not a detail — it is the demo. If a future
change lets her see one more fact there, the closing beat stops being true and this fails.
"""

from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.adapters.outbound.scripted_oracle import ScriptedBranchOracle
from story_engine.resources.dexter_demo import FORK_ID, THE_SECRET
from story_engine.resources.dexter_demo_script import DEMO_SCRIPT
from story_engine.services.demo_seed import demo_branches, seed_canon
from story_engine.services.playthrough import PlaythroughService
from story_engine.services.working_memory import WorkingMemory

pytestmark = pytest.mark.e2e

REHEARSED = (
    "t1:hunt",
    "t2:take-deb",
    "t3:confront-doakes",
    "t4:rita-dinner",
    "t5:finish",
)


class _RecordingLLM(ScriptedLLM):
    """A scripted LLM that remembers which keys it was asked for."""

    def __init__(self, script: dict[str, str]) -> None:
        super().__init__(script)
        self.requested: list[str] = []

    def generate(self, **kwargs: object) -> object:  # type: ignore[override]
        key = kwargs.get("idempotency_key")
        if isinstance(key, str):
            self.requested.append(key)
        return super().generate(**kwargs)  # type: ignore[arg-type]


def _service(db: Path, llm: ScriptedLLM) -> PlaythroughService:
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)
    seed_canon(store, PdfDocumentSource())
    return PlaythroughService(
        store=store,
        memory=WorkingMemory(store),
        oracle=ScriptedBranchOracle(demo_branches()),
        llm=llm,
        prompts=FilePromptStore("prompts"),
    )


def test_every_beat_of_the_rehearsed_path_is_authored(tmp_path: Path) -> None:
    """Play the demo exactly as it will be shown, and require the script to cover all of it."""
    llm = _RecordingLLM(DEMO_SCRIPT)
    service = _service(tmp_path / "demo.db", llm)

    run = service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)
    for choice_id in REHEARSED:
        run = service.advance(run, choice_id)
    service.replay_as(run, "deborah")

    unscripted = [key for key in llm.requested if key not in DEMO_SCRIPT]
    assert not unscripted, (
        f"these beats would fall back to mechanical prose on stage: {unscripted}. "
        f"Author them in resources/dexter_demo_script.py."
    )
    assert len(llm.requested) == 12, "six turns as Dexter, six re-rendered as Deborah"


def test_deborah_never_sees_the_secret_anywhere_in_the_replay(tmp_path: Path) -> None:
    """The closing beat, checked against the guard rather than against the authored prose."""
    service = _service(tmp_path / "demo.db", ScriptedLLM(DEMO_SCRIPT))

    run = service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)
    for choice_id in REHEARSED:
        run = service.advance(run, choice_id)
    replay = service.replay_as(run, "deborah")

    cited = {citation.fact_id for turn in replay.turns for citation in turn.citations}
    assert THE_SECRET not in cited

    dexter_cited = {
        citation.fact_id for turn in run.turns for citation in turn.citations
    }
    assert THE_SECRET in dexter_cited, (
        "and Dexter's own run must cite it, or there is no contrast"
    )


def test_deborahs_knowledge_stalls_across_the_disclosure_turn(tmp_path: Path) -> None:
    """Chapter 4 must add exactly nothing to Deborah's view, while adding to Dexter's.

    Chapter 4 is where Doakes ends up in the lot and learns what Dexter is. Standing outside it,
    Deborah gains nothing at all — that flat spot is the mechanism made visible, and it is the
    reason the closing beat lands.

    Measured against `visible_to` rather than against the rendered turn: `citations` is capped at
    `CITATION_LIMIT` and `withheld_count` moves for reasons of its own, so neither is a faithful
    proxy for "how much can she actually see".
    """
    db = tmp_path / "demo.db"
    service = _service(db, ScriptedLLM(DEMO_SCRIPT))

    run = service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)
    for choice_id in REHEARSED:
        run = service.advance(run, choice_id)

    store = SqliteCanonStore(create_engine(f"sqlite:///{db}"))

    def visible(knower: str, chapter: int) -> int:
        return len(store.visible_to(FORK_ID, knower, chapter))

    assert visible("deborah", 1) == 0, "she begins the branch knowing nothing at all"
    assert visible("deborah", 3) == visible("deborah", 4), (
        "chapter 4 is the disclosure; Deborah was not there, so it must teach her nothing"
    )
    assert visible("dexter", 4) > visible("dexter", 3), (
        "and it must teach Dexter something, or the flat spot proves nothing"
    )
    assert visible("doakes", 4) > visible("doakes", 3), "Doakes was in the room"

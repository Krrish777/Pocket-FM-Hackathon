"""The rest of the cast must actually reach the prompt, and must not smuggle anything in with them.

`domain/reactions.py` is unit-tested in isolation; this asserts the wiring — that a real turn
assembles real directives from the real guard and puts them in front of the renderer. A derivation
nothing calls is not a feature (`project_context.md` §4.4).
"""

import re
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
from story_engine.ports.llm import Generation
from story_engine.resources.dexter_demo import CAST, FORK_ID
from story_engine.services.demo_seed import demo_branches, seed_canon
from story_engine.services.playthrough import PlaythroughService
from story_engine.services.working_memory import WorkingMemory

pytestmark = pytest.mark.e2e


class _PromptCapture(ScriptedLLM):
    """Keeps every prompt the loop built, so the assembled context itself can be inspected."""

    def __init__(self) -> None:
        super().__init__()
        self.prompts: list[str] = []

    def generate(self, **kwargs: object) -> Generation:  # type: ignore[override]
        messages = kwargs["messages"]
        assert isinstance(messages, list)
        self.prompts.append(str(messages[-1]["content"]))
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
        cast=CAST,
    )


def test_the_prompt_tells_the_renderer_what_the_other_cast_does_not_know(
    tmp_path: Path,
) -> None:
    """Dexter's opening beat must carry directives for the other four, with real blind spots."""
    llm = _PromptCapture()
    service = _service(tmp_path / "demo.db", llm)

    service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)

    prompt = llm.prompts[0]
    assert "WHO ELSE IS IN THIS STORY" in prompt
    for name in (
        "Deborah Morgan",
        "Sergeant Doakes",
        "Migdia LaGuerta",
        "Rita Bennett",
    ):
        assert name in prompt, f"{name} should be present as a reacting character"
    assert "Dexter Morgan —" not in prompt, "the actor gets no directive about himself"
    assert "Does NOT know:" in prompt, "the blind spots are the behavioural instruction"


def test_a_directive_never_names_a_fact_the_actor_cannot_see(tmp_path: Path) -> None:
    """The structural anti-leak property, asserted on the real assembled prompt.

    Play far enough that Doakes learns the secret, then render a beat for DEBORAH. Doakes now knows
    something she does not — and because directives are a subtraction from *her* view, his knowledge
    cannot appear anywhere in her prompt. A design that described each character's own state would
    look almost identical here and would leak.
    """
    llm = _PromptCapture()
    service = _service(tmp_path / "demo.db", llm)

    run = service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)
    for choice_id in ("t1:hunt", "t2:take-deb", "t3:confront-doakes"):
        run = service.advance(run, choice_id)

    llm.prompts.clear()
    service.replay_as(run, "deborah")

    for prompt in llm.prompts:
        assert "Dark Passenger" not in prompt, (
            "Deborah's prompt named the secret she never learned — either the guard or the "
            "directive derivation is leaking"
        )


def test_tension_is_derived_from_the_story_not_authored(tmp_path: Path) -> None:
    """Reaction is computed from state, not from a personality stat somebody typed in.

    A stat would be a stored asymmetry by another name, and it would not move when the story does.
    """
    llm = _PromptCapture()
    service = _service(tmp_path / "demo.db", llm)

    run = service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)
    opening = llm.prompts[0]

    for choice_id in ("t1:hunt", "t2:take-deb", "t3:confront-doakes"):
        run = service.advance(run, choice_id)
    later = llm.prompts[-1]

    def tension_of(name: str, prompt: str) -> int:
        found = re.search(rf"{name} — tension toward dexter: (\d)/5", prompt)
        assert found, f"no directive for {name} in the prompt"
        return int(found.group(1))

    # The relationship, not a guessed constant. Doakes was in the parking lot and learned the
    # secret; Rita has been in none of it. So Doakes must read as CLOSER to Dexter's picture than
    # Rita does — and nobody edited a character sheet to make that true.
    assert tension_of("Sergeant Doakes", later) < tension_of("Rita Bennett", later), (
        "being in the room must reduce how far behind a character reads"
    )
    assert opening != later, "the directives must change as the story does"

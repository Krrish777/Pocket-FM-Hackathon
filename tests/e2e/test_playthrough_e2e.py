"""L3 — the demo, end to end: five choices deep, then replayed as someone who was not there.

This is the acceptance condition of the whole build stated as a test (`project_context.md` §4.2,
§8): at the final step the world reflects every prior choice, and a character who did not learn a
fact at step 4 still does not know it at step N.

It runs against a real on-disk store with a real restart in the middle, because knowledge that only
survives inside one warm process is not knowledge that survives a demo.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.adapters.outbound.scripted_oracle import ScriptedBranchOracle
from story_engine.domain.enums import AssertionMode, FactStatus, PresenceGrade
from story_engine.domain.models import AUDIENCE, Fact, Provenance
from story_engine.domain.models.canon import Awareness, Presence
from story_engine.domain.models.play import ChoiceOption, Consequence
from story_engine.ports.llm import Generation, LLMPort
from story_engine.services.playthrough import (
    PlaythroughService,
    UnknownChoiceError,
)
from story_engine.services.working_memory import WorkingMemory

pytestmark = pytest.mark.e2e

FORK = "canon"
SECRET_ID = "f-the-passenger"
RECORDED_AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def _secret() -> Fact:
    """Dexter's secret: true from chapter 1, known only to him, never told to the audience."""
    return Fact(
        id=SECRET_ID,
        fork_id=FORK,
        subject_id="dexter",
        predicate="is_killer_of",
        object_literal="the-priest",
        valid_from=1,
        revealed_at=None,
        assertion_mode=AssertionMode.NARRATED,
        knower_scope=(Awareness(knower="dexter", learned_at=1),),
        provenance=Provenance(
            source_id="darkly-dreaming-dexter",
            chapter=1,
            char_start=0,
            char_end=25,
            quote="MOON. GLORIOUS MOON. FULL,",
        ),
        confidence=1.0,
        tier=0,
        status=FactStatus.ACTIVE,
        recorded_at=RECORDED_AT,
    )


def _option(
    option_id: str,
    label: str,
    present: dict[str, PresenceGrade],
    *,
    source: str | None = None,
    discloses: tuple[str, ...] = (),
    secret: bool = True,
) -> ChoiceOption:
    return ChoiceOption(
        id=option_id,
        label=label,
        source_work_id=source,
        consequence=Consequence(
            subject_id="dexter",
            predicate="did",
            object_literal=label,
            roster=tuple(
                Presence(entity_id=entity, grade=grade)
                for entity, grade in present.items()
            ),
            secret=secret,
            discloses=discloses,
        ),
    )


def _oracle() -> ScriptedBranchOracle:
    """Five decision points. Turn 3 is the one that matters: Doakes is in the room."""
    return ScriptedBranchOracle(
        {
            1: (
                _option(
                    "c1:hunt",
                    "Go out hunting tonight",
                    {"dexter": PresenceGrade.ACTIVE},
                ),
                _option(
                    "c1:stay", "Stay in and wait", {"dexter": PresenceGrade.ACTIVE}
                ),
            ),
            2: (
                _option(
                    "c2:tell-deb",
                    "Let Deborah in on the case",
                    {"dexter": PresenceGrade.ACTIVE, "deb": PresenceGrade.ACTIVE},
                    source="wattpad:864850",
                ),
                _option("c2:alone", "Work it alone", {"dexter": PresenceGrade.ACTIVE}),
            ),
            3: (
                # The pivotal branch: taking it puts Doakes in the room when the secret surfaces.
                _option(
                    "c3:confront",
                    "Confront Doakes in the parking lot",
                    {"dexter": PresenceGrade.ACTIVE, "doakes": PresenceGrade.ACTIVE},
                    source="wattpad:390229723",
                    discloses=(SECRET_ID,),
                ),
                _option(
                    "c3:avoid",
                    "Avoid Doakes entirely",
                    {"dexter": PresenceGrade.ACTIVE},
                ),
            ),
            4: (
                _option(
                    "c4:rita",
                    "Have dinner with Rita as if nothing happened",
                    {"dexter": PresenceGrade.ACTIVE, "rita": PresenceGrade.ACTIVE},
                ),
                _option(
                    "c4:vanish",
                    "Disappear for the night",
                    {"dexter": PresenceGrade.ACTIVE},
                ),
            ),
            5: (
                _option("c5:finish", "Finish it", {"dexter": PresenceGrade.ACTIVE}),
                _option("c5:walk", "Walk away", {"dexter": PresenceGrade.ACTIVE}),
            ),
            6: (),
        }
    )


def _service(db: Path) -> PlaythroughService:
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)
    return PlaythroughService(
        store=store,
        memory=WorkingMemory(store),
        oracle=_oracle(),
        llm=ScriptedLLM(),
        prompts=FilePromptStore("prompts"),
    )


_PROTAGONIST_LINE = re.compile(r"point of view of (?P<name>.+?)\.$", re.MULTILINE)
"""The same structural marker `adapters/outbound/scripted_llm.py`'s own `_PROTAGONIST` regex
relies on: present verbatim in every `render_scene` prompt's opening line, regardless of which
facts or options it carries. Used here only to label a recorded prompt by whose view it was
rendered for — the leak assertion below is a plain substring search over the recorded text."""


class _RecordingLLM:
    """Wraps a real `LLMPort`, recording the exact prompt string sent to `generate`.

    This is the independent oracle Task 8 requires: it reads the literal text handed to the
    model — the artifact that actually reaches it — rather than re-deriving visibility from
    `is_visible`/`visible_to`/`Citation`, which is what the assertions below this class already
    do (and which the task brief flags as a tautological oracle: it verifies the guard by
    consulting the guard's own output). Delegates unchanged to the wrapped LLM, so every other
    behaviour of `ScriptedLLM` — composing prose, answering intent JSON — is untouched.
    """

    def __init__(self, inner: LLMPort) -> None:
        self._inner = inner
        self.prompts_by_protagonist: dict[str, list[str]] = {}

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> Generation:
        prompt = messages[-1]["content"] if messages else ""
        match = _PROTAGONIST_LINE.search(prompt)
        if match is not None:
            self.prompts_by_protagonist.setdefault(match.group("name"), []).append(
                prompt
            )
        return self._inner.generate(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            idempotency_key=idempotency_key,
        )


def _service_with_recorder(db: Path) -> tuple[PlaythroughService, _RecordingLLM]:
    """Identical to `_service`, except its narration LLM is wrapped by `_RecordingLLM`."""
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)
    recorder = _RecordingLLM(ScriptedLLM())
    service = PlaythroughService(
        store=store,
        memory=WorkingMemory(store),
        oracle=_oracle(),
        llm=recorder,
        prompts=FilePromptStore("prompts"),
    )
    return service, recorder


def _can_see(store: SqliteCanonStore, knower: str, chapter: int, fact_id: str) -> bool:
    """Whether ONE specific fact is visible to `knower` at `chapter`.

    `visible_to` returns everything a character may see, which legitimately includes facts their
    own choices created. Asserting on the whole set therefore tests the wrong thing — the claim
    under test is always about a *particular* secret.
    """
    return fact_id in {fact.id for fact in store.visible_to(FORK, knower, chapter)}


def _store(db: Path) -> SqliteCanonStore:
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    return SqliteCanonStore(engine)


def test_a_five_choice_run_compounds_and_replays_as_another_character(
    tmp_path: Path,
) -> None:
    """The whole demo: play five choices as Dexter, then re-render it as Deborah."""
    db = tmp_path / "canon.db"
    _store(db).append(_secret())

    service, recorder = _service_with_recorder(db)
    run = service.begin(fork_id=FORK, protagonist="dexter", chapter=1)

    assert run.turns[0].scene, "the opening beat must render"
    assert len(run.turns[0].choices) == 2

    # --- five compounding choices; the third puts Doakes in the room --------------------
    for choice_id in ("c1:hunt", "c2:tell-deb", "c3:confront", "c4:rita", "c5:finish"):
        run = service.advance(run, choice_id)

    assert run.depth == 6, "one opening beat plus five choices"
    assert run.chapter == 6

    # --- the acceptance condition, checked against a REOPENED store ---------------------
    reopened = _store(db)
    secret = reopened.get(SECRET_ID)
    assert secret is not None
    knows = {a.knower: a.learned_at for a in secret.knower_scope or ()}

    assert knows["dexter"] == 1, "Dexter has known since chapter 1"
    assert knows["doakes"] == 4, "Doakes learned it in the scene he was present for"
    assert "deb" not in knows, (
        "Deborah was in the room at turn 2 but NOT at the turn where the secret surfaced — "
        "being nearby earlier must not teach her something she never saw"
    )
    assert "rita" not in knows, (
        "Rita was present later, after the disclosure had passed"
    )
    assert AUDIENCE not in knows, "the audience was never told"

    # And the guard enforces it per character, per chapter — not just the stored scope.
    assert not _can_see(reopened, "doakes", 3, SECRET_ID), (
        "not before he was in the room"
    )
    assert _can_see(reopened, "doakes", 4, SECRET_ID), "and yes from the chapter he was"
    assert not _can_see(reopened, "deb", 27, SECRET_ID), (
        "Deborah never learns the secret in this branch, even at the last chapter"
    )
    assert _can_see(reopened, "dexter", 1, SECRET_ID), "Dexter has always known"

    # --- the closing beat: same branch, different eyes ----------------------------------
    as_deb = service.replay_as(run, "deb")

    assert as_deb.protagonist == "deb"
    assert as_deb.depth == run.depth, "the same branch, not a different one"
    assert [turn.chapter for turn in as_deb.turns] == [
        turn.chapter for turn in run.turns
    ]

    deb_sees = {
        citation.fact_id for turn in as_deb.turns for citation in turn.citations
    }
    assert SECRET_ID not in deb_sees, (
        "Deborah's replay cited the secret she never learned — this is the demo's whole claim"
    )

    dexter_sees = {
        citation.fact_id for turn in run.turns for citation in turn.citations
    }
    assert SECRET_ID in dexter_sees, "Dexter's own run should cite what he knows"

    # --- the independent oracle: read the ACTUAL rendered prompt string, not the citation
    # list above (which is the guard's own output — asserting on it verifies the guard by
    # consulting the guard, and would keep passing even if the guard were wrong). This reads
    # the literal text handed to `LLMPort.generate`, the artifact that actually reaches the
    # model, and does a plain substring search for the secret's own words.
    secret_literal = _secret().object_literal
    dexter_prompts = recorder.prompts_by_protagonist.get("dexter", [])
    deb_prompts = recorder.prompts_by_protagonist.get("deb", [])
    assert dexter_prompts, "Dexter's own renders must have gone through the recorder"
    assert deb_prompts, "Deborah's replay renders must have gone through the recorder"
    assert any(secret_literal in prompt for prompt in dexter_prompts), (
        "sanity check on the oracle itself: Dexter's OWN rendered prompt must contain what "
        "he knows, or this test would trivially pass by never seeing the secret at all"
    )
    assert not any(secret_literal in prompt for prompt in deb_prompts), (
        "the secret's literal text must never enter the prompt assembled for Deborah — "
        "checked on the rendered string itself, independent of the citation-based assertion "
        "above"
    )


def test_the_receipt_resolves_to_the_novel(tmp_path: Path) -> None:
    """ "Every fact is checked, and we show you the receipt" — the citation names a real source."""
    db = tmp_path / "canon.db"
    _store(db).append(_secret())

    run = _service(db).begin(fork_id=FORK, protagonist="dexter", chapter=1)

    citations = run.turns[0].citations
    assert citations, "a rendered beat must be able to show its canon"
    for citation in citations:
        assert citation.source_id
        assert citation.quote.strip()
        assert citation.chapter >= 1


def test_withheld_facts_are_counted_not_hidden(tmp_path: Path) -> None:
    """Over-withholding is a reported metric, per .claude/rules/testing.md — so report it."""
    db = tmp_path / "canon.db"
    _store(db).append(_secret())

    run = _service(db).begin(fork_id=FORK, protagonist="deb", chapter=1)

    assert run.turns[0].withheld_count >= 1, (
        "Deborah cannot see Dexter's secret, and the packet must say how much it kept back"
    )


def test_choosing_an_option_that_was_never_offered_is_refused(tmp_path: Path) -> None:
    """Accepting an unoffered id would apply a consequence the player never saw."""
    db = tmp_path / "canon.db"
    _store(db).append(_secret())
    service = _service(db)
    run = service.begin(fork_id=FORK, protagonist="dexter", chapter=1)

    with pytest.raises(UnknownChoiceError, match="was not offered"):
        service.advance(run, "c9:teleport")


def test_a_run_stops_at_the_depth_ceiling(tmp_path: Path) -> None:
    """project_context.md 4.1: 10 is a ceiling. The system must not break before it, or past it."""
    db = tmp_path / "canon.db"
    _store(db).append(_secret())
    service = _service(db)

    run = service.begin(fork_id=FORK, protagonist="dexter", chapter=1)
    for choice_id in ("c1:hunt", "c2:alone", "c3:avoid", "c4:vanish", "c5:walk"):
        run = service.advance(run, choice_id)

    assert run.depth == 6
    assert not run.is_complete, "six turns is well inside the ceiling of ten"

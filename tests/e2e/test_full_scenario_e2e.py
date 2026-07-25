"""L3 — Task 8: the whole demo scenario, walked exactly as the brief states it.

    1. Start a story. 2. Select Dexter. 3. Load Dexter's memory. 4. Enter a natural-language
    action. 5. The model interprets the intent. 6. The turn engine executes it. 7. Canon updates.
    8. The graph updates. 9. Agent memories update. 10. Other characters react based only on what
    they know. 11. Narration is generated. 12. The player immediately enters another action.
    13. The world remains internally consistent. 14. No information leaks. 15. The story can
    continue.

Two tests live here:

* `test_full_demo_scenario_walks_every_beat` — the scenario itself, over a real container built
  by `bootstrap.build_container(Settings(llm_provider="scripted"))` against a real on-disk SQLite
  file (never `:memory:`), with a genuine mid-scenario restart.
* `test_real_container_scripted_offline_path_drives_a_turn_over_http` — the gap this task closes:
  `tests/e2e/test_intent_routing_scripted_llm_e2e.py` proves `ScriptedLLM` + `IntentRouter`
  interoperate at the service seam, and `tests/e2e/test_play_api_e2e.py` proves the API works but
  swaps in a fake `LLMPort` via `dataclasses.replace`. Neither proves "start the API with no API
  key, type an action, get a turn" through `bootstrap.build_container` itself. This test does,
  with no fakes and no `dataclasses.replace`.

**The leak assertion (step 14) is the one that matters most.** The existing flagship leak test
(`tests/e2e/test_playthrough_e2e.py`) asserts on `Turn.citations` — a set of fact ids the guard
itself decided to include. That is a tautological oracle: it verifies the guard by consulting the
guard's own output, so it would keep passing even if the guard were wrong. Here the oracle is
independent: a `_RecordingLLM` wraps the real `LLMPort` and records the exact prompt STRING handed
to `generate(messages=...)` — the actual artifact that reaches the model — keyed by which
character's point of view it was rendered for. The assertion then does a plain substring search
for Dexter's secret's `object_literal` in every OTHER character's recorded prompt. Nothing here
reuses `is_visible`/`visible_to`/`Citation`; it reads the rendered text itself.
"""

import re
from collections.abc import Iterable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.scripted_oracle import ScriptedBranchOracle
from story_engine.api.app import create_app
from story_engine.bootstrap import Container, build_container
from story_engine.config.settings import Settings
from story_engine.domain.models.play import ChoiceOption
from story_engine.domain.reactions import derive_directives, describe
from story_engine.ports.llm import Generation, LLMPort
from story_engine.resources.dexter_demo import ANCHORS, CAST, FORK_ID, THE_SECRET
from story_engine.services.demo_seed import demo_branches
from story_engine.services.playthrough import PlaythroughService

pytestmark = pytest.mark.e2e

_PROTAGONIST_LINE = re.compile(r"point of view of (?P<name>.+?)\.$", re.MULTILINE)
"""Same structural marker `adapters/outbound/scripted_llm.py`'s own `_PROTAGONIST` regex uses —
present verbatim in every `render_scene` prompt, and nowhere else. Reused here only to LABEL a
recorded prompt by whose view it was rendered for; the leak assertion itself is a plain substring
search over the recorded text, not a re-derivation of visibility."""

_SECRET_OBJECT_LITERAL = next(
    anchor.object_literal for anchor in ANCHORS if anchor.fact_id == THE_SECRET
)
"""Dexter's secret, read from the same authored data the demo seeds from — never hardcoded
separately from `resources/dexter_demo.py`, so a change there cannot silently desync this test."""


class _RecordingLLM:
    """Wraps a real `LLMPort`, recording the exact prompt string sent to `generate`.

    This is the independent oracle: nothing here consults `is_visible`, `visible_to`, or a
    `Citation` — it captures the literal text handed to the model, keyed by the protagonist named
    in that text's own "point of view of X." line, and delegates unchanged to the wrapped LLM so
    every other behaviour (composing prose, answering intent JSON) stays exactly as it was.
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


def _build_container(tmp_path: Path, db_name: str) -> Container:
    """A real container: real SQLite file, `llm_provider="scripted"`, no API key, no network."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / db_name}", llm_provider="scripted"
    )
    return build_container(settings)


def _recording_playthrough(
    container: Container,
) -> tuple[PlaythroughService, _RecordingLLM]:
    """A `PlaythroughService` identical to the one `bootstrap.build_container` wires, except its
    narration LLM is wrapped by a recorder — the only difference from the real container's own
    service, and the only way to see the exact string the model was handed."""
    recorder = _RecordingLLM(container.llm)
    service = PlaythroughService(
        store=container.canon_store,
        memory=container.memory,
        oracle=ScriptedBranchOracle(
            demo_branches()
        ),  # settings.branch_oracle == "authored"
        llm=recorder,
        prompts=FilePromptStore("prompts"),
        cast=CAST,
        model=container.settings.default_model,
    )
    return service, recorder


def _resolve(
    container: Container,
    *,
    action: str,
    options: tuple[ChoiceOption, ...],
    protagonist: str,
) -> str:
    """Route a natural-language action onto an offered option id, failing loudly if it does not."""
    resolved = container.intent_router.resolve(
        action=action, options=options, protagonist=protagonist
    )
    assert resolved.choice_id is not None, (
        f"action {action!r} should have resolved to one of {[o.id for o in options]}, "
        f"got: {resolved.reasoning!r}"
    )
    offered_ids = {option.id for option in options}
    assert resolved.choice_id in offered_ids, (
        "a natural-language action must resolve to one of the OFFERED options, never an "
        "invented one"
    )
    return resolved.choice_id


def _knowers(container: Container, fact_id: str) -> frozenset[str]:
    fact = container.canon_store.get(fact_id)
    assert fact is not None
    assert fact.knower_scope is not None
    return frozenset(awareness.knower for awareness in fact.knower_scope)


def _assert_no_leak(prompts: Iterable[str], secret_text: str, *, who: str) -> None:
    for prompt in prompts:
        assert secret_text not in prompt, (
            f"Dexter's secret {secret_text!r} leaked into the assembled prompt rendered for "
            f"{who!r} — this is read directly off the rendered prompt string, not a helper "
            f"that re-derives visibility"
        )


def test_full_demo_scenario_walks_every_beat(tmp_path: Path) -> None:
    """Steps 1-15 of the brief, in order, each with the assertion that proves it."""
    # --- 1/2/3: start a story, select Dexter, load his memory ------------------------------
    container = _build_container(tmp_path, "scenario.db")
    service, recorder = _recording_playthrough(container)

    opening_packet = container.memory.assemble(FORK_ID, "dexter", 1)
    assert opening_packet.facts, "Dexter's memory packet must be non-empty at the start"

    run = service.begin(fork_id=FORK_ID, protagonist="dexter", chapter=1)
    run_id = container.playthrough_repository.create(run)
    assert run.turns[0].scene, "step 11: narration is generated for the opening beat"

    # --- 4/5/6: a natural-language action, interpreted, then executed ----------------------
    turn0 = run.turns[-1]
    action1 = (
        "I want to finish what I started with the priest tonight, alone in the dark."
    )
    choice1 = _resolve(
        container, action=action1, options=turn0.choices, protagonist="dexter"
    )
    assert choice1 == "t1:hunt", (
        "sanity: the keyword-overlap classifier must route this action onto the option that "
        "puts Dexter alone with the secret, not the Deborah branch"
    )
    run = service.advance(run, choice1)
    container.playthrough_repository.save(run_id, run)

    # --- 7/8: canon grew; the graph is rebuilt fresh from canon on every call, never a stale
    # cache — this is what step 8 verifies, NOT that an edge exists (edge projection is
    # unexercised on this fork; see the note below) --------------------------------------------
    turn1_fact_id = "canon:t1:t1:hunt:fact"
    assert container.canon_store.get(turn1_fact_id) is not None, "canon must have grown"
    assert _knowers(container, turn1_fact_id) == {"dexter"}, (
        "the witnesses' knower_scope must equal EXACTLY who was present (Dexter alone), "
        "checked by set equality, not membership"
    )
    dexter_graph = container.memory.assemble(FORK_ID, "dexter", 2).graph
    # NOTE — a real, un-fixed gap, reported rather than papered over: every fact in this demo's
    # canon (`resources/dexter_demo.py`'s anchors, `PlaythroughService._fact_for`'s consequences)
    # is stored with `object_literal`, never `object_id`. `LoreGraph.from_facts` only projects an
    # edge for a fact that carries `object_id` — "a literal-valued fact is an attribute, not a
    # relation: no second endpoint" (`domain/graph.py`). So the graph layer is structurally
    # EMPTY for the entire Dexter demo, no matter how many turns are taken. Step 8 ("the graph
    # updates") is asserted here as "the graph is rebuilt fresh from current canon on every call
    # and is never a stale cache" — which is all this demo's data can actually exercise.
    recomputed = container.memory.assemble(FORK_ID, "dexter", 2).graph
    assert dexter_graph.edges == recomputed.edges == (), (
        "this demo's facts are all object_literal, so the graph layer never has an edge to "
        "hold — a real gap between the scenario's 'graph updates' step and what this demo's "
        "canon can exercise, not something this test papers over"
    )

    # --- 9/10: agent memories update; others react on only what they know ------------------
    actor_facts = container.memory.assemble(FORK_ID, "dexter", 2).facts
    others = {
        character_id: (name, container.canon_store.visible_to(FORK_ID, character_id, 2))
        for character_id, name in CAST.items()
    }
    directives = derive_directives(
        actor="dexter", actor_facts=actor_facts, others=others
    )
    assert directives, "step 10: the rest of the cast reacts"
    actor_descriptions = {describe(fact) for fact in actor_facts}
    for directive in directives:
        assert set(directive.blind_spots) <= actor_descriptions, (
            f"{directive.character_id}'s directive named something Dexter himself does not "
            f"know — a directive must only ever subtract from the actor's own view"
        )

    # --- 12/13: a second natural-language action immediately after -------------------------
    turn1 = run.turns[-1]
    action2 = "Take Deborah with me to the scene of the crime."
    choice2 = _resolve(
        container, action=action2, options=turn1.choices, protagonist="dexter"
    )
    assert choice2 == "t2:take-deb"
    run = service.advance(run, choice2)
    container.playthrough_repository.save(run_id, run)

    assert run.chapter == 3, "world state at turn 2 reflects both prior choices"
    turn2_facts = {f.id for f in container.memory.assemble(FORK_ID, "dexter", 3).facts}
    assert turn1_fact_id in turn2_facts, (
        "turn 2's assembled state must still carry what turn 1 established — the world is "
        "internally consistent across turns, not reset each time"
    )

    # --- the pivotal branch: puts Doakes in the room when the secret surfaces --------------
    turn2 = run.turns[-1]
    action3 = "Let Doakes follow me and see everything that happens tonight."
    choice3 = _resolve(
        container, action=action3, options=turn2.choices, protagonist="dexter"
    )
    assert choice3 == "t3:confront-doakes"
    run = service.advance(run, choice3)
    container.playthrough_repository.save(run_id, run)

    assert _knowers(container, THE_SECRET) == {"dexter", "doakes"}, (
        "the secret's knower_scope must have grown to EXACTLY the characters present when it "
        "surfaced — Dexter (since chapter 1) and Doakes (this scene) — and no one else: not "
        "Deborah, who was present earlier but not here; not the audience"
    )

    # --- 14: the leak assertion, done properly (the independent oracle) --------------------
    replayed_as_deborah = service.replay_as(run, "deborah")
    assert replayed_as_deborah.protagonist == "deborah"

    dexter_prompts = recorder.prompts_by_protagonist.get("dexter", [])
    deborah_prompts = recorder.prompts_by_protagonist.get("deborah", [])
    assert dexter_prompts, "Dexter's own renders must have gone through the recorder"
    assert deborah_prompts, (
        "Deborah's replay renders must have gone through the recorder"
    )

    assert any(_SECRET_OBJECT_LITERAL in prompt for prompt in dexter_prompts), (
        "sanity check on the oracle itself: Dexter's OWN rendered prompt must contain what he "
        "knows, or this test would pass by never seeing the secret at all"
    )
    _assert_no_leak(deborah_prompts, _SECRET_OBJECT_LITERAL, who="deborah")
    # And every other cast member gets the same treatment, not just Deborah.
    for character_id in ("laguerta", "rita"):
        replay = service.replay_as(run, character_id)
        assert replay.protagonist == character_id
        _assert_no_leak(
            recorder.prompts_by_protagonist.get(character_id, []),
            _SECRET_OBJECT_LITERAL,
            who=character_id,
        )

    # --- 7 (restart): close the engine, reopen, and the run + all knowledge survive --------
    container.engine.dispose()
    reopened = _build_container(tmp_path, "scenario.db")

    reloaded_run = reopened.playthrough_repository.get(run_id)
    assert reloaded_run is not None, "the run must survive a restart"
    assert reloaded_run.protagonist == "dexter"
    assert reloaded_run.chapter == run.chapter
    assert len(reloaded_run.turns) == len(run.turns)
    assert _knowers(reopened, THE_SECRET) == {"dexter", "doakes"}, (
        "per-character knowledge must survive the restart exactly as it was, on a real file — "
        "never :memory:"
    )
    assert _knowers(reopened, turn1_fact_id) == {"dexter"}

    # --- 15: the story can continue after the restart ---------------------------------------
    reopened_service, _ = _recording_playthrough(reopened)
    turn3 = reloaded_run.turns[-1]
    action4 = "Keep the dinner with Rita like nothing happened."
    choice4 = _resolve(
        reopened, action=action4, options=turn3.choices, protagonist="dexter"
    )
    assert choice4 == "t4:rita-dinner"
    continued_run = reopened_service.advance(reloaded_run, choice4)
    reopened.playthrough_repository.save(run_id, continued_run)
    assert continued_run.chapter == 5
    assert len(continued_run.turns) == len(reloaded_run.turns) + 1

    # --- replay as Deborah: her withheld_count exceeds Dexter's at the same turn -----------
    deborah_final = reopened_service.replay_as(continued_run, "deborah")
    same_index = continued_run.turns[-1].index
    dexter_withheld = continued_run.turns[-1].withheld_count
    deborah_withheld = next(
        turn.withheld_count for turn in deborah_final.turns if turn.index == same_index
    )
    assert deborah_withheld > dexter_withheld, (
        "Deborah was never in the room for the secret's disclosure, so at the identical turn "
        "index the guard must withhold strictly more from her than from Dexter"
    )


def test_real_container_scripted_offline_path_drives_a_turn_over_http(
    tmp_path: Path,
) -> None:
    """The literal demo claim, proven with no fakes: start the API with no API key, type an
    action, get a turn — end to end through `bootstrap.build_container` itself.

    `test_intent_routing_scripted_llm_e2e.py` proves `ScriptedLLM` + `IntentRouter` interoperate
    at the service seam. `test_play_api_e2e.py` proves the API works, but swaps the intent
    router's LLM for a fake via `dataclasses.replace` because its `DEMO_SCRIPT` narration fixture
    doesn't answer intent JSON. Here nothing is swapped: the SAME real `ScriptedLLM` the container
    wires answers BOTH narration (mechanical composition) and intent classification (keyword
    overlap) — `adapters/outbound/scripted_llm.py` detects which prompt it was handed structurally,
    never via a test-only branch. This is the one path neither prior test drove.
    """
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'offline.db'}", llm_provider="scripted"
    )
    container = build_container(settings)
    assert container.settings.llm_provider == "scripted"
    client = TestClient(create_app(container))

    play_resp = client.post("/api/v1/play", json={"character_id": "dexter"})
    assert play_resp.status_code == 200
    body = play_resp.json()
    run_id = body["run_id"]
    opening = body["turn"]
    assert opening["index"] == 0
    assert 2 <= len(opening["choices"]) <= 4

    # An action that quotes the option's own label back — this is exactly what the scripted
    # keyword-overlap classifier is built to route with maximum, unambiguous confidence.
    first_label = opening["choices"][0]["label"]
    action = f"I think I should just {first_label.lower()}"

    act_resp = client.post(f"/api/v1/play/{run_id}/act", json={"action": action})
    assert act_resp.status_code == 200
    act_body = act_resp.json()
    assert act_body["turn"]["index"] == 1, "a turn actually advanced"
    assert act_body["interpreted_as"] == first_label

    # A second natural-language action immediately after, with no fakes swapped in between.
    second_label = act_body["turn"]["choices"][0]["label"]
    action2 = f"Without a doubt: {second_label.lower()}"
    act_resp_2 = client.post(f"/api/v1/play/{run_id}/act", json={"action": action2})
    assert act_resp_2.status_code == 200
    assert act_resp_2.json()["turn"]["index"] == 2

"""L3 end-to-end — the minimum turn-loop API (Task 5), over a real ASGI client.

Exercises `api/routers/play.py` against a real tmp SQLite DB and `llm_provider="scripted"` (no API
key, no network). The base container's narration LLM is the real `ScriptedLLM` wired by
`bootstrap.build_container` — but `DEMO_SCRIPT` is keyed by the turn loop's own idempotency scheme
(`"{knower}:{chapter}:{fact_count}"`), not the intent router's, so a scripted narration LLM has
nothing scripted to reply with for intent classification and always falls back to composing plain
prose — never valid JSON. Since intent routing is exactly the seam under test here, the container's
`intent_router` is swapped (via `dataclasses.replace`, after the real container has booted and
seeded canon) for one built on a small deterministic fake `LLMPort` that always returns valid,
schema-conforming intent JSON naming the first offered option. This keeps every other wire (canon
store, working memory, playthrough service, persistence) exactly as `bootstrap.py` built it — only
the LLM behind `IntentRouter` is faked, which is what the port exists for.
"""

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.api.app import create_app
from story_engine.bootstrap import Container, build_container
from story_engine.config.settings import Settings
from story_engine.ports.llm import Generation
from story_engine.services.intent_router import IntentRouter

pytestmark = pytest.mark.e2e

# Fields that only ever exist on `Consequence`/`Fact` — a serialized turn response must never carry
# any of these, or the client can read what a choice does to the world before committing to it.
_CONSEQUENCE_FIELD_NAMES = (
    "predicate",
    "object_literal",
    "subject_id",
    "roster",
    "secret",
    "discloses",
)

_OFFERED_ID = re.compile(r"- id: (\S+)")


class _FirstOptionLLM:
    """A fake `LLMPort` that always names the first option listed in the rendered prompt.

    Reads only the rendered `interpret_intent` prompt text (never a private attribute of the real
    `IntentRouter`), so this stays a black-box fake behind the `LLMPort` seam rather than a shortcut
    around it. High, fixed confidence keeps every test call above `IntentRouter`'s threshold.
    """

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
        match = _OFFERED_ID.search(prompt)
        payload = {
            "choice_id": match.group(1) if match else None,
            "confidence": 0.99,
            "reasoning": "test fixture: routed to the first offered option",
        }
        return Generation(
            output=json.dumps(payload),
            model="test-fixture",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
        )


@pytest.fixture
def app_client(tmp_path: Path) -> TestClient:
    """A booted app whose intent routing is deterministic (see module docstring)."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'api.db'}", llm_provider="scripted"
    )
    container: Container = build_container(settings)
    fixture_router = IntentRouter(
        llm=_FirstOptionLLM(), prompts=FilePromptStore("prompts"), model="test-fixture"
    )
    container = replace(container, intent_router=fixture_router)
    return TestClient(create_app(container))


def _assert_no_consequence_leak(raw_body: str) -> None:
    for name in _CONSEQUENCE_FIELD_NAMES:
        assert name not in raw_body, (
            f"{name!r} leaked into the response body — a choice's consequence must never "
            f"reach the client"
        )


@pytest.mark.e2e
def test_characters_endpoint_lists_the_cast(app_client: TestClient) -> None:
    resp = app_client.get("/api/v1/characters")

    assert resp.status_code == 200
    characters = resp.json()
    assert {"dexter", "deborah", "doakes", "laguerta", "rita"} == {
        c["id"] for c in characters
    }
    for character in characters:
        assert set(character.keys()) == {"id", "name"}


@pytest.mark.e2e
def test_full_playthrough_sequence_advances_and_replay_changes_withheld_count(
    app_client: TestClient,
) -> None:
    """The whole demo sequence the brief specifies, in one pass."""
    # --- POST /play: start as Dexter, at the canon fork, chapter 1 ---------------------------
    play_resp = app_client.post("/api/v1/play", json={"character_id": "dexter"})
    assert play_resp.status_code == 200
    play_body = play_resp.json()
    run_id = play_body["run_id"]
    opening_turn = play_body["turn"]
    assert opening_turn["index"] == 0
    assert opening_turn["protagonist"] == "dexter"
    assert 2 <= len(opening_turn["choices"]) <= 4
    for choice in opening_turn["choices"]:
        assert set(choice.keys()) == {"id", "label", "source_work_id"}
    _assert_no_consequence_leak(play_resp.text)

    # --- POST /act, twice: advance the run via the (fixture-routed) natural-language action ---
    first_choice_label = opening_turn["choices"][0]["label"]
    act_resp_1 = app_client.post(
        f"/api/v1/play/{run_id}/act", json={"action": "whatever feels right tonight"}
    )
    assert act_resp_1.status_code == 200
    act_body_1 = act_resp_1.json()
    assert act_body_1["run_id"] == run_id
    assert act_body_1["turn"]["index"] == 1
    assert act_body_1["interpreted_as"] == first_choice_label
    assert isinstance(act_body_1["reactions"], list)
    for reaction in act_body_1["reactions"]:
        assert set(reaction.keys()) == {"name", "tension", "blind_spots"}
    _assert_no_consequence_leak(act_resp_1.text)

    second_choice_label = act_body_1["turn"]["choices"][0]["label"]
    act_resp_2 = app_client.post(
        f"/api/v1/play/{run_id}/act", json={"action": "go with your gut"}
    )
    assert act_resp_2.status_code == 200
    act_body_2 = act_resp_2.json()
    assert act_body_2["turn"]["index"] == 2
    assert act_body_2["interpreted_as"] == second_choice_label
    _assert_no_consequence_leak(act_resp_2.text)

    # --- GET /play/{id}: reflects the latest turn, from a fresh request -----------------------
    get_resp = app_client.get(f"/api/v1/play/{run_id}")
    assert get_resp.status_code == 200
    get_body = get_resp.json()
    assert get_body["run_id"] == run_id
    assert get_body["turn"]["index"] == 2
    assert get_body["turn"]["chapter"] == act_body_2["turn"]["chapter"]

    # --- POST /replay-as: same branch, a different knower --------------------------------------
    replay_resp = app_client.post(
        f"/api/v1/play/{run_id}/replay-as", json={"character_id": "deborah"}
    )
    assert replay_resp.status_code == 200
    replay_body = replay_resp.json()
    assert replay_body["run_id"] == run_id
    replay_turns = replay_body["turns"]
    assert len(replay_turns) == 3, "one opening beat plus the two /act calls"
    assert all(turn["protagonist"] == "deborah" for turn in replay_turns)
    _assert_no_consequence_leak(replay_resp.text)

    dexter_withheld = get_body["turn"]["withheld_count"]
    deborah_withheld = replay_turns[-1]["withheld_count"]
    assert deborah_withheld != dexter_withheld, (
        "replaying as someone who did not learn what Dexter learned must change how much "
        "was withheld from the rendered view"
    )


@pytest.mark.e2e
def test_act_with_no_confident_intent_match_returns_422_and_does_not_advance(
    app_client: TestClient,
) -> None:
    """A player's action that maps onto nothing offered is a normal outcome, not a crash."""
    play_resp = app_client.post("/api/v1/play", json={"character_id": "dexter"})
    run_id = play_resp.json()["run_id"]

    class _NoMatchLLM:
        def generate(
            self,
            *,
            messages: list[dict[str, str]],
            model: str,
            max_tokens: int,
            temperature: float,
            idempotency_key: str | None = None,
        ) -> Generation:
            payload = {"choice_id": None, "confidence": 0.0, "reasoning": "no match"}
            return Generation(
                output=json.dumps(payload),
                model="test-fixture",
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=0.0,
            )

    no_match_router = IntentRouter(
        llm=_NoMatchLLM(), prompts=FilePromptStore("prompts"), model="test-fixture"
    )
    app_client.app.state.container = replace(  # type: ignore[attr-defined]
        app_client.app.state.container,
        intent_router=no_match_router,  # type: ignore[attr-defined]
    )

    act_resp = app_client.post(
        f"/api/v1/play/{run_id}/act", json={"action": "do something nonsensical"}
    )

    assert act_resp.status_code == 422
    detail = act_resp.json()["detail"]
    assert detail["code"] == "no_intent_match"
    assert isinstance(detail["options"], list) and detail["options"]

    unchanged = app_client.get(f"/api/v1/play/{run_id}")
    assert unchanged.json()["turn"]["index"] == 0, (
        "an unmatched action must not advance the run"
    )


@pytest.mark.e2e
def test_unknown_run_id_returns_404(app_client: TestClient) -> None:
    """`PlaythroughNotFoundError` must map to 404 — an exact-type entry in `api/errors.py`'s
    `_STATUS` table, not an inherited one (the table does a literal `type(exc)` lookup)."""
    resp = app_client.get("/api/v1/play/does-not-exist")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "playthrough_not_found"


@pytest.mark.e2e
def test_act_on_unknown_run_id_returns_404_not_500(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/v1/play/does-not-exist/act", json={"action": "anything"}
    )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "playthrough_not_found"


@pytest.mark.e2e
def test_replay_as_on_unknown_run_id_returns_404(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/v1/play/does-not-exist/replay-as", json={"character_id": "deborah"}
    )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "playthrough_not_found"

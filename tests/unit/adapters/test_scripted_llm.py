"""The fallback narrator must never say anything the prompt did not give it.

Two properties matter here and both are about containment, not prose quality: it may not recite the
player's upcoming options, and it may not invent knowledge that was not in the assembled context.

Also covers the intent-routing seam (Task 5b): `ScriptedLLM` must answer an `interpret_intent`
prompt with deterministic JSON, and this is proved by driving the real `IntentRouter` against it —
not by calling `ScriptedLLM` directly — because the bug this fixes was exactly the two not
interoperating.
"""

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.domain.enums import PresenceGrade
from story_engine.domain.models.play import ChoiceOption, Consequence, Presence
from story_engine.services.intent_router import IntentRouter


def _prompt(protagonist: str, facts: list[dict[str, str]], choices: list[str]) -> str:
    return FilePromptStore("prompts").render(
        "render_scene",
        version="v1",
        variables={
            "protagonist": protagonist,
            "chapter": 3,
            "facts": facts,
            "choices": choices,
        },
    )


def _generate(
    prompt: str, script: dict[str, str] | None = None, key: str | None = None
) -> str:
    return (
        ScriptedLLM(script)
        .generate(
            messages=[{"role": "user", "content": prompt}],
            model="scripted",
            max_tokens=500,
            temperature=0.8,
            idempotency_key=key,
        )
        .output
    )


def test_the_narration_never_recites_the_upcoming_choices() -> None:
    """The template renders facts AND options as `- ` bullets; a naive scan reads the menu.

    It did exactly that, and the demo narrated the player's own options back at them, three lines
    below a prompt instruction saying never to name them.
    """
    prompt = _prompt(
        "dexter",
        [
            {
                "subject": "dexter",
                "predicate": "hunts_with",
                "object": "the Dark Passenger",
                "quote": "we belonged to the Dark Passenger",
            }
        ],
        ["Finish what you started with the priest tonight", "Answer Deborah's message"],
    )

    output = _generate(prompt)

    assert "priest tonight" not in output
    assert "Deborah's message" not in output
    assert "Dark Passenger" in output, "it should still use what the character knows"


def test_a_character_who_knows_nothing_is_narrated_as_knowing_nothing() -> None:
    """Deborah at chapter 1 must not acquire knowledge from the renderer's imagination."""
    prompt = _prompt("deborah", [], ["Go north", "Go south"])

    output = _generate(prompt)

    assert "nothing to go on" in output
    assert "north" not in output.lower()


def test_a_scripted_beat_is_replayed_verbatim() -> None:
    """The demo path must be byte-identical every run — no sampling, no drift."""
    prompt = _prompt("dexter", [], ["a", "b"])
    authored = "The moon was full and Dexter was already gone."

    assert _generate(prompt, {"dexter:3:0": authored}, "dexter:3:0") == authored


def test_an_unscripted_beat_falls_back_instead_of_failing() -> None:
    """A missing beat should degrade to something readable, not break the run mid-demo."""
    prompt = _prompt("dexter", [], ["a", "b"])

    assert _generate(prompt, {"other:9:0": "unused"}, "dexter:3:0").strip()


def test_token_counts_are_zero_rather_than_invented() -> None:
    """A fabricated count would flow into the cost meter and make the budget confidently wrong."""
    generation = ScriptedLLM().generate(
        messages=[{"role": "user", "content": _prompt("dexter", [], [])}],
        model="scripted",
        max_tokens=100,
        temperature=0.8,
    )

    assert generation.prompt_tokens == 0
    assert generation.completion_tokens == 0
    assert generation.cost_usd == 0.0


def _choice_option(choice_id: str, label: str) -> ChoiceOption:
    return ChoiceOption(
        id=choice_id,
        label=label,
        consequence=Consequence(
            subject_id="dexter",
            predicate="does_something_secret",
            object_literal="a-consequence-that-must-never-reach-the-prompt",
            roster=(Presence(entity_id="dexter", grade=PresenceGrade.ACTIVE),),
        ),
    )


def _offered_options() -> tuple[ChoiceOption, ...]:
    return (
        _choice_option("opt-a", "Confront Doakes"),
        _choice_option("opt-b", "Hide the evidence"),
    )


def _intent_router(script: dict[str, str] | None = None) -> IntentRouter:
    return IntentRouter(
        llm=ScriptedLLM(script),
        prompts=FilePromptStore("prompts"),
        model="scripted-intent-model",
    )


def test_a_plainly_matching_typed_action_routes_through_the_real_intent_router() -> (
    None
):
    """Proves the fix: `ScriptedLLM` and `IntentRouter` actually interoperate now, not just that
    `ScriptedLLM` can produce JSON in isolation."""
    router = _intent_router()

    resolved = router.resolve(
        action="I want to hide the evidence before anyone finds it",
        options=_offered_options(),
        protagonist="dexter",
    )

    assert resolved.choice_id == "opt-b"
    assert resolved.confidence >= 0.6
    assert resolved.reasoning


def test_an_unrelated_typed_action_still_resolves_to_no_match() -> None:
    """The unresolved (422-over-HTTP) path must stay reachable in scripted mode — an action that
    shares no vocabulary with any offered option must not be forced onto one."""
    router = _intent_router()

    resolved = router.resolve(
        action="I fly to Cuba and start a new life",
        options=_offered_options(),
        protagonist="dexter",
    )

    assert resolved.choice_id is None


def test_a_render_prompt_still_returns_prose_not_json() -> None:
    """The existing render-prompt behaviour must be untouched by the intent-detection branch."""
    prompt = _prompt("dexter", [], ["Go north", "Go south"])

    output = _generate(prompt)

    assert not output.strip().startswith("{")
    assert "choice_id" not in output


def test_the_router_never_receives_a_choice_id_that_was_not_offered() -> None:
    """The router's security property, exercised against this adapter specifically: whatever
    `ScriptedLLM` answers, `IntentRouter.resolve` only ever returns an id drawn from the options it
    was given, or `None` — never something invented, and never something merely plausible."""
    options = _offered_options()
    offered_ids = {option.id for option in options}
    router = _intent_router()

    for action in [
        "I confront him about the blood slides",
        "I stash the evidence in the boat",
        "I fly to Cuba and start a new life",
        "",
        "hmm not sure what to do",
    ]:
        resolved = router.resolve(action=action, options=options, protagonist="dexter")
        assert resolved.choice_id is None or resolved.choice_id in offered_ids

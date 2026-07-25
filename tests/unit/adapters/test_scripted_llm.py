"""The fallback narrator must never say anything the prompt did not give it.

Two properties matter here and both are about containment, not prose quality: it may not recite the
player's upcoming options, and it may not invent knowledge that was not in the assembled context.
"""

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM


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

"""E2E — natural-language routing works with no API key (Task 5b).

`story-engine play` and the HTTP API both wire `IntentRouter` onto `ScriptedLLM` when
`settings.llm_provider == "scripted"` (see `cli/play.py`, `bootstrap.py`). This test exercises that
exact pairing at the service seam, without going through the CLI process or the ASGI app, to keep
it cheap while still proving the two real components interoperate end to end.
"""

import pytest

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.domain.enums import PresenceGrade
from story_engine.domain.models.play import ChoiceOption, Consequence, Presence
from story_engine.services.intent_router import IntentRouter

pytestmark = pytest.mark.e2e


def _option(choice_id: str, label: str) -> ChoiceOption:
    return ChoiceOption(
        id=choice_id,
        label=label,
        consequence=Consequence(
            subject_id="dexter",
            predicate="does_something_secret",
            object_literal="never-reaches-the-prompt",
            roster=(Presence(entity_id="dexter", grade=PresenceGrade.ACTIVE),),
        ),
    )


def test_no_api_key_scripted_stack_routes_natural_language_end_to_end() -> None:
    """The stage guarantee: with no API key configured, a typed action still resolves."""
    router = IntentRouter(
        llm=ScriptedLLM(),
        prompts=FilePromptStore("prompts"),
        model="gpt-4o-mini",  # never read by ScriptedLLM; a stand-in for the demo's placeholder id
    )
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )

    matched = router.resolve(
        action="I hide the evidence before he sees it",
        options=options,
        protagonist="dexter",
    )
    unmatched = router.resolve(
        action="I fly to Cuba and start a new life",
        options=options,
        protagonist="dexter",
    )

    assert matched.choice_id == "opt-b"
    assert unmatched.choice_id is None, (
        "the 422-over-HTTP path must stay reachable for scripted mode"
    )

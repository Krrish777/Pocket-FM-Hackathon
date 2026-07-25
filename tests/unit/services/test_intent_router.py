"""Unit tests for the natural-language intent router — a router onto a constrained action set.

The LLM is a hand-written fake (`_FakeLLM`), never a network call, per `.claude/rules/testing.md`.
The properties under test are the ones that make this a router and not an interpreter: a
hallucinated `choice_id` must never reach a caller, malformed output must never raise, and the
prompt the model sees must never carry a consequence.
"""

from collections.abc import Sequence

import pytest

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.domain.enums import PresenceGrade
from story_engine.domain.models.play import ChoiceOption, Consequence, Presence
from story_engine.ports.llm import Generation
from story_engine.services.intent_router import IntentRouter

MODEL = "test-intent-model"


class _FakeLLM:
    """Records every call it receives and returns pre-scripted output, in call order."""

    def __init__(self, outputs: Sequence[str]) -> None:
        self._outputs = list(outputs)
        self.calls: list[dict[str, object]] = []

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> Generation:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "idempotency_key": idempotency_key,
            }
        )
        output = self._outputs.pop(0)
        return Generation(
            output=output,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
        )


def _option(choice_id: str, label: str) -> ChoiceOption:
    return ChoiceOption(
        id=choice_id,
        label=label,
        consequence=Consequence(
            subject_id="dexter",
            predicate="does_something_secret",
            object_literal="a-consequence-nobody-should-see-in-the-prompt",
            roster=(Presence(entity_id="dexter", grade=PresenceGrade.ACTIVE),),
        ),
    )


@pytest.fixture
def prompts() -> FilePromptStore:
    return FilePromptStore("prompts")


def _router(
    llm: _FakeLLM, prompts: FilePromptStore, threshold: float = 0.6
) -> IntentRouter:
    return IntentRouter(llm=llm, prompts=prompts, model=MODEL, threshold=threshold)


def test_clear_match_routes_to_the_right_choice(prompts: FilePromptStore) -> None:
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(
        [
            '{"choice_id": "opt-b", "confidence": 0.9, "reasoning": "you chose to hide it"}'
        ]
    )
    router = _router(llm, prompts)

    resolved = router.resolve(
        action="I stash the evidence where no one will look",
        options=options,
        protagonist="dexter",
    )

    assert resolved.choice_id == "opt-b"
    assert resolved.confidence == pytest.approx(0.9)
    assert resolved.reasoning


def test_invented_choice_id_is_rejected_to_none(prompts: FilePromptStore) -> None:
    """The security test: a `choice_id` the model made up must never reach a caller."""
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(
        [
            '{"choice_id": "opt-z-does-not-exist", "confidence": 0.95, "reasoning": "invented"}'
        ]
    )
    router = _router(llm, prompts)

    resolved = router.resolve(action="anything", options=options, protagonist="dexter")

    assert resolved.choice_id is None


def test_malformed_json_resolves_to_no_match_without_raising(
    prompts: FilePromptStore,
) -> None:
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(["this is not json at all {{{"])
    router = _router(llm, prompts)

    resolved = router.resolve(action="anything", options=options, protagonist="dexter")

    assert resolved.choice_id is None


def test_json_wrapped_in_a_code_fence_still_parses(prompts: FilePromptStore) -> None:
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(
        [
            '```json\n{"choice_id": "opt-a", "confidence": 0.8, '
            '"reasoning": "you chose to confront him"}\n```'
        ]
    )
    router = _router(llm, prompts)

    resolved = router.resolve(
        action="I go talk to Doakes", options=options, protagonist="dexter"
    )

    assert resolved.choice_id == "opt-a"


def test_below_threshold_confidence_resolves_to_no_match(
    prompts: FilePromptStore,
) -> None:
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(
        ['{"choice_id": "opt-a", "confidence": 0.3, "reasoning": "weak guess"}']
    )
    router = _router(llm, prompts, threshold=0.6)

    resolved = router.resolve(
        action="hmm, not sure", options=options, protagonist="dexter"
    )

    assert resolved.choice_id is None


def test_empty_options_short_circuits_with_zero_llm_calls(
    prompts: FilePromptStore,
) -> None:
    llm = _FakeLLM([])
    router = _router(llm, prompts)

    resolved = router.resolve(action="anything", options=(), protagonist="dexter")

    assert resolved.choice_id is None
    assert llm.calls == []


def test_rendered_prompt_carries_labels_but_never_consequence(
    prompts: FilePromptStore,
) -> None:
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(
        [
            '{"choice_id": "opt-a", "confidence": 0.9, "reasoning": "you chose to confront him"}'
        ]
    )
    router = _router(llm, prompts)

    router.resolve(action="I go talk to Doakes", options=options, protagonist="dexter")

    rendered = llm.calls[0]["messages"][0]["content"]  # type: ignore[index]
    assert "Confront Doakes" in rendered
    assert "Hide the evidence" in rendered
    for option in options:
        assert option.consequence.predicate not in rendered
        assert option.consequence.object_literal not in rendered


def test_llm_call_uses_low_temperature_and_max_tokens(prompts: FilePromptStore) -> None:
    options = (
        _option("opt-a", "Confront Doakes"),
        _option("opt-b", "Hide the evidence"),
    )
    llm = _FakeLLM(
        [
            '{"choice_id": "opt-a", "confidence": 0.9, "reasoning": "you chose to confront him"}'
        ]
    )
    router = _router(llm, prompts)

    router.resolve(action="I go talk to Doakes", options=options, protagonist="dexter")

    call = llm.calls[0]
    assert call["temperature"] == pytest.approx(0.2)
    assert call["max_tokens"] == 200
    assert isinstance(call["idempotency_key"], str)
    assert call["idempotency_key"].startswith("intent:dexter:")

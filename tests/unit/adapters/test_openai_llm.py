"""Unit tests for `OpenAILLM` — a fake `_ChatClient`, never the real SDK, never a key.

Every test injects a double through `client=`, so the suite proves the adapter's own behaviour
(cost accounting, retries, idempotent replay, boundary validation) without touching the network or
requiring `OPENAI_API_KEY`. `.claude/rules/testing.md` forbids asserting on generated text; these
tests assert schema and invariants instead.
"""

import logging
from types import SimpleNamespace
from typing import Any

import pytest

from story_engine.adapters.outbound.openai_llm import OpenAILLM
from story_engine.shared.errors import BudgetExceededError, GenerationError


class RateLimitError(Exception):
    """Stands in for `openai.RateLimitError` — the adapter matches on class name only."""


class _StatusError(Exception):
    """A generic SDK error carrying `status_code`, the other retry signal the adapter reads."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class FakeChatClient:
    """A tiny double for the `.chat.completions.create(...)` slice of the OpenAI SDK.

    `script` is consumed one item per call: a response object is returned, an exception is raised.
    Every request's kwargs are recorded in `calls` so tests can assert on what was sent.
    """

    def __init__(self, script: list[Any]) -> None:
        self._script = list(script)
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_response(
    *,
    content: str | None = "Dexter checks the blood spatter twice.",
    model: str = "gpt-4o",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    finish_reason: str = "stop",
    choices: list[Any] | None = None,
) -> SimpleNamespace:
    """Build a minimal fake chat-completion response."""
    if choices is None:
        message = SimpleNamespace(content=content)
        choices = [SimpleNamespace(message=message, finish_reason=finish_reason)]
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    return SimpleNamespace(choices=choices, usage=usage, model=model)


def test_a_normal_call_returns_a_generation_matching_the_fake_response() -> None:
    response = make_response(
        content="Dexter checks the blood spatter twice.",
        model="gpt-4o",
        prompt_tokens=120,
        completion_tokens=64,
    )
    client = FakeChatClient([response])
    adapter = OpenAILLM(client=client)

    generation = adapter.generate(
        messages=[{"role": "user", "content": "narrate"}],
        model="gpt-4o",
        max_tokens=500,
        temperature=0.8,
    )

    assert generation.output == "Dexter checks the blood spatter twice."
    assert generation.model == "gpt-4o"
    assert generation.prompt_tokens == 120
    assert generation.completion_tokens == 64


def test_max_completion_tokens_is_present_in_every_request() -> None:
    client = FakeChatClient([make_response(), make_response()])
    adapter = OpenAILLM(client=client)

    adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=321,
        temperature=0.5,
    )
    adapter.generate(
        messages=[{"role": "user", "content": "b"}],
        model="gpt-4o-mini",
        max_tokens=64,
        temperature=0.2,
    )

    assert len(client.calls) == 2
    for call, expected_tokens in zip(client.calls, (321, 64), strict=True):
        assert call["max_completion_tokens"] == expected_tokens


def test_temperature_is_sent_for_gpt4o_and_omitted_for_gpt5() -> None:
    client = FakeChatClient(
        [make_response(model="gpt-4o"), make_response(model="gpt-5")]
    )
    adapter = OpenAILLM(client=client)

    adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
    )
    adapter.generate(
        messages=[{"role": "user", "content": "b"}],
        model="gpt-5",
        max_tokens=100,
        temperature=0.7,
    )

    assert client.calls[0]["temperature"] == 0.7
    assert "temperature" not in client.calls[1]


def test_a_repeated_idempotency_key_does_not_call_the_client_again() -> None:
    client = FakeChatClient([make_response(content="only once")])
    adapter = OpenAILLM(client=client)

    first = adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
        idempotency_key="dexter:1:2",
    )
    second = adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
        idempotency_key="dexter:1:2",
    )

    assert len(client.calls) == 1
    assert second == first


def test_spent_usd_accumulates_and_a_replay_does_not_increase_it() -> None:
    client = FakeChatClient(
        [
            make_response(prompt_tokens=100, completion_tokens=50, model="gpt-4o"),
            make_response(prompt_tokens=200, completion_tokens=100, model="gpt-4o"),
        ]
    )
    adapter = OpenAILLM(client=client)

    adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
        idempotency_key="dexter:1:2",
    )
    first_cost = adapter.spent_usd
    assert first_cost == pytest.approx((100 * 2.50 + 50 * 10.00) / 1_000_000)

    adapter.generate(
        messages=[{"role": "user", "content": "b"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
        idempotency_key="dexter:1:4",
    )
    second_cost = adapter.spent_usd
    assert second_cost > first_cost

    adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
        idempotency_key="dexter:1:2",
    )
    assert adapter.spent_usd == second_cost
    assert len(client.calls) == 2


def test_an_unpriced_model_yields_zero_cost_and_logs_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeChatClient([make_response(model="some-unknown-model")])
    adapter = OpenAILLM(client=client)

    with caplog.at_level(logging.WARNING):
        generation = adapter.generate(
            messages=[{"role": "user", "content": "a"}],
            model="some-unknown-model",
            max_tokens=100,
            temperature=0.7,
        )

    assert generation.cost_usd == 0.0
    assert any("no price" in record.getMessage() for record in caplog.records)


def test_a_dated_snapshot_prices_via_longest_prefix_match() -> None:
    client = FakeChatClient(
        [
            make_response(
                model="gpt-4o-2024-08-06", prompt_tokens=100, completion_tokens=50
            )
        ]
    )
    adapter = OpenAILLM(client=client)

    generation = adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o-2024-08-06",
        max_tokens=100,
        temperature=0.7,
    )

    assert generation.model == "gpt-4o-2024-08-06"
    assert generation.cost_usd == pytest.approx((100 * 2.50 + 50 * 10.00) / 1_000_000)


def test_empty_content_raises_generation_error() -> None:
    client = FakeChatClient([make_response(content="   ")])
    adapter = OpenAILLM(client=client)

    with pytest.raises(GenerationError):
        adapter.generate(
            messages=[{"role": "user", "content": "a"}],
            model="gpt-4o",
            max_tokens=100,
            temperature=0.7,
        )


def test_no_choices_raises_generation_error() -> None:
    client = FakeChatClient([make_response(choices=[])])
    adapter = OpenAILLM(client=client)

    with pytest.raises(GenerationError):
        adapter.generate(
            messages=[{"role": "user", "content": "a"}],
            model="gpt-4o",
            max_tokens=100,
            temperature=0.7,
        )


def test_a_retryable_failure_is_retried_and_then_succeeds() -> None:
    client = FakeChatClient([RateLimitError("rate limited"), make_response()])
    adapter = OpenAILLM(client=client, backoff_seconds=0)

    generation = adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
    )

    assert len(client.calls) == 2
    assert generation.output


def test_a_status_429_failure_is_retried_and_then_succeeds() -> None:
    client = FakeChatClient([_StatusError(429), make_response()])
    adapter = OpenAILLM(client=client, backoff_seconds=0)

    generation = adapter.generate(
        messages=[{"role": "user", "content": "a"}],
        model="gpt-4o",
        max_tokens=100,
        temperature=0.7,
    )

    assert len(client.calls) == 2
    assert generation.output


def test_a_non_retryable_failure_raises_after_exactly_one_attempt() -> None:
    client = FakeChatClient([_StatusError(400)])
    adapter = OpenAILLM(client=client, backoff_seconds=0)

    with pytest.raises(GenerationError):
        adapter.generate(
            messages=[{"role": "user", "content": "a"}],
            model="gpt-4o",
            max_tokens=100,
            temperature=0.7,
        )

    assert len(client.calls) == 1


def test_constructing_with_neither_client_nor_api_key_raises() -> None:
    with pytest.raises(GenerationError):
        OpenAILLM()


def test_budget_already_reached_raises_before_any_client_call() -> None:
    client = FakeChatClient([make_response()])
    adapter = OpenAILLM(client=client, budget_usd=0.0)

    with pytest.raises(BudgetExceededError):
        adapter.generate(
            messages=[{"role": "user", "content": "a"}],
            model="gpt-4o",
            max_tokens=100,
            temperature=0.7,
        )

    assert client.calls == []

"""Unit tests for `build_llm` — the provider switch driven by `Settings.llm_provider`.

No test sets `OPENAI_API_KEY` or touches the network: the `"openai"` branch is exercised only
through the fail-fast path (missing key), and the `"scripted"` branch never needs a key at all.
"""

import pytest
from pydantic import SecretStr

from story_engine.adapters.outbound.llm_factory import build_llm
from story_engine.adapters.outbound.openai_llm import OpenAILLM
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.config.settings import Settings
from story_engine.resources.dexter_demo_script import DEMO_SCRIPT
from story_engine.shared.errors import GenerationError


def test_scripted_provider_returns_a_scripted_llm_preloaded_with_the_demo_script() -> (
    None
):
    settings = Settings(llm_provider="scripted", openai_api_key=None)

    llm = build_llm(settings)

    assert isinstance(llm, ScriptedLLM)
    assert llm.scripted_keys == frozenset(DEMO_SCRIPT)


def test_openai_provider_without_a_key_raises_generation_error_before_any_call() -> (
    None
):
    settings = Settings(llm_provider="openai", openai_api_key=None)

    with pytest.raises(GenerationError):
        build_llm(settings)


def test_openai_provider_with_a_key_returns_an_openai_llm_configured_with_the_budget() -> (
    None
):
    settings = Settings(
        llm_provider="openai",
        openai_api_key=SecretStr("sk-test-not-a-real-key"),
        request_budget_usd=1.23,
    )

    llm = build_llm(settings)

    assert isinstance(llm, OpenAILLM)
    assert llm.spent_usd == 0.0

"""Selects the configured `LLMPort` implementation.

The one place `Settings.llm_provider` is turned into a live adapter. Kept separate from
`bootstrap.py` (Task 3 owns wiring the container) so this module can be built and unit-tested in
isolation: constructing the wrong adapter is a boot-time failure, not a mid-demo one.
"""

from story_engine.adapters.outbound.openai_llm import OpenAILLM
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.config.settings import Settings
from story_engine.ports.llm import LLMPort
from story_engine.resources.dexter_demo_script import DEMO_SCRIPT
from story_engine.shared.errors import GenerationError


def build_llm(settings: Settings) -> LLMPort:
    """Return the `LLMPort` named by `settings.llm_provider`.

    Args:
        settings: The process-wide settings singleton.

    Returns:
        An `OpenAILLM` for `"openai"`, or a `ScriptedLLM` preloaded with the rehearsed demo script
        for `"scripted"` — the offline stage fallback.

    Raises:
        GenerationError: `llm_provider` is `"openai"` but `openai_api_key` is unset. Raised at
            construction, before any request, so a misconfigured process fails at boot rather than
            mid-demo.
    """
    if settings.llm_provider == "scripted":
        return ScriptedLLM(DEMO_SCRIPT)

    if settings.openai_api_key is None:
        raise GenerationError(
            "llm_provider is 'openai' but OPENAI_API_KEY is not set",
            context={"llm_provider": settings.llm_provider},
        )
    return OpenAILLM(
        api_key=settings.openai_api_key, budget_usd=settings.request_budget_usd
    )

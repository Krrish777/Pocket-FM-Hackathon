"""Stub LLM adapter — placeholder implementing `LLMPort`.

Keeps the scaffold importable/runnable. Calling `generate` fails LOUD (no silent fallback) until a
real provider adapter (anthropic/openai) is wired. Replace with a client wrapper that logs
tokens/cost and sets max_tokens. See .claude/rules/llm-storytelling.md.
"""

from story_engine.ports.llm import Generation


class StubLLM:
    """A non-functional LLM adapter that raises until a real one is implemented."""

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> Generation:
        raise NotImplementedError(
            "StubLLM: wire a real LLM adapter (anthropic/openai) that logs tokens/cost. "
            "See .claude/rules/llm-storytelling.md."
        )

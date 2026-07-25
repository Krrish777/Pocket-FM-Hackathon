"""The LLM port — the ONE seam every model call goes through.

Domain/services depend on `LLMPort`, never on a vendor SDK. The concrete adapter (in
`adapters/outbound/`) logs tokens + cost, sets `max_tokens`, and handles retries/idempotency.
See .claude/rules/llm-storytelling.md.
"""

from typing import Protocol

from story_engine.domain.base import DomainModel


class Generation(DomainModel):
    """The result of one LLM call, with the accounting needed for cost governance."""

    output: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class LLMPort(Protocol):
    """A minimal, vendor-agnostic text-generation interface."""

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        idempotency_key: str | None = None,
    ) -> Generation:
        """Generate a completion. Implementations MUST set max_tokens and log tokens/cost."""
        ...

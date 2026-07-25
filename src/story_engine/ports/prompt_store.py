"""Prompt store port — loads versioned prompt templates as assets.

Prompts are versioned files in `prompts/` (`name/vN.jinja`), never string literals in code. The
adapter renders a named/versioned template with variables. See
.claude/rules/llm-storytelling.md.
"""

from typing import Protocol


class PromptStorePort(Protocol):
    """Render a versioned prompt template to a string."""

    def render(self, name: str, *, version: str, variables: dict[str, object]) -> str:
        """Return the rendered template `name` at `version`, or raise `PromptError`."""
        ...

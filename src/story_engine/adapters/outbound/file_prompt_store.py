"""File-backed prompt store implementing `PromptStorePort`.

Loads versioned Jinja templates from the prompts directory (`<name>/<version>.jinja`). StrictUndefined
so a missing variable fails loud rather than rendering blank. No autoescape (prose, not HTML).
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from story_engine.shared.errors import PromptError


class FilePromptStore:
    """Render `<name>/<version>.jinja` templates from a prompts root directory."""

    def __init__(self, root: Path | str = "prompts") -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(root)),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )

    def render(self, name: str, *, version: str, variables: dict[str, object]) -> str:
        try:
            template = self._env.get_template(f"{name}/{version}.jinja")
            return template.render(**variables)
        except TemplateError as exc:
            raise PromptError(
                f"failed to render prompt {name!r} {version!r}", context={"name": name}
            ) from exc

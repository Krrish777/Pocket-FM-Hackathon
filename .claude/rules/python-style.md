---
paths:
  - "**/*.py"
---

# Python Style, Naming & Docstrings

Formatting is the formatter's job — `ruff format` (Black-compatible) owns layout, line length, and quotes.
Never argue whitespace; run the tool. This rule covers what tools *don't* decide.

## Layout (formatter-enforced — reference only)
- 4 spaces, never tabs. Line length **88** (`E501` ignored; the formatter wraps).
- 2 blank lines between top-level defs/classes; 1 between methods. Double quotes.

## Imports (ruff `I` sorts automatically)
- Grouped stdlib → third-party → first-party, blank-line separated; one per line.
- **No wildcard imports** (`from x import *`). Prefer absolute imports
  (`from story_engine.domain import models`); no cross-package relative imports.

## Naming
| Kind | Convention | Example |
|---|---|---|
| Module / package | `short_lowercase` | `episode_generator` |
| Class | `CapWords` | `EpisodeGenerator` |
| Function / variable | `lower_with_under` | `generate_next_episode` |
| Constant | `ALL_CAPS` | `MAX_OUTPUT_TOKENS` |
| Internal | `_leading_underscore` | `_render_prompt` |

- Descriptive names, no cryptic abbreviations. Single-char names only for counters (`i`), exceptions
  (`e`), file handles (`f`). First arg: `self` (instance methods), `cls` (class methods).

## Readability (PEP 20)
- Explicit over implicit; one obvious way. Comprehensions are fine but **no multiple `for`/filter
  clauses** — if it needs two, write a loop.
- `if __name__ == "__main__":` + a `main()` for any runnable module.

## Type hints
- **Type-hint every public function signature** and every dataclass/model field.
- **Modern syntax only** (ruff `UP` autofixes old forms): `list[str]`, `dict[str, int]`,
  `tuple[int, ...]` — never `typing.List/Dict/Tuple`. `X | None` — never `Optional[X]`. `X | Y` — never `Union`.
- Never `def f(x: int = None)` — write `x: int | None = None`.
- `typing.Protocol` for structural interfaces; `TypedDict`/Pydantic for structured payloads.
- **Generics: PEP 695 native syntax** (3.12+): `def first[T](xs: list[T]) -> T:`,
  `class Repo[T](Protocol): ...`, `type Alias = X | Y` — not module-level `TypeVar`. Ruff flags legacy (`UP046`/`UP047`).
- **`typing.Self`** (3.11+) for a method returning its own class.
- **mypy `strict = true`** (configured in `pyproject.toml`). `--strict` already bundles
  `disallow_untyped_defs`, `check_untyped_defs`, `warn_return_any` — don't re-list them. Keep
  `no_implicit_optional = true` explicit (not in the strict bundle). Relax untyped third-party libs
  per-module via `[[tool.mypy.overrides]]`, never globally.
- **`from __future__ import annotations`:** this repo omits it (3.12 + Pydantic reads annotations at
  runtime) unless a concrete need arises. Decide once, repo-wide.

## Docstrings — Google style
- Triple double quotes `"""..."""` on every **public** module, class, function.
- One-liners: imperative, ending in a period, closing quotes on the same line ("Return the next
  episode.", not "Returns..."). Don't restate the signature.
- Multi-line: summary, blank line, body. Sections: `Args:`, `Returns:`/`Yields:`, `Raises:`.
- Private helpers (`_name`) need only a one-line comment when the name isn't self-explanatory.
- Comments explain **why**, not **what**. Delete commented-out code (git remembers). Keep docstrings
  in sync with signatures — a stale docstring is worse than none.

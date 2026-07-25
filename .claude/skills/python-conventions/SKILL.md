---
name: python-conventions
description: Use when writing or editing Python in THIS project — modules, classes, type hints, OOP design, error handling, tests, or any LLM/storytelling code. Points to the project's researched conventions, now delivered as path-scoped rules in `.claude/rules/` (auto-loaded when you edit matching files). Invoke for an on-demand deep-dive or the inline non-negotiables before authoring Python.
---

# Python Conventions (this project)

The full rules live in **`.claude/rules/`** and **auto-load by file type** (`paths:` frontmatter), so
editing a `.py` file already injects them. This skill is the on-demand deep-dive + inline
non-negotiables.

## Where each rule lives
- style / naming / typing / docstrings → `.claude/rules/python-style.md`
- OOP design / errors / logging → `.claude/rules/python-design.md`
- SQLModel/SQLite persistence → `.claude/rules/persistence.md`
- repo layout / hexagonal architecture / tooling → `.claude/rules/structure.md` (always-on)
- prompts / cost / reproducibility / LLM boundaries → `.claude/rules/llm-storytelling.md`
- prompt authoring (Opus 4.8) → `.claude/rules/prompts.md`
- testing (pytest + DeepEval, two tiers) → `.claude/rules/testing.md`

## Non-negotiables (carry these even if you don't open the rules)
1. Type-hint every public signature — modern syntax (`list[str]`, `X | None`), never `Optional`/`List`.
2. No bare `except:` and no silent `except: pass` — catch specific, fail loud.
3. No hardcoded secrets — `pydantic-settings` + gitignored `.env`; `SecretStr` for keys.
4. Prompts are versioned assets in `prompts/` — never string literals in domain logic.
5. All LLM calls go through ONE client wrapper — log tokens + cost, always set `max_tokens`.
6. Tests assert schema/invariants (Pydantic), never exact generated text; mock the LLM in unit tests.
7. `src/` layout; hexagonal — vendor SDKs only in `adapters/outbound/`, never in `domain/`/`services/`.
8. Google-style docstrings; run `ruff check` + `ruff format` + `mypy` + `pytest` before calling it done.

## Tooling
uv (env/deps, commit `uv.lock`) · Ruff (lint + import sort + `ruff format`) · mypy (strict-ish) ·
pytest · pre-commit. Config is in `pyproject.toml` — see `.claude/rules/structure.md`.

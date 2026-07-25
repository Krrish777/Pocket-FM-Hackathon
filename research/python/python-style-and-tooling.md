# Research: Python Code-Style Conventions & Tooling (2025)

> **Provenance:** Web research conducted by a `general-purpose` sub-agent for the Pocket FM
> hackathon conventions system. This is the raw, cited research artifact — the distilled rules
> live in `.claude/rules/python/`. Preserved so future edits can trace every rule to a source.
> Tool version numbers below are illustrative; **pin to the current release at adoption time.**

---

## 1. PEP Style Standards

### PEP 8 — Style Guide for Python Code (https://peps.python.org/pep-0008/)
- **Indentation:** 4 spaces per level. Never tabs in new code.
- **Line length:** PEP 8 says 79 (72 for docstrings/comments), team may raise code to 99. Modern
  formatters override this — see §3 (88 is the de-facto standard).
- **Blank lines:** 2 between top-level defs/classes; 1 between methods; sparingly inside functions.
- **Imports:** one per line; grouped stdlib → third-party → local, blank-line separated.
- **Whitespace:** no space inside brackets; no space before `,;:`; single spaces around binary
  operators; no spaces around `=` for kwargs/unannotated defaults, but DO for annotated defaults
  (`x: int = 0`).
- **Naming:** modules `short_lowercase`, classes `CapWords`, funcs/vars `lower_with_under`,
  constants `ALL_CAPS`, `self`/`cls` first arg, `_single_leading` = internal, `__double` = mangling.
- **"Know when to be inconsistent":** ignore a rule when it hurts readability or breaks
  back-compat. *"Do not break backwards compatibility just to comply with this PEP."*

### PEP 257 — Docstring Conventions (https://peps.python.org/pep-0257/)
- Always `"""triple double quotes"""`; `r"""..."""` if backslashes.
- One-liners: imperative phrase ending in a period, closing quotes same line, no surrounding blanks.
- Multi-line: summary line, blank line, body, closing `"""` on its own line; blank line after a
  class docstring.

### PEP 20 — Zen of Python (https://peps.python.org/pep-0020/)
Philosophy, not enforceable rules. "Explicit is better than implicit", "Readability counts",
"There should be one obvious way to do it". `import this`.

### Type-hint PEPs
- **PEP 484** (https://peps.python.org/pep-0484/): foundational typing spec.
- **PEP 585** (https://peps.python.org/pep-0585/): builtin generics `list[str]`, `dict[str, int]`
  (3.9+); `typing.List/Dict/...` deprecated — treat as banned in new code.
- **PEP 604** (https://peps.python.org/pep-0604/): `X | Y`, `X | None` (native 3.10+), replaces
  `Union`/`Optional`.

**Enforced nuances:** prefer `X | None` and `list[str]` (ruff `UP` autofixes). `from __future__
import annotations` (PEP 563): makes annotations strings — **⚠ breaks runtime-annotation libs
(Pydantic v1, some dataclass/FastAPI uses)**. For 3.10+ with runtime-annotation libs you often
don't need it. Decide one policy repo-wide.

---

## 2. Google Python Style Guide (https://google.github.io/styleguide/pyguide.html)
Rules **beyond PEP 8**:
- **Imports:** import modules/packages only, never individual classes/functions (exception:
  typing/`collections.abc`). Full package paths; **no relative imports**.
- **Line length: 80** (⚠ conflicts with PEP 8's 79 and Black's 88).
- **Docstrings:** Google sections — `Args:`, `Returns:`/`Yields:`, `Raises:`.
- **Types:** explicit `X | None`, never `a: str = None`.
- **Exceptions:** use builtins; never bare `except:` or catch `Exception` unless re-raising; don't
  `assert` for precondition/app-logic validation.
- **Mutable default args: forbidden** — use `None` sentinel.
- **Properties:** only for real computation, not trivial passthrough.
- **f-strings** allowed — **except logging**, which must use `%`-style (`logger.info("x=%s", x)`).
- **Comprehensions:** no multiple `for`/filter clauses.
- **`main()` + `if __name__ == '__main__':`** for executables.

---

## 3. Modern 2025 Tooling

### Ruff (https://docs.astral.sh/ruff/)
- Single Rust binary subsuming **Flake8, isort, pydocstyle, pyupgrade, and Black** — the defining
  2024–2025 shift.
- Rule namespaces: `F` Pyflakes, `E`/`W` pycodestyle, `I` isort, `UP` pyupgrade, `B` bugbear,
  `C4` comprehensions, `SIM` simplify, `TID`/`PTH`/`RET` etc.
- `ruff format` = drop-in Black replacement (>99.9% identical), default line length 88. It DOES
  format inside f-strings (Black doesn't).

### Black (https://github.com/psf/black)
- Default 88, deterministic. **Use `ruff format` for new projects** (one tool, faster); keep Black
  only if already standardized. Never run both.

### mypy (https://mypy.readthedocs.io/en/stable/config_file.html)
- `strict = true` bundles disallow_untyped_defs, check_untyped_defs, disallow_incomplete_defs,
  warn_return_any, no_implicit_optional, warn_unused_configs, strict_equality, etc.
- Most-important flags: `disallow_untyped_defs`, `warn_return_any`, `no_implicit_optional`
  (default True in mypy ≥0.990), `check_untyped_defs`.
- Migration: legacy code → enable incrementally + `[[tool.mypy.overrides]]` per module. New repos:
  strict from day one.

### pytest (https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- `src/` layout, `tests/` sibling. Config in `[tool.pytest.ini_options]`.
- `--strict-markers`; register markers. Naming `test_*.py` / `test_*` / `Test*`.
- Shared fixtures in `conftest.py` (auto-discovered, never import it). Arrange-Act-Assert. Avoid
  overusing `autouse`. Plugins: pytest-cov, pytest-xdist, pytest-mock.

### uv (https://docs.astral.sh/uv/)
- Rust tool (Astral) replacing pip/pip-tools/pyenv/virtualenv/most of Poetry; 10–100× faster; 2025
  default.
- `uv add` → `[project.dependencies]` + `uv.lock`; `uv sync` installs; `uv run` executes.
- **Commit `uv.lock`.** CI: `uv sync --frozen` (stale lockfile fails build). Never hand-edit.

### pre-commit (https://github.com/astral-sh/ruff-pre-commit)
- **Order matters:** `ruff check --fix` BEFORE `ruff-format`. mypy hook needs type stubs in
  `additional_dependencies`. Add hygiene hooks (trailing-whitespace, end-of-file-fixer, etc.).

---

## 4. Notable 2024–2025 shifts
- Ruff subsumes Flake8+isort+pyupgrade+pydocstyle+Black → 4–5 tools collapse to `ruff check` +
  `ruff format`.
- uv (Feb 2024) consolidates env/dependency management.
- `X | None` / `list[str]` are the modern default; `typing.List`/`Optional`/`Union` legacy.
- Line-length consensus moved 79/80 → **88**.

---

## Recommended `pyproject.toml`

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "C4", "SIM", "TID", "PTH", "RET"]
ignore = ["E501"]  # line length handled by the formatter

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401", "E402"]
"tests/**/*" = ["S101"]

[tool.ruff.lint.isort]
known-first-party = ["your_package"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
no_implicit_optional = true
disallow_untyped_defs = true
check_untyped_defs = true
show_error_codes = true

[[tool.mypy.overrides]]
module = ["some_untyped_lib.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
python_classes = ["Test*"]
markers = [
    "slow: marks tests as slow",
    "integration: integration tests",
]
```

`.pre-commit-config.yaml` (pin `rev` to current release before adopting):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.22  # verify latest
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.19.1  # verify latest
    hooks:
      - id: mypy
        additional_dependencies: []
```

---

## Conflicts flagged
1. **Line length:** PEP 8 = 79, Google = 80, Black/ruff = 88 → standardize on **88**, ignore `E501`.
2. **Black vs ruff format:** near-identical → choose one (ruff format for new work).
3. **`from __future__ import annotations`:** helps perf/forward-refs, breaks runtime-annotation
   consumers → decide per project.
4. **uv for libraries:** clear win for apps; some keep Poetry for publishing maturity.

## Sources
- https://peps.python.org/pep-0008/ — style, naming, imports, whitespace.
- https://peps.python.org/pep-0257/ — docstrings.
- https://peps.python.org/pep-0020/ — Zen.
- https://peps.python.org/pep-0484/ , /pep-0585/ , /pep-0604/ — typing.
- https://google.github.io/styleguide/pyguide.html — Google rules beyond PEP 8.
- https://docs.astral.sh/ruff/configuration/ , /formatter/ , /linter/ — Ruff config/format/rules.
- https://mypy.readthedocs.io/en/stable/config_file.html — mypy strict flags.
- https://docs.pytest.org/en/stable/explanation/goodpractices.html — pytest layout/fixtures.
- https://docs.astral.sh/uv/guides/projects/ — uv workflow, lockfile, `--frozen`.
- https://github.com/astral-sh/ruff-pre-commit — pre-commit hook ids/ordering.
- https://github.com/psf/black — Black 88 default.

---

## 2026-07-24 currency refresh (session 3 — REVIEW-03)
Convention docs re-verified against current authoritative sources; changes applied to `.claude/rules/python/`:
- **mypy `--strict` already bundles** `disallow_untyped_defs` / `check_untyped_defs` / `warn_return_any` — stop re-listing them; keep only `no_implicit_optional` explicit. https://mypy.readthedocs.io/en/stable/command_line.html
- **PEP 695 native generics** (`def f[T]`, `type X = ...`, `class C[T]`) are the 3.12 idiom; Ruff flags the old form (`UP046`/`UP047`). https://docs.python.org/3/whatsnew/3.12.html · https://docs.astral.sh/ruff/rules/non-pep695-generic-function/
- **Ruff**: add `RUF`; defaults expanded substantially in v0.16.0. https://astral.sh/blog/ruff-v0.16.0 · https://docs.astral.sh/ruff/formatter/
- **pytest 9** removed nose-style setup/teardown + yield tests (now errors); bump `minversion`. https://docs.pytest.org/en/stable/deprecations.html
- **Black demoted** to "`ruff format` (Black-compatible)" — not run as a separate tool.

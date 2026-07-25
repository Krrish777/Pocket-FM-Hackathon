# mypy — Story Engine reference note

> Strict static type checker; the `mypy src` gate in `make check` is what makes "type-hint everything"
> enforceable rather than aspirational.

- **Version pin (ours):** `mypy>=1.11`
- **Latest stable (verified):** 2.3.0 (released 2026-07-13; checked 2026-07). Note: mypy has moved to a **2.x line**; dropped Python 3.9 as a runtime (still type-checks 3.9 targets via `--python-version`).
- **Upstream `llms.txt`:** none — `mypy.readthedocs.io/.../llms.txt` is 404. Use the docs site.
- **Docs home:** https://mypy.readthedocs.io/en/stable/

## How Story Engine uses it
- Invoked as `mypy src` inside `make check`; a clean run is part of the definition of done.
- Config in `[tool.mypy]` of the single root `pyproject.toml`: `strict = true` and `no_implicit_optional = true` (the latter kept explicit because it is **not** in the `strict` bundle).
- Modern typing only — `list[str]`, `X | None`, PEP 695 generics (`def f[T]`, `class C[T]`) on Python 3.12; no `Optional`/`List`.
- `typing.Protocol` for ports (structural interfaces the pure domain consumes) — checked structurally, no explicit subclassing.
- Untyped third-party libs relaxed per-module via `[[tool.mypy.overrides]]` (e.g. `ignore_missing_imports`), scoped to named modules — never globally.

## Read this for… (task → doc link)
- Configure `[tool.mypy]` in `pyproject.toml` → https://mypy.readthedocs.io/en/stable/config_file.html
- What `strict = true` turns on (the flag list can shift between releases) → https://mypy.readthedocs.io/en/stable/config_file.html#confval-strict
- Relax an untyped dependency per-module with `[[tool.mypy.overrides]]` → https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
- Define/consume ports as `typing.Protocol` (structural subtyping) → https://mypy.readthedocs.io/en/stable/protocols.html
- PEP 695 generic syntax → https://mypy.readthedocs.io/en/stable/generics.html
- Diagnose recurring errors and `# type: ignore[code]` usage → https://mypy.readthedocs.io/en/stable/common_issues.html

## Gotchas that bite us
- **`no_implicit_optional` is NOT in the `strict` bundle** — we set it explicitly; without it, an implicit-Optional default would slip through even under `strict = true`.
- **Keep per-module relaxations scoped** in `[[tool.mypy.overrides]]` (one block per module pattern) — a project-wide `ignore_missing_imports` would blind the whole gate.
- **Pydantic `@computed_field @property` needs `# type: ignore[prop-decorator]`** — a known mypy/Pydantic-plugin friction (present in our `settings.py`).
- **SQLModel/SQLAlchemy column attributes type-check awkwardly** (descriptor / `Mapped[...]` vs instance-value) — annotate/narrow at the boundary (`col()`) rather than fight the ORM's declarative attributes.

_Sources: mypy.readthedocs.io, github.com/python/mypy releases. Verified 2026-07-24 (base pages fetch-verified; exact anchor spellings high-confidence)._

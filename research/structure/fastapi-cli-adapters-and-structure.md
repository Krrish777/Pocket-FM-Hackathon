# Research: FastAPI + CLI Inbound Adapters, Resources/Bootstrap, Root Hygiene

> **Provenance:** Web research by a `general-purpose` sub-agent. Distilled into the `api/`, `cli/`,
> `resources/`, and `bootstrap.py` scaffold under `src/story_engine/`.

## 1. FastAPI as an INBOUND (driving) adapter
- HTTP is a driving adapter: parse HTTP → build request DTO → call an **application service** (input port) →
  map result/exception back to HTTP. Routers hold **no** domain logic; domain models are **never** serialized
  directly (use DTOs).
- **App factory** `create_app()` (testable, fresh wiring); per-feature `APIRouter` in `api/routers/`;
  request/response DTOs in `api/schemas.py`; DI via `Depends` that resolves services from the container on
  `app.state`; central exception handlers (domain code raises pure exceptions, never `HTTPException`).
- **Composition root** = `api/app.py` calls `bootstrap.build_container()`.

**Placement:** `api/app.py` (`create_app()`+`app`), `api/routers/*.py`, `api/schemas.py`,
`api/dependencies.py`, `api/errors.py` (`register_exception_handlers`).

## 2. CLI as an INBOUND adapter — **use Typer**
- **Typer** over Click/argparse: type-hint-native (matches the repo's "type-hint every signature" constraint),
  built on Click (mature parsing, completion), free `--help`/completion. Argparse only for zero-dep stdlib tools.
- CLI stays thin: parse args → `build_container()` → call the **same** services the API uses.
- Entry point via `[project.scripts] story-engine = "story_engine.cli.main:main"` (needs a build system; `src/`
  layout already provides it). After install: `story-engine ...` and `uv run story-engine ...`.

**Placement:** `cli/main.py` (`app = typer.Typer()`, commands, `main()` wrapper).

## 3. The "things that get loaded" folder(s) — keep TWO concerns separate
- **(a) Non-code runtime assets → `src/story_engine/resources/`** (a subpackage, INSIDE the package so it's
  packaged). Read via `importlib.resources.files("story_engine.resources...")` — **not** `open()`+`__file__`
  (breaks in zip/wheel installs). Holds style guides, lore, seed data, JSON schemas. The versioned `prompts/`
  are the same category (keep at repo root behind a config path, or move under `resources/prompts/`).
- **(b) Composition root / DI wiring → `bootstrap.py`** (Cosmic Python's name; alt: `container.py`,
  `dependencies.py`). The **one** module that imports `adapters/outbound/*`, instantiates concrete adapters,
  and injects them into services. Both `api/app.py` and `cli/main.py` call `build_container()`.
- **(c) Startup plugins** — only if external extensibility is needed: `[project.entry-points]` groups
  (`importlib.metadata.entry_points`), as pytest/flake8 do. Otherwise a simple in-repo `plugins/` iterated by
  bootstrap. Don't build the plugin system for a hackathon.

**Placement:** `src/story_engine/resources/{style_guides,lore,schemas}/`, `src/story_engine/bootstrap.py`,
`src/story_engine/config/settings.py` (pydantic-settings).

## 4. Root-folder hygiene (uv + `src/` layout)
- **Remove root `main.py`** — it's a bare `uv init` leftover (no build system, "not installed"). Real entry
  points live in the package: CLI `story_engine.cli.main:main`, ASGI `story_engine.api.app:app`.
- `src/` layout forces importing the **installed** package (catches packaging bugs).
- **Keep at root:** `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, `LICENSE`, `.gitignore`,
  `.env.example`, `Makefile`, `.pre-commit-config.yaml`, `src/`, `tests/`, harness state files.
- **Avoid at root:** `main.py`, `requirements.txt`, `setup.py`/`setup.cfg`, app code files.

## Sources
- https://fastapi.tiangolo.com/tutorial/bigger-applications/ — APIRouter + routers/ + dependencies.py + include_router.
- https://fastapi.tiangolo.com/tutorial/handling-errors/ — exception handlers.
- https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/ — driving/driven adapters, pure domain, edge wiring.
- https://typer.tiangolo.com/ — type-hint CLI; Typer vendors Click.
- https://docs.astral.sh/uv/concepts/projects/init/ , /config/ — bare app root main.py vs --package src/ layout; [project.scripts].
- https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ — why src/ layout.
- https://docs.python.org/3/library/importlib.resources.html , https://www.bowmanjd.com/python-importlib-resources/ — packaged assets via files(), not __file__.
- https://www.cosmicpython.com/book/chapter_13_dependency_injection.html , /appendix_project_structure.html — bootstrap.py composition root; reference layout.
- https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/ — Typer for modern CLIs.

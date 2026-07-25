# Typer — Story Engine reference note

> Click-based, type-hint-driven CLI framework backing Story Engine's thin `cli/main.py` inbound adapter.

- **Version pin (ours):** `typer>=0.12`
- **Latest stable (verified):** 0.27.0 (released 2026-07-15; checked 2026-07).
- **Upstream `llms.txt`:** none — `typer.tiangolo.com/llms.txt` is 404 (tiangolo/FastAPI family ships none). Use the docs site.
- **Docs home:** https://typer.tiangolo.com/

## How Story Engine uses it
- `cli/main.py` is a thin Typer app acting as an inbound/delivery adapter — no business logic, no adapter instantiation.
- Commands obtain application services from `bootstrap.build_container()` and delegate; the CLI only parses args/options and renders output.
- Exposed as a console script `story-engine = "story_engine.cli.main:main"` under `[project.scripts]`, so install puts a `story-engine` entrypoint on PATH.

## Read this for… (task → doc link)
- Define subcommands (multi-command app) → https://typer.tiangolo.com/tutorial/commands/
- Declare positional CLI arguments → https://typer.tiangolo.com/tutorial/arguments/
- Declare flags/options (defaults, required, prompts, env vars) → https://typer.tiangolo.com/tutorial/options/
- Unit-test commands with `CliRunner` → https://typer.tiangolo.com/tutorial/testing/
- Package as a console script / installable entrypoint → https://typer.tiangolo.com/tutorial/package/

## Gotchas that bite us
- Keep the CLI thin: commands call `build_container()` services and return — pushing orchestration or adapter wiring into `cli/main.py` violates the hexagon (delivery layer only).
- Test via `from typer.testing import CliRunner`, invoke the app object, assert on exit code + structured output — not exact generated story text; mock the LLM-backed services.
- No upstream `llms.txt` (404, tiangolo family) — this note points at the human docs, not a mirror.
- Because `src/` layout tests the installed package, run `uv sync`/`make setup` before the `story-engine` command resolves; the entrypoint must reference a real callable named `main`.

_Sources: pypi.org/project/typer, typer.tiangolo.com, official release notes. Verified 2026-07-24 (0.27.0 confirmed via project page + release notes; a PyPI JSON mirror briefly reported a stale 0.23.1)._

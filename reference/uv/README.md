# uv — Story Engine reference note

> Astral's all-in-one Python package/project manager: env, dependency resolution, and lockfile in one fast tool.

- **Version pin (ours):** managed externally (not a project dep) — standalone tool, invoked via `make setup`/CI.
- **Latest stable (verified):** 0.11.32 (released 2026-07-23; checked 2026-07).
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`. No `llms-full.txt` (404 upstream).
- **Docs home:** https://docs.astral.sh/uv/

## How Story Engine uses it
- `make setup` runs `uv sync` — creates the venv and installs project + dev tooling in one step.
- Dev tooling lives in a PEP 735 `[dependency-groups]` table (the `dev` group), **not** extras. uv installs the `dev` group by default on `uv sync`/`uv run`, so no flag is needed to get ruff/mypy/pytest.
- `uv.lock` committed for reproducible installs; CI runs `uv sync --frozen` (installs exactly the lock, no re-resolve).
- Console entrypoint under `[project.scripts]`; run in-env with `uv run`. Add deps with `uv add` (updates `pyproject.toml` + `uv.lock` together).

## Read this for… (task → doc link)
- Set up / structure a project → https://docs.astral.sh/uv/concepts/projects/config/
- Manage deps & PEP 735 dependency groups (`dev` group, `default-groups`, `--dev`/`--no-dev`) → https://docs.astral.sh/uv/concepts/projects/dependencies/
- Lock & sync, including `--frozen` for CI → https://docs.astral.sh/uv/concepts/projects/sync/
- Run commands in the project env (`uv run`) & the run/add workflow → https://docs.astral.sh/uv/concepts/projects/run/
- Single-file scripts (inline deps) → https://docs.astral.sh/uv/guides/scripts/
- Multi-package workspaces → https://docs.astral.sh/uv/concepts/projects/workspaces/

## Gotchas that bite us
- **Dependency groups ≠ extras.** `[dependency-groups]` (PEP 735) is dev-only tooling, not installable extras under `[project.optional-dependencies]`. Put ruff/mypy/pytest in the `dev` group.
- **Commit `uv.lock`.** It's the reproducibility contract — CI's `--frozen` fails if it's missing or out of sync with `pyproject.toml`.
- **`--frozen` never re-resolves.** In CI it installs exactly the lock and errors on drift instead of silently updating — regenerate locally (`uv lock`/`uv add`) and commit, or CI breaks.
- **`dev` group auto-installs.** Use `--no-dev`/`--no-default-groups` for a lean production install, or you'll ship dev tooling.

_Sources: docs.astral.sh/uv, github.com/astral-sh/uv releases. Verified 2026-07-24._

# pytest (+ pytest-cov, httpx) — Story Engine reference note

> The code-correctness test tier: pytest runs the unit/integration/e2e suites, pytest-cov measures
> coverage, and httpx backs the FastAPI TestClient for e2e. (LLM output *quality* lives in a separate
> DeepEval tier — see `.claude/rules/testing.md`.)

- **Version pin (ours):** `pytest>=8`, `pytest-cov>=5`, `httpx>=0.27`
- **Latest stable (verified):** pytest 9.1.1 (2026-06-19), pytest-cov 7.1.0 (2026-03-21), httpx 0.28.1 (2024-12-06) — checked 2026-07. Note: httpx **1.0 is still pre-release**; don't pin it as stable.
- **Upstream `llms.txt`:** none — `docs.pytest.org/llms.txt` is 404. Use the docs sites.
- **Docs home:** pytest → https://docs.pytest.org/en/stable/ · pytest-cov → https://pytest-cov.readthedocs.io/en/latest/ · httpx → https://www.python-httpx.org/

## How Story Engine uses it
- Runs with `--strict-markers` so any unregistered marker is an error, not a silent typo.
- Suite split `tests/unit | integration | e2e` mirroring `src/story_engine/`; because it's a src layout, the package must be installed (`uv sync` / `make setup`) before pytest can import it.
- Unit tests **mock the LLM** (via `monkeypatch` / fixtures) and assert Pydantic schema + invariants — never exact generated text.
- Integration tests hit real SQLite; e2e boots the FastAPI app through the TestClient (which runs on httpx).
- pytest-cov reports coverage (`--cov`). This is the code-correctness tier only.

## Read this for… (task → doc link)
- Src layout / where tests go → https://docs.pytest.org/en/stable/explanation/goodpractices.html
- Writing & scoping fixtures (mock the LLM, DB setup) → https://docs.pytest.org/en/stable/how-to/fixtures.html
- Markers & `--strict-markers` → https://docs.pytest.org/en/stable/how-to/mark.html
- Parametrizing test cases → https://docs.pytest.org/en/stable/how-to/parametrize.html
- Monkeypatch / mocking modules & env → https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- Coverage config (`--cov`, `--cov-report`, `--cov-fail-under`, `--cov-branch`) → https://pytest-cov.readthedocs.io/en/latest/config.html

## Gotchas that bite us
- **Src layout = install first.** pytest can't import `story_engine` until the package is installed; skip `uv sync`/`make setup` and you get "works locally, fails in CI" import errors.
- **`--strict-markers` fails on unregistered markers** — register every custom marker in `pyproject.toml`.
- **Mock the LLM in unit tests** — no live API calls; patch via fixtures/`monkeypatch` so unit tests stay deterministic and free.
- **Never assert exact LLM text** — assert Pydantic schema/invariants; generated prose varies run to run and exact-string asserts are flaky by construction.

_Sources: docs.pytest.org, pytest-cov.readthedocs.io, python-httpx.org. Verified 2026-07-24._

# Tests — the Validation Hierarchy (Definition of Done)

> **Done = end-to-end verification passed, not "code is written." Confidence is not evidence.**
> Sourced from `Harness-Engineering/Harness-Engineering-Preventing-Premature-Victory.md` and
> `...-Beyond-Unit-Tests-E2E.md`. This is *how we verify an implementation is actually implemented.*

Three layers. **A layer must pass before the next is trusted** — don't advance on a red layer, and
never self-grade ("it looks right") in place of a command that exits zero.

| Layer | Proves | Command | Lives in |
|---|---|---|---|
| **L1 — Syntax & Static** | It's spelled right; types hold | `make lint` + `make fmt-check` + `make typecheck` | `ruff`, `mypy` |
| **L2 — Runtime Behavior** | It runs; critical paths + **side effects (DB writes)** are correct | `make test` | `tests/unit/` (mocked), `tests/integration/` (real SQLite in `tmp_path`) |
| **L3 — System-Level / E2E** | Wired together, it boots and is correct | `make test` | `tests/e2e/` (app boots via `TestClient`, schema initializes) |

`make check` runs **all three** in order (L1 → L2 → L3) and is THE gate. `pytest` discovers everything
under `tests/`, so one `make test` runs unit + integration + e2e.

## Layout & markers
- `tests/unit/` — fast, mocked, mirrors the package. No real IO.
- `tests/integration/` — `@pytest.mark.integration`. Real adapter against a real (temp) resource.
- `tests/e2e/` — `@pytest.mark.e2e`. The whole app, exercised as a system.

Run a single layer: `uv run pytest -m integration` · `uv run pytest -m e2e` · `uv run pytest tests/unit`.

## Rules (from the harness docs)
1. **Assert schema/invariants, never exact generated text.** Mock the LLM in unit tests.
2. **Cross-component changes require an L3 check** (e.g. the SQLite persistence adapter → the app-boot + schema E2E).
3. **No "refactor while we're at it"** before the core path is verified — refactoring moves the verified/unverified boundary.
4. Capture runtime signals: does the app reach a ready state? are DB writes correct? are temp resources cleaned up?

## Known E2E gap (tracked, not hidden)
A full `premise -> episode -> persist` request path is **not yet** E2E-testable: the LLM adapter is
deferred to the event brief and `StubLLM` raises by design. Today's E2E proves boot + schema init.
Closing that gap (a deterministic offline LLM + a persistence-backed route) is a next-session task.

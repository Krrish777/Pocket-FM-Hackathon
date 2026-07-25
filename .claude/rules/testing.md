---
paths:
  - "tests/**"
  - "evals/**"
---

# Testing — Two Tiers

Two **separate** testing conventions, because an LLM product can pass code tests yet still produce bad
stories:
1. **pytest — code correctness.** Deterministic; mocks the LLM. (Full hierarchy in `tests/README.md`.)
2. **DeepEval — LLM/agent output quality.** Runs the real model; scored against metrics. Lives in `evals/`.

A green `make check` is **not** a passing eval — the two answer different questions.

## Tier 1 — pytest (code correctness)
### Layout
- `tests/` lives **outside** the package and **mirrors** it (`.../services/episode_generator.py` →
  `tests/unit/services/test_episode_generator.py`).
- Files `test_*.py`, functions `test_*`. Arrange-Act-Assert. Shared fixtures in `conftest.py` (never
  `import conftest`). `--import-mode=importlib`, `--strict-markers`; register markers in `pyproject.toml`.
- **pytest 9:** nose-style `setup`/`teardown` and `yield` tests now **error** — use fixtures + plain `assert`.

### The three sub-tiers (all three matter)
| Sub-tier | Location | LLM | In CI gate? |
|---|---|---|---|
| Unit | `tests/unit/` | **Mocked** | Yes — fast, free, deterministic |
| Integration | `tests/integration/` | Recorded cassette or real, marked | Opt-in |
| E2E | `tests/e2e/` | app boots via `TestClient` | Yes |

### The generative-code testing rule
- **Never assert exact generated text** — probabilistic, flaky, worthless.
- **Assert structure, schema, invariants:** parse output into a Pydantic model; assert domain invariants
  (episode has ≥1 scene; every referenced character exists in the bible; word count within bounds).
- **Mock the LLM client** in unit tests (inject a fake through the one wrapper).
- **Record cassettes** for integration; re-record deliberately when the contract changes.
- Coverage target: **≥80% on domain/service logic**; don't chase 100% on thin adapters.

## Tier 2 — DeepEval (LLM/agent output quality)
Authority is the `deepeval` skill (`.claude/skills/deepeval/`). Lives in `evals/` (`cases/`,
`datasets/`, `metrics/`) — **separate from `tests/`** (non-deterministic, graded, costs money → not in
the unit path).
- **Generate goldens, don't fabricate them.** Use `deepeval generate` (target **30–50**) from real
  app/docs; manual goldens are more biased.
- **Metrics live in a `metrics.py` module**, not inline in the eval file.
- **Run via `deepeval test run`** (not raw `pytest`). Single-turn `Golden` vs multi-turn
  `ConversationalGolden` — don't mix in one dataset.
- Evals are **directional signals**, not pass/fail gates.
- **BLOCKED until the brief:** real dataset creation waits on (a) the hackathon brief defining the
  engine's input→output contract and (b) a deterministic offline LLM path (today `StubLLM` raises by
  design). Until then: scaffold `metrics.py` + document the `deepeval generate` command only.

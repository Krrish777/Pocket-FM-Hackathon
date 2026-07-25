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

## Testing the Canon Kernel (tri-temporal memory storage)
**Full standard: `tests/README.md` § "Testing the Canon Kernel".** The short version, because these are
the mistakes that get made:

- **Assert every load-bearing field after a real save-and-reload.** We read Graphiti's suite: it builds
  edges carrying `valid_at`/`invalid_at`/`expired_at`, reloads them, then asserts only on `uuid` — and one
  of its search tests has no assertions at all. Both pass while the temporal semantics go unverified.
  A test that checks identity, or only that nothing raised, is a smoke test and does not count toward done.
- **Never `:memory:` for store tests.** Real file via `tmp_path`, and **close then reopen** — a store that
  only works while the process is warm passes every test that skips the reopen.
- **Nine invariants** (I-1…I-9 in `tests/README.md`): one-live-fact-per-key, atomic + append-only
  supersession, as-of correctness on a **2D grid** (story time × record time, not a line),
  projection-equals-replay, idempotent replay, no-lost-update, monotonic record time.
- **The spoiler guard is access control.** Assert **set equality** on the returned ids, never spot checks.
  Encode the asymmetry: a **leak is a hard build failure**; over-withholding is a reported metric only.
- **Property-based testing** (`Hypothesis RuleBasedStateMachine` + in-memory oracle) earns its place on the
  mutation-sequence surface only — append/supersede/query-as-of. Not for schema validation; Pydantic has it.

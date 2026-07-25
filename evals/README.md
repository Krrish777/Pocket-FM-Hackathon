# Evals — Tier 2: LLM/Agent Output Quality (DeepEval)

The **second** testing tier. Tier 1 (pytest, code correctness) lives in `tests/`; this measures whether
the *generated stories are actually good* — which a green `make check` cannot tell you. Convention:
`.claude/rules/testing.md`. Authority for the workflow: the **`deepeval` skill**
(`.claude/skills/deepeval/`).

## Layout
| Folder | Holds |
|---|---|
| `metrics/` | `metrics.py` — metric instances + thresholds (one module; eval files import from here) |
| `datasets/` | generated goldens (`.dataset.json` / `.jsonl`) — **not** hand-authored |
| `cases/` | committed pytest eval suites (`test_<app>.py`) run via `deepeval test run` |

## Status — BLOCKED until the brief
Real eval work cannot start yet, and this is deliberate:
1. **No brief.** The hackathon problem statement (drops 2026-07-25) defines the engine's input→output
   contract — without it, any golden is a guess about what we're evaluating.
2. **Nothing to run.** `StubLLM` raises by design; there is no deterministic generation path to score.
3. **The skill forbids the shortcut.** `deepeval` mandates *generated* goldens (`deepeval generate`,
   target 30–50) — **do not hand-fabricate them.**

## When the brief lands — the workflow
1. Add the dep: `uv add --group eval deepeval` (then `deepeval login` only if using Confident AI).
2. Instrument a deterministic/offline generation path (replace the raising `StubLLM`).
3. Generate goldens (don't fabricate):
   ```bash
   deepeval generate --method docs --variation single-turn --documents ./docs \
     --output-dir ./evals/datasets --file-name .dataset
   ```
4. Fill in thresholds in `metrics/metrics.py` (already scaffolded from the skill template).
5. Write a suite in `cases/` from a `deepeval` template and run it:
   ```bash
   deepeval test run evals/cases/test_story_engine.py --num-processes 5 --identifier "round-1"
   ```

Evals are **directional signals**, not a pass/fail gate — keep them out of `make check`.

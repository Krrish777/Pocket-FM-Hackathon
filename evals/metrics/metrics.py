"""DeepEval metric definitions (Tier-2 quality evals) — SCAFFOLD, not yet wired.

Prerequisite: `deepeval` is NOT yet a project dependency — add it under an eval group
(`uv add --group eval deepeval`) before running any eval. Goldens/datasets are BLOCKED until the
hackathon brief defines the engine's input->output contract AND a deterministic offline LLM path
exists (today `StubLLM` raises). See `evals/README.md` and `.claude/rules/testing.md`.

Copied from the `deepeval` skill template (`.claude/skills/deepeval/templates/metrics.py`). Reuse
existing metrics and thresholds before adding new ones. Keep metrics in this one module so eval files
stay focused on app execution.
"""

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    StepEfficiencyMetric,
    TaskCompletionMetric,
)

SINGLE_TURN_TRACE_METRICS = [
    TaskCompletionMetric(),
    StepEfficiencyMetric(),
]

SINGLE_TURN_NO_TRACING_METRICS = [
    AnswerRelevancyMetric(),
]

MULTI_TURN_METRICS: list = []

# Component-level metrics are span-specific. Do not create one shared list for the whole app.
# Name each list after the exact component/span it evaluates, then attach it with either
# next_agent_span / next_llm_span / next_tool_span / next_retriever_span, or @observe(metrics=[...]).
RETRIEVER_SPAN_METRICS = [
    ContextualRelevancyMetric(),
]

GENERATOR_LLM_SPAN_METRICS = [
    AnswerRelevancyMetric(),
]

TOOL_SPAN_METRICS: list = []

PLANNER_AGENT_SPAN_METRICS: list = []

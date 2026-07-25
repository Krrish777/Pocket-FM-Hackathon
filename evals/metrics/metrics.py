"""DeepEval metric definitions (Tier-2 quality evals).

Scoped to what this repo can actually evaluate today. There is **no generator** — the LLM adapter
is unbuilt and `StubLLM` raises — so every generator-side metric (`AnswerRelevancyMetric`,
`FaithfulnessMetric`) is deliberately absent. Adding them now would produce metrics that error on
a missing `actual_output` rather than signal.

Metric selection follows one rule from `.claude/rules/testing.md`: **pytest answers code
correctness, DeepEval answers output quality.** Anything checkable deterministically stays in
`tests/` and does not appear here. Concretely, the spoiler guard is NOT a metric on this page —
a leak is a set-equality violation and a hard build failure (`tests/integration/
test_canon_invariants.py`), not something to hand to a probabilistic judge.

⚠ **Every metric here is LLM-judged and needs credentials for an evaluation model.** With no key
configured, `deepeval test run` fails at metric construction, not with a low score.
"""

from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    GEval,
)
from deepeval.test_case import LLMTestCaseParams

RETRIEVAL_THRESHOLD = 0.5
"""Deliberately not 0.7. The current embedder is `HashingEmbedder`, a bag-of-character-n-grams
stand-in whose own docstring says it is *not* semantically meaningful. A threshold tuned for a real
embedding model would fail every case and teach us nothing about the ranking we actually have. Raise
this the moment a real embedder lands behind `EmbedderPort` — a threshold that never fails is as
useless as one that always does."""


NO_GOLDEN_METRICS = [
    # The only retriever metric needing no reference answer: it scores retrieved passages against
    # the query alone. This is the one that can run before a golden dataset exists.
    ContextualRelevancyMetric(threshold=RETRIEVAL_THRESHOLD),
]

RETRIEVER_METRICS = [
    ContextualRelevancyMetric(threshold=RETRIEVAL_THRESHOLD),
    # Both of the following require `expected_output` on the golden — they will error, not score,
    # on a dataset without it. See references/metrics.md "Reference-Based Metrics".
    ContextualPrecisionMetric(threshold=RETRIEVAL_THRESHOLD),
    ContextualRecallMetric(threshold=RETRIEVAL_THRESHOLD),
]

CANON_GROUNDING = GEval(
    name="CanonGrounding",
    criteria=(
        "Determine whether the retrieved passages actually come from the Dexter novel and could "
        "support answering the question. Passages that merely share vocabulary with the question "
        "but concern an unrelated moment in the story should score low. Judge the passages only; "
        "do not judge whether an answer was produced."
    ),
    # Only `input` and `retrieval_context` are listed because those are the only fields the test
    # cases carry. Naming `expected_output` here would fail at runtime on a golden without one.
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.RETRIEVAL_CONTEXT,
    ],
    threshold=RETRIEVAL_THRESHOLD,
)
"""The domain-specific criterion. Standard relevancy asks "is this on topic?"; this asks the thing
that actually decides whether a scene can be rendered — could these passages *support* the claim?"""

RETRIEVAL_QUALITY_METRICS = [*NO_GOLDEN_METRICS, CANON_GROUNDING]

"""Tier-2 eval: does the canon retriever surface the right passages from the Dexter novel?

Run with the DeepEval runner, never bare pytest:

    uv run deepeval test run evals/test_canon_retrieval.py --num-processes 5 \
        --identifier "canon-retrieval-round-1"

This suite lives in `evals/`, outside `testpaths = ["tests"]`, so `make check` never collects it.
That separation is the point (`.claude/rules/testing.md`): these cases are non-deterministic,
LLM-judged, and cost money, so they are a directional signal and never a build gate.

**Prerequisite — an evaluation model.** Every metric here is judged by an LLM. With no credentials
configured the run fails at metric construction, not with a low score. Set `ANTHROPIC_API_KEY` (or
`OPENAI_API_KEY`) in `.env` first; see `.env.example`.

**Dataset.** `.dataset.json` is generated, never hand-written — hand-made goldens encode the
author's assumptions about what retrieval should find, which is the very thing under test:

    uv run deepeval generate --method docs --variation single-turn \
        --documents data/external --output-dir evals --file-name .dataset
"""

import sys
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.test_case import LLMTestCase

sys.path.insert(0, str(Path(__file__).parent))

from canon_rag import get_retriever
from metrics.metrics import RETRIEVAL_QUALITY_METRICS

DATASET = Path(__file__).parent / ".dataset.json"

dataset = EvaluationDataset()
if DATASET.exists():
    dataset.add_goldens_from_json_file(file_path=str(DATASET))


@pytest.mark.skipif(
    not DATASET.exists(),
    reason=(
        "No generated dataset. Run `deepeval generate` (see this module's docstring). "
        "Goldens are generated, not fabricated — .claude/rules/testing.md."
    ),
)
@pytest.mark.parametrize("golden", dataset.goldens)
def test_canon_retrieval(golden: Golden) -> None:
    """Score the passages the real retriever returns for each generated question."""
    retrieval_context = get_retriever().retrieve(golden.input, k=5)

    assert_test(
        test_case=LLMTestCase(
            input=golden.input,
            # The retriever is the whole app under test right now: there is no generator to
            # produce an answer, so the retrieved passages stand in as the output being judged.
            actual_output="\n\n".join(retrieval_context),
            retrieval_context=retrieval_context,
        ),
        metrics=RETRIEVAL_QUALITY_METRICS,
    )

"""Selects the configured `BranchOraclePort` implementation.

Mirrors `adapters/outbound/llm_factory.py`'s shape: one function, turning `Settings.branch_oracle`
into a live adapter, called from both the composition root (`bootstrap.py`) and the offline CLI
(`cli/play.py`, which already builds its own adapters directly rather than going through the
container — see that module's docstring).

`DECISIONS.md`, 2026-07-26 session 8: `authored` is the DEFAULT and MUST stay the default —
`corpus` changes a chapter's option set, which changes the visible-fact count `DEMO_SCRIPT` keys on
(`{knower}:{chapter}:{fact_count}`), silently degrading the rehearsed beats into mechanical
fallback prose. A flag buys the honest beat without betting the stage run on it.
"""

from pathlib import Path

from story_engine.adapters.outbound.fanfic.corpus_branch_oracle import (
    CorpusBranchOracle,
    default_chapter_branch_keys,
    load_branch_points,
)
from story_engine.config.settings import Settings
from story_engine.ports.branch_oracle import BranchOraclePort
from story_engine.resources.dexter_demo import chapter_subjects


def build_branch_oracle(
    settings: Settings, *, fallback: BranchOraclePort
) -> BranchOraclePort:
    """Return `fallback` unless `settings.branch_oracle == "corpus"`.

    Args:
        settings: The process-wide settings singleton.
        fallback: Served (with every `source_work_id` forced to `None`) for any chapter the corpus
            oracle has no mined option for. Also returned as-is when `branch_oracle == "authored"`.

    Returns:
        `fallback` unchanged for `"authored"`; otherwise a `CorpusBranchOracle` reading
        `settings.branch_oracle_corpus_dir`, wrapping `fallback`.

    Raises:
        CorpusReadError: `branch_oracle == "corpus"` and the harvested corpus is missing or
            malformed. Never caught here and never degraded to `fallback` — a silent fallback
            would make the flag look like it worked while proving nothing (see this module's
            docstring). The error names the harvest command to run.
    """
    if settings.branch_oracle == "authored":
        return fallback

    corpus_dir = Path(settings.branch_oracle_corpus_dir)
    branch_points = load_branch_points(corpus_dir / "manifest.json")
    chapter_branch_keys = default_chapter_branch_keys(branch_points, chapter_subjects())
    return CorpusBranchOracle(
        corpus_dir=corpus_dir,
        chapter_branch_keys=chapter_branch_keys,
        fallback=fallback,
    )

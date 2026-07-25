"""Unit tests for `build_branch_oracle` — the config -> adapter selection for GAP 2.

Each branch of `settings.branch_oracle` gets a test, plus a standing check that the default stays
"authored": switching it is a silent regression that would degrade the rehearsed `DEMO_SCRIPT`
beats into mechanical fallback prose (`DECISIONS.md`, 2026-07-26 session 8), so the default is
worth locking down explicitly rather than trusting it stays put.
"""

from pathlib import Path

import pytest

from story_engine.adapters.outbound.fanfic.branch_oracle_factory import (
    build_branch_oracle,
)
from story_engine.config.settings import Settings
from story_engine.domain.enums import PresenceGrade
from story_engine.domain.models.canon import Presence
from story_engine.domain.models.play import ChoiceOption, Consequence
from story_engine.shared.errors import CorpusReadError

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "fanfic" / "dexter"
FORK_ID = "canon"


class _FakeFallback:
    """A minimal authored stand-in: one option per chapter, always returned as-is."""

    def __init__(self, by_chapter: dict[int, tuple[ChoiceOption, ...]]) -> None:
        self._by_chapter = by_chapter

    def options_at(
        self, *, fork_id: str, chapter: int, protagonist: str
    ) -> tuple[ChoiceOption, ...]:
        return self._by_chapter.get(chapter, ())


def _authored_option(option_id: str) -> ChoiceOption:
    return ChoiceOption(
        id=option_id,
        label=f"authored {option_id}",
        source_work_id=None,
        consequence=Consequence(
            subject_id="dexter",
            predicate="did",
            object_literal="something authored",
            roster=(Presence(entity_id="dexter", grade=PresenceGrade.ACTIVE),),
        ),
    )


@pytest.fixture
def fallback() -> _FakeFallback:
    return _FakeFallback({1: (_authored_option("t1:a"), _authored_option("t1:b"))})


def test_default_branch_oracle_setting_is_authored() -> None:
    """Regression lock: the default MUST stay `"authored"` — see this module's docstring."""
    assert Settings().branch_oracle == "authored"


def test_authored_setting_returns_the_fallback_unchanged(
    fallback: _FakeFallback,
) -> None:
    settings = Settings(branch_oracle="authored")

    oracle = build_branch_oracle(settings, fallback=fallback)

    assert oracle is fallback


def test_corpus_setting_serves_a_mined_option_with_real_provenance(
    fallback: _FakeFallback,
) -> None:
    settings = Settings(
        branch_oracle="corpus", branch_oracle_corpus_dir=str(FIXTURE_DIR)
    )

    oracle = build_branch_oracle(settings, fallback=fallback)
    options = oracle.options_at(fork_id=FORK_ID, chapter=1, protagonist="dexter")

    assert 2 <= len(options) <= 4
    mined = [o for o in options if o.source_work_id is not None]
    assert len(mined) == 1
    assert mined[0].source_work_id == "wattpad:390229723"


def test_corpus_setting_falls_back_to_authored_with_source_work_id_forced_none(
    fallback: _FakeFallback,
) -> None:
    """A chapter the fixture's mined branch points do not name still renders — from the fallback,
    audited to `source_work_id=None` — never a fabricated mined id."""
    settings = Settings(
        branch_oracle="corpus", branch_oracle_corpus_dir=str(FIXTURE_DIR)
    )

    oracle = build_branch_oracle(settings, fallback=fallback)
    options = oracle.options_at(fork_id=FORK_ID, chapter=1, protagonist="deborah")

    assert len(options) == 2
    assert all(option.source_work_id is None for option in options)


def test_corpus_setting_with_missing_corpus_fails_loudly_naming_the_harvest_command(
    tmp_path: Path, fallback: _FakeFallback
) -> None:
    """A missing corpus must never silently degrade to the fallback — that would make the flag
    look like it worked while proving nothing (this module's docstring)."""
    settings = Settings(
        branch_oracle="corpus",
        branch_oracle_corpus_dir=str(tmp_path / "no-such-corpus"),
    )

    with pytest.raises(CorpusReadError, match="harvest"):
        build_branch_oracle(settings, fallback=fallback)

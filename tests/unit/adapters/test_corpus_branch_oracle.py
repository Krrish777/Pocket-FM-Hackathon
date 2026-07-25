"""Unit tests for `CorpusBranchOracle`, driven by a small fixture corpus — no network.

The fixture lives at `tests/fixtures/fanfic/dexter/` (schema 1.2, hand-trimmed from a real Dexter
harvest shape) rather than `data/raw/` — that directory is gitignored and regenerated, so a unit
test cannot depend on it.
"""

import json
from pathlib import Path

import pytest

from story_engine.adapters.outbound.fanfic.corpus_branch_oracle import (
    CorpusBranchOracle,
    CorpusReadError,
    MinedBranchPoint,
    MinedOption,
    default_chapter_branch_keys,
    load_branch_points,
)
from story_engine.domain.enums import PresenceGrade
from story_engine.domain.models.canon import Presence
from story_engine.domain.models.play import ChoiceOption, Consequence

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "fanfic" / "dexter"
FORK_ID = "canon"


class _FakeFallback:
    """A stand-in authored oracle: returns fixed options per chapter, some with a real-looking id.

    The real fallback (`ScriptedBranchOracle`) is exercised elsewhere; this fake exists only to
    prove `CorpusBranchOracle` forces `source_work_id=None` on whatever it is handed, even when the
    fallback itself reports a non-`None` id.
    """

    def __init__(self, by_chapter: dict[int, tuple[ChoiceOption, ...]]) -> None:
        self._by_chapter = by_chapter

    def options_at(
        self, *, fork_id: str, chapter: int, protagonist: str
    ) -> tuple[ChoiceOption, ...]:
        return self._by_chapter.get(chapter, ())


def _option(option_id: str, source_work_id: str | None) -> ChoiceOption:
    return ChoiceOption(
        id=option_id,
        label=f"authored option {option_id}",
        source_work_id=source_work_id,
        consequence=Consequence(
            subject_id="dexter",
            predicate="did",
            object_literal="something authored",
            roster=(Presence(entity_id="dexter", grade=PresenceGrade.ACTIVE),),
        ),
    )


@pytest.fixture
def fallback() -> _FakeFallback:
    return _FakeFallback(
        {
            2: (
                # Deliberately carries a real-looking id to prove the oracle strips it anyway.
                _option("t2:a", "wattpad:864850"),
                _option("t2:b", None),
            ),
            3: (),  # a chapter the authored table also has nothing for
        }
    )


def test_load_branch_points_parses_the_fixture_manifest() -> None:
    points = load_branch_points(FIXTURE_DIR / "manifest.json")

    assert set(points) == {"reader_insert:dexter", "thin_point"}
    dexter_point = points["reader_insert:dexter"]
    assert dexter_point.focal_entities == ("dexter",)
    assert dexter_point.options[0].is_canon is True
    assert dexter_point.options[1].sources == ("wattpad:390229723",)


def test_load_branch_points_missing_manifest_raises_loudly(tmp_path: Path) -> None:
    with pytest.raises(CorpusReadError):
        load_branch_points(tmp_path / "does-not-exist" / "manifest.json")


def test_load_branch_points_malformed_json_raises_loudly(tmp_path: Path) -> None:
    bad = tmp_path / "manifest.json"
    bad.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(CorpusReadError):
        load_branch_points(bad)


def test_load_branch_points_missing_key_on_recent_schema_raises_loudly(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": "1.2"}), encoding="utf-8")

    with pytest.raises(CorpusReadError):
        load_branch_points(manifest)


def test_load_branch_points_missing_key_on_old_schema_is_legitimately_empty(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")

    assert load_branch_points(manifest) == {}


def test_default_chapter_branch_keys_matches_on_shared_entity() -> None:
    points = load_branch_points(FIXTURE_DIR / "manifest.json")

    mapping = default_chapter_branch_keys(
        points, chapter_subjects={1: "dexter", 2: "deborah"}
    )

    # Chapter 1's subject ("dexter") matches the mined point's focal entity; chapter 2's ("deborah")
    # matches nothing in this fixture, so it is legitimately absent from the mapping.
    assert mapping == {1: "reader_insert:dexter"}


def test_options_at_returns_a_mined_option_with_a_real_source_work_id(
    fallback: _FakeFallback,
) -> None:
    oracle = CorpusBranchOracle(
        corpus_dir=FIXTURE_DIR,
        chapter_branch_keys={1: "reader_insert:dexter"},
        fallback=fallback,
    )

    options = oracle.options_at(fork_id=FORK_ID, chapter=1, protagonist="dexter")

    assert 2 <= len(options) <= 4
    mined = [o for o in options if o.source_work_id is not None]
    canon = [o for o in options if o.is_canon_baseline]
    assert len(mined) == 1
    assert mined[0].source_work_id == "wattpad:390229723"
    assert len(canon) == 1
    # The mined label is synthesized from the taxonomy, never copied from the work's blurb.
    assert mined[0].label not in (
        "A newcomer arrives in Miami and becomes close to Dexter.",
    )


def test_options_at_falls_back_when_protagonist_does_not_match_focal_entity(
    fallback: _FakeFallback,
) -> None:
    oracle = CorpusBranchOracle(
        corpus_dir=FIXTURE_DIR,
        chapter_branch_keys={2: "reader_insert:dexter"},
        fallback=fallback,
    )

    options = oracle.options_at(fork_id=FORK_ID, chapter=2, protagonist="deborah")

    assert len(options) == 2
    assert all(o.source_work_id is None for o in options)


def test_options_at_forces_authored_fallback_ids_to_none(
    fallback: _FakeFallback,
) -> None:
    oracle = CorpusBranchOracle(
        corpus_dir=FIXTURE_DIR,
        chapter_branch_keys={},  # nothing mapped: chapter 2 always falls back
        fallback=fallback,
    )

    options = oracle.options_at(fork_id=FORK_ID, chapter=2, protagonist="dexter")

    assert len(options) == 2
    assert all(o.source_work_id is None for o in options), (
        "authored fallback options must always report source_work_id=None, "
        "even when the fallback itself carries a real-looking id"
    )


def test_options_at_falls_back_without_raising_on_a_thin_branch_point(
    fallback: _FakeFallback,
) -> None:
    oracle = CorpusBranchOracle(
        corpus_dir=FIXTURE_DIR,
        chapter_branch_keys={2: "thin_point"},
        fallback=fallback,
    )

    options = oracle.options_at(fork_id=FORK_ID, chapter=2, protagonist="dexter")

    assert len(options) == 2
    assert all(o.source_work_id is None for o in options)


def test_options_at_returns_empty_tuple_when_neither_mined_nor_authored_cover_a_chapter(
    fallback: _FakeFallback,
) -> None:
    oracle = CorpusBranchOracle(
        corpus_dir=FIXTURE_DIR,
        chapter_branch_keys={},
        fallback=fallback,
    )

    # Chapter 3 has no mined mapping and the fake fallback returns () for it too.
    options = oracle.options_at(fork_id=FORK_ID, chapter=3, protagonist="dexter")

    assert options == ()


def test_construction_raises_on_story_count_mismatch(
    tmp_path: Path, fallback: _FakeFallback
) -> None:
    corpus_dir = tmp_path / "dexter"
    corpus_dir.mkdir()
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    manifest["story_count"] = 99  # disagrees with the 2 lines actually written below
    (corpus_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (corpus_dir / "stories.jsonl").write_text(
        (FIXTURE_DIR / "stories.jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )

    with pytest.raises(CorpusReadError):
        CorpusBranchOracle(
            corpus_dir=corpus_dir, chapter_branch_keys={}, fallback=fallback
        )


def test_construction_raises_on_missing_corpus(
    tmp_path: Path, fallback: _FakeFallback
) -> None:
    with pytest.raises(CorpusReadError):
        CorpusBranchOracle(
            corpus_dir=tmp_path / "no-such-fandom",
            chapter_branch_keys={},
            fallback=fallback,
        )


def test_mined_option_with_no_sources_raises_rather_than_silently_dropping(
    tmp_path: Path, fallback: _FakeFallback
) -> None:
    corpus_dir = tmp_path / "broken"
    corpus_dir.mkdir()
    manifest = {
        "schema_version": "1.2",
        "story_count": 0,
        "branch_points": [
            {
                "key": "broken_point",
                "decision_point": "A decision with a corrupted alternate",
                "focal_entities": ["dexter"],
                "options": [
                    {
                        "label": "Let canon stand",
                        "is_canon": True,
                        "support": 0,
                        "sources": [],
                    },
                    {
                        "label": "An alternate with no source",
                        "is_canon": False,
                        "support": 1,
                        "sources": [],
                    },
                ],
            }
        ],
    }
    (corpus_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (corpus_dir / "stories.jsonl").write_text("", encoding="utf-8")

    oracle = CorpusBranchOracle(
        corpus_dir=corpus_dir,
        chapter_branch_keys={1: "broken_point"},
        fallback=fallback,
    )

    with pytest.raises(CorpusReadError):
        oracle.options_at(fork_id=FORK_ID, chapter=1, protagonist="dexter")


def test_mined_branch_point_dataclasses_are_frozen_value_objects() -> None:
    option = MinedOption(label="x", is_canon=True, support=0, sources=())
    point = MinedBranchPoint(
        key="k", decision_point="d", focal_entities=(), options=(option,)
    )
    assert hash(point) is not None  # frozen + slots => hashable

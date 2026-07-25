"""Unit tests for the JSONL corpus sink — the on-disk contract another branch ingests.

The manifest is a published contract, so these tests assert it stays honest: the schema version, the
premise/quality blocks, and an ordering claim that matches the file's actual record order.
"""

import json
from pathlib import Path

from story_engine.adapters.outbound.fanfic.jsonl_sink import (
    CORPUS_SCHEMA_VERSION,
    JsonlCorpusSink,
    slugify,
)
from story_engine.domain.fanfic_premise import premise_signature_for
from story_engine.domain.models.fanfic import (
    Chapter,
    FanficSource,
    HarvestedStory,
    StoryRef,
)
from story_engine.domain.prose_score import prose_quality

SPARES_BRIAN = (
    "Dexter doesn't kill Brian. They rekindle the brotherly bond that has been lost."
)
VIVID = (
    "The cold air of the room raised goose bumps on my arms, but I ignored them. Something "
    "twitched inside of me, something that had been dead a long time.\n\n"
    '"You came back," he murmured, and she did not answer at once.\n\n'
    "She watched the treeline, and the broth burned her tongue, and she did not care at all.\n"
) * 6
FLAT = 'I said, "Okay."\nHe said, "Fine."\nShe said, "Sure."\n' * 30


def _story(source_id: str, description: str, text: str) -> HarvestedStory:
    ref = StoryRef(
        source=FanficSource.WATTPAD,
        source_id=source_id,
        title=f"A Dexter Fanfiction {source_id}",
        author="someone",
        url=f"https://example.test/{source_id}",
        description=description,
        tags=("dexter", "fanfiction"),
    )
    return HarvestedStory(
        ref=ref,
        chapters=(Chapter(index=1, source_id=f"{source_id}-1", text=text),),
        alias_hits=("dexter",),
        premise=premise_signature_for(ref, fandom="Dexter"),
        prose_quality=prose_quality(text),
    )


def _write(tmp_path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    good = _story("1", SPARES_BRIAN, VIVID)
    weak = _story("2", SPARES_BRIAN, FLAT)
    ranked = tuple(
        sorted(
            (good, weak),
            key=lambda s: -(s.prose_quality.score if s.prose_quality else 0.0),
        )
    )
    JsonlCorpusSink(tmp_path).write("Dexter", ranked)
    target = tmp_path / "dexter"
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    records = [
        json.loads(line)
        for line in (target / "stories.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return manifest, records


class TestRecordSchema:
    def test_schema_version_is_bumped_for_the_new_blocks(self) -> None:
        assert CORPUS_SCHEMA_VERSION == "1.1"

    def test_every_record_carries_premise_and_quality(self, tmp_path: Path) -> None:
        _, records = _write(tmp_path)
        for record in records:
            assert record["schema_version"] == "1.1"
            premise = record["premise"]
            assert premise["key"] == "character_survives:brian"
            assert premise["decision_point"]
            assert premise["alternate_path"]
            quality = record["prose_quality"]
            assert 0.0 <= quality["score"] <= 100.0
            assert len(quality["components"]) == 6

    def test_v1_0_attribution_fields_are_untouched(self, tmp_path: Path) -> None:
        # A 1.0 reader must keep working: 1.1 only adds fields.
        _, records = _write(tmp_path)
        for field in (
            "source",
            "source_id",
            "title",
            "author",
            "url",
            "relevance",
            "chapters",
        ):
            assert field in records[0]


class TestManifest:
    def test_ordering_claim_matches_the_file(self, tmp_path: Path) -> None:
        manifest, records = _write(tmp_path)
        assert manifest["ordering"] == "prose_quality_score_desc"
        scores = [r["prose_quality"]["score"] for r in records]
        assert scores == sorted(scores, reverse=True)

    def test_premise_group_collects_both_branches(self, tmp_path: Path) -> None:
        manifest, _ = _write(tmp_path)
        groups = manifest["premise_groups"]
        assert groups[0]["key"] == "character_survives:brian"
        assert groups[0]["size"] == 2

    def test_branch_point_offers_a_canon_option(self, tmp_path: Path) -> None:
        manifest, _ = _write(tmp_path)
        point = manifest["branch_points"][0]
        assert point["decision_point"] == "Whether Brian dies, as canon has it"
        assert point["options"][0]["is_canon"] is True
        assert 2 <= len(point["options"]) <= 4

    def test_quality_summary_reports_the_spread(self, tmp_path: Path) -> None:
        manifest, _ = _write(tmp_path)
        summary = manifest["prose_quality"]
        assert summary["scored_works"] == 2
        assert summary["min"] <= summary["median"] <= summary["max"]

    def test_unscored_corpus_reports_harvest_order(self, tmp_path: Path) -> None:
        bare = _story("3", "", VIVID).model_copy(
            update={"premise": None, "prose_quality": None}
        )
        JsonlCorpusSink(tmp_path).write("Dexter", (bare,))
        manifest = json.loads(
            (tmp_path / "dexter" / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["ordering"] == "harvest_order"
        assert manifest["prose_quality"] is None

    def test_slug_is_filesystem_safe(self) -> None:
        assert slugify("The Witcher!") == "the-witcher"

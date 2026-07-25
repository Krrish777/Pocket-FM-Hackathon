"""Unit tests for the JSONL vocabulary artifact — the EXT-1 integration contract.

These assertions are deliberately about *field names and shapes*, not values: the artifact is a
cross-session contract, so a rename must fail a test rather than silently break the consumer.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from story_engine.adapters.outbound.wiki.jsonl_index_sink import (
    INDEX_SCHEMA_VERSION,
    JsonlWikiIndexSink,
    natural_key,
    slugify,
    to_record,
)
from story_engine.domain.models.wiki_index import (
    WikiAttribute,
    WikiCanonBasis,
    WikiEntity,
    WikiEntityIndex,
    WikiEntityKind,
    WikiLifeStatus,
    WikiRelationship,
    WikiSourcePage,
)

AT = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)

BRIAN = WikiEntity(
    canonical_name="Brian Moser",
    kind=WikiEntityKind.CHARACTER,
    canon_basis=WikiCanonBasis.BOTH,
    aliases=("The Ice Truck Killer", "Tamiami Slasher"),
    summary="Brian Moser is Dexter's brother.",
    life_status=WikiLifeStatus.DECEASED,
    relationships=(
        WikiRelationship(
            target="Dexter Morgan",
            kind="younger brother",
            field="relatives",
            canon_basis=WikiCanonBasis.SCREEN,
            source_url="https://dexter.fandom.com/wiki/Brian_Moser",
        ),
    ),
    attributes=(
        WikiAttribute(
            predicate="status",
            value="Deceased",
            canon_basis=WikiCanonBasis.BOTH,
            source_url="https://dexter.fandom.com/wiki/Brian_Moser",
        ),
    ),
    sources=(
        WikiSourcePage(
            source_name="fandom_wiki",
            wiki_url="https://dexter.fandom.com",
            page_title="Brian Moser",
            page_id="2196",
            page_url="https://dexter.fandom.com/wiki/Brian_Moser",
            canon_basis=WikiCanonBasis.SCREEN,
            basis_evidence=("Category:Season 1 characters",),
            retrieved_at=AT,
        ),
    ),
    prominence=82058,
)

HANNAH = WikiEntity(
    canonical_name="Hannah McKay",
    kind=WikiEntityKind.CHARACTER,
    canon_basis=WikiCanonBasis.SCREEN,
    summary="Hannah McKay is a serial killer.",
    prominence=43648,
)

INDEX = WikiEntityIndex(
    fandom="Dexter",
    source_name="fandom_wiki",
    wiki_url="https://dexter.fandom.com",
    retrieved_at=AT,
    entities=(BRIAN, HANNAH),
)


class TestRecordSchema:
    def test_top_level_fields_are_exactly_the_documented_contract(self) -> None:
        record = to_record(BRIAN, fandom_slug="dexter")
        assert set(record) == {
            "schema_version",
            "natural_key",
            "canonical_name",
            "aliases",
            "type",
            "status",
            "canon_basis",
            "canon_basis_evidence",
            "summary",
            "prominence",
            "relationships",
            "attributes",
            "provenance",
        }

    def test_enums_serialize_as_lowercase_strings(self) -> None:
        record = to_record(BRIAN, fandom_slug="dexter")
        assert record["type"] == "character"
        assert record["status"] == "deceased"
        assert record["canon_basis"] == "both"

    def test_no_id_or_fork_id_is_invented(self) -> None:
        # Identity and fork semantics belong to the consumer (project_context.md 11 OD-1).
        record = to_record(BRIAN, fandom_slug="dexter")
        assert "id" not in record
        assert "fork_id" not in record

    def test_natural_key_is_stable_and_derived_only_from_stated_inputs(self) -> None:
        assert (
            natural_key(BRIAN, fandom_slug="dexter")
            == "fandom_wiki:dexter:character:brian moser"
        )
        assert natural_key(BRIAN, fandom_slug="dexter") == natural_key(
            BRIAN, fandom_slug="dexter"
        )

    def test_natural_key_degrades_when_provenance_is_absent(self) -> None:
        assert natural_key(HANNAH, fandom_slug="dexter").startswith("unknown:")

    def test_relationship_records_carry_their_own_basis_and_source(self) -> None:
        relationships = to_record(BRIAN, fandom_slug="dexter")["relationships"]
        assert isinstance(relationships, list)
        assert set(relationships[0]) == {
            "target",
            "kind",
            "field",
            "canon_basis",
            "source_url",
        }
        assert relationships[0]["canon_basis"] == "screen"

    def test_attribute_records_carry_their_own_basis_and_source(self) -> None:
        attributes = to_record(BRIAN, fandom_slug="dexter")["attributes"]
        assert isinstance(attributes, list)
        assert set(attributes[0]) == {
            "predicate",
            "value",
            "canon_basis",
            "source_url",
        }

    def test_provenance_is_present_and_timestamped(self) -> None:
        provenance = to_record(BRIAN, fandom_slug="dexter")["provenance"]
        assert isinstance(provenance, list)
        assert set(provenance[0]) == {
            "source_name",
            "wiki_url",
            "page_title",
            "page_id",
            "page_url",
            "canon_basis",
            "basis_evidence",
            "retrieved_at",
        }
        assert provenance[0]["retrieved_at"] == "2026-07-25T12:00:00+00:00"

    def test_every_record_is_json_serializable(self) -> None:
        json.dumps(to_record(BRIAN, fandom_slug="dexter"))


class TestWrite:
    def test_writes_one_json_object_per_line(self, tmp_path: Path) -> None:
        location = JsonlWikiIndexSink(tmp_path).write(INDEX)
        lines = (
            (Path(location) / "entities.jsonl").read_text(encoding="utf-8").splitlines()
        )
        assert len(lines) == 2
        assert json.loads(lines[0])["canonical_name"] == "Brian Moser"

    def test_manifest_reports_the_canon_basis_breakdown(self, tmp_path: Path) -> None:
        location = JsonlWikiIndexSink(tmp_path).write(INDEX)
        manifest = json.loads(
            (Path(location) / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["schema_version"] == INDEX_SCHEMA_VERSION
        assert manifest["counts_by_canon_basis"] == {"both": 1, "screen": 1}
        assert manifest["screen_only_names"] == ["Hannah McKay"]
        assert manifest["entity_count"] == 2
        assert manifest["relationship_count"] == 1

    def test_manifest_states_the_artifact_is_not_a_canon_knowledge_base(
        self, tmp_path: Path
    ) -> None:
        location = JsonlWikiIndexSink(tmp_path).write(INDEX)
        manifest = json.loads(
            (Path(location) / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["artifact_kind"] == "wiki_entity_vocabulary"
        assert "NOT a canon" in manifest["usage_note"]

    def test_output_directory_is_the_fandom_slug(self, tmp_path: Path) -> None:
        index = INDEX.model_copy(update={"fandom": "Dexter: New Blood"})
        assert (
            Path(JsonlWikiIndexSink(tmp_path).write(index)).name == "dexter-new-blood"
        )


class TestSlugify:
    def test_lowercases_and_hyphenates(self) -> None:
        assert (
            slugify("  Percy Jackson & the Olympians ") == "percy-jackson-the-olympians"
        )

    def test_falls_back_for_an_unnameable_value(self) -> None:
        assert slugify("!!!") == "unnamed"

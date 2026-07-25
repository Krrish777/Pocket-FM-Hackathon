"""JSONL entity-vocabulary sink — **this file defines the EXT-1 integration contract.**

The handoff to the knowledge-base session is this artifact, not a shared Python type. Nothing here
imports their models and they import nothing here, so neither branch depends on the other's unmerged
code. The contract is the schema below, versioned by `INDEX_SCHEMA_VERSION`; changing a field name is a
version bump and a conversation, not a refactor.

Written to `<root>/<fandom-slug>/`:

* `entities.jsonl` — one JSON object per entity, streamable so an ingester never loads the whole
  vocabulary into memory.
* `manifest.json` — run-level counts, provenance, and the canon-basis breakdown that answers §11 OD-2.

**Record schema (v1.0)** — field names chosen to map 1:1 onto the consumer's `CanonEntity` where one
exists, and deliberately *omitting* `id` and `fork_id`: those are the consumer's identity and
fork-model semantics (§11 OD-1) and this side must not invent them. `natural_key` is offered instead as
a stable, reproducible key derived only from source + fandom + kind + name.

| field | type | notes |
|---|---|---|
| `schema_version` | str | `"1.0"` |
| `natural_key` | str | `"<source>:<fandom-slug>:<kind>:<lowercased name>"`. Stable across runs. Not an `id`. |
| `canonical_name` | str | Maps to `CanonEntity.canonical_name`. Media qualifiers stripped: `Brian Moser (Novels)` -> `Brian Moser`. |
| `aliases` | list[str] | Maps to `CanonEntity.aliases`. Excludes `canonical_name`. |
| `type` | str | Lowercase: `character`/`location`/`event`/`organization`/`other`. Maps to `CanonEntity.type`. |
| `status` | str | Lowercase: `alive`/`deceased`/`unknown`. **Intended** for `CanonEntity.status`; the exact `EntityStatus` member names are UNVERIFIED from this side, so treat as a string to map. |
| `canon_basis` | str | `novel`/`screen`/`both`/`unknown`. The OD-2 discriminator. **`screen` is a review flag, not a verdict** — see `canon_basis.py`. |
| `canon_basis_evidence` | list[str] | The page title/categories the basis was inferred from, so the label is auditable (§5.4). |
| `summary` | str | Lead-section prose, truncated. For entity recognition, **not** a canon fact. |
| `prominence` | int | Source page size in bytes. Ranking signal only. |
| `relationships` | list[obj] | `{target, kind, field, canon_basis, source_url}`. `target` is an unresolved name string. |
| `attributes` | list[obj] | `{predicate, value, canon_basis, source_url}`. Observations, **never** asserted facts. |
| `provenance` | list[obj] | **Mandatory** (§5.1). `{source_name, wiki_url, page_title, page_id, page_url, canon_basis, basis_evidence[], retrieved_at}` — `retrieved_at` is ISO-8601 UTC. |
"""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from story_engine.domain.models.wiki_index import (
    WikiCanonBasis,
    WikiEntity,
    WikiEntityIndex,
)

logger = logging.getLogger(__name__)

INDEX_SCHEMA_VERSION = "1.0"
DEFAULT_INDEX_ROOT = Path("data/raw/wiki_index")

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")

USAGE_NOTE = (
    "Entity VOCABULARY harvested from a fan wiki, for recognizing canon entities in fan-fiction "
    "text and for flagging screen-vs-novel canon (project_context.md 11 OD-2). It is NOT a canon "
    "knowledge base: per 6.1 canon is the Dexter novels, and a fan wiki is predominantly screen "
    "canon. Do not ingest `attributes` or `summary` as canon facts. Every record carries provenance "
    "so any value can be traced to a page and a retrieval time, or deleted on request."
)


def slugify(value: str) -> str:
    """Return a filesystem-safe slug for a fandom name."""
    return _SLUG_STRIP_RE.sub("-", value.strip().lower()).strip("-") or "unnamed"


class JsonlWikiIndexSink:
    """Write an entity vocabulary to local JSONL. Implements `WikiSinkPort`."""

    def __init__(self, root: Path | str = DEFAULT_INDEX_ROOT) -> None:
        """Initialize the sink.

        Args:
            root: Directory to write fandom subdirectories into. `data/raw/` is gitignored, so the
                artifact stays local by default.
        """
        self._root = Path(root)

    def write(self, index: WikiEntityIndex) -> str:
        """Write `entities.jsonl` and `manifest.json`, returning the output directory path."""
        slug = slugify(index.fandom)
        target = self._root / slug
        target.mkdir(parents=True, exist_ok=True)
        entities_path = target / "entities.jsonl"

        with entities_path.open("w", encoding="utf-8") as handle:
            for entity in index.entities:
                record = to_record(entity, fandom_slug=slug)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        manifest = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "artifact_kind": "wiki_entity_vocabulary",
            "fandom": index.fandom,
            "fandom_slug": slug,
            "source_name": index.source_name,
            "wiki_url": index.wiki_url,
            "retrieved_at": index.retrieved_at.astimezone(UTC).isoformat(),
            "written_at": datetime.now(UTC).isoformat(),
            "entities_file": entities_path.name,
            "entity_count": index.entity_count,
            "relationship_count": index.relationship_count,
            "attribute_count": index.attribute_count,
            "counts_by_kind": index.counts_by_kind(),
            "counts_by_canon_basis": index.counts_by_basis(),
            "screen_only_names": list(index.names_with_basis(WikiCanonBasis.SCREEN)),
            "novel_names": list(index.names_with_basis(WikiCanonBasis.NOVEL)),
            "both_canons_names": list(index.names_with_basis(WikiCanonBasis.BOTH)),
            "unresolved_relationship_targets": len(index.unresolved_targets()),
            "usage_note": USAGE_NOTE,
        }
        (target / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("wrote %s entities to %s", index.entity_count, entities_path)
        return str(target)


def natural_key(entity: WikiEntity, *, fandom_slug: str) -> str:
    """Return a stable key for an entity: `<source>:<fandom>:<kind>:<name>`.

    Deliberately not called `id`: identity and fork semantics belong to the consuming knowledge base
    (`project_context.md` §11 OD-1), and inventing them here would prejudge that decision.
    """
    source = entity.sources[0].source_name if entity.sources else "unknown"
    return (
        f"{source}:{fandom_slug}:{entity.kind}:{entity.canonical_name.strip().lower()}"
    )


def to_record(entity: WikiEntity, *, fandom_slug: str) -> dict[str, object]:
    """Flatten one entity into the on-disk record shape documented in this module's docstring."""
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "natural_key": natural_key(entity, fandom_slug=fandom_slug),
        "canonical_name": entity.canonical_name,
        "aliases": list(entity.aliases),
        "type": str(entity.kind),
        "status": str(entity.life_status),
        "canon_basis": str(entity.canon_basis),
        "canon_basis_evidence": sorted(
            {item for source in entity.sources for item in source.basis_evidence}
        ),
        "summary": entity.summary,
        "prominence": entity.prominence,
        "relationships": [
            {
                "target": relationship.target,
                "kind": relationship.kind,
                "field": relationship.field,
                "canon_basis": str(relationship.canon_basis),
                "source_url": relationship.source_url,
            }
            for relationship in entity.relationships
        ],
        "attributes": [
            {
                "predicate": attribute.predicate,
                "value": attribute.value,
                "canon_basis": str(attribute.canon_basis),
                "source_url": attribute.source_url,
            }
            for attribute in entity.attributes
        ],
        "provenance": [
            {
                "source_name": source.source_name,
                "wiki_url": source.wiki_url,
                "page_title": source.page_title,
                "page_id": source.page_id,
                "page_url": source.page_url,
                "canon_basis": str(source.canon_basis),
                "basis_evidence": list(source.basis_evidence),
                "retrieved_at": source.retrieved_at.astimezone(UTC).isoformat(),
            }
            for source in entity.sources
        ],
    }

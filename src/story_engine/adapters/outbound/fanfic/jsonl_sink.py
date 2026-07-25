"""JSONL corpus sink — the handoff artifact for the knowledge-base branch.

Writes one JSON object per harvested work to `<root>/<fandom-slug>/stories.jsonl`, plus a
`manifest.json` describing the run. JSONL is chosen over a single JSON array so the file streams:
the knowledge-base ingester can process a work at a time without loading the corpus into memory.

The schema is a contract — see `CORPUS_SCHEMA_VERSION`. Every record keeps `source`, `source_id`,
`url`, and `author` so any passage stays attributable to its origin and can be deleted on request.
"""

import json
import logging
import re
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from statistics import median

from story_engine.domain.fanfic_premise import (
    MAX_BRANCH_OPTIONS,
    branch_points,
    group_by_premise,
)
from story_engine.domain.models.fanfic import HarvestedStory

logger = logging.getLogger(__name__)

CORPUS_SCHEMA_VERSION = "1.2"
"""Contract version for the on-disk corpus.

* **1.0** — attribution + relevance + chapter text.
* **1.1** — adds `premise` (Branch Oracle signature: decision point + alternate path) and
  `prose_quality` (scored components) per record, and `premise_groups` / `branch_points` /
  `prose_quality` / `ordering` blocks to the manifest. Every 1.0 field is unchanged and still
  present, so a 1.0 reader keeps working; the new fields may be `null` when the producer did not
  compute them.
* **1.2** — adds `chapters_dropped` (`non_prose`, `duplicate`, `is_partial`) per record. Chapters
  rejected by the prose gate or dropped as exact duplicates were previously invisible: a work
  could ship starting at chapter 2 with nothing saying so, since index gaps are indistinguishable
  from an author's own numbering. Additive only — a 1.0/1.1 reader keeps working.
"""
DEFAULT_CORPUS_ROOT = Path("data/raw/fanfic")

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Return a filesystem-safe slug for a fandom name."""
    return _SLUG_STRIP_RE.sub("-", value.strip().lower()).strip("-") or "unnamed"


class JsonlCorpusSink:
    """Write a harvested corpus to local JSONL. Implements `CorpusSinkPort`."""

    def __init__(self, root: Path | str = DEFAULT_CORPUS_ROOT) -> None:
        """Initialize the sink.

        Args:
            root: Directory to write fandom subdirectories into. `data/raw/` is gitignored, so the
                corpus stays local by default.
        """
        self._root = Path(root)

    def write(
        self,
        fandom: str,
        stories: tuple[HarvestedStory, ...],
        *,
        max_branch_options: int = MAX_BRANCH_OPTIONS,
    ) -> str:
        """Write `stories` and a manifest, returning the corpus directory path."""
        target = self._root / slugify(fandom)
        target.mkdir(parents=True, exist_ok=True)
        corpus_path = target / "stories.jsonl"

        with corpus_path.open("w", encoding="utf-8") as handle:
            for story in stories:
                handle.write(json.dumps(_to_record(story), ensure_ascii=False) + "\n")

        manifest_path = target / "manifest.json"
        manifest = {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "fandom": fandom,
            "harvested_at": datetime.now(UTC).isoformat(),
            "story_count": len(stories),
            "chapter_count": sum(len(s.chapters) for s in stories),
            "total_words": sum(s.total_words for s in stories),
            "sources": sorted({str(s.ref.source) for s in stories}),
            "corpus_file": corpus_path.name,
            "ordering": _ordering(stories),
            "prose_quality": _quality_summary(stories),
            "premise_groups": [
                {
                    "key": group.key,
                    "label": group.label,
                    "size": group.size,
                    "members": list(group.members),
                    "member_titles": list(group.member_titles),
                }
                for group in group_by_premise(stories)
            ],
            "branch_points": [
                {
                    "key": point.key,
                    "decision_point": point.decision_point,
                    "tropes": [str(t) for t in point.tropes],
                    "focal_entities": list(point.focal_entities),
                    "support": point.support,
                    "options": [
                        {
                            "label": option.label,
                            "is_canon": option.is_canon,
                            "support": option.support,
                            "sources": list(option.sources),
                        }
                        for option in point.options
                    ],
                }
                for point in branch_points(stories, max_options=max_branch_options)
            ],
            "branch_oracle_note": (
                "Branch structure only: fan fiction supplies WHAT the options are. Option labels "
                "are synthesized from the premise taxonomy and no harvested prose is reproduced "
                "as story text (project_context.md 5.2)."
            ),
            "usage_note": (
                "Local demo canon / retrieval input. Not redistributable and not training data; "
                "each record retains source attribution so it can be traced or deleted."
            ),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("wrote %s works to %s", len(stories), corpus_path)
        return str(target)


def _ordering(stories: tuple[HarvestedStory, ...]) -> str:
    """Describe the file's record order honestly, by inspecting it rather than trusting a flag."""
    scores = [s.prose_quality.score for s in stories if s.prose_quality is not None]
    if len(scores) != len(stories):
        return "harvest_order"
    if all(a >= b for a, b in pairwise(scores)):
        return "prose_quality_score_desc"
    return "harvest_order"


def _quality_summary(stories: tuple[HarvestedStory, ...]) -> dict[str, object] | None:
    """Summarize the prose-quality spread, or `None` if no work was scored."""
    scores = sorted(
        s.prose_quality.score for s in stories if s.prose_quality is not None
    )
    if not scores:
        return None
    return {
        "scored_works": len(scores),
        "min": scores[0],
        "median": round(median(scores), 2),
        "max": scores[-1],
        "scale": "0-100, weighted mean of six bounded components; see domain/prose_score.py",
    }


def _to_record(story: HarvestedStory) -> dict[str, object]:
    """Flatten a harvested work into the on-disk record shape."""
    ref = story.ref
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "source": str(ref.source),
        "source_id": ref.source_id,
        "title": ref.title,
        "author": ref.author,
        "url": ref.url,
        "description": ref.description,
        "tags": list(ref.tags),
        "language": ref.language,
        "completed": ref.completed,
        "mature": ref.mature,
        "reads": ref.reads,
        "votes": ref.votes,
        "num_chapters_reported": ref.num_chapters,
        "relevance": {
            "alias_hits": list(story.alias_hits),
            "score": story.relevance_score,
        },
        "premise": None
        if story.premise is None
        else {
            "key": story.premise.key,
            "label": story.premise.label,
            "tropes": [str(t) for t in story.premise.tropes],
            "focal_entities": list(story.premise.focal_entities),
            "decision_point": story.premise.decision_point,
            "alternate_path": story.premise.alternate_path,
            "evidence": list(story.premise.evidence),
        },
        "prose_quality": None
        if story.prose_quality is None
        else {
            "score": story.prose_quality.score,
            "word_count": story.prose_quality.word_count,
            "components": [
                {
                    "name": component.name,
                    "value": round(component.value, 4),
                    "weight": component.weight,
                    "detail": component.detail,
                }
                for component in story.prose_quality.components
            ],
        },
        "total_words": story.total_words,
        "chapters_dropped": {
            "non_prose": story.dropped_non_prose,
            "duplicate": story.dropped_duplicate,
            "is_partial": story.is_partial,
        },
        "chapters": [
            {
                "index": chapter.index,
                "source_id": chapter.source_id,
                "title": chapter.title,
                "word_count": chapter.word_count,
                "text": chapter.text,
            }
            for chapter in story.chapters
        ],
    }

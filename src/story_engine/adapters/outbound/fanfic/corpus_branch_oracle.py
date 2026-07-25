"""`CorpusBranchOracle` — Branch Oracle options mined from a harvested fan-fiction corpus.

Implements `BranchOraclePort` (`ports/branch_oracle.py`), replacing the honesty gap recorded in
`resources/dexter_demo.py`: today every `source_work_id` there is hand-typed into an authored
table, so a judge cannot tell a real divergence from an invented one just by looking at the code.
This adapter reads the artifact `EXT-1` actually produced (`docs/EXT-1-scraper-output-contract.md`)
and only ever emits `source_work_id`s that trace back to a real harvested work.

**Measured facts about the real Dexter harvest, not assumptions:**

* Every `premise_groups[].size` is 1 and every `branch_points[].support` is 1 — "N independent
  authors branched here" does not hold at this corpus's scale. Every mined branch point is
  therefore exactly a canon baseline plus one mined alternate: a legal 2-option `Turn`.
* The corpus's branch points are keyed by canon **entity**, not canon **scene** —
  `docs/EXT-1-scraper-output-contract.md` §6 records this as an open, bidirectional hazard: EXT-1
  cannot yet emit a `diverges_from` scene reference, so the consumer (this module) owns the
  moment-matching. `default_chapter_branch_keys` below does that matching from two pieces of real
  data (the corpus's `focal_entities` and the demo's own canon anchors) rather than inventing a
  plot-chapter guess, and callers may always supply their own mapping instead.

Reads `manifest.json` for branch structure and cross-checks `stories.jsonl`'s line count against
the manifest's `story_count` — the integrity check the contract doc itself recommends (§3.2): a
mismatch means the harvest run was interrupted and the corpus is suspect, so this fails loudly
rather than serving what could be a truncated branch table.
"""

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from story_engine.domain.enums import PresenceGrade
from story_engine.domain.models.canon import ChapterIndex, Presence
from story_engine.domain.models.play import ChoiceOption, Consequence
from story_engine.ports.branch_oracle import BranchOraclePort
from story_engine.shared.errors import CorpusReadError

logger = logging.getLogger(__name__)

_MIN_SCHEMA_WITH_BRANCH_POINTS = (1, 1)
"""Corpus schema 1.1 is when `manifest.json` started carrying `branch_points`. A corpus below this
version legitimately has none to read; a corpus at or above it that lacks the key is corrupt."""


@dataclass(frozen=True, slots=True)
class MinedOption:
    """One option as recorded in a harvested manifest's `branch_points[].options[]`."""

    label: str
    is_canon: bool
    support: int
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MinedBranchPoint:
    """One canon decision point as recorded in a harvested manifest's `branch_points[]`."""

    key: str
    decision_point: str
    focal_entities: tuple[str, ...]
    options: tuple[MinedOption, ...]


def _schema_tuple(schema_version: object) -> tuple[int, ...]:
    """Parse a `"1.2"`-shaped version string into a comparable tuple, defaulting to `(0,)`.

    Args:
        schema_version: The manifest's raw `schema_version` value, which may be missing or the
            wrong type on a malformed file — both degrade to `(0,)` rather than raising, since the
            caller decides what a too-old version means.
    """
    if not isinstance(schema_version, str):
        return (0,)
    parts: list[int] = []
    for piece in schema_version.split("."):
        if not piece.isdigit():
            return (0,)
        parts.append(int(piece))
    return tuple(parts) if parts else (0,)


def load_branch_points(manifest_path: Path) -> dict[str, MinedBranchPoint]:
    """Parse `branch_points[]` out of a harvested `manifest.json`, keyed by `key`.

    Args:
        manifest_path: Path to `manifest.json` inside a corpus directory
            (`data/raw/fanfic/<fandom-slug>/manifest.json`).

    Returns:
        `{}` if the manifest predates schema 1.1 (branch structure was never computed) — a real,
        legitimate "nothing mined yet" answer. Otherwise one `MinedBranchPoint` per entry.

    Raises:
        CorpusReadError: the manifest is missing, is not valid JSON, is schema >= 1.1 but has no
            `branch_points` key, or a `branch_points` entry is missing a required field. A corpus
            this broken must fail loudly rather than silently present as "no branches here" — that
            would be indistinguishable from a chapter fan fiction genuinely never wrote about.
    """
    if not manifest_path.is_file():
        raise CorpusReadError(
            f"no manifest at {manifest_path}; harvest a corpus first, e.g. "
            f"'uv run story-engine harvest \"<fandom>\" --kind novel'",
            context={"path": str(manifest_path)},
        )
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CorpusReadError(
            f"manifest at {manifest_path} is not valid JSON: {err}",
            context={"path": str(manifest_path)},
        ) from err
    if not isinstance(raw, dict):
        raise CorpusReadError(
            f"manifest at {manifest_path} is not a JSON object",
            context={"path": str(manifest_path)},
        )

    if "branch_points" not in raw:
        if _schema_tuple(raw.get("schema_version")) < _MIN_SCHEMA_WITH_BRANCH_POINTS:
            logger.info(
                "manifest at %s predates schema 1.1 (schema_version=%r); no branch_points to read",
                manifest_path,
                raw.get("schema_version"),
            )
            return {}
        raise CorpusReadError(
            f"manifest at {manifest_path} declares schema_version={raw.get('schema_version')!r} "
            "but has no 'branch_points' key — the file is truncated or corrupt",
            context={"path": str(manifest_path)},
        )

    points: dict[str, MinedBranchPoint] = {}
    try:
        for raw_point in raw["branch_points"]:
            options = tuple(
                MinedOption(
                    label=raw_option["label"],
                    is_canon=raw_option["is_canon"],
                    support=raw_option["support"],
                    sources=tuple(raw_option["sources"]),
                )
                for raw_option in raw_point["options"]
            )
            point = MinedBranchPoint(
                key=raw_point["key"],
                decision_point=raw_point["decision_point"],
                focal_entities=tuple(raw_point["focal_entities"]),
                options=options,
            )
            points[point.key] = point
    except (KeyError, TypeError) as err:
        raise CorpusReadError(
            f"manifest at {manifest_path} has a malformed branch_points entry: {err}",
            context={"path": str(manifest_path)},
        ) from err
    return points


def verify_story_count(corpus_dir: Path) -> None:
    """Cross-check `manifest.json`'s `story_count` against `stories.jsonl`'s line count.

    This is the integrity check `docs/EXT-1-scraper-output-contract.md` §3.2 itself names: if the
    two disagree, the harvest run was interrupted and the corpus is suspect. Skipped (not failed)
    when either file is simply absent — `load_branch_points` already fails loudly on that case with
    a more specific message; this function only judges consistency between files that both exist.
    """
    manifest_path = corpus_dir / "manifest.json"
    stories_path = corpus_dir / "stories.jsonl"
    if not manifest_path.is_file() or not stories_path.is_file():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CorpusReadError(
            f"manifest at {manifest_path} is not valid JSON: {err}",
            context={"path": str(manifest_path)},
        ) from err
    expected = manifest.get("story_count")
    if not isinstance(expected, int):
        return
    with stories_path.open(encoding="utf-8") as handle:
        actual = sum(1 for line in handle if line.strip())
    if actual != expected:
        raise CorpusReadError(
            f"manifest at {manifest_path} claims story_count={expected} but "
            f"{stories_path} has {actual} record(s) — the harvest run was interrupted; "
            "re-run the harvest before trusting this corpus",
            context={"path": str(corpus_dir), "expected": expected, "actual": actual},
        )


def default_chapter_branch_keys(
    branch_points: Mapping[str, MinedBranchPoint],
    chapter_subjects: Mapping[ChapterIndex, str],
) -> dict[ChapterIndex, str]:
    """Pair each chapter's canon subject with a mined branch point naming that same entity.

    Both inputs are real, measured data — `chapter_subjects` from the demo's own canon anchors
    (`resources/dexter_demo.ANCHORS`, one row per chapter's focal character) and `branch_points`
    from the harvested corpus. The entity-identity link BETWEEN them is the consumer-side inference
    `docs/EXT-1-scraper-output-contract.md` §6 says this side owns, since EXT-1 cannot yet emit a
    canon-scene reference. This is a heuristic, not a mined fact: it says "a branch point names the
    same entity this chapter is anchored to", not "fan fiction diverged at this exact chapter".

    Args:
        branch_points: The corpus's mined branch points, keyed by `key`.
        chapter_subjects: One canon entity id per chapter, e.g. `{1: "dexter", 2: "deborah"}`.

    Returns:
        `{chapter: branch_point_key}` for every chapter whose subject matches at least one mined
        branch point's `focal_entities`. A chapter with no match is simply absent — that chapter
        gets no mined option and the oracle falls back to authored options for it. Deterministic
        when more than one branch point names the same entity: the alphabetically-first key wins.
    """
    keys_by_entity: dict[str, list[str]] = {}
    for key, point in branch_points.items():
        for entity in point.focal_entities:
            keys_by_entity.setdefault(entity.casefold(), []).append(key)

    mapping: dict[ChapterIndex, str] = {}
    for chapter, subject in chapter_subjects.items():
        candidates = sorted(keys_by_entity.get(subject.casefold(), ()))
        if candidates:
            mapping[chapter] = candidates[0]
    return mapping


class CorpusBranchOracle:
    """Serves options mined from a harvested corpus, falling back to authored options.

    Implements `BranchOraclePort`. Every option this class emits carries an honest
    `source_work_id`: mined alternates carry the real `<source>:<source_id>` handle of the
    harvested work that took that path, mined canon-baseline options and every authored fallback
    option carry `None` — regardless of what `fallback` itself would otherwise report — so a judge
    can always tell a mined option from an authored one by that one field alone.
    """

    def __init__(
        self,
        *,
        corpus_dir: Path | str,
        chapter_branch_keys: Mapping[ChapterIndex, str],
        fallback: BranchOraclePort,
    ) -> None:
        """Load a corpus and wire it behind `BranchOraclePort`.

        Args:
            corpus_dir: The fandom's corpus directory, e.g. `data/raw/fanfic/dexter` — must contain
                `manifest.json` (and, for the integrity check, `stories.jsonl`).
            chapter_branch_keys: Which mined `branch_points[].key` (if any) applies at each chapter.
                Build one with `default_chapter_branch_keys`, or supply a hand-picked mapping.
            fallback: Served, with `source_work_id` forced to `None`, for any chapter this oracle
                has no mined option for — an unmapped chapter, a chapter whose mined branch point
                does not name the requested protagonist, or one that renders outside 2-4 options.

        Raises:
            CorpusReadError: the corpus is missing or malformed (see `load_branch_points` and
                `verify_story_count`).
        """
        corpus_dir = Path(corpus_dir)
        verify_story_count(corpus_dir)
        self._branch_points = load_branch_points(corpus_dir / "manifest.json")
        self._chapter_branch_keys = dict(chapter_branch_keys)
        self._fallback = fallback

    def options_at(
        self, *, fork_id: str, chapter: ChapterIndex, protagonist: str
    ) -> tuple[ChoiceOption, ...]:
        """Return mined options for `chapter` if one applies to `protagonist`, else fall back."""
        point = self._point_for(chapter, protagonist)
        if point is None:
            return self._fallback_options(
                fork_id=fork_id, chapter=chapter, protagonist=protagonist
            )
        options = _render(
            point, fork_id=fork_id, chapter=chapter, protagonist=protagonist
        )
        if not 2 <= len(options) <= 4:
            logger.info(
                "chapter %s: mined branch point %r rendered %s option(s) (need 2-4); "
                "falling back to authored options",
                chapter,
                point.key,
                len(options),
            )
            return self._fallback_options(
                fork_id=fork_id, chapter=chapter, protagonist=protagonist
            )
        logger.info(
            "chapter %s: served %s mined option(s) from branch point %r",
            chapter,
            len(options),
            point.key,
        )
        return options

    def _point_for(
        self, chapter: ChapterIndex, protagonist: str
    ) -> MinedBranchPoint | None:
        """Look up the mined branch point mapped to `chapter`, if it applies to `protagonist`."""
        key = self._chapter_branch_keys.get(chapter)
        if key is None:
            logger.info(
                "chapter %s: no mined branch point mapped; falling back to authored options",
                chapter,
            )
            return None
        point = self._branch_points.get(key)
        if point is None:
            logger.info(
                "chapter %s: mapped to branch point %r, which is not in this corpus; "
                "falling back to authored options",
                chapter,
                key,
            )
            return None
        if point.focal_entities and protagonist.casefold() not in {
            e.casefold() for e in point.focal_entities
        }:
            logger.info(
                "chapter %s: mined branch point %r names %s, not protagonist %r; "
                "falling back to authored options",
                chapter,
                point.key,
                point.focal_entities,
                protagonist,
            )
            return None
        return point

    def _fallback_options(
        self, *, fork_id: str, chapter: ChapterIndex, protagonist: str
    ) -> tuple[ChoiceOption, ...]:
        """Delegate to the authored fallback, auditing every option to `source_work_id=None`."""
        options = self._fallback.options_at(
            fork_id=fork_id, chapter=chapter, protagonist=protagonist
        )
        if not options:
            return options
        audited = tuple(
            option.model_copy(update={"source_work_id": None}) for option in options
        )
        logger.info(
            "chapter %s: served %s authored fallback option(s) (source_work_id forced to None)",
            chapter,
            len(audited),
        )
        return audited


def _render(
    point: MinedBranchPoint, *, fork_id: str, chapter: ChapterIndex, protagonist: str
) -> tuple[ChoiceOption, ...]:
    """Render a mined branch point's options as `ChoiceOption`s.

    Raises:
        CorpusReadError: a non-canon option carries no source — every alternate the harvester
            writes is backed by at least one work (`fanfic_premise.branch_points`), so a sourceless
            alternate means the manifest was hand-edited or corrupted, not that coverage is thin.
    """
    rendered: list[ChoiceOption] = []
    for index, option in enumerate(point.options):
        if option.is_canon:
            source_work_id = None
        else:
            if not option.sources:
                raise CorpusReadError(
                    f"branch point {point.key!r} has a non-canon option with no sources: "
                    f"{option.label!r}",
                    context={"branch_point": point.key, "label": option.label},
                )
            source_work_id = option.sources[0]
        suffix = "canon" if option.is_canon else f"alt-{index}"
        rendered.append(
            ChoiceOption(
                id=f"{fork_id}:{chapter}:{point.key}:{suffix}",
                label=option.label,
                source_work_id=source_work_id,
                consequence=Consequence(
                    subject_id=protagonist,
                    predicate="upheld" if option.is_canon else "diverged_on",
                    object_literal=point.decision_point
                    if option.is_canon
                    else option.label,
                    roster=(
                        Presence(entity_id=protagonist, grade=PresenceGrade.ACTIVE),
                    ),
                    secret=False,
                    discloses=(),
                ),
            )
        )
    return tuple(rendered)

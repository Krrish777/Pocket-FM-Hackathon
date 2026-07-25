"""AO3 fan-fiction source, read from a HuggingFace mirror instead of the archive itself.

archiveofourown.org is behind a Cloudflare challenge from this machine (verified 2026-07-25), so the
works are reached through the `midwestern-simulation-active/ao3_random_subset` dataset (64,000 rows,
features `id, title, metadata, text`) over the HuggingFace datasets-server REST API. No `datasets` or
`pyarrow` dependency: one endpoint carries the whole adapter.

    GET https://datasets-server.huggingface.co/rows?dataset=&config=default&split=train
        &offset=N&length=<=100        -> {"rows": [{"row": {id, title, metadata, text}}]}

Everything else on that server is unusable, measured 2026-07-25:
  * `/search` -> HTTP 500 "The dataset index is corrupted and being rebuilt".
  * `/filter` -> HTTP 500 "the dataset index is loading".
  * `length` is capped at 100, and a `columns=` projection is ignored, so every page is ~2.45 MB.

Fandom selection is therefore a **client-side scan** over paged rows: a full pass is 640 requests and
~1.6 GB. That is unusable in a demo, so this adapter is deliberately bounded (`max_scan_rows`) and
resumable (the scan offset and a row index are persisted under `data/interim/`, which is gitignored),
and it logs the rows scanned against the 64,000 total so coverage is never silently overstated.
"""

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from story_engine.adapters.outbound.fanfic.http_util import build_client, get_with_retry
from story_engine.domain.models.fanfic import (
    Chapter,
    ChapterRef,
    FandomQuery,
    FanficSource,
    StoryRef,
)
from story_engine.shared.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

DATASET = "midwestern-simulation-active/ao3_random_subset"
TOTAL_ROWS = 64_000
_ROWS_URL = "https://datasets-server.huggingface.co/rows"
# Server-enforced: length=200 returns HTTP 422 "must not be greater than 100".
_PAGE_SIZE = 100
_MAX_SCAN_ROWS = 5_000
_CACHE_DIR = Path("data/interim/hf_ao3")
_WORK_URL = "https://archiveofourown.org/works/{}"
# A one- or two-letter alias ("AU", "PJ") matches half the archive by accident.
_MIN_TERM_CHARS = 3
_MATURE_RATINGS = frozenset({"mature", "explicit"})
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_INT_RE = re.compile(r"\d+")
_LANGUAGE_CODES = {
    "english": "en",
    "spanish": "es",
    "español": "es",
    "french": "fr",
    "français": "fr",
    "german": "de",
    "deutsch": "de",
    "portuguese": "pt",
    "italian": "it",
    "russian": "ru",
    "chinese": "zh",
    "中文": "zh",
    "japanese": "ja",
    "日本語": "ja",
    "korean": "ko",
}


@dataclass(slots=True)
class _RowRecord:
    """One scanned dataset row, minus its prose — the unit the resumable index stores.

    Keeping prose out of the index is what makes re-querying cheap: ~300 bytes a row lets a second
    fandom be matched against thousands of already-scanned rows with no download, and `offset` lets
    the prose of a late match be re-fetched with a single one-row request.
    """

    offset: int
    source_id: str
    title: str
    fandom: str
    characters: str
    author: str
    language: str
    rating: str
    warning: str
    tags: tuple[str, ...]
    words: int
    hits: int
    kudos: int
    chapters: str
    completed: bool
    text_chars: int


@dataclass(slots=True)
class _ScanState:
    """How far the scan has got, so a second run resumes instead of re-downloading."""

    dataset: str
    rows_scanned: int


class HuggingFaceAO3Source:
    """Search and fetch AO3 works from the HuggingFace mirror. Implements `FanficSourcePort`."""

    source_name: str = FanficSource.AO3

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_scan_rows: int = _MAX_SCAN_ROWS,
        cache_dir: Path | str = _CACHE_DIR,
        dataset: str = DATASET,
        total_rows: int = TOTAL_ROWS,
        page_size: int = _PAGE_SIZE,
        request_delay: float = 1.0,
    ) -> None:
        """Initialize the adapter.

        Args:
            client: An HTTP client to reuse; one is built if omitted.
            max_scan_rows: Ceiling on rows downloaded by a single `search` call. The scan resumes
                from the persisted offset, so successive runs extend coverage rather than repeat it.
                A full pass would be 640 requests / ~1.6 GB, hence the bound.
            cache_dir: Where the row index, scan offset, and fetched prose are persisted.
                Under `data/interim/` by default, which is gitignored.
            dataset: HuggingFace dataset id to page through.
            total_rows: Row count of the split, used only for honest coverage logging.
            page_size: Rows per request; the server caps this at 100.
            request_delay: Seconds to pause between requests. 1.0 by default because the
                datasets-server starts returning 429 during a sustained scan (observed after
                ~3,200 rows at a 0.1s delay on 2026-07-25).
        """
        self._client = client or build_client()
        self._max_scan_rows = max(0, max_scan_rows)
        self._cache_dir = Path(cache_dir)
        self._dataset = dataset
        self._total_rows = max(0, total_rows)
        self._page_size = max(1, min(page_size, _PAGE_SIZE))
        self._request_delay = request_delay

    # --- port surface ---------------------------------------------------------------------
    def search(self, query: FandomQuery, *, limit: int) -> tuple[StoryRef, ...]:
        """Return up to `limit` works whose AO3 fandom label matches the query's alias set.

        Already-scanned rows are matched from the on-disk index first (free), then the scan resumes
        from the persisted offset for at most `max_scan_rows` further rows. Selection is on
        `metadata.Fandom`/`metadata.Fandoms` only — the dataset carries no full-text search — so a
        work whose fandom field is empty is invisible here even if its prose is on-topic.
        """
        terms = _match_terms(query.search_terms)
        if not terms or limit < 1:
            return ()

        index = self._load_index()
        matched: dict[str, StoryRef] = {}
        for record in index.values():
            if len(matched) >= limit:
                break
            if _matches(record, terms):
                matched.setdefault(record.source_id, _to_ref(record))
        from_cache = len(matched)

        state = self._load_state()
        scanned = self._scan(query, terms, index, matched, state, limit=limit)

        logger.info(
            "hf-ao3 search for %r: %s works (%s from cache, %s newly scanned); "
            "scanned %s new rows, cumulative coverage %s/%s rows (%.1f%%)",
            query.name,
            len(matched),
            from_cache,
            len(matched) - from_cache,
            scanned,
            state.rows_scanned,
            self._total_rows,
            100.0 * state.rows_scanned / self._total_rows if self._total_rows else 0.0,
        )
        return tuple(matched.values())

    def fetch_chapters(
        self, ref: StoryRef, *, max_chapters: int
    ) -> tuple[Chapter, ...]:
        """Return the work's prose as a single chapter, or `()` if the prose is unavailable.

        This dataset stores each work as one undivided `text` blob, and only 5 of the 39
        multi-chapter works in a 400-row sample carried a detectable "Chapter N" heading (measured
        2026-07-25). Splitting on a heading would therefore mis-slice most works, so the whole work
        is emitted as chapter 1 — and `search` sets `chapter_refs` to exactly that one handle, so the
        ref and this method never disagree.
        """
        if max_chapters < 1:
            return ()
        text = self._text_for(ref.source_id)
        if not text:
            logger.warning(
                "hf-ao3 has no prose cached or fetchable for %s", ref.source_id
            )
            return ()
        return (Chapter(index=1, source_id=ref.source_id, title=ref.title, text=text),)

    # --- scanning ------------------------------------------------------------------------
    def _scan(
        self,
        query: FandomQuery,
        terms: tuple[str, ...],
        index: dict[str, _RowRecord],
        matched: dict[str, StoryRef],
        state: _ScanState,
        *,
        limit: int,
    ) -> int:
        """Page forward from the persisted offset, indexing rows and collecting matches.

        Returns the number of rows newly downloaded. Mutates `index`, `matched`, and `state`.

        Raises:
            SourceUnavailableError: If the host cuts the scan off before anything was matched.
                Sustained paging does get rate-limited (429 observed after ~3,200 rows on
                2026-07-25), so once there are matches in hand a cut-off degrades to a partial
                result — the alternative discards thousands of rows of paid-for download.
        """
        new_records: list[_RowRecord] = []
        scanned = 0
        try:
            while (
                len(matched) < limit
                and scanned < self._max_scan_rows
                and state.rows_scanned < self._total_rows
            ):
                length = min(self._page_size, self._max_scan_rows - scanned)
                page = self._fetch_page(state.rows_scanned, length)
                if not page:
                    break
                for position, raw in enumerate(page):
                    record = _parse_row(raw, state.rows_scanned + position)
                    if record is None:
                        continue
                    index[record.source_id] = record
                    new_records.append(record)
                    if len(matched) >= limit or record.source_id in matched:
                        continue
                    if _matches(record, terms):
                        self._write_text(record.source_id, _row_text(raw))
                        matched[record.source_id] = _to_ref(record)
                scanned += len(page)
                state.rows_scanned += len(page)
        except SourceUnavailableError:
            if not matched:
                raise
            logger.warning(
                "hf-ao3 scan cut short at row %s after %s rows; returning %s matches found so far",
                state.rows_scanned,
                scanned,
                len(matched),
                exc_info=True,
            )
        finally:
            # Persist whatever the scan reached even if the host fails mid-run, so the next call
            # resumes instead of re-downloading pages that already cost 2.45 MB each.
            self._append_index(new_records)
            self._save_state(state)
        logger.debug("hf-ao3 scanned %s rows for %r", scanned, query.name)
        return scanned

    def _fetch_page(self, offset: int, length: int) -> list[dict[str, Any]]:
        """Fetch one page of rows, unwrapping the server's `{"rows": [{"row": {...}}]}` envelope."""
        params: dict[str, Any] = {
            "dataset": self._dataset,
            "config": "default",
            "split": "train",
            "offset": offset,
            "length": length,
        }
        response = get_with_retry(self._client, _ROWS_URL, params=params)
        self._pause()
        try:
            payload = response.json()
        except ValueError as err:
            raise SourceUnavailableError(
                "huggingface datasets-server returned non-JSON",
                context={"dataset": self._dataset, "offset": offset},
            ) from err
        if not isinstance(payload, dict):
            raise SourceUnavailableError(
                f"huggingface datasets-server returned {type(payload).__name__}, expected an object",
                context={"dataset": self._dataset, "offset": offset},
            )
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise SourceUnavailableError(
                "huggingface datasets-server response had no rows array",
                context={"dataset": self._dataset, "offset": offset},
            )
        return [
            row
            for item in rows
            if isinstance(item, dict) and isinstance(row := item.get("row"), dict)
        ]

    def _pause(self) -> None:
        if self._request_delay > 0:
            time.sleep(self._request_delay)

    # --- cache ---------------------------------------------------------------------------
    @property
    def _index_path(self) -> Path:
        return self._cache_dir / "row_index.jsonl"

    @property
    def _state_path(self) -> Path:
        return self._cache_dir / "scan_state.json"

    def _text_path(self, source_id: str) -> Path:
        return self._cache_dir / "texts" / f"{_safe_name(source_id)}.txt"

    def _load_index(self) -> dict[str, _RowRecord]:
        """Read the persisted row index, skipping any line that is not a usable record."""
        path = self._index_path
        if not path.is_file():
            return {}
        index: dict[str, _RowRecord] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("skipping corrupt line in %s", path)
                continue
            record = _record_from_json(payload)
            if record is not None:
                index[record.source_id] = record
        logger.debug("hf-ao3 loaded %s cached rows from %s", len(index), path)
        return index

    def _append_index(self, records: list[_RowRecord]) -> None:
        if not records:
            return
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._index_path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _load_state(self) -> _ScanState:
        """Read the resume offset, restarting from 0 if it belongs to a different dataset."""
        path = self._state_path
        fresh = _ScanState(dataset=self._dataset, rows_scanned=0)
        if not path.is_file():
            return fresh
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("unreadable scan state at %s; restarting the scan", path)
            return fresh
        if not isinstance(payload, dict) or payload.get("dataset") != self._dataset:
            return fresh
        return _ScanState(
            dataset=self._dataset,
            rows_scanned=_non_negative_int(payload.get("rows_scanned")),
        )

    def _save_state(self, state: _ScanState) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(asdict(state), indent=2) + "\n", encoding="utf-8"
        )

    def _write_text(self, source_id: str, text: str) -> None:
        if not text:
            return
        path = self._text_path(source_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _text_for(self, source_id: str) -> str:
        """Return the work's prose from cache, re-fetching its single row if need be.

        A match found in the index from an earlier run under a different fandom has no cached prose;
        the stored offset makes recovering it one small request rather than another full scan.
        """
        path = self._text_path(source_id)
        if path.is_file():
            return path.read_text(encoding="utf-8")
        record = self._load_index().get(source_id)
        if record is None:
            return ""
        page = self._fetch_page(record.offset, 1)
        for raw in page:
            if str(raw.get("id") or "").strip() != source_id:
                continue
            text = _row_text(raw)
            self._write_text(source_id, text)
            return text
        logger.warning("row %s no longer at cached offset %s", source_id, record.offset)
        return ""


# --- row mapping -------------------------------------------------------------------------------
def _parse_row(raw: dict[str, Any], offset: int) -> _RowRecord | None:
    """Map one dataset row onto an index record, or None if it is unusable.

    Third-party data is untrusted: every field is coerced defensively. Rows without an id, a title,
    or any prose are dropped — text length runs `min 0, median 9,093, max 1,552,438` chars, and an
    empty work has nothing to contribute to a corpus.
    """
    source_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or "").strip()
    text = _row_text(raw)
    if not source_id or not title or not text:
        return None
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return _RowRecord(
        offset=offset,
        source_id=source_id,
        title=title[:500],
        # `Fandom` is singular, `Fandoms` is what crossovers populate instead: in a 400-row sample
        # `Fandom` covered 236 rows and `Fandoms` another 43, so reading both raises fandom-labelled
        # coverage from 59% to 70%.
        fandom=_join_fields(metadata, ("Fandom", "Fandoms")),
        characters=_join_fields(metadata, ("Characters", "Character")),
        author=_author_name(metadata.get("author")),
        language=_language_code(metadata.get("Language")),
        rating=_text_field(metadata.get("Rating")),
        warning=_join_fields(metadata, ("Archive Warning", "Archive Warnings")),
        tags=_split_tags(
            _join_fields(
                metadata,
                (
                    "Additional Tags",
                    "Relationship",
                    "Relationships",
                    "Categories",
                    "Category",
                ),
            )
        ),
        words=_non_negative_int(metadata.get("words") or metadata.get("Words")),
        # Hits/Kudos are AO3's read/vote analogues but are present on only ~30% of rows
        # (120/400 and 117/400 sampled); the rest legitimately map to 0.
        hits=_non_negative_int(metadata.get("Hits")),
        kudos=_non_negative_int(metadata.get("Kudos")),
        chapters=_text_field(metadata.get("chapters") or metadata.get("Chapters")),
        completed=_is_completed(metadata),
        text_chars=len(text),
    )


def _to_ref(record: _RowRecord) -> StoryRef:
    """Map an index record onto a `StoryRef`.

    Four decisions worth knowing about:
      * `num_chapters` is 1, matching the single `ChapterRef`, because that is what
        `fetch_chapters` can actually deliver. The archive's own count is preserved as an
        `ao3_chapters:` tag instead of being asserted as fetchable structure.
      * `reads`/`votes` come from AO3 Hits/Kudos where present and are 0 otherwise, so a caller
        leaving `min_reads`/`min_votes` above 0 will reject most AO3 works.
      * `description` carries AO3's fandom/character/tag line, not an author summary — the dataset
        has no summary field. It is populated because `domain.fanfic_quality.alias_hits` matches
        multi-word aliases on word boundaries in title+description only; with it empty, a work
        labelled `'Harry Potter - J. K. Rowling'` scored zero alias hits and the relevance gate
        rejected every AO3 work (observed end-to-end, 2026-07-25).
      * Each fandom and character label is also emitted as its own tag, because that same function
        matches tags as whole normalized keys — a single joined tag matches nothing.
    """
    fandoms = _split_tags(record.fandom)
    characters = _split_tags(record.characters)
    provenance = [f"ao3_fandom:{record.fandom}"] if record.fandom else []
    if record.characters:
        provenance.append(f"ao3_characters:{record.characters}")
    if record.chapters:
        provenance.append(f"ao3_chapters:{record.chapters}")
    return StoryRef(
        source=FanficSource.AO3,
        source_id=record.source_id,
        title=record.title,
        author=record.author,
        url=_WORK_URL.format(record.source_id),
        description=_describe(record),
        tags=(*fandoms, *characters, *record.tags, *provenance),
        chapter_refs=(
            ChapterRef(source_id=record.source_id, index=1, title=record.title),
        ),
        num_chapters=1,
        reads=record.hits,
        votes=record.kudos,
        completed=record.completed,
        mature=_is_mature(record),
        language=record.language,
    )


def _describe(record: _RowRecord) -> str:
    """Compose the work's AO3 label line, the closest thing this dataset has to a blurb."""
    parts = []
    if record.fandom:
        parts.append(f"Fandom: {record.fandom}.")
    if record.characters:
        parts.append(f"Characters: {record.characters}.")
    if record.tags:
        parts.append(f"Tags: {', '.join(record.tags)}.")
    return " ".join(parts)


def _record_from_json(payload: object) -> _RowRecord | None:
    """Rebuild an index record from a cache line, or None if the line is not one."""
    if not isinstance(payload, dict):
        return None
    source_id = str(payload.get("source_id") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not source_id or not title:
        return None
    return _RowRecord(
        offset=_non_negative_int(payload.get("offset")),
        source_id=source_id,
        title=title[:500],
        fandom=_text_field(payload.get("fandom")),
        characters=_text_field(payload.get("characters")),
        author=_text_field(payload.get("author")),
        language=_text_field(payload.get("language")) or "en",
        rating=_text_field(payload.get("rating")),
        warning=_text_field(payload.get("warning")),
        tags=_string_tuple(payload.get("tags")),
        words=_non_negative_int(payload.get("words")),
        hits=_non_negative_int(payload.get("hits")),
        kudos=_non_negative_int(payload.get("kudos")),
        chapters=_text_field(payload.get("chapters")),
        completed=bool(payload.get("completed")),
        text_chars=_non_negative_int(payload.get("text_chars")),
    )


# --- fandom matching ---------------------------------------------------------------------------
def _match_terms(search_terms: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize the query's alias set into the terms fandom labels are matched against."""
    terms: dict[str, None] = {}
    for term in search_terms:
        normalized = _normalize(term)
        if len(normalized) >= _MIN_TERM_CHARS:
            terms.setdefault(normalized, None)
    return tuple(terms)


def _matches(record: _RowRecord, terms: tuple[str, ...]) -> bool:
    """Return True if any alias term appears as whole words in the work's fandom label.

    AO3 fandom strings are not bare titles — `'Harry Potter - J. K. Rowling'`,
    `'Teen Wolf (TV)'` — so matching is word-boundary containment over a punctuation-stripped
    form, not equality. Word boundaries stop `'star'` from matching `'Stargate SG-1'`.
    """
    if not record.fandom:
        return False
    haystack = _normalize(record.fandom)
    if not haystack:
        return False
    padded = f" {haystack} "
    return any(f" {term} " in padded for term in terms)


def _normalize(value: str) -> str:
    """Lowercase and reduce every run of non-alphanumerics to a single space."""
    return _NON_ALNUM_RE.sub(" ", value.lower()).strip()


# --- field coercion ----------------------------------------------------------------------------
def _row_text(raw: dict[str, Any]) -> str:
    """Extract a row's prose, tolerating a null or non-string `text`."""
    text = raw.get("text")
    return text.strip() if isinstance(text, str) else ""


def _text_field(raw_value: object) -> str:
    """Coerce a metadata value to a trimmed string, treating null as empty."""
    if raw_value is None or isinstance(raw_value, bool):
        return ""
    return str(raw_value).strip()


def _join_fields(metadata: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Join the non-empty values of `keys` into one comma-separated string, de-duplicated."""
    parts: dict[str, None] = {}
    for key in keys:
        for piece in _text_field(metadata.get(key)).split(","):
            cleaned = piece.strip()
            if cleaned:
                parts.setdefault(cleaned, None)
    return ", ".join(parts)


def _split_tags(joined: str) -> tuple[str, ...]:
    """Split a comma-separated AO3 tag string into distinct tags."""
    return tuple(piece.strip() for piece in joined.split(",") if piece.strip())


def _author_name(raw_value: object) -> str:
    """Strip AO3's `"by <name>"` byline prefix from the author field."""
    author = _text_field(raw_value)
    if author.lower().startswith("by "):
        return author[3:].strip()
    return author


def _language_code(raw_value: object) -> str:
    """Map AO3's language name ("English") onto a two-letter code."""
    name = _text_field(raw_value).lower()
    if not name:
        return "en"
    return _LANGUAGE_CODES.get(name, name[:2])


def _is_mature(record: _RowRecord) -> bool:
    """Flag a work mature on an adult rating or an explicit archive warning."""
    if record.rating.lower() in _MATURE_RATINGS:
        return True
    warning = record.warning.lower()
    return "rape" in warning or "underage" in warning


def _is_completed(metadata: dict[str, Any]) -> bool:
    """Read completion from the `completed` date, falling back to a `chapters` "N/N" count."""
    if _text_field(metadata.get("completed")) or _text_field(metadata.get("Completed")):
        return True
    chapters = _text_field(metadata.get("chapters") or metadata.get("Chapters"))
    written, _, planned = chapters.partition("/")
    return bool(written.strip()) and written.strip() == planned.strip()


def _string_tuple(raw_value: object) -> tuple[str, ...]:
    """Coerce a JSON list into a tuple of non-empty strings."""
    if not isinstance(raw_value, list):
        return ()
    return tuple(str(item).strip() for item in raw_value if str(item).strip())


def _non_negative_int(raw_value: object) -> int:
    """Coerce a value to a non-negative int, defaulting to 0.

    AO3 counts arrive as strings with thousands separators (`"10,817"`), so digits are extracted
    rather than parsed strictly; a value with no digits degrades to 0 instead of raising.
    """
    if isinstance(raw_value, bool):
        return 0  # JSON true would otherwise coerce to 1 and read as a real count
    if isinstance(raw_value, int):
        return max(0, raw_value)
    if isinstance(raw_value, float):
        return max(0, int(raw_value))
    if isinstance(raw_value, str):
        digits = "".join(_INT_RE.findall(raw_value))
        return int(digits) if digits else 0
    return 0


def _safe_name(source_id: str) -> str:
    """Reduce a row id to a filesystem-safe cache filename."""
    return _NON_ALNUM_RE.sub("_", source_id.lower()) or "unknown"

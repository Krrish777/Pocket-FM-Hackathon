"""Wattpad fan-fiction source adapter.

Wattpad is the primary source because, verified 2026-07-25, it is the only major fanfic host that
is both reachable and fandom-searchable without credentials: AO3 and fanfiction.net sit behind
Cloudflare challenges, and Reddit's API now requires manual approval while its fandom subreddits
carry recommendation threads rather than prose.

Two endpoints carry the whole adapter:
  GET /api/v3/stories?query=&limit=&offset=   -> story metadata incl. parts[] (id + title)
  GET /apiv2/storytext?id=<partId>           -> that chapter's prose as an HTML fragment
"""

import logging
import time
from typing import Any

import httpx

from story_engine.adapters.outbound.fanfic.http_util import (
    build_client,
    get_with_retry,
    html_to_text,
)
from story_engine.domain.models.fanfic import (
    Chapter,
    ChapterRef,
    FandomQuery,
    FanficSource,
    StoryRef,
)
from story_engine.shared.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.wattpad.com/api/v3/stories"
_STORYTEXT_URL = "https://www.wattpad.com/apiv2/storytext"
_PAGE_SIZE = 20
# Searching every expanded alias costs one request each for diminishing returns; relevance scoring
# still uses the full set, so breadth of MATCHING is free while breadth of QUERYING is not.
_MAX_QUERY_TERMS = 6
_LANGUAGE_CODES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "portuguese": "pt",
    "italian": "it",
    "indonesian": "id",
    "filipino": "tl",
    "turkish": "tr",
    "russian": "ru",
    "hindi": "hi",
    "arabic": "ar",
}


class WattpadSource:
    """Search and fetch fan fiction from Wattpad. Implements `FanficSourcePort`."""

    source_name: str = FanficSource.WATTPAD

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        request_delay: float = 0.4,
        page_size: int = _PAGE_SIZE,
        max_query_terms: int = _MAX_QUERY_TERMS,
    ) -> None:
        """Initialize the adapter.

        Args:
            client: An HTTP client to reuse; one is built if omitted.
            request_delay: Seconds to pause between requests, to stay a polite client.
            page_size: Stories requested per search page (Wattpad caps this in practice).
            max_query_terms: How many aliases to issue queries for. The full alias set is still
                used for relevance scoring — searching every alias costs a request each for
                diminishing returns, while matching against every alias is free.
        """
        self._client = client or build_client()
        self._request_delay = request_delay
        self._page_size = page_size
        self._max_query_terms = max_query_terms

    # --- port surface ---------------------------------------------------------------------
    def search(self, query: FandomQuery, *, limit: int) -> tuple[StoryRef, ...]:
        """Return up to `limit` candidate works, spread across the fandom's alias set.

        Round-robins one page per alias per round. Exhausting each alias in turn instead would let
        the first alias consume the whole budget — observed on the first live run, where 18 aliases
        were expanded but only one was ever queried.
        """
        terms = list(query.search_terms[: self._max_query_terms])
        if not terms:
            return ()

        collected: dict[str, StoryRef] = {}
        offsets = dict.fromkeys(terms, 0)
        exhausted: set[str] = set()

        while len(collected) < limit and len(exhausted) < len(terms):
            for term in terms:
                if term in exhausted or len(collected) >= limit:
                    continue
                refs, has_more = self._search_page(term, offsets[term])
                offsets[term] += self._page_size
                if not refs or not has_more:
                    exhausted.add(term)
                for ref in refs:
                    collected.setdefault(ref.source_id, ref)
                    if len(collected) >= limit:
                        break

        logger.info(
            "wattpad search for %r used %s of %s alias terms, found %s distinct works",
            query.name,
            len(terms),
            len(query.search_terms),
            len(collected),
        )
        return tuple(collected.values())

    def fetch_chapters(
        self, ref: StoryRef, *, max_chapters: int
    ) -> tuple[Chapter, ...]:
        """Return up to `max_chapters` chapters of prose, skipping any that fail to fetch."""
        chapters: list[Chapter] = []
        for chapter_ref in ref.chapter_refs[:max_chapters]:
            text = self._fetch_chapter_text(chapter_ref)
            if text is None:
                continue
            chapters.append(
                Chapter(
                    index=chapter_ref.index,
                    source_id=chapter_ref.source_id,
                    title=chapter_ref.title,
                    text=text,
                )
            )
        return tuple(chapters)

    # --- internals ------------------------------------------------------------------------
    def _search_page(self, term: str, offset: int) -> tuple[list[StoryRef], bool]:
        """Fetch one page of results for `term`, returning its refs and whether more remain."""
        payload = self._get_json(
            _SEARCH_URL,
            {
                "query": f"{term} fanfiction",
                "limit": self._page_size,
                "offset": offset,
            },
        )
        stories = payload.get("stories")
        if not isinstance(stories, list) or not stories:
            return [], False
        refs = [
            ref
            for raw in stories
            if isinstance(raw, dict) and (ref := _parse_story(raw)) is not None
        ]
        return refs, bool(payload.get("nextUrl"))

    def _fetch_chapter_text(self, chapter_ref: ChapterRef) -> str | None:
        """Fetch and clean one chapter's prose, or None if the host refused it."""
        try:
            response = get_with_retry(
                self._client, _STORYTEXT_URL, params={"id": chapter_ref.source_id}
            )
        except SourceUnavailableError:
            # One unavailable chapter must not abort a whole harvest; the run reports counts.
            logger.warning("skipping unavailable chapter %s", chapter_ref.source_id)
            return None
        self._pause()
        return html_to_text(response.text)

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET `url` and decode a JSON object, raising if the payload is not one."""
        response = get_with_retry(self._client, url, params=params)
        self._pause()
        try:
            payload = response.json()
        except ValueError as err:
            raise SourceUnavailableError(
                f"wattpad returned non-JSON from {url}", context={"url": url}
            ) from err
        if not isinstance(payload, dict):
            raise SourceUnavailableError(
                f"wattpad returned {type(payload).__name__}, expected an object",
                context={"url": url},
            )
        return payload

    def _pause(self) -> None:
        if self._request_delay > 0:
            time.sleep(self._request_delay)


def _parse_story(raw: dict[str, Any]) -> StoryRef | None:
    """Map one Wattpad story object onto a `StoryRef`, or None if it is unusable.

    Third-party JSON is untrusted: every field is coerced defensively, and a work missing an id or
    title is dropped rather than guessed at.
    """
    source_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or "").strip()
    if not source_id or not title:
        return None
    if raw.get("deleted"):
        return None

    return StoryRef(
        source=FanficSource.WATTPAD,
        source_id=source_id,
        title=title[:500],
        author=_author_name(raw.get("user")),
        url=str(raw.get("url") or ""),
        description=str(raw.get("description") or ""),
        tags=_string_tuple(raw.get("tags")),
        chapter_refs=_parse_parts(raw.get("parts")),
        num_chapters=_non_negative_int(raw.get("numParts")),
        reads=_non_negative_int(raw.get("readCount")),
        votes=_non_negative_int(raw.get("voteCount")),
        completed=bool(raw.get("completed")),
        mature=bool(raw.get("mature")),
        language=_language_code(raw.get("language")),
    )


def _parse_parts(raw_parts: object) -> tuple[ChapterRef, ...]:
    """Map Wattpad `parts[]` onto ordered chapter handles, skipping drafts."""
    if not isinstance(raw_parts, list):
        return ()
    refs: list[ChapterRef] = []
    for part in raw_parts:
        if not isinstance(part, dict) or part.get("draft"):
            continue
        part_id = str(part.get("id") or "").strip()
        if not part_id:
            continue
        refs.append(
            ChapterRef(
                source_id=part_id,
                index=len(refs) + 1,
                title=str(part.get("title") or "").strip(),
            )
        )
    return tuple(refs)


def _author_name(raw_user: object) -> str:
    """Extract a username from Wattpad's nested user object."""
    if isinstance(raw_user, dict):
        return str(raw_user.get("name") or raw_user.get("fullname") or "")
    return ""


def _language_code(raw_language: object) -> str:
    """Map Wattpad's `{"id": 1, "name": "English"}` onto a two-letter code."""
    if isinstance(raw_language, dict):
        name = str(raw_language.get("name") or "").strip().lower()
        return _LANGUAGE_CODES.get(name, name[:2] if name else "en")
    return "en"


def _string_tuple(raw_value: object) -> tuple[str, ...]:
    """Coerce a JSON list into a tuple of non-empty strings."""
    if not isinstance(raw_value, list):
        return ()
    return tuple(str(item).strip() for item in raw_value if str(item).strip())


def _non_negative_int(raw_value: object) -> int:
    """Coerce a JSON number to a non-negative int, defaulting to 0.

    Narrowed by type rather than by catching a broad coercion failure, so a host that starts sending
    `"readCount": "lots"` degrades to 0 instead of raising.
    """
    if isinstance(raw_value, bool):
        return 0  # JSON true would otherwise coerce to 1 and read as a real count
    if isinstance(raw_value, int):
        return max(0, raw_value)
    if isinstance(raw_value, float):
        return max(0, int(raw_value))
    if isinstance(raw_value, str):
        try:
            return max(0, int(float(raw_value)))
        except ValueError:
            return 0
    return 0

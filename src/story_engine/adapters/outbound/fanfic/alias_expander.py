"""Fandom alias expansion via Wikipedia redirects.

Every redirect a human bothered to create for a title is, by construction, a real alias people use.
Verified 2026-07-25: one unauthenticated call for "Percy Jackson" returns `Perseus Jackson`,
`Percy Jackson (character)`, and crucially the *universe terms* `Anaklusmos` and `Celestial bronze`.
Universe terms are the highest-precision fandom fingerprints — nobody outside the fandom writes
"celestial bronze" — which is why lexical matching beats embeddings for this job.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Any

import httpx

from story_engine.adapters.outbound.fanfic.http_util import build_client, get_with_retry
from story_engine.shared.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

_WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

# Redirects that are disambiguation scaffolding rather than usable aliases.
_PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)\s*$")
_NOISE_SUFFIXES = ("(disambiguation)", "(franchise)", "(series)")
_MIN_ALIAS_LENGTH = 3

# Wikipedia redirects include meta-pages about the work rather than names used inside it. Observed
# live: "List of box office records set by The Avengers", "Anti-Harry Potter community",
# "Harry Potter Criticism", "Abstinence porn". As match terms these cause false positives, and as
# search queries they waste requests, so they are dropped.
_NOISE_PATTERNS = (
    re.compile(
        r"^(?:list|lists|index|outline|timeline|glossary)\s+of\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:criticism|controversy|controversies|reception|legacy)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:box\s*office|merchandise|soundtrack|video\s*game|theme\s*park)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:fandom|community|influence|adaptations?|bibliograph(?:y|ies))\b",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:anti|pro)-", re.IGNORECASE),
    re.compile(
        r"^books?\s+in\b|further\s+reading|^cast\s+of\b|^awards?\b", re.IGNORECASE
    ),
)

# Titles whose plain form is ambiguous resolve to something unrelated: verified live, "Dexter" ->
# "USS Dexter" (a warship), "Titanic" -> the ship, "The Avengers" -> the 1960s British spy series.
# When the bare title yields too little, retry with the qualifiers Wikipedia uses for fiction. The
# ORDER matters, so the caller's `kind` hint picks which family to try first.
_SUFFIXES_BY_KIND: dict[str, tuple[str, ...]] = {
    "movie": ("(film)", "(franchise)", "(film series)", "(TV series)", "(novel)"),
    "novel": (
        "(novel)",
        "(novel series)",
        "(book series)",
        "(book)",
        "(TV series)",
        "(film)",
    ),
    "series": ("(TV series)", "(franchise)", "(novel series)", "(film)"),
}
_DEFAULT_SUFFIXES = (
    "(TV series)",
    "(film)",
    "(novel)",
    "(novel series)",
    "(book series)",
    "(franchise)",
    "(book)",
)
_MIN_USEFUL_ALIASES = 4

# Suffix guessing cannot reach the real articles, because Wikipedia disambiguates films by YEAR:
# "Titanic (1997 film)", "The Avengers (2012 film)". So resolve the article via Wikipedia search
# instead of guessing, and only fall back to suffixes.
_KIND_SEARCH_HINT = {"movie": "film", "novel": "novel", "series": "television series"}
_KIND_TITLE_MARKERS: dict[str, tuple[str, ...]] = {
    "movie": ("film",),
    "novel": ("novel", "book"),
    "series": ("tv series", "television series"),
}
_SEARCH_RESULT_LIMIT = 6

# Above this similarity to the fandom name, an alias is a spelling/format variant ("Hairy potter",
# "Harry Poter") — harmless for matching but worthless as a distinct signal, so it ranks last and
# does not consume a query slot ahead of a real entity like "Miami Metro Police Department".
_VARIANT_SIMILARITY = 0.8


class WikipediaAliasExpander:
    """Expand a fandom title into its alias surface. Implements `AliasExpanderPort`."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or build_client()

    def expand(
        self, fandom: str, *, limit: int = 60, kind: str = "auto"
    ) -> tuple[str, ...]:
        """Return up to `limit` distinct aliases for `fandom`, best signal first.

        Tries the bare title first, then fiction-specific Wikipedia qualifiers if that yields too
        little — a bare ambiguous title can resolve to something unrelated. Returns an empty tuple
        when nothing is reachable; a harvest still runs on the name alone, just with narrower reach.

        Args:
            fandom: The work's title, as a user would type it.
            limit: Maximum aliases to return.
            kind: `movie`, `novel`, `series`, or `auto` — reorders the disambiguation attempts, so
                "Titanic" as a movie is not resolved to the ship.
        """
        best: tuple[str, ...] = ()
        best_title = fandom
        for candidate in self._candidate_titles(fandom, kind=kind):
            aliases = self._expand_one(candidate, fandom=fandom)
            if len(aliases) > len(best):
                best, best_title = aliases, candidate
            if len(best) >= _MIN_USEFUL_ALIASES:
                break

        ranked = _rank_aliases(best, fandom=fandom)
        if best_title != fandom:
            logger.info("disambiguated %r via Wikipedia title %r", fandom, best_title)
        logger.info("expanded %r into %s aliases", fandom, len(ranked))
        return ranked[:limit]

    def _candidate_titles(self, fandom: str, *, kind: str) -> list[str]:
        """Return Wikipedia titles to try, in priority order.

        When the caller states a `kind`, the qualified titles are tried BEFORE the bare one. The
        bare title often has plenty of redirects for the wrong subject — "Titanic" resolves to the
        ship and "The Avengers" to the 1960s spy series — so trying it first would satisfy the
        early-exit and silently ignore the hint.
        """
        if _PARENTHETICAL_RE.search(fandom):
            return [fandom]  # caller already disambiguated; respect it
        suffixes = _SUFFIXES_BY_KIND.get(kind.lower())
        if suffixes is None:
            return [fandom, *(f"{fandom} {s}" for s in _DEFAULT_SUFFIXES)]

        candidates: list[str] = []
        resolved = self._resolve_title(fandom, kind=kind.lower())
        if resolved is not None:
            candidates.append(resolved)
        candidates.extend(f"{fandom} {s}" for s in suffixes)
        candidates.append(fandom)
        return candidates

    def _resolve_title(self, fandom: str, *, kind: str) -> str | None:
        """Resolve `fandom` to a real Wikipedia article title of the requested kind, if findable."""
        hint = _KIND_SEARCH_HINT.get(kind)
        if hint is None:
            return None
        try:
            results = self._search_titles(f"{fandom} {hint}")
        except SourceUnavailableError:
            logger.warning("wikipedia search unavailable for %r", fandom)
            return None

        name = fandom.strip().lower()
        markers = _KIND_TITLE_MARKERS.get(kind, ())
        # Prefer a title that both names the work and is marked as the right medium.
        for title in results:
            lowered = title.lower()
            if lowered.startswith(name) and any(m in lowered for m in markers):
                return title
        for title in results:
            if title.lower().startswith(name):
                return title
        return None

    def _search_titles(self, term: str) -> list[str]:
        """Return Wikipedia article titles matching `term`, best match first."""
        response = get_with_retry(
            self._client,
            _WIKIPEDIA_API,
            params={
                "action": "query",
                "list": "search",
                "srsearch": term,
                "srlimit": _SEARCH_RESULT_LIMIT,
                "format": "json",
                "formatversion": "2",
            },
        )
        try:
            payload = response.json()
        except ValueError as err:
            raise SourceUnavailableError(
                "wikipedia search returned non-JSON", context={"term": term}
            ) from err
        hits = (
            payload.get("query", {}).get("search")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(hits, list):
            return []
        return [
            str(hit["title"])
            for hit in hits
            if isinstance(hit, dict) and hit.get("title")
        ]

    def _expand_one(self, title: str, *, fandom: str) -> tuple[str, ...]:
        """Expand a single Wikipedia title, returning () if it is missing or unreachable."""
        try:
            payload = self._query_redirects(title)
        except SourceUnavailableError:
            logger.warning("alias expansion unavailable for %r", title)
            return ()
        return _clean_aliases(_extract_redirect_titles(payload), fandom=fandom)

    def _query_redirects(self, fandom: str) -> dict[str, Any]:
        """Call the MediaWiki API for every redirect pointing at `fandom`'s page."""
        response = get_with_retry(
            self._client,
            _WIKIPEDIA_API,
            params={
                "action": "query",
                "titles": fandom,
                "prop": "redirects",
                "rdlimit": "max",
                "format": "json",
                "formatversion": "2",
            },
        )
        try:
            payload = response.json()
        except ValueError as err:
            raise SourceUnavailableError(
                "wikipedia returned non-JSON", context={"fandom": fandom}
            ) from err
        if not isinstance(payload, dict):
            raise SourceUnavailableError(
                "wikipedia returned a non-object payload", context={"fandom": fandom}
            )
        return payload


def _extract_redirect_titles(payload: dict[str, Any]) -> list[str]:
    """Pull redirect titles out of a formatversion=2 MediaWiki response."""
    pages = payload.get("query", {}).get("pages")
    if not isinstance(pages, list):
        return []
    titles: list[str] = []
    for page in pages:
        if not isinstance(page, dict) or page.get("missing"):
            continue
        redirects = page.get("redirects")
        if not isinstance(redirects, list):
            continue
        for redirect in redirects:
            if isinstance(redirect, dict):
                title = str(redirect.get("title") or "").strip()
                if title:
                    titles.append(title)
    return titles


def _rank_aliases(aliases: tuple[str, ...], *, fandom: str) -> tuple[str, ...]:
    """Order aliases so distinct entities come before mere variants of the title.

    "Miami Metro Police Department" discriminates between fandoms; "Hairy potter" does not. Both are
    kept for matching, but only the first kind deserves a scarce search-query slot.
    """
    name = fandom.strip().lower()

    def is_variant(alias: str) -> bool:
        lowered = alias.lower()
        if name in lowered or lowered in name:
            return True
        return SequenceMatcher(None, lowered, name).ratio() >= _VARIANT_SIMILARITY

    distinct = [a for a in aliases if not is_variant(a)]
    variants = [a for a in aliases if is_variant(a)]
    return tuple(distinct + variants)


def _clean_aliases(titles: list[str], *, fandom: str) -> tuple[str, ...]:
    """Drop meta-pages, disambiguation scaffolding, and duplicates, preserving discovery order.

    Deduplication is case-insensitive so "Celestial bronze" and "Celestial Bronze" do not both
    occupy a query slot, since matching is case-insensitive anyway.
    """
    fandom_lower = fandom.strip().lower()
    kept: dict[str, str] = {}
    for title in titles:
        lowered = title.lower()
        if any(suffix in lowered for suffix in _NOISE_SUFFIXES):
            continue
        if any(pattern.search(title) for pattern in _NOISE_PATTERNS):
            continue
        # "Percy Jackson (character)" adds nothing over the bare name it disambiguates.
        bare = _PARENTHETICAL_RE.sub("", title).strip()
        if len(bare) < _MIN_ALIAS_LENGTH or bare.lower() == fandom_lower:
            continue
        kept.setdefault(bare.lower(), bare)
    return tuple(kept.values())

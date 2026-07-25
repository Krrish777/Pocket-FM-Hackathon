"""Fandom.com wiki source adapter — reads an entity vocabulary out of a fan wiki.

Verified live 2026-07-25 against `https://dexter.fandom.com/api.php` (no auth, MediaWiki API):

* `?action=query&meta=siteinfo&siprop=general` confirms a subdomain exists; a wrong guess is a clean
  404 (`zzzznotarealfandomxyz.fandom.com`), which is why resolution can degrade instead of crashing.
* `?generator=categorymembers&gcmtitle=Category:Characters&prop=info` returns 500 titles *plus each
  page's byte `length`* in one request — the prominence signal that ranks leads above walk-ons
  (Dexter Morgan 153583 bytes vs "Acupuncturist"). `Category:Characters` had 2458 members.
* **`prop=extracts` is NOT installed on Fandom.** Page text must come from `action=parse` (HTML) or
  `prop=revisions&rvprop=content` (wikitext). This adapter reads wikitext — see `wikitext.py`.
* Category names differ per wiki (`Category:Characters` has members, `Category:Character` has zero),
  so every candidate is probed and the empties are skipped.

**What this adapter is for.** Not canon truth — `project_context.md` §6.1 puts canon in the *novels*
and §6.4 records that a screen-based scrape is a silent corruption path. It produces (a) a name
vocabulary for recognizing entities in fan-fiction text and (b) a per-entity novel-vs-screen label
(`canon_basis.py`) so screen-only references can be flagged, which is §11 OD-2's blocker.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from story_engine.adapters.outbound.fanfic.http_util import build_client, get_with_retry
from story_engine.adapters.outbound.wiki import canon_basis, wikitext
from story_engine.domain.models.wiki_index import (
    WikiAttribute,
    WikiCanonBasis,
    WikiEntity,
    WikiEntityKind,
    WikiLifeStatus,
    WikiPageRef,
    WikiRelationship,
    WikiSourcePage,
)
from story_engine.shared.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

SOURCE_NAME = "fandom_wiki"

# Probed in order per kind; the first non-empty ones are all used. Novel-marked categories are listed
# because they are the scarce half of the discriminator — see `_is_protected_category`.
CATEGORY_CANDIDATES: dict[WikiEntityKind, tuple[str, ...]] = {
    WikiEntityKind.CHARACTER: (
        "Characters",
        "Characters (Novels)",
        "Character",
        "Main Characters",
        "People",
    ),
    WikiEntityKind.LOCATION: (
        "Locations",
        "Locations (Novels)",
        "Places",
        "Location",
    ),
    WikiEntityKind.EVENT: ("Episodes", "Events", "Chapters"),
    WikiEntityKind.ORGANIZATION: (
        "Organizations",
        "Organisations",
        "Groups",
        "Factions",
    ),
}

# Categories whose *members* name the source work's books, used to recognize per-book categories
# ("Darkly Dreaming Dexter characters") without hardcoding any book title.
NOVEL_WORK_CATEGORIES = ("Category:Novels", "Category:Books")

_MAIN_NAMESPACE = 0
_CATEGORY_PAGE_LIMIT = 500
_MAX_DISCOVERY_PAGES = 6  # bounds one category at ~3000 members
_CONTENT_BATCH_SIZE = 20  # keeps `categories` continuation rounds low per request
_MAX_CONTINUATIONS = 12
_MAX_ATTRIBUTES = 40
_DEFAULT_SUMMARY_CHARS = 1500


class FandomWikiSource:
    """Read an entity vocabulary from a Fandom wiki. Implements `WikiSourcePort`."""

    source_name: str = SOURCE_NAME

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        request_delay: float = 0.3,
        subdomain_overrides: dict[str, str] | None = None,
        summary_chars: int = _DEFAULT_SUMMARY_CHARS,
    ) -> None:
        """Initialize the adapter.

        Args:
            client: HTTP client to reuse; one is built if omitted.
            request_delay: Seconds paused between requests, to stay a polite client.
            subdomain_overrides: Fandom name -> wiki subdomain, for the common case where the
                obvious guess is wrong. Verified live: "Percy Jackson" lives on `riordan`, which no
                slug rule reaches, so an override is the honest fix rather than a cleverer guesser.
            summary_chars: Characters of lead prose kept per entity. Summaries are for recognition,
                not reading, so they are capped to keep the artifact small.
        """
        self._client = client or build_client()
        self._request_delay = request_delay
        self._overrides = {
            key.strip().lower(): value
            for key, value in (subdomain_overrides or {}).items()
        }
        self._summary_chars = summary_chars
        self._resolved: dict[str, str | None] = {}
        self._basis_rules: dict[str, canon_basis.BasisRules] = {}

    # --- port surface ---------------------------------------------------------------------
    def resolve(self, fandom: str) -> str | None:
        """Return the wiki base URL for `fandom`, or None if no candidate subdomain answers."""
        key = fandom.strip().lower()
        if key in self._resolved:
            return self._resolved[key]
        resolved: str | None = None
        for subdomain in self._candidate_subdomains(fandom):
            resolved = self._probe_subdomain(subdomain)
            if resolved is not None:
                break
        if resolved is None:
            logger.warning(
                "no Fandom wiki found for %r; pass subdomain_overrides to point at the right one",
                fandom,
            )
        else:
            logger.info("resolved fandom %r to %s", fandom, resolved)
        self._resolved[key] = resolved
        return resolved

    def discover(
        self,
        fandom: str,
        *,
        kinds: tuple[WikiEntityKind, ...],
        limit_per_kind: int,
    ) -> tuple[WikiPageRef, ...]:
        """Return candidate pages for each kind, most prominent first.

        Pages from a novel-marked category bypass the prominence cap: they are typically short stubs
        that a byte-length ranking would drop, yet they are the entire novel half of the OD-2
        discriminator. Losing them would silently reduce the index to screen canon.
        """
        wiki_url = self.resolve(fandom)
        if wiki_url is None:
            return ()

        collected: dict[str, WikiPageRef] = {}
        for kind in kinds:
            protected: list[WikiPageRef] = []
            ranked: list[WikiPageRef] = []
            for category in CATEGORY_CANDIDATES.get(kind, ()):
                refs = self._category_members(wiki_url, category, kind)
                if not refs:
                    logger.debug("category %r empty on %s", category, wiki_url)
                    continue
                logger.info("category %r yielded %s pages", category, len(refs))
                target = protected if _is_protected_category(category) else ranked
                target.extend(refs)
            ranked.sort(key=lambda ref: -ref.prominence)
            for ref in (*protected, *ranked[:limit_per_kind]):
                collected.setdefault(ref.title, ref)
        return tuple(collected.values())

    def fetch_entities(
        self, fandom: str, refs: tuple[WikiPageRef, ...]
    ) -> tuple[WikiEntity, ...]:
        """Read `refs` into typed entities, skipping pages that yield nothing usable."""
        wiki_url = self.resolve(fandom)
        if wiki_url is None or not refs:
            return ()
        rules = self._novel_basis_rules(wiki_url)
        # The work's own title is bolded in most leads ("...of Showtime's '''DEXTER'''"), and as an
        # alias it would match every fan-fiction blurb about the fandom. Excluded by name.
        work_titles = frozenset({fandom.strip().lower(), *rules.novel_work_titles})
        by_title = {ref.title: ref for ref in refs}

        entities: list[WikiEntity] = []
        for batch in _batched(list(by_title), _CONTENT_BATCH_SIZE):
            for page in self._fetch_pages(wiki_url, batch):
                ref = by_title.get(str(page.get("title") or ""))
                if ref is None:
                    continue
                entity = self._to_entity(
                    page, ref, wiki_url=wiki_url, rules=rules, work_titles=work_titles
                )
                if entity is not None:
                    entities.append(entity)
        return tuple(entities)

    # --- resolution ----------------------------------------------------------------------
    def _candidate_subdomains(self, fandom: str) -> tuple[str, ...]:
        """Return subdomains to try for `fandom`, best guess first."""
        override = self._overrides.get(fandom.strip().lower())
        if override:
            return (override,)
        words = [
            w
            for w in "".join(
                char if char.isalnum() or char.isspace() else " "
                for char in fandom.lower()
            ).split()
            if w
        ]
        if not words:
            return ()
        compact = "".join(words)
        candidates = [compact, "-".join(words)]
        if words[0] in {"the", "a", "an"} and len(words) > 1:
            candidates.extend(("".join(words[1:]), "-".join(words[1:])))
        return tuple(dict.fromkeys(candidates))

    def _probe_subdomain(self, subdomain: str) -> str | None:
        """Return the wiki base URL if `subdomain` hosts a MediaWiki API, else None."""
        api = f"https://{subdomain}.fandom.com/api.php"
        try:
            payload = self._get_json(api, {"meta": "siteinfo", "siprop": "general"})
        except SourceUnavailableError:
            # A wrong subdomain 404s. That is a normal outcome of guessing, not a failure to report.
            logger.debug("subdomain %r did not answer", subdomain)
            return None
        general = payload.get("query", {}).get("general")
        if not isinstance(general, dict):
            return None
        server = str(general.get("server") or f"https://{subdomain}.fandom.com")
        logger.debug("subdomain %r is %r", subdomain, general.get("sitename"))
        return server

    def _novel_basis_rules(self, wiki_url: str) -> canon_basis.BasisRules:
        """Build (and memoize) the basis vocabulary for a wiki from its own book categories."""
        if wiki_url in self._basis_rules:
            return self._basis_rules[wiki_url]
        titles: set[str] = set()
        for category in NOVEL_WORK_CATEGORIES:
            for member in self._raw_category_members(wiki_url, category):
                if member.get("ns") == _MAIN_NAMESPACE:
                    title = str(member.get("title") or "").strip().lower()
                    if title:
                        titles.add(title)
        rules = canon_basis.BasisRules(novel_work_titles=frozenset(titles))
        logger.info(
            "discovered %s book titles for basis rules on %s", len(titles), wiki_url
        )
        self._basis_rules[wiki_url] = rules
        return rules

    # --- discovery -----------------------------------------------------------------------
    def _category_members(
        self, wiki_url: str, category: str, kind: WikiEntityKind
    ) -> list[WikiPageRef]:
        """List article pages in `Category:<category>` with their byte length as prominence."""
        refs: list[WikiPageRef] = []
        params: dict[str, Any] = {
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmlimit": _CATEGORY_PAGE_LIMIT,
            "gcmnamespace": _MAIN_NAMESPACE,
            "prop": "info",
        }
        api = _api_url(wiki_url)
        for _ in range(_MAX_DISCOVERY_PAGES):
            payload = self._get_json(api, params)
            for page in _pages_of(payload):
                title = str(page.get("title") or "").strip()
                if not title or not _is_entity_title(title, category):
                    continue
                refs.append(
                    WikiPageRef(
                        title=title,
                        kind=kind,
                        page_id=str(page.get("pageid") or ""),
                        page_url=_page_url(wiki_url, title),
                        prominence=max(0, int(page.get("length") or 0)),
                    )
                )
            cursor = payload.get("continue")
            if not isinstance(cursor, dict):
                break
            params = {**params, **cursor}
        return refs

    def _raw_category_members(
        self, wiki_url: str, category: str
    ) -> list[dict[str, Any]]:
        """Return raw `categorymembers` rows for `category`, including subcategories."""
        payload = self._get_json(
            _api_url(wiki_url),
            {
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": _CATEGORY_PAGE_LIMIT,
            },
        )
        members = payload.get("query", {}).get("categorymembers")
        return (
            [row for row in members if isinstance(row, dict)]
            if isinstance(members, list)
            else []
        )

    # --- content -------------------------------------------------------------------------
    def _fetch_pages(self, wiki_url: str, titles: list[str]) -> list[dict[str, Any]]:
        """Fetch wikitext and categories for a batch of titles, following API continuation.

        Categories are paginated independently of revisions, so continuation rounds are merged rather
        than truncated: a partial category list would misclassify a page's canon basis, which is the
        one error this adapter exists to prevent.
        """
        merged: dict[str, dict[str, Any]] = {}
        params: dict[str, Any] = {
            "titles": "|".join(titles),
            "prop": "revisions|categories",
            "rvprop": "content",
            "rvslots": "main",
            "cllimit": "max",
            "clshow": "!hidden",
        }
        api = _api_url(wiki_url)
        for _ in range(_MAX_CONTINUATIONS):
            payload = self._get_json(api, params)
            for page in _pages_of(payload):
                title = str(page.get("title") or "")
                if not title:
                    continue
                target = merged.setdefault(title, {"title": title, "categories": []})
                if "revisions" in page:
                    target["revisions"] = page["revisions"]
                if "pageid" in page:
                    target["pageid"] = page["pageid"]
                categories = page.get("categories")
                if isinstance(categories, list):
                    existing = target["categories"]
                    if isinstance(existing, list):
                        existing.extend(c for c in categories if isinstance(c, dict))
            cursor = payload.get("continue")
            if not isinstance(cursor, dict):
                break
            params = {**params, **cursor}
        return list(merged.values())

    def _to_entity(
        self,
        page: dict[str, Any],
        ref: WikiPageRef,
        *,
        wiki_url: str,
        rules: canon_basis.BasisRules,
        work_titles: frozenset[str] = frozenset(),
    ) -> WikiEntity | None:
        """Map one page's wikitext and categories onto a `WikiEntity`, or None if it is empty."""
        markup = _revision_content(page)
        if not markup:
            logger.debug("no wikitext for %r", ref.title)
            return None

        title = str(page.get("title") or ref.title)
        categories = tuple(
            str(row.get("title") or "")
            for row in page.get("categories", [])
            if isinstance(row, dict)
        )
        basis, evidence = canon_basis.classify(title, categories, rules)
        page_url = ref.page_url or _page_url(wiki_url, title)

        lead = wikitext.lead_wikitext(markup)
        summary = _truncate(wikitext.strip_markup(lead), self._summary_chars)
        profile = wikitext.select_profile_template(
            wikitext.parse_templates(wikitext.preprocess(markup))
        )
        params = profile.params if profile is not None else {}

        aliases = _collect_aliases(
            params,
            lead=lead,
            canonical=canon_basis.canonical_name(title),
            work_titles=work_titles,
        )
        relationships = _collect_relationships(params, basis=basis, source_url=page_url)
        attributes = _collect_attributes(params, basis=basis, source_url=page_url)
        if not _is_entity_page(
            canon_basis.canonical_name(title),
            profile=profile,
            lead=lead,
            relationships=relationships,
        ):
            logger.debug("page %r reads as an index page, not an entity", title)
            return None

        return WikiEntity(
            canonical_name=canon_basis.canonical_name(title),
            kind=ref.kind,
            canon_basis=basis,
            aliases=aliases,
            summary=summary,
            life_status=_life_status(params),
            relationships=relationships,
            attributes=attributes,
            sources=(
                WikiSourcePage(
                    source_name=SOURCE_NAME,
                    wiki_url=wiki_url,
                    page_title=title,
                    page_id=str(page.get("pageid") or ref.page_id),
                    page_url=page_url,
                    canon_basis=basis,
                    basis_evidence=evidence,
                    retrieved_at=_now(),
                ),
            ),
            prominence=ref.prominence,
        )

    # --- transport -----------------------------------------------------------------------
    def _get_json(self, api: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET a MediaWiki API query and decode the JSON object, raising if it is not one."""
        response = get_with_retry(
            self._client,
            api,
            params={
                "action": "query",
                "format": "json",
                "formatversion": "2",
                **params,
            },
        )
        self._pause()
        try:
            payload = response.json()
        except ValueError as err:
            raise SourceUnavailableError(
                f"{api} returned non-JSON", context={"api": api}
            ) from err
        if not isinstance(payload, dict):
            raise SourceUnavailableError(
                f"{api} returned {type(payload).__name__}, expected an object",
                context={"api": api},
            )
        error = payload.get("error")
        if isinstance(error, dict):
            raise SourceUnavailableError(
                f"{api} rejected the query: {error.get('code')}",
                context={"api": api, "code": str(error.get("code"))},
            )
        return payload

    def _pause(self) -> None:
        if self._request_delay > 0:
            time.sleep(self._request_delay)


# --- module helpers -----------------------------------------------------------------------
def _now() -> datetime:
    """Return the current UTC time — wrapped so provenance timestamps are patchable in tests."""
    return datetime.now(UTC)


def _api_url(wiki_url: str) -> str:
    """Return the MediaWiki API endpoint for a wiki base URL."""
    return f"{wiki_url.rstrip('/')}/api.php"


def _page_url(wiki_url: str, title: str) -> str:
    """Return the human-readable article URL for a page title."""
    return f"{wiki_url.rstrip('/')}/wiki/{quote(title.replace(' ', '_'), safe='/:()')}"


def _pages_of(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the `query.pages` rows of a formatversion=2 response, dropping missing pages."""
    pages = payload.get("query", {}).get("pages")
    if not isinstance(pages, list):
        return []
    return [row for row in pages if isinstance(row, dict) and not row.get("missing")]


def _revision_content(page: dict[str, Any]) -> str:
    """Extract the main-slot wikitext of a page's latest revision, or "" if absent."""
    revisions = page.get("revisions")
    if not isinstance(revisions, list) or not revisions:
        return ""
    first = revisions[0]
    if not isinstance(first, dict):
        return ""
    main = (
        first.get("slots", {}).get("main")
        if isinstance(first.get("slots"), dict)
        else None
    )
    if isinstance(main, dict):
        return str(main.get("content") or "")
    return str(first.get("content") or "")


def _is_protected_category(category: str) -> bool:
    """Return True for a category whose members must survive the prominence cap."""
    return any(
        pattern.search(category) for pattern in canon_basis.DEFAULT_NOVEL_PATTERNS
    )


def _is_entity_title(title: str, category: str) -> bool:
    """Reject subpages, index pages, and the category's own list page."""
    if "/" in title:
        return False  # "Dexter Morgan/Season 1" is a sub-article, not a distinct entity
    lowered = title.lower()
    if lowered.startswith(("list of", "index of", "category:", "gallery of")):
        return False
    return lowered != category.strip().lower()


def _is_entity_page(
    canonical: str,
    *,
    profile: wikitext.WikiTemplate | None,
    lead: str,
    relationships: tuple[WikiRelationship, ...],
) -> bool:
    """Return True when a page describes an entity rather than indexing several.

    `Category:Characters` on the live wiki contains stats and index pages — "Total Deaths",
    "Hallucination Characters" — which would otherwise enter the vocabulary as people and then match
    fan-fiction text. Three positive signals, any one of which is enough:

    * a profile infobox, or
    * links to other entities from relationship fields, or
    * its own name bolded in the lead, which is how an article introduces its subject and how a thin
      stub still proves it *has* a subject. An index page opens "This page lists...".
    """
    if profile is not None or relationships:
        return True
    needle = canonical.strip().lower()
    return any(term.lower() == needle for term in wikitext.lead_aliases(lead))


def _collect_aliases(
    params: dict[str, str],
    *,
    lead: str,
    canonical: str,
    work_titles: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    """Union alias-bearing infobox fields with the names bolded in the lead's opening paragraph.

    Both sources are needed: verified live, "Rita Bennett" is neither the page title nor a redirect of
    `Rita Morgan` — it appears only in the `full name` parameter and bolded in the lead.

    `work_titles` are excluded because an alias that names the *work* matches every blurb about the
    fandom, which silently turns entity recognition into a keyword match on the franchise.
    """
    excluded = canonical.strip().lower()
    seen: dict[str, str] = {}
    for field, value in params.items():
        if field in wikitext.ALIAS_FIELDS:
            for alias in wikitext.parse_aliases(value):
                seen.setdefault(alias.lower(), alias)
    for alias in wikitext.lead_aliases(lead):
        seen.setdefault(alias.lower(), alias)
    seen.pop(excluded, None)
    for title in work_titles:
        seen.pop(title, None)
    return tuple(seen.values())


def _collect_relationships(
    params: dict[str, str], *, basis: WikiCanonBasis, source_url: str
) -> tuple[WikiRelationship, ...]:
    """Turn relationship-bearing infobox fields into stamped, deduplicated relationships."""
    seen: dict[tuple[str, str], WikiRelationship] = {}
    for field, value in params.items():
        default_kind = wikitext.RELATIONSHIP_FIELDS.get(field)
        if default_kind is None or wikitext.is_null_value(wikitext.clean_value(value)):
            continue
        for target, kind in wikitext.parse_entity_links(value):
            resolved = kind or default_kind
            key = (target.lower(), resolved.lower())
            seen.setdefault(
                key,
                WikiRelationship(
                    target=target,
                    kind=resolved,
                    field=field,
                    canon_basis=basis,
                    source_url=source_url,
                ),
            )
    return tuple(seen.values())


def _collect_attributes(
    params: dict[str, str], *, basis: WikiCanonBasis, source_url: str
) -> tuple[WikiAttribute, ...]:
    """Turn the remaining infobox fields into stamped attributes.

    A drop-list of presentational fields is used rather than an allow-list of interesting ones: the
    interesting set differs per wiki (`wand`, `patronus`, `killerstatus`), while "this parameter is
    styling" generalizes.
    """
    attributes: list[WikiAttribute] = []
    for field, raw in params.items():
        if len(attributes) >= _MAX_ATTRIBUTES:
            break
        if (
            field in wikitext.PRESENTATIONAL_FIELDS
            or field in wikitext.RELATIONSHIP_FIELDS
            or field in wikitext.ALIAS_FIELDS
        ):
            continue
        value = wikitext.clean_value(raw)
        if not value or wikitext.is_null_value(value):
            continue
        attributes.append(
            WikiAttribute(
                predicate=field[:80],
                value=value,
                canon_basis=basis,
                source_url=source_url,
            )
        )
    return tuple(attributes)


def _life_status(params: dict[str, str]) -> WikiLifeStatus:
    """Read alive/deceased off the profile's status field, defaulting to unknown."""
    for field in wikitext.STATUS_FIELDS:
        value = wikitext.clean_value(params.get(field, "")).lower()
        if not value:
            continue
        if "deceased" in value or "dead" in value or "killed" in value:
            return WikiLifeStatus.DECEASED
        if "alive" in value or "living" in value:
            return WikiLifeStatus.ALIVE
    return WikiLifeStatus.UNKNOWN


def _truncate(text: str, limit: int) -> str:
    """Cut `text` to `limit` characters on a word boundary."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = head.rfind(" ")
    return (head[:cut] if cut > limit // 2 else head).rstrip() + "…"


def _batched(items: list[str], size: int) -> list[list[str]]:
    """Split `items` into consecutive chunks of at most `size`."""
    return [items[start : start + size] for start in range(0, len(items), size)]
